"""
app/auth.py — Dual authentication: API key + Supabase JWT.

Supports three modes:
  1. Per-account API keys: X-API-Key header (WordPress plugin).
  2. Supabase JWT: Authorization: Bearer <token> (dashboard).
  3. Admin fallback: X-API-Key matches PIXELVAULT_API_KEY from .env.

If no key configured and no token -> open access (dev mode).
"""

import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_sync_db

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _hash_key(raw: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_supabase_jwt(token: str) -> str | None:
    """
    Verify a Supabase JWT and return the email.
    Returns None if verification fails or JWT auth is disabled.
    """
    if not settings.supabase_jwt_secret:
        return None

    try:
        from jose import jwt as jose_jwt

        payload = jose_jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload.get("email")
    except Exception:
        return None


def _auto_provision_account(email: str, db: Session) -> "Account":
    """Create a free-tier account for a first-time dashboard user."""
    from app.models import Account
    from app.routers.accounts import PLAN_LIMITS

    limits = PLAN_LIMITS["free"]
    account = Account(
        email=email,
        name=email.split("@")[0],
        plan="free",
        generations_used=0,
        generations_limit=limits["generations_limit"],
        sync_limit=limits["sync_limit"],
    )
    db.add(account)
    db.flush()
    return account


def get_current_account(
    api_key: str = Security(api_key_header),
    authorization: str | None = Header(None),
    db: Session = Depends(get_sync_db),
):
    """
    Resolve the caller's Account from API key or Supabase JWT.

    Returns:
        Account instance if authenticated as a user.
        None if admin key or dev mode.

    Raises:
        HTTPException 403 if credentials are invalid.
    """
    from app.models import Account, ApiKey

    # Try JWT first (dashboard).
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        email = verify_supabase_jwt(token)
        if email:
            account = db.query(Account).filter(Account.email == email).first()
            if not account:
                account = _auto_provision_account(email, db)
            return account
        raise HTTPException(403, "Invalid or expired token")

    # Dev mode: no key configured and none sent.
    if not settings.pixelvault_api_key and not api_key:
        return None

    if not api_key:
        raise HTTPException(403, "API key required")

    # Check admin key.
    if api_key == settings.pixelvault_api_key:
        return None

    # Check per-account key.
    key_hash = _hash_key(api_key)
    api_key_record = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()

    if not api_key_record:
        raise HTTPException(403, "Invalid API key")

    api_key_record.last_used = datetime.now(timezone.utc)
    db.flush()

    return api_key_record.account


def verify_api_key(
    api_key: str = Security(api_key_header),
    authorization: str | None = Header(None),
    db: Session = Depends(get_sync_db),
):
    """
    Simple gate: reject if credentials are required but missing/wrong.
    Accepts API key OR Supabase JWT.
    """
    # Try JWT first.
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        email = verify_supabase_jwt(token)
        if email:
            from app.models import Account
            account = db.query(Account).filter(Account.email == email).first()
            if not account:
                _auto_provision_account(email, db)
            return
        raise HTTPException(403, "Invalid or expired token")

    if not settings.pixelvault_api_key:
        return  # Dev mode.

    if not api_key:
        raise HTTPException(403, "API key required")

    if api_key == settings.pixelvault_api_key:
        return

    from app.models import ApiKey
    key_hash = _hash_key(api_key)
    found = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if not found:
        raise HTTPException(403, "Invalid API key")
