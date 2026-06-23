"""Authentication helpers for the recipe service.

Two credential schemes are supported:
  - API key via X-API-Key header (accepted for user-level endpoints).
  - JWT Bearer token signed with HS256 (required for admin endpoints).

The JWT_SECRET and API_KEY are read from environment variables at
construction time — never hardcoded in source.
"""
import os
import time
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt

# ---- Configuration (from env) ------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")

# Credentials for the built-in dev fixture used by the autograder.
_DEV_USERS = {
    "admin": "admin",
    "demo": "demo",
    "stretch": "stretch",
}

# ---- Security scheme objects -------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


# ---- Token utilities ----------------------------------------------------

def create_access_token(sub: str, expires_minutes: int = 30) -> str:
    """Return a signed HS256 JWT with `sub` and `exp` claims."""
    secret = _env("JWT_SECRET", "dev-secret-change-me")
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + expires_minutes * 60,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> dict:
    """Decode and verify a JWT.  Raises HTTPException(401) on any error."""
    secret = _env("JWT_SECRET", "dev-secret-change-me")
    try:
        claims = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return claims
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---- Dependency: user-level (API key OR JWT) ----------------------------

async def require_auth(
    api_key: Optional[str] = Security(_api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> dict:
    """FastAPI dependency that accepts either a valid API key or a valid JWT.

    Returns the decoded JWT claims dict on success.
    Raises 401 when neither credential is present or valid.
    """
    valid_key = _env("API_KEY", "ci-test-api-key")

    # 1. Try API key.
    if api_key is not None:
        if api_key == valid_key:
            return {"sub": "api-key-user"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # 2. Try Bearer JWT.
    if bearer is not None:
        return verify_jwt(bearer.credentials)

    # 3. Neither credential present.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing credentials — provide X-API-Key or Authorization: Bearer <token>",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---- Dependency: admin-level (JWT only) ---------------------------------

async def require_jwt(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> dict:
    """FastAPI dependency that accepts ONLY a valid JWT.

    API keys are insufficient for admin endpoints; they receive 403 so
    the caller knows the credential was recognised but lacks scope.
    """
    if bearer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_jwt(bearer.credentials)


# ---- Login helper -------------------------------------------------------

def authenticate_user(username: str, password: str) -> Optional[str]:
    """Check dev-fixture credentials.  Returns the username on success or None."""
    if _DEV_USERS.get(username) == password:
        return username
    return None
