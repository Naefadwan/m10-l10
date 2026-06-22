"""Lab-level docker-compose.yml structural check."""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_compose():
    return yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())


def test_lab_compose_declares_api_and_web():
    """Catches buggy variant: learner ships the integration-style 4-service
    Compose in the Lab repo."""
    cfg = _load_compose()
    services = cfg.get("services") or {}
    assert "api" in services
    assert "web" in services


def test_lab_compose_web_depends_on_api():
    """Catches buggy variant: bare `depends_on: [api]` waits only for
    container start, not readiness."""
    cfg = _load_compose()
    web_deps = cfg["services"]["web"].get("depends_on") or {}
    # Allow either dict form (preferred) or list form (less strict).
    if isinstance(web_deps, dict):
        assert "api" in web_deps
        assert web_deps["api"].get("condition") == "service_healthy"
    else:
        assert "api" in web_deps


def test_lab_compose_web_uses_localhost_api_url():
    """Catches buggy variant: learner uses http://api:8000 — browser
    cannot resolve service-name DNS — OR learner sets the URL as a
    runtime environment variable instead of a Next.js build arg.

    Per the reading's Web service section (Sections 8, 11, Common
    Pitfalls): NEXT_PUBLIC_API_URL is baked at build time by Next.js
    into the client-side bundle, so it must be declared under
    `services.web.build.args` (not `environment`)."""
    cfg = _load_compose()
    web_svc = cfg["services"]["web"]
    build = web_svc.get("build")
    args = {}
    if isinstance(build, dict):
        args = build.get("args") or {}
        if isinstance(args, list):
            args = dict(s.split("=", 1) for s in args if "=" in s)
    url = args.get("NEXT_PUBLIC_API_URL", "")
    assert url, (
        "NEXT_PUBLIC_API_URL must be declared as a build arg under "
        "`services.web.build.args` — Next.js bakes NEXT_PUBLIC_* values "
        "into the client bundle at build time, so a runtime "
        "`environment:` entry never reaches the browser."
    )
    assert "localhost" in url
    assert "//api:" not in url


def test_lab_compose_api_build_context_is_repo_root():
    """Catches buggy variant: learner writes `build: ./api` (the
    intuitive form). Image builds, but the api container crashes at
    startup with `ModuleNotFoundError: No module named 'api'` because
    `uvicorn api.main:app` runs from /app and expects the `api/`
    package directory to exist there.

    Per lab guide Task 5: use long-form build with `context: .` and
    `dockerfile: api/Dockerfile` so the build context is the repo root
    and the starter's package-relative imports resolve."""
    cfg = _load_compose()
    api_build = cfg["services"]["api"].get("build")
    assert isinstance(api_build, dict), (
        "api service must use long-form build with `context` and "
        "`dockerfile` keys (not short-form `build: ./api`). Short form "
        "sets context to api/, the Dockerfile's `COPY api/...` lines "
        "fail, and even if the image builds, the container crashes "
        "with ModuleNotFoundError. See lab guide Task 5."
    )
    context = api_build.get("context", "")
    dockerfile = api_build.get("dockerfile", "")
    assert context in (".", "./"), (
        f"api build context must be the repo root (`.`), got {context!r}."
    )
    assert dockerfile == "api/Dockerfile", (
        f"api dockerfile must be `api/Dockerfile`, got {dockerfile!r}."
    )
