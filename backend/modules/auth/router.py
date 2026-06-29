"""
auth.py — Authentication Router
Handles registration, login, and fetching current user info.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.database import get_db, User
from models.schemas import UserRegister, UserOut, Token
from services.auth_service import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    create_verify_token,
    decode_token,
    get_current_user,
    get_password_hash,
    require_admin,
    set_auth_cookies,
    verify_password,
)
from services.email_service import send_email
from services.rate_limit import limiter

router = APIRouter()


def _normalize_email(email: str) -> str:
    """Lowercase + strip so 'User@Example.COM' and 'user@example.com' are one account."""
    return (email or "").strip().lower()


def _validate_password(password: str) -> None:
    """Enforce a minimum password strength. Raises HTTP 400 if too weak."""
    if not password or len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter and one number",
        )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    email = _normalize_email(payload.email)
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required",
        )
    _validate_password(payload.password)

    # Check if user already exists
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_pw = get_password_hash(payload.password)
    user = User(email=email, hashed_pw=hashed_pw, plan="free", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """OAuth2 password flow login.

    Sets httpOnly access + refresh cookies (the secure, XSS-resistant path) AND
    returns the access token in the body (backward compatible with header-based
    clients during the migration off localStorage)."""
    stmt = select(User).where(User.email == _normalize_email(form_data.username))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    csrf = set_auth_cookies(response, access_token, refresh_token)
    return {"access_token": access_token, "token_type": "bearer", "csrf_token": csrf}


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Mint a fresh access token from the httpOnly refresh cookie, rotating the
    refresh token. Returns 401 if the refresh cookie is missing/invalid/expired."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise unauthorized
    payload = decode_token(token, expected_type="refresh")
    if not payload or not payload.get("sub"):
        raise unauthorized

    email = payload["sub"]
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not user.is_active:
        raise unauthorized

    access_token = create_access_token(data={"sub": email})
    new_refresh = create_refresh_token(data={"sub": email})  # rotation
    csrf = set_auth_cookies(response, access_token, new_refresh)
    return {"access_token": access_token, "token_type": "bearer", "csrf_token": csrf}


@router.post("/logout")
async def logout(response: Response):
    """Clear the auth cookies. (Stateless JWTs: the access token remains valid until
    expiry; the short access TTL + refresh rotation bound the exposure.)"""
    clear_auth_cookies(response)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Fetch current user details."""
    return current_user


# ── Password reset / email verification ───────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class TokenRequest(BaseModel):
    token: str


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Email a password-reset link. Always returns 200 (no user enumeration)."""
    email = _normalize_email(payload.email)
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user and user.is_active:
        token = create_reset_token(email)
        link = f"{get_settings().frontend_base_url}/reset-password?token={token}"
        await send_email(
            email, "Reset your QuantAI password",
            f"Use this link to reset your password (valid 30 min):\n{link}\n\n"
            "If you didn't request this, ignore this email.",
        )
    return {"detail": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Complete a password reset using the emailed token."""
    bad = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    data = decode_token(payload.token, expected_type="reset")
    if not data or not data.get("sub"):
        raise bad
    _validate_password(payload.new_password)
    user = (await db.execute(select(User).where(User.email == data["sub"]))).scalar_one_or_none()
    if not user:
        raise bad
    user.hashed_pw = get_password_hash(payload.new_password)
    await db.commit()
    return {"detail": "Password reset successful"}


@router.post("/send-verification")
async def send_verification(current_user: User = Depends(get_current_user)):
    """Email the current user a verification link."""
    if current_user.is_verified:
        return {"detail": "Email already verified"}
    token = create_verify_token(current_user.email)
    link = f"{get_settings().frontend_base_url}/verify-email?token={token}"
    await send_email(
        current_user.email, "Verify your QuantAI email",
        f"Confirm your email address:\n{link}",
    )
    return {"detail": "Verification email sent"}


@router.post("/verify-email")
async def verify_email(payload: TokenRequest, db: AsyncSession = Depends(get_db)):
    """Mark the user's email verified using the emailed token."""
    bad = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")
    data = decode_token(payload.token, expected_type="verify")
    if not data or not data.get("sub"):
        raise bad
    user = (await db.execute(select(User).where(User.email == data["sub"]))).scalar_one_or_none()
    if not user:
        raise bad
    user.is_verified = True
    await db.commit()
    return {"detail": "Email verified"}


@router.get("/admin/ping")
async def admin_ping(current_user: User = Depends(require_admin)):
    """Admin-only sanity route — demonstrates RBAC enforcement."""
    return {"detail": "pong", "admin": current_user.email}
