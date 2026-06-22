"""Structural check: web/lib/types.ts mirrors api/models.py.

Catches buggy variant: hand-written interface drift — backend returns
`chunk_id` but the frontend type expects `chunkId`; page renders nothing
because the destructure fails silently.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

EXPECTED_FIELDS = {
    "Entity": {"text", "label", "start", "end"},
    "ExtractResponse": {"entities"},
    "KGResponse": {"cypher", "rows", "count"},
    "Citation": {"chunk_id", "score"},
    "RAGResponse": {"answer", "citations", "confidence"},
}


def test_typescript_interfaces_declare_expected_field_names():
    """Catches buggy variant: TS interface drift from Pydantic shapes.

    Strips `//` comment lines first so TODO scaffolding that mentions
    field names does not satisfy the field-presence check, then requires
    `export interface Foo { ... }` (TODO comments cannot match because
    they start with `//`)."""
    raw = (REPO_ROOT / "web" / "lib" / "types.ts").read_text()
    # Strip single-line comments so TODO text never satisfies the check.
    stripped_lines = []
    for line in raw.splitlines():
        # Remove inline trailing `//` comment, keep code before it.
        code = line.split("//", 1)[0]
        stripped_lines.append(code)
    ts = "\n".join(stripped_lines)

    for interface, expected in EXPECTED_FIELDS.items():
        # Require `export interface Foo { ... }` — not just `interface Foo`.
        m = re.search(
            rf"export\s+interface\s+{interface}\s*\{{([^}}]*)\}}",
            ts,
        )
        assert m, (
            f"`export interface {interface}` not declared in web/lib/types.ts"
        )
        block = m.group(1)
        for field in expected:
            assert field in block, (
                f"interface {interface} missing field {field!r} — "
                f"Pydantic ↔ TypeScript drift"
            )


def test_typescript_avoids_camelcase_for_snake_fields():
    """Catches buggy variant: learner camelCases `chunk_id` → `chunkId`."""
    ts = (REPO_ROOT / "web" / "lib" / "types.ts").read_text()
    assert "chunkId" not in ts
    assert "startChar" not in ts
