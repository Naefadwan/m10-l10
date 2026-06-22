"""Shared counter dict for the lifespan-discipline test.

pytest loads `conftest.py` as a plugin separately from a regular
`from tests.backend.conftest import ...` import. The two loads produce
distinct module objects with independent module-level state — so a
counter mutated by conftest's fake clients would not be visible to a
test that imported the conftest copy. Hosting the dict in this
plain-import module keeps both readers pointed at the same object.
"""

construction_counts: dict[str, int] = {
    "neo4j": 0,
    "weaviate": 0,
    "nlp": 0,
    "generator": 0,
    "embedder": 0,
}
