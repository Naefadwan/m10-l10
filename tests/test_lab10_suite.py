"""Top-level marker for the Lab 10 autograder suite.

The Lab 10 autograder is organized into two subdirectories:
- ``tests/backend/`` — FastAPI endpoint behavior (TestClient + mocked services)
- ``tests/frontend/`` — Next.js build, Dockerfile structure, TypeScript shape

This file exists so tools that glob ``tests/test_*.py`` at the top level (e.g.,
the precheck preflight in `learning-outcomes-test`) can confirm the suite is
present. Real tests live under ``tests/backend/`` and ``tests/frontend/``; the
autograder workflow runs both subdirectories explicitly.
"""


def test_lab10_test_layout_is_present():
    """Confirms the two subdirectories are populated with autograder tests."""
    from pathlib import Path

    tests_dir = Path(__file__).parent
    backend = tests_dir / "backend"
    frontend = tests_dir / "frontend"

    assert backend.is_dir(), "tests/backend/ missing"
    assert frontend.is_dir(), "tests/frontend/ missing"
    assert any(backend.glob("test_*.py")), "no test_*.py files under tests/backend/"
    assert any(frontend.glob("test_*.py")), "no test_*.py files under tests/frontend/"
