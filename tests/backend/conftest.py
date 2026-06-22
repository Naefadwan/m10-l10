"""Backend test fixtures with mocked external services.

Neo4j, Weaviate, spaCy, and the flan-t5-base generator are constructed
in `api.main.lifespan`. The autograder substitutes the lifespan with a
mock that injects controllable doubles so tests run hermetically.
"""
import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Used to count how many times each resource is constructed. Hosted in
# a sibling module so the test file and the conftest plugin share the
# same dict object — see _construction_counters.py for rationale.
from tests.backend._construction_counters import construction_counts  # noqa: E402


class _FakeSession:
    def __init__(self, store):
        self._store = store

    def run(self, cypher, **params):
        self._store["last_cypher"] = cypher
        self._store["last_params"] = params
        # Behavior is overridden per-test via `store["rows"]`.
        records = self._store.get("rows", [])
        return _FakeResult(records)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class _FakeResult:
    def __init__(self, records):
        self._records = records

    def __iter__(self):
        for r in self._records:
            yield _FakeRecord(r)

    def single(self):
        return _FakeRecord(self._records[0]) if self._records else None


class _FakeRecord:
    def __init__(self, payload):
        self._payload = payload

    def data(self):
        return dict(self._payload)


class _FakeDriver:
    def __init__(self, store):
        self._store = store
        construction_counts["neo4j"] += 1

    def session(self):
        return _FakeSession(self._store)

    def close(self):
        pass


class _FakeWeaviateQueryBuilder:
    def __init__(self, store):
        self._store = store

    def with_near_vector(self, _):
        return self

    def with_limit(self, _):
        return self

    def with_additional(self, _):
        return self

    def do(self):
        chunks = self._store.get("weaviate_chunks", [])
        return {"data": {"Get": {"Chunk": chunks}}}


class _FakeWeaviateQuery:
    def __init__(self, store):
        self._store = store

    def get(self, *_args, **_kw):
        return _FakeWeaviateQueryBuilder(self._store)


class _FakeWeaviateClient:
    def __init__(self, store):
        self._store = store
        self.query = _FakeWeaviateQuery(store)
        construction_counts["weaviate"] += 1

    def is_ready(self):
        return self._store.get("weaviate_ready", True)


class _FakeNlp:
    def __init__(self, store):
        self._store = store
        construction_counts["nlp"] += 1

    def __call__(self, text):
        return _FakeDoc(self._store.get("entities", []))


class _FakeDoc:
    def __init__(self, ents):
        self.ents = [_FakeEnt(**e) for e in ents]


class _FakeEnt:
    def __init__(self, text, label, start_char, end_char):
        self.text = text
        self.label_ = label
        self.start_char = start_char
        self.end_char = end_char


def _fake_generator_factory(store):
    construction_counts["generator"] += 1

    def _gen(prompt, **_kw):
        return [{"generated_text": store.get("answer", "I cannot answer this from the available sources")}]

    return _gen


class _FakeEmbedder:
    """Mock sentence-transformers embedder.

    `encode(text)` returns a stable zero vector — the fake Weaviate
    `with_near_vector` ignores the value anyway and returns the
    pre-seeded chunks from the per-test store.
    """

    def __init__(self, store):
        self._store = store
        construction_counts["embedder"] += 1

    def encode(self, _text):
        # Return an ndarray-like with .tolist(); a plain list with a
        # tolist shim is enough for the mock.
        import numpy as np

        return np.zeros(384, dtype=float)


@pytest.fixture
def store():
    """Mutable per-test state shared with the fake clients."""
    construction_counts.update({"neo4j": 0, "weaviate": 0, "nlp": 0, "generator": 0, "embedder": 0})
    return {}


@pytest.fixture
def client(store):
    """TestClient against the app with mocked external resources."""
    from api import main as main_module

    fake_driver = _FakeDriver(store)
    fake_weaviate = _FakeWeaviateClient(store)
    fake_nlp = _FakeNlp(store)
    fake_gen = _fake_generator_factory(store)
    fake_embedder = _FakeEmbedder(store)

    @asynccontextmanager
    async def _lifespan(app):
        app.state.neo4j_driver = fake_driver
        app.state.weaviate_client = fake_weaviate
        app.state.nlp = fake_nlp
        app.state.generator = fake_gen
        app.state.embedder = fake_embedder
        yield

    main_module.app.router.lifespan_context = _lifespan
    with TestClient(main_module.app) as c:
        yield c
