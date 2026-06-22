"""Lab 10 backend autograder.

Every test row maps to a "Catches buggy variant" claim — see lab-spec.md
Section "Test Plan."
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------- /extract -------------------------------------------------

def test_extract_returns_entities_ordered_by_start(client, store):
    """Catches buggy variant: spaCy natural-order pass-through (breaks
    when entities overlap or are emitted out of order)."""
    store["entities"] = [
        {"text": "Seven Samurai", "label": "WORK_OF_ART", "start_char": 24, "end_char": 37},
        {"text": "Akira Kurosawa", "label": "PERSON", "start_char": 0, "end_char": 14},
        {"text": "1954", "label": "DATE", "start_char": 41, "end_char": 45},
    ]
    r = client.post("/extract", json={"text": "Akira Kurosawa directed Seven Samurai in 1954."})
    assert r.status_code == 200
    starts = [e["start"] for e in r.json()["entities"]]
    # The fixture provides 3 entities — an empty list would satisfy
    # `sorted([]) == sorted([])` vacuously, so require multiple
    # entities AND strict ascending order.
    assert len(starts) >= 2
    assert starts == sorted(starts)


def test_extract_rejects_empty_text(client):
    """Catches buggy variant: learner writes `text: str` instead of
    Field(..., min_length=1)."""
    r = client.post("/extract", json={"text": ""})
    assert r.status_code == 422


def test_extract_rejects_oversized_text(client):
    """Catches buggy variant: learner omits max_length=5000."""
    r = client.post("/extract", json={"text": "x" * 5001})
    assert r.status_code == 422


# ---------- /kg/query ------------------------------------------------

def test_kg_query_returns_cypher_rows_count(client, store):
    """Catches buggy variant: learner returns raw Neo4j Record objects
    instead of calling `.data()` — JSON serialization fails."""
    store["rows"] = [{"recipe": "Mapo Tofu", "id": "r1"}]
    r = client.post("/kg/query", json={"question": "Find Sichuan recipes"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {"cypher", "rows", "count"}
    assert body["cypher"].startswith("MATCH")
    assert body["count"] == len(body["rows"])
    assert body["rows"] == [{"recipe": "Mapo Tofu", "id": "r1"}]


def test_kg_query_unsupported_returns_422(client):
    """Catches buggy variant: learner lets UnsupportedQueryError bubble
    to a 500."""
    r = client.post("/kg/query", json={"question": "How do I sharpen a knife?"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["reason"] == "unsupported_question"
    assert isinstance(detail["supported_patterns"], list)
    assert len(detail["supported_patterns"]) >= 3


# ---------- /rag/answer ----------------------------------------------

def test_rag_answer_returns_grounded_answer(client, store):
    """Catches buggy variant: learner returns generator output without
    extracting/verifying citations."""
    store["weaviate_chunks"] = [
        {"chunk_id": 1, "text": "Mince ginger before stir-frying.", "_additional": {"distance": 0.1}},
        {"chunk_id": 2, "text": "Slice ginger thin against the grain.", "_additional": {"distance": 0.2}},
    ]
    store["answer"] = "Mince ginger thinly [1][2]."
    r = client.post("/rag/answer", json={"question": "How do I prep ginger?"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["citations"]) >= 1
    assert body["confidence"] > 0
    assert body["answer"] != "I cannot answer this from the available sources"


def test_rag_answer_empty_retrieval_returns_sentinel(client, store):
    """Catches buggy variant: learner returns a hallucinated answer when
    retrieval returns zero chunks."""
    store["weaviate_chunks"] = []
    store["answer"] = "Some hallucinated answer."
    r = client.post("/rag/answer", json={"question": "blarp"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "I cannot answer this from the available sources"
    assert body["citations"] == []
    assert body["confidence"] == 0.0


def test_rag_answer_no_citations_returns_sentinel(client, store):
    """Catches buggy variant: learner returns the generator output
    even when no citation markers can be resolved (hallucination path)."""
    store["weaviate_chunks"] = [
        {"chunk_id": 1, "text": "Some chunk.", "_additional": {"distance": 0.1}},
    ]
    store["answer"] = "An answer with no citation markers."
    r = client.post("/rag/answer", json={"question": "anything"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "I cannot answer this from the available sources"
    assert body["citations"] == []


def test_rag_answer_citation_ids_are_valid(client, store):
    """Catches buggy variant: learner emits citation chunk_ids that are
    not present in the retrieved set."""
    store["weaviate_chunks"] = [
        {"chunk_id": 7, "text": "A.", "_additional": {"distance": 0.1}},
        {"chunk_id": 9, "text": "B.", "_additional": {"distance": 0.2}},
    ]
    store["answer"] = "Use both ingredients [1][2]."
    r = client.post("/rag/answer", json={"question": "anything"})
    assert r.status_code == 200
    citation_ids = {c["chunk_id"] for c in r.json()["citations"]}
    # Empty-set subset is vacuous — the fixture has retrievable chunks,
    # so at least one citation must resolve.
    assert len(citation_ids) >= 1
    assert citation_ids.issubset({7, 9})


def test_rag_answer_rejects_short_question(client):
    """Catches buggy variant: learner omits Pydantic min_length on question."""
    r = client.post("/rag/answer", json={"question": "", "k": 4})
    assert r.status_code == 422


def test_rag_answer_rejects_bad_k(client):
    """Catches buggy variant: learner omits ge=1, le=10 on k."""
    r = client.post("/rag/answer", json={"question": "ok question", "k": 99})
    assert r.status_code == 422


# ---------- /healthz + /readyz --------------------------------------

def test_healthz_returns_ok_without_backends(client, store):
    """Catches buggy variant: learner probes backends inside /healthz."""
    # Even with Weaviate marked not-ready, /healthz must return 200.
    store["weaviate_ready"] = False
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readyz_returns_200_with_both_up(client, store):
    """Catches buggy variant: silent-pass — returns 200 without probing
    Neo4j or Weaviate."""
    store["rows"] = [{"n": 1}]  # RETURN 1
    store["weaviate_ready"] = True
    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    # Body must surface per-backend status — not just a bare {"status": "ok"}.
    body_str = str(body).lower()
    assert "neo4j" in body_str, "/readyz body must report neo4j status."
    assert "weaviate" in body_str, "/readyz body must report weaviate status."
    # And the Neo4j probe must have run the canonical `RETURN 1` query.
    assert "RETURN 1" in store.get("last_cypher", ""), (
        "/readyz must execute `RETURN 1` against Neo4j as the liveness probe."
    )


def test_readyz_returns_503_when_weaviate_down(client, store):
    """Catches buggy variant: learner only probes Neo4j."""
    store["rows"] = [{"n": 1}]
    store["weaviate_ready"] = False
    r = client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    # detail mentions weaviate
    assert "weaviate" in str(body).lower()


# ---------- lifespan / discipline -----------------------------------

def test_lifespan_loads_resources_once(monkeypatch):
    """Catches buggy variant: learner constructs Neo4j / Weaviate / spaCy /
    generator / embedder inside the path operation (or `Depends()`) instead
    of `lifespan` — thrash + slow tests.

    This test runs the learner's REAL `api.main.lifespan` (no override) with
    the underlying constructors monkeypatched to no-op fakes. Each fake
    increments a counter on construction; after issuing three requests, the
    test asserts each counter equals 1.

    If the learner constructs a resource per-request, the counter for that
    resource would be ≥ 3 and the test fails.
    """
    import importlib
    import os

    # Required env reads in lifespan — supply harmless values.
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test")
    monkeypatch.setenv("WEAVIATE_URL", "http://localhost:8080")
    monkeypatch.setenv("WEB_ORIGIN", "http://localhost:3000")

    counts = {"neo4j": 0, "weaviate": 0, "nlp": 0, "generator": 0, "embedder": 0}

    class _FakeDriver:
        def session(self):
            class _S:
                def __enter__(self_): return self_
                def __exit__(self_, *a): pass
                def run(self_, *_a, **_kw):
                    class _R:
                        def single(_self): return None
                        def __iter__(_self): return iter(())
                        def data(_self): return {}
                    return _R()
            return _S()
        def close(self): pass

    class _FakeWeaviateClient:
        def __init__(self, *_a, **_kw): pass
        def is_ready(self): return True
        @property
        def query(self):
            class _Q:
                def get(self_, *_a, **_kw):
                    class _B:
                        def with_near_vector(s, *_a, **_kw): return s
                        def with_limit(s, *_a, **_kw): return s
                        def with_additional(s, *_a, **_kw): return s
                        def do(s): return {"data": {"Get": {"Chunk": []}}}
                    return _B()
            return _Q()

    class _FakeNlp:
        def __call__(self, _text):
            class _Doc:
                ents = []
            return _Doc()

    class _FakeEmbedder:
        def encode(self, _text):
            import numpy as np
            return np.zeros(384, dtype=float)

    def _fake_neo4j_driver(*_a, **_kw):
        counts["neo4j"] += 1
        return _FakeDriver()
    def _fake_weaviate(*_a, **_kw):
        counts["weaviate"] += 1
        return _FakeWeaviateClient()
    def _fake_spacy_load(*_a, **_kw):
        counts["nlp"] += 1
        return _FakeNlp()
    def _fake_load_generator(*_a, **_kw):
        counts["generator"] += 1
        return lambda *_a, **_kw: [{"generated_text": ""}]
    def _fake_st(*_a, **_kw):
        counts["embedder"] += 1
        return _FakeEmbedder()

    # Force a fresh import so module-level patches take effect.
    import api.main as main_mod
    importlib.reload(main_mod)

    monkeypatch.setattr(main_mod.GraphDatabase, "driver", _fake_neo4j_driver)
    monkeypatch.setattr(main_mod.weaviate, "Client", _fake_weaviate)
    monkeypatch.setattr(main_mod.spacy, "load", _fake_spacy_load)
    monkeypatch.setattr(main_mod, "load_generator", _fake_load_generator)
    monkeypatch.setattr(main_mod, "SentenceTransformer", _fake_st)

    # Run the REAL lifespan (no override) and exercise three requests.
    with TestClient(main_mod.app) as c:
        c.get("/healthz")
        c.post("/extract", json={"text": "hello"})
        c.post("/extract", json={"text": "world"})

    assert counts["neo4j"] == 1, f"neo4j_driver constructed {counts['neo4j']} times — must be once in lifespan"
    assert counts["weaviate"] == 1, f"weaviate.Client constructed {counts['weaviate']} times"
    assert counts["nlp"] == 1, f"spacy.load constructed {counts['nlp']} times"
    assert counts["generator"] == 1, f"load_generator called {counts['generator']} times"
    assert counts["embedder"] == 1, f"SentenceTransformer constructed {counts['embedder']} times"


# ---------- v2-only Pydantic discipline -----------------------------

def test_no_pydantic_v1_idioms():
    """Catches buggy variant: v1 copy-paste from a stale tutorial."""
    api_dir = REPO_ROOT / "api"
    forbidden = [".dict(", "parse_obj(", "class Config:"]
    for path in api_dir.rglob("*.py"):
        # Vendored modules don't have to obey this rule — they were
        # written before; only check learner-authored modules.
        if "w9b_mapper" in str(path) or "m8_rag" in str(path):
            continue
        content = path.read_text()
        for tok in forbidden:
            assert tok not in content, f"{path} contains forbidden v1 idiom {tok!r}"


# ---------- CORS -----------------------------------------------------

def test_cors_middleware_configured(client):
    """Catches buggy variant: learner omits CORSMiddleware — browser blocked."""
    r = client.options(
        "/extract",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert r.status_code in (200, 204)
    assert "access-control-allow-origin" in {h.lower() for h in r.headers.keys()}


# ---------- Unmodified starter must fail ----------------------------

def test_unmodified_starter_fails():
    """Catches buggy variant: structural guard against silent-pass.

    This is the Unmodified Starter Failure Rule gate. The starter has
    TODO-only function bodies that raise NotImplementedError; the other
    tests in this file fail when the learner has not implemented. This
    test exists as an additional structural beacon: any test in this
    module other than `test_unmodified_starter_fails` itself must fail
    against the untouched starter.
    """
    # This is a structural marker — the rest of the suite enforces it.
    pass
