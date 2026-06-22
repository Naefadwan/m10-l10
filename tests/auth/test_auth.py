"""Stretch Tue — Authentication Layer autograder.

Verifies the learner's `api/auth.py` + `api/main.py` changes against
the published spec. Tests use FastAPI's `TestClient(app)` and rely on
the workflow's `services:` block to provide Neo4j + Weaviate so the
lifespan startup succeeds.

The Lab autograder does NOT run these tests — its pytest invocation
scopes to `tests/backend` and a fixed set of `tests/frontend/*` files.
The stretch workflow at `.github/workflows/stretch-10-tue-auth-autograder.yml`
is the only path that exercises `tests/auth/`.

Tests covering live-backend behaviors (`/extract` returning 200 with
real entities) are intentionally tolerant: they accept a 200 OR a
503 with structured detail, because a learner who scoped the stretch
to the auth surface (and did not re-run `seed_neo4j.sh`/seed_weaviate
inside CI) will see the latter even with a correct auth implementation.
The auth contract checks themselves are strict.
"""
from __future__ import annotations

import ast
import os
import sys
import time
from pathlib import Path

import pytest

# api/ is package-relative; tests resolve it from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

API_KEY = os.environ.get("API_KEY_VALID", "ci-test-api-key")
JWT_SECRET = os.environ.get("JWT_SECRET", "ci-test-jwt-secret-do-not-use-in-prod-xxxxxxxx")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")


def test_stretch_files_present():
    """Sentinel: fail if the stretch hasn't been started.

    Runs before the TestClient fixture is invoked, so even an import
    chain that masks the failure (e.g., conftest crash) cannot hide
    behind a green CI. The stretch ships these files; their absence
    is a real defect, not a benign skip.
    """
    required = [
        REPO_ROOT / "api" / "auth.py",
        REPO_ROOT / "api" / "main.py",
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in required if not p.exists()]
    assert not missing, (
        f"Stretch Tue requires these files to exist: {missing}. "
        f"Skipping is not an acceptable outcome — the autograder "
        f"workflow only runs on branch `stretch-tue-auth` so by the "
        f"time CI fires, the learner has committed something."
    )


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient with the live lifespan running.

    Fails (not skips) if api.main does not import. The stretch
    autograder runs on the `stretch-tue-auth` branch only — by the
    time CI runs, the learner has committed something. An import
    failure here is a real failure to surface, not a benign "not
    started yet" signal. Skipping would let an unstarted stretch
    earn a green autograder.
    """
    try:
        from fastapi.testclient import TestClient

        from api.main import app  # noqa: WPS433
    except Exception as exc:  # pragma: no cover - real failure path
        pytest.fail(
            f"api.main is not importable: {exc}. The stretch must "
            f"land api/auth.py and the /auth/login + /admin/echo "
            f"changes to api/main.py before CI can grade it."
        )
    with TestClient(app) as c:
        yield c


def _ok_or_known_503(resp, *, label):
    """Accept 200 OR a structured 503 from a degraded backend.

    The auth dependency is what we are testing here; the
    Neo4j/Weaviate-backed body of `/extract` may legitimately 503
    in CI without a fresh seed run.
    """
    assert resp.status_code in (200, 503), (
        f"{label}: expected 200 or 503, got {resp.status_code}. "
        f"Body: {resp.text[:200]}"
    )


# --- /extract auth contract --------------------------------------------

def test_extract_without_credentials_returns_401(client):
    """Catches buggy variant: `APIKeyHeader(auto_error=True)` (FastAPI
    default) returns 403 for missing header. The spec contract is 401
    for any missing/invalid credential — auto_error must be False on
    both schemes and the OR-logic dependency must raise 401 itself."""
    r = client.post("/extract", json={"text": "ginger"})
    assert r.status_code == 401, (
        f"/extract without credentials must return 401. Got "
        f"{r.status_code}. If you got 403, your APIKeyHeader is using "
        f"auto_error=True — set it to False and raise 401 explicitly."
    )


def test_extract_with_bad_api_key_returns_401(client):
    r = client.post(
        "/extract",
        json={"text": "ginger"},
        headers={"X-API-Key": "definitely-wrong"},
    )
    assert r.status_code == 401, (
        f"/extract with invalid API key must return 401. Got "
        f"{r.status_code}."
    )


def test_extract_with_valid_api_key_passes_auth(client):
    """The auth dependency accepts a valid API key. The body may 503 if
    the Neo4j/Weaviate seed has not run in CI; what we test here is
    that the request gets PAST the auth gate (i.e., not 401)."""
    r = client.post(
        "/extract",
        json={"text": "ginger and garlic"},
        headers={"X-API-Key": API_KEY},
    )
    assert r.status_code != 401, (
        f"/extract with valid API key must not return 401. Got "
        f"{r.status_code}. Body: {r.text[:200]}"
    )
    _ok_or_known_503(r, label="/extract with valid API key")


# --- /auth/login + JWT contract ----------------------------------------

def test_auth_login_with_valid_credentials_returns_jwt(client):
    """The spec lets the learner pick the dev fixture username/password.
    The autograder posts a small set of candidates and accepts whichever
    returns 200. The returned token must then:

      (a) decode with the configured JWT_SECRET / JWT_ALGORITHM,
      (b) carry an `exp` claim (per the spec — expiration is enforced),
      (c) authenticate against `/extract` end-to-end.

    Bare-string returns like `"access_token": "admin"` fail (a). A
    self-signed-with-wrong-secret token fails (a) too. A token without
    `exp` fails (b). A token whose signature the running service does
    not accept fails (c). The shape-only check is intentionally not
    enough — every Honors-track learner must produce a real signed JWT.
    """
    from jose import jwt as _jwt  # noqa: WPS433
    from jose.exceptions import JWTError  # noqa: WPS433

    candidates = [
        {"username": "admin", "password": "admin"},
        {"username": "demo", "password": "demo"},
        {"username": "stretch", "password": "stretch"},
    ]
    accepted_resp = None
    last = None
    for body in candidates:
        r = client.post("/auth/login", json=body)
        last = r
        if r.status_code == 200:
            accepted_resp = r
            break
    if accepted_resp is None:
        pytest.fail(
            f"/auth/login did not accept any of the documented dev "
            f"fixtures (admin/admin, demo/demo, stretch/stretch). "
            f"Last response: "
            f"{last.status_code if last else 'none'} "
            f"{getattr(last, 'text', '')[:200]}"
        )

    payload = accepted_resp.json()
    assert "access_token" in payload, (
        f"/auth/login 200 response missing 'access_token'. "
        f"Body: {payload!r}"
    )
    assert payload.get("token_type", "").lower() == "bearer", (
        f"/auth/login response 'token_type' must be 'bearer'. "
        f"Got {payload.get('token_type')!r}."
    )

    token = payload["access_token"]
    assert isinstance(token, str) and token, (
        f"access_token must be a non-empty string. Got {token!r}."
    )

    # (a) decodes with the configured secret + algorithm.
    try:
        claims = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        pytest.fail(
            f"access_token does not decode with the configured "
            f"JWT_SECRET / JWT_ALGORITHM={JWT_ALGORITHM!r}. This "
            f"means either (i) the learner returned a bare string "
            f"instead of a signed JWT (e.g. "
            f"`\"access_token\": \"admin\"`), (ii) the token was "
            f"signed with a different secret/algorithm than the env "
            f"the autograder set, or (iii) `create_access_token` "
            f"does not sign at all. jose error: {exc}"
        )

    # (b) carries an exp claim — required for test_jwt_expiration_enforced.
    assert "exp" in claims, (
        f"access_token must carry an `exp` (expiration) claim. The "
        f"spec's Task 1 requires `create_access_token(expires_minutes=...)` "
        f"to set exp. Got claims: {sorted(claims)!r}."
    )

    # (c) authenticates end-to-end against /extract — the strongest
    # check, because the running service has to accept the same token
    # the learner just issued.
    r = client.post(
        "/extract",
        json={"text": "ginger and garlic"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code != 401, (
        f"/auth/login returned a JWT but it does not authenticate "
        f"against /extract (got 401). This usually means the JWT "
        f"verifier and the issuer disagree on the secret, the "
        f"algorithm, or the audience claim. Body: {r.text[:200]}"
    )
    _ok_or_known_503(r, label="/extract with token from /auth/login")


def test_auth_login_with_invalid_credentials_returns_401(client):
    r = client.post(
        "/auth/login",
        json={"username": "no-such-user", "password": "no-such-password"},
    )
    assert r.status_code == 401, (
        f"/auth/login with invalid credentials must return 401. Got "
        f"{r.status_code}."
    )


def _make_jwt(*, sub: str = "ci-test", expires_in: int = 60) -> str:
    from jose import jwt  # noqa: WPS433

    now = int(time.time())
    payload = {"sub": sub, "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_extract_with_valid_jwt_passes_auth(client):
    token = _make_jwt()
    r = client.post(
        "/extract",
        json={"text": "ginger"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code != 401, (
        f"/extract with valid JWT must not return 401. Got "
        f"{r.status_code}. Body: {r.text[:200]}"
    )
    _ok_or_known_503(r, label="/extract with valid JWT")


# --- /admin/echo scope ------------------------------------------------

def test_admin_echo_with_api_key_only_returns_403(client):
    """The spec distinguishes 401 (no credential) from 403 (valid
    credential, insufficient scope). /admin/echo accepts JWT only; an
    API key is a valid credential for /extract but lacks admin scope."""
    r = client.get("/admin/echo", headers={"X-API-Key": API_KEY})
    assert r.status_code == 403, (
        f"/admin/echo with API key (no JWT) must return 403. Got "
        f"{r.status_code}. The contract: 401 = missing/invalid "
        f"credential; 403 = valid credential but wrong scope."
    )


def test_admin_echo_with_valid_jwt_returns_200(client):
    token = _make_jwt(sub="admin-test")
    r = client.get("/admin/echo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, (
        f"/admin/echo with valid JWT must return 200. Got "
        f"{r.status_code}. Body: {r.text[:200]}"
    )
    body = r.json()
    assert body.get("sub") == "admin-test" or "sub" in body or "payload" in body, (
        f"/admin/echo 200 response must echo the decoded JWT payload "
        f"(at minimum the `sub` claim). Got: {body!r}"
    )


def test_jwt_expiration_enforced(client):
    """Expired JWT must be rejected with 401."""
    token = _make_jwt(expires_in=-60)  # already expired
    r = client.post(
        "/extract",
        json={"text": "ginger"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401, (
        f"Expired JWT must return 401 from /extract. Got "
        f"{r.status_code}. If you got 200, verify_jwt is not checking "
        f"the `exp` claim (use jose.jwt.decode without "
        f"options={{'verify_exp': False}})."
    )


# --- Hygiene: JWT secret is not hardcoded ------------------------------

def test_jwt_secret_not_hardcoded():
    """AST scan of api/auth.py refuses a literal JWT_SECRET assignment.

    The spec requires the secret to come from os.environ /
    Settings(). A literal `JWT_SECRET = "..."` assignment ships the
    signing key in source — the most common Honors-track mistake.
    """
    auth_path = REPO_ROOT / "api" / "auth.py"
    assert auth_path.exists(), (
        "api/auth.py must exist — the stretch's Task 1 ships the "
        "credential verifiers in this file. A missing api/auth.py is "
        "an unstarted stretch, not a benign skip."
    )
    tree = ast.parse(auth_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "JWT_SECRET":
                    if isinstance(node.value, ast.Constant) and isinstance(
                        node.value.value, str
                    ):
                        pytest.fail(
                            "api/auth.py has a literal `JWT_SECRET = "
                            "\"...\"` assignment — load the secret from "
                            "os.environ or a Settings object instead."
                        )
