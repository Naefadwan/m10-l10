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

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Process-scoped resource setup and teardown.

    On startup: open the Neo4j Bolt driver, construct the Weaviate
    client, load the spaCy `en_core_web_sm` pipeline, and load the
    flan-t5-base generator. Stash each on `app.state` so `Depends()`
    helpers can resolve them.
    """
    # TODO: construct the five resources once and stash each on
    #       `app.state` (see deps.py for the attribute names the
    #       autograder pins):
    #         - Neo4j Bolt driver — read the URI + credentials from
    #           os.environ.
    #         - Weaviate client — read WEAVIATE_URL from os.environ.
    #         - spaCy pipeline — the `en_core_web_sm` model installed by
    #           the Lab Dockerfile.
    #         - flan-t5-base generator — load via the vendored helper in
    #           `.m8_rag` (do NOT modify the m8_rag package).
    #         - sentence-transformers embedder — load the same model
    #           the seed used (`sentence-transformers/all-MiniLM-L6-v2`).
    #           Required for the query-side embedding `/rag/answer`
    #           needs to do, since the Weaviate class is
    #           `vectorizer=none`.
    # Then `yield` (so request handling can proceed), and on shutdown
    # close the Neo4j driver.
    yield


app = FastAPI(title="M10 Recipe Service", lifespan=lifespan)

# TODO: register CORSMiddleware so the Next.js frontend can call the
#       API from the browser. Allow the origin set by the WEB_ORIGIN
#       env var (with a sensible localhost default for `npm run dev`).
#       See the Reading's CORS section for the middleware arguments.


@app.post("/extract")
def extract(req, nlp=Depends(get_nlp)):
    """Run spaCy NER on the input text; return entities ordered by `start`.

    Returns ExtractResponse with entities sorted by `start` ascending.
    """
    # TODO: type-annotate the request body, wire response_model on the
    #       decorator, run NER via the helper in nlp.py, and return the
    #       typed response.
    raise NotImplementedError


@app.post("/kg/query")
def kg_query(req, session=Depends(get_session)):
    """Run the W9B mapper and execute the resulting Cypher.

    Returns KGResponse(cypher=..., rows=[r.data() for r in session.run(...)], count=len(rows)).
    UnsupportedQueryError → HTTPException(422, detail=UnsupportedQueryDetail(...).model_dump()).
    """
    # TODO: type-annotate the request body, wire response_model on the
    #       decorator, run the W9B mapper via the helper in kg.py,
    #       execute the cypher in a Neo4j session, materialize the rows,
    #       and return the typed response. Convert UnsupportedQueryError
    #       to a structured 422.
    raise NotImplementedError


@app.post("/rag/answer")
def rag_answer(req, weaviate_client=Depends(get_weaviate), generator=Depends(get_generator), embedder=Depends(get_embedder)):
    """Retrieve → assemble → generate → cite → grounding check.

    Returns RAGResponse with citations populated when a grounded answer
    is available, or the SENTINEL with empty citations when retrieval
    or citation extraction fails.
    """
    # TODO: type-annotate the request body, wire response_model on the
    #       decorator, run the RAG composition via the helper in rag.py
    #       (passing the injected weaviate client and generator), and
    #       return the typed response.
    raise NotImplementedError


@app.get("/healthz")
def healthz():
    """Liveness probe. Must NOT touch Neo4j or Weaviate."""
    # TODO: wire response_model on the decorator and return the typed
    #       liveness response.
    raise NotImplementedError


@app.get("/readyz")
def readyz(session=Depends(get_session), weaviate_client=Depends(get_weaviate)):
    """Readiness probe.

    Returns 200 only if `RETURN 1` against Neo4j AND `client.is_ready()`
    against Weaviate both succeed within 2 seconds. Otherwise 503 with
    structured detail naming which backend failed.
    """
    # TODO: probe both backends within the 2-second budget, populate
    #       the readiness detail, and raise an HTTP error with the
    #       readiness detail if either probe fails.
    raise NotImplementedError
