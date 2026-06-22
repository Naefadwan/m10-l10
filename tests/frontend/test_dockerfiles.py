"""Structural tests for the two Dockerfiles.

These tests are pure lint — they search for required Dockerfile
instructions while ignoring comment lines, so TODO scaffolding that
mentions the expected tokens does not satisfy the check. The Step-7
staging validation runs without Docker available; the CI workflow runs
a structural `docker build` smoke check in addition.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _read(rel: str) -> str:
    p = REPO_ROOT / rel
    return p.read_text() if p.exists() else ""


def _non_comment_lines(content: str) -> list[str]:
    """Drop comment-only lines so TODO text does not satisfy substring
    checks. A line whose first non-whitespace character is `#` is a
    comment in Dockerfile syntax."""
    return [
        line for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_backend_dockerfile_uses_python_311_slim():
    """Catches buggy variant: learner uses a fat base image (multi-GB)."""
    content = _read("api/Dockerfile")
    # Must appear as a real `FROM` line, not in a TODO comment.
    assert re.search(
        r"^FROM\s+python:3\.11-slim\b",
        content,
        re.MULTILINE,
    ), "api/Dockerfile must start a build stage with `FROM python:3.11-slim`."


def test_backend_dockerfile_caches_requirements_first():
    """Catches buggy variant: learner copies the whole context before
    pip install — every code change re-installs requirements."""
    lines = _non_comment_lines(_read("api/Dockerfile"))
    req_pos = next(
        (i for i, line in enumerate(lines) if line.startswith("COPY requirements.txt")),
        -1,
    )
    full_copy_pos = next(
        (i for i, line in enumerate(lines) if re.match(r"COPY\s+\.\s", line) or line.strip() == "COPY ."),
        -1,
    )
    assert req_pos > -1, "api/Dockerfile missing `COPY requirements.txt` instruction."
    assert full_copy_pos > -1, "api/Dockerfile missing `COPY . .` (or `COPY .`) instruction."
    assert req_pos < full_copy_pos, (
        "`COPY requirements.txt` must precede `COPY .` so pip install layer caches."
    )


def test_backend_dockerfile_downloads_spacy_model():
    """Catches buggy variant: learner forgets `python -m spacy download
    en_core_web_sm` — runtime crashes on first /extract call."""
    lines = _non_comment_lines(_read("api/Dockerfile"))
    assert any(
        re.search(r"^RUN\b.*python\s+-m\s+spacy\s+download\s+en_core_web_sm", line)
        for line in lines
    ), "api/Dockerfile must `RUN python -m spacy download en_core_web_sm`."


def test_backend_dockerignore_excludes_tests_and_env():
    """Catches buggy variant: learner ships .env or tests/ inside the
    image."""
    content = _read("api/.dockerignore")
    assert "tests" in content
    assert ".env" in content


def test_frontend_dockerfile_is_multistage():
    """Catches buggy variant: learner ships a single-stage Dockerfile —
    final image is 700 MB instead of <400 MB."""
    content = _read("web/Dockerfile")
    assert "AS builder" in content or "as builder" in content
    assert "AS runner" in content or "as runner" in content


def test_frontend_dockerfile_uses_node_20_alpine():
    """Catches buggy variant: learner uses node:20 (fat image)."""
    content = _read("web/Dockerfile")
    assert re.search(
        r"^FROM\s+node:20-alpine\b",
        content,
        re.MULTILINE,
    ), "web/Dockerfile must start a build stage with `FROM node:20-alpine`."


def test_frontend_dockerignore_excludes_node_modules():
    """Catches buggy variant: learner ships node_modules into the image
    — balloons to 2 GB+."""
    content = _read("web/.dockerignore")
    assert "node_modules" in content
