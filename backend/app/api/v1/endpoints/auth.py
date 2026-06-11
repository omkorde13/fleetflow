from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional
import httpx
import structlog

from app.db.session import get_db
from app.models.models import User, UserRole, RefreshToken, AuditLog
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user, get_client_ip
)
from app.core.config import settings
from app.core.redis import get_redis, CacheManager
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest
)
from app.services.notification_service import NotificationService

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Authentication"])


async def _log_audit(db: AsyncSession, user_id, action: str, request: Request, details: dict = {}):
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=details
    )
    db.add(log)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check if user exists
    existing = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=payload.role or UserRole.CLIENT,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Create tokens
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    db.add(refresh_token)

    await _log_audit(db, user.id, "REGISTER", request, {"role": user.role})

    # Send welcome email in background
    background_tasks.add_task(
        NotificationService.send_welcome_email,
        user.email, user.full_name
    )

    logger.info("User registered", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        user_id=str(user.id),
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check account lock
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=423,
            detail=f"Account locked until {user.locked_until.isoformat()}"
        )

    # Verify password
    if not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        user.login_attempts = (user.login_attempts or 0) + 1
        if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=settings.ACCOUNT_LOCKOUT_MINUTES
            )
        await db.commit()
        await _log_audit(db, user.id, "LOGIN_FAILED", request)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    # Reset login attempts on success
    user.login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    db.add(refresh_token)
    await _log_audit(db, user.id, "LOGIN", request)

    logger.info("User logged in", user_id=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        user_id=str(user.id),
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == payload.refresh_token,
            RefreshToken.is_revoked == False
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token or stored_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    # Revoke old token
    stored_token.is_revoked = True

    result = await db.execute(select(User).where(User.id == stored_token.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    new_access = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    new_token = RefreshToken(
        user_id=user.id,
        token=new_refresh,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=get_client_ip(request),
    )
    db.add(new_token)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        user_id=str(user.id),
        role=user.role,
    )


@router.post("/logout")
async def logout(
    payload: RefreshTokenRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == payload.refresh_token)
    )
    token = result.scalar_one_or_none()
    if token:
        token.is_revoked = True

    await _log_audit(db, current_user.id, "LOGOUT", request)
    return {"message": "Logged out successfully"}


@router.get("/google/login")
async def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google login is not configured on this server",
        )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    from urllib.parse import urlencode
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    code: Optional[str] = None,
    error: Optional[str] = None,
):
    if error or not code:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?error=access_denied")

    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                }
            )
            token_data = token_response.json()
            if "access_token" not in token_data:
                logger.error("Google token exchange failed", response=token_data)
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?error=oauth_failed")

            # Get user info
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            userinfo = userinfo_response.json()
            if "sub" not in userinfo or "email" not in userinfo:
                logger.error("Google userinfo failed", response=userinfo)
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?error=oauth_failed")
    except httpx.HTTPError as e:
        logger.error("Google OAuth request failed", error=str(e))
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?error=oauth_failed")

    google_id = userinfo["sub"]
    email = userinfo["email"]
    full_name = userinfo.get("name", email)
    avatar_url = userinfo.get("picture")

    # Find or create user
    result = await db.execute(
        select(User).where(User.google_id == google_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Check if email exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_id = google_id
            user.avatar_url = avatar_url
        else:
            user = User(
                email=email,
                full_name=full_name,
                google_id=google_id,
                avatar_url=avatar_url,
                role=UserRole.CLIENT,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()

    user.last_login = datetime.utcnow()
    await _log_audit(db, user.id, "GOOGLE_LOGIN", request)

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token)

    # Redirect to frontend with tokens
    frontend_url = f"{settings.FRONTEND_URL}/auth/callback?access_token={access_token}&refresh_token={refresh_token_str}"
    return RedirectResponse(url=frontend_url)


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if user:
        import secrets
        reset_token = secrets.token_urlsafe(32)
        cache = CacheManager(redis)
        await cache.set(f"password_reset:{reset_token}", str(user.id), ttl=3600)

        background_tasks.add_task(
            NotificationService.send_password_reset_email,
            user.email, user.full_name, reset_token
        )

    # Always return success to prevent email enumeration
    return {"message": "If your email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache = CacheManager(redis)
    user_id = await cache.get(f"password_reset:{payload.token}")

    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    await cache.delete(f"password_reset:{payload.token}")

    # Revoke all existing refresh tokens
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False
        )
    )
    for token in result.scalars():
        token.is_revoked = True

    return {"message": "Password reset successfully"}
