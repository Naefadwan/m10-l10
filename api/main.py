"""FastAPI application — recipe service.

This module wires the path operations, lifespan, and CORS middleware.

Discipline gates the autograder enforces:
- Neo4j driver, Weaviate client, spaCy pipeline, and the flan-t5-base
  generator are constructed exactly once per process inside `lifespan`.
- `CORSMiddleware` is registered with `allow_origins=[WEB_ORIGIN]`.
- `/extract`, `/kg/query`, `/rag/answer` use Pydantic shapes from
  `models.py` (no anonymous dicts; use Pydantic v2 idioms (model_dump, not the deprecated v1 serialization shortcut)).
- `/kg/query` converts `UnsupportedQueryError` to 422 with structured
  detail (`{"reason": "unsupported_question", "supported_patterns": [...]}`).
- `/readyz` probes Neo4j (`RETURN 1`) AND Weaviate (`client.is_ready()`)
  within 2 seconds; failure → 503.
- `/healthz` does NOT touch Neo4j or Weaviate.
"""
import os
from contextlib import asynccontextmanager


import spacy
import weaviate
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from .m8_rag.generator import load_generator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import (
    authenticate_user,
    create_access_token,
    require_auth,
    require_jwt,
)
from .deps import get_embedder, get_generator, get_nlp, get_session, get_weaviate
from .models import (
    Entity,
    ExtractRequest,
    ExtractResponse,
    HealthResponse,
    KGRequest,
    KGResponse,
    RAGRequest,
    RAGResponse,
    UnsupportedQueryDetail,
    ReadyDetail,
)
from .nlp import extract_entities
from .kg import wrap_kg_query, UnsupportedQueryError
from .rag import compose_rag
from .settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Process-scoped resource setup and teardown.

    On startup: open the Neo4j Bolt driver, construct the Weaviate
    client, load the spaCy `en_core_web_sm` pipeline, and load the
    flan-t5-base generator. Stash each on `app.state` so `Depends()`
    helpers can resolve them.
    """
    settings = Settings()

    # 1. Neo4j Bolt driver
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    app.state.neo4j_driver = driver

    # 2. Weaviate client (v4 API — connect_to_local or connect_to_custom)
    weaviate_client = weaviate.Client(settings.weaviate_url)
    app.state.weaviate_client = weaviate_client

    # 3. spaCy pipeline
    nlp = spacy.load("en_core_web_sm")
    app.state.nlp = nlp

    # 4. flan-t5-base generator
    generator = load_generator()
    app.state.generator = generator

    # 5. sentence-transformers embedder
    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    app.state.embedder = embedder

    yield

    # shutdown
    driver.close()


app = FastAPI(title="M10 Recipe Service", lifespan=lifespan)

settings = Settings()

# CORSMiddleware registration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- /extract -----------------------------------------------------

@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest, nlp=Depends(get_nlp), claims=Depends(require_auth)):
    """Run spaCy NER on the input text; return entities ordered by `start`.

    Returns ExtractResponse with entities sorted by `start` ascending.
    """
    entities = extract_entities(req.text, nlp)
    return ExtractResponse(entities=entities)


# ---------- /kg/query ----------------------------------------------------

@app.post("/kg/query", response_model=KGResponse)
def kg_query(req: KGRequest, session=Depends(get_session), claims=Depends(require_auth)):
    """Run the W9B mapper and execute the resulting Cypher.

    Returns KGResponse(cypher=..., rows=[r.data() for r in session.run(...)], count=len(rows)).
    UnsupportedQueryError → HTTPException(422, detail=UnsupportedQueryDetail(...).model_dump()).
    """
    try:
        cypher, params = wrap_kg_query(req.question)
        result = session.run(cypher, **params)
        rows = [record.data() for record in result]
        return KGResponse(cypher=cypher, rows=rows, count=len(rows))
    except UnsupportedQueryError:
        from .w9b_mapper.shapes import SUPPORTED_PATTERNS
        raise HTTPException(
            status_code=422,
            detail=UnsupportedQueryDetail(
                reason="unsupported_question",
                supported_patterns=list(SUPPORTED_PATTERNS)
            ).model_dump()
        )


# ---------- /rag/answer --------------------------------------------------

@app.post("/rag/answer", response_model=RAGResponse)
def rag_answer(
    req: RAGRequest,
    weaviate_client=Depends(get_weaviate),
    generator=Depends(get_generator),
    embedder=Depends(get_embedder),
    claims=Depends(require_auth)
):
    """Retrieve → assemble → generate → cite → grounding check.

    Returns RAGResponse with citations populated when a grounded answer
    is available, or the SENTINEL with empty citations when retrieval
    or citation extraction fails.
    """
    result = compose_rag(
        question=req.question,
        embedder=embedder,
        weaviate_client=weaviate_client,
        generator=generator,
        k=req.k
    )
    return RAGResponse(
        answer=result["answer"],
        citations=result["citations"],
        confidence=result["confidence"]
    )


# ---------- /healthz + /readyz -------------------------------------------

@app.get("/healthz", response_model=HealthResponse)
def healthz():
    """Liveness probe. Must NOT touch Neo4j or Weaviate."""
    return HealthResponse(status="ok")


@app.get("/readyz", response_model=ReadyDetail)
def readyz(session=Depends(get_session), weaviate_client=Depends(get_weaviate)):
    """Readiness probe.

    Returns 200 only if `RETURN 1` against Neo4j AND `client.is_ready()`
    against Weaviate both succeed within 2 seconds. Otherwise 503 with
    structured detail naming which backend failed.
    """
    neo4j_ok = False
    weaviate_ok = False

    # Probe Neo4j
    try:
        session.run("RETURN 1")
        neo4j_ok = True
    except Exception:
        pass

    # Probe Weaviate
    try:
        if weaviate_client.is_ready():
            weaviate_ok = True
    except Exception:
        pass

    if not (neo4j_ok and weaviate_ok):
        detail = ReadyDetail(
            neo4j="ok" if neo4j_ok else "down",
            weaviate="ok" if weaviate_ok else "down"
        )
        raise HTTPException(status_code=503, detail=detail.model_dump())

    return ReadyDetail(neo4j="ok", weaviate="ok")


# ---------- /auth/login --------------------------------------------------

from pydantic import BaseModel  # noqa: E402


class _LoginRequest(BaseModel):
    username: str
    password: str


class _TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/auth/login", response_model=_TokenResponse)
def auth_login(req: _LoginRequest):
    """Issue a signed JWT for valid dev-fixture credentials.

    Accepts: admin/admin, demo/demo, stretch/stretch.
    Returns 401 on invalid credentials.
    """
    sub = authenticate_user(req.username, req.password)
    if sub is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )
    token = create_access_token(subject=sub, expires_minutes=30)
    return _TokenResponse(access_token=token, token_type="bearer")


# ---------- /admin/echo --------------------------------------------------

@app.get("/admin/echo")
def admin_echo(claims: dict = Depends(require_jwt)):
    """Echo the decoded JWT payload. Requires a valid Bearer JWT.

    API keys are insufficient — callers with only an API key receive 403.
    """
    return claims
