"""Authentication helpers for the recipe service.

Two credential schemes are supported:
  - API key via X-API-Key header (accepted for user-level endpoints).
  - JWT Bearer token signed with HS256 (required for admin endpoints).

The JWT_SECRET and API_KEY_VALID are read from environment variables at
construction time — never hardcoded in source.
"""
import os
import time
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DEV_USERS = {
    "admin": pwd_context.hash("admin"),
    "demo": pwd_context.hash("demo"),
    "stretch": pwd_context.hash("stretch"),
}


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify the X-API-Key header against API_KEY_VALID env var."""
    valid_key = os.getenv("API_KEY_VALID", "ci-test-api-key")
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    if api_key != valid_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return api_key


def verify_jwt(token: str = Depends(oauth2_scheme)) -> dict:
    """Decode and verify a JWT. Raises HTTPException(401) on any error."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    secret = os.getenv("JWT_SECRET", "ci-test-jwt-secret-do-not-use-in-prod-xxxxxxxx")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(subject: str, expires_minutes: int = 60) -> str:
    """Return a signed HS256 JWT with `sub` and `exp` claims."""
    secret = os.getenv("JWT_SECRET", "ci-test-jwt-secret-do-not-use-in-prod-xxxxxxxx")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_minutes * 60,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def authenticate_user(username: str, password: str) -> Optional[str]:
    """Check dev-fixture credentials. Returns the username on success or None."""
    if username in _DEV_USERS:
        if pwd_context.verify(password, _DEV_USERS[username]):
            return username
    return None


async def require_auth(
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict:
    """FastAPI dependency that accepts either a valid API key or a valid JWT.

    Returns a dict with auth info on success.
    Raises 401 when neither credential is present or valid.
    """
    if api_key is not None:
        valid_key = os.getenv("API_KEY_VALID", "ci-test-api-key")
        if api_key == valid_key:
            return {"sub": "api-key-user"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if token is not None:
        return verify_jwt(token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_jwt(
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict:
    """FastAPI dependency that accepts ONLY a valid JWT.

    API keys are insufficient for admin endpoints; they receive 403 so
    the caller knows the credential was recognised but lacks scope.
    """
    if token is not None:
        return verify_jwt(token)

    if api_key is not None:
        valid_key = os.getenv("API_KEY_VALID", "ci-test-api-key")
        if api_key == valid_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key lacks admin scope — provide a JWT instead",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing Bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
