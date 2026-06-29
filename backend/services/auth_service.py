"""
auth_service.py — Authentication services
Provides password hashing (bcrypt) and JWT token generation/verification.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.database import get_db, User

logger = logging.getLogger(__name__)

# Secret keys and algorithms
_DEFAULT_SECRET = "change-this-to-a-random-secret-in-production"
_settings = get_settings()

# Cookie names for the httpOnly auth cookies.
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
# CSRF: a NON-httpOnly cookie + a matching header (double-submit). Returned in the
# login/refresh body too, so a cross-site frontend (which can't read the backend's
# cookie) can still echo it back in the header.
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def _load_secret() -> str:
    """Use a configured JWT_SECRET_KEY if real; otherwise generate and persist a
    random secret so tokens are never signed with the publicly-known default.
    In production, a missing secret is a hard misconfiguration — warn loudly."""
    configured = _settings.jwt_secret_key
    if configured and configured != _DEFAULT_SECRET:
        return configured
    if _settings.environment.lower() in ("production", "prod"):
        logger.error(
            "JWT_SECRET_KEY is not set in production — using a machine-local generated "
            "secret. Set JWT_SECRET_KEY via your secret store so tokens survive restarts "
            "and are consistent across instances."
        )
    import secrets
    import pathlib
    path = pathlib.Path(__file__).resolve().parent.parent / ".jwt_secret"
    try:
        if path.exists():
            existing = path.read_text().strip()
            if existing:
                return existing
        generated = secrets.token_urlsafe(48)
        path.write_text(generated)
        logger.warning("JWT_SECRET_KEY not set — generated a persistent random secret at %s", path)
        return generated
    except Exception:
        return secrets.token_urlsafe(48)


SECRET_KEY = _load_secret()
ALGORITHM = _settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = _settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = _settings.refresh_token_expire_days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# auto_error=False → endpoints that work for both guests and logged-in users.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def generate_csrf_token() -> str:
    import secrets
    return secrets.token_urlsafe(32)


def set_auth_cookies(response, access_token: str, refresh_token: str) -> str:
    """Set the httpOnly access + refresh cookies plus the (readable) CSRF cookie.
    httpOnly defeats XSS token theft (the reason to move off localStorage); the
    refresh cookie is path-scoped to /api/v1/auth. Returns the CSRF token so the
    caller can also include it in the response body for cross-site frontends."""
    response.set_cookie(
        ACCESS_COOKIE, access_token, httponly=True,
        secure=_settings.cookie_secure, samesite=_settings.cookie_samesite,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, httponly=True,
        secure=_settings.cookie_secure, samesite=_settings.cookie_samesite,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400, path="/api/v1/auth",
    )
    csrf = generate_csrf_token()
    response.set_cookie(
        CSRF_COOKIE, csrf, httponly=False,  # readable so the SPA can echo it in a header
        secure=_settings.cookie_secure, samesite=_settings.cookie_samesite,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/",
    )
    return csrf


def clear_auth_cookies(response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")


def install_csrf_protection(app) -> None:
    """Double-submit CSRF guard. For unsafe methods authenticated *via cookie*, an
    `X-CSRF-Token` header must match the CSRF cookie. Requests authenticated by a
    Bearer header are exempt (CSRF can't set custom headers cross-site), as are the
    auth bootstrap endpoints and safe methods."""
    import secrets

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}
    exempt_prefixes = ("/api/v1/auth/",)

    class CSRFMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.method not in safe_methods:
                path = request.url.path
                cookie_authed = ACCESS_COOKIE in request.cookies
                header_authed = request.headers.get("authorization") is not None
                exempt = any(path.startswith(p) for p in exempt_prefixes)
                if cookie_authed and not header_authed and not exempt:
                    sent = request.headers.get(CSRF_HEADER)
                    expected = request.cookies.get(CSRF_COOKIE)
                    if not sent or not expected or not secrets.compare_digest(sent, expected):
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "CSRF token missing or invalid"},
                        )
            return await call_next(request)

    app.add_middleware(CSRFMiddleware)


def _encode(data: dict, token_type: str, delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + delta, "type": token_type})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return _encode(data, "access", expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(data: dict) -> str:
    """A longer-lived token usable only to mint new access tokens (via /auth/refresh)."""
    return _encode(data, "refresh", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def create_reset_token(email: str) -> str:
    return _encode({"sub": email}, "reset",
                   timedelta(minutes=_settings.reset_token_expire_minutes))


def create_verify_token(email: str) -> str:
    return _encode({"sub": email}, "verify",
                   timedelta(minutes=_settings.verify_token_expire_minutes))


def decode_token(token: str, expected_type: Optional[str] = "access") -> Optional[dict]:
    """Decode + validate a JWT. Enforces the token ``type`` so a refresh token can't
    be used for access (and vice-versa). Returns the payload, or None if invalid.
    ``expected_type=None`` skips the type check; a token with no ``type`` claim is
    treated as an access token for backward compatibility with pre-existing tokens."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if expected_type is not None:
        if payload.get("type", "access") != expected_type:
            return None
    return payload


def _token_from(request: Request, header_token: Optional[str]) -> Optional[str]:
    """Prefer the Authorization header (back-compat); fall back to the httpOnly cookie."""
    return header_token or request.cookies.get(ACCESS_COOKIE)


async def _user_for_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token, expected_type="access")
    if not payload:
        return None
    email = payload.get("sub")
    if not email:
        return None
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        return user
    return None


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Bearer header OR the httpOnly cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = await _user_for_token(_token_from(request, token), db)
    if user is None:
        raise credentials_exception
    return user


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401 when no/invalid token.
    Lets a route serve guests (anonymous, id-scoped data) and logged-in users alike."""
    return await _user_for_token(_token_from(request, token), db)


def require_role(*roles: str):
    """Dependency factory: require the authenticated user to hold one of ``roles``.

    Usage:  current_user: User = Depends(require_role("admin"))
    Returns 403 for an authenticated user lacking the role (401 handled upstream)."""
    allowed = set(roles)

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if getattr(current_user, "role", "user") not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker


require_admin = require_role("admin")
