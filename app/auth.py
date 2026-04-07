"""
app/auth.py — API key authentication.

Supports two modes:
  1. Per-account API keys: X-API-Key contains a key that hashes to an api_keys row.
  2. Admin fallback: X-API-Key matches PIXELVAULT_API_KEY from .env (full access, no account).

If no key is configured in .env AND no per-account key matches → open access (dev mode).
"""

import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_sync_db

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _hash_key(raw: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw.encode()).hexdigest()


def get_current_account(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_sync_db),
):
    """
    Resolve the caller's Account from the API key.

    Returns:
        Account instance if a per-account key was used.
        None if the admin key was used or dev mode (no key configured).

    Raises:
        HTTPException 403 if the key is invalid.
    """
    from app.models import ApiKey

    # Dev mode: no key configured and none sent.
    if not settings.pixelvault_api_key and not api_key:
        return None

    if not api_key:
        raise HTTPException(403, "API key required")

    # Check admin key first.
    if api_key == settings.pixelvault_api_key:
        return None  # Admin — no account context.

    # Check per-account key.
    key_hash = _hash_key(api_key)
    api_key_record = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()

    if not api_key_record:
        raise HTTPException(403, "Invalid API key")

    # Update last_used.
    api_key_record.last_used = datetime.now(timezone.utc)
    db.flush()

    return api_key_record.account


def verify_api_key(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_sync_db),
):
    """
    Simple gate: reject if a key is required but missing/wrong.
    Now also accepts per-account keys.
    """
    if not settings.pixelvault_api_key:
        return  # Dev mode.

    if not api_key:
        raise HTTPException(403, "API key required")

    # Admin key match.
    if api_key == settings.pixelvault_api_key:
        return

    # Per-account key match.
    from app.models import ApiKey
    key_hash = _hash_key(api_key)
    found = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if not found:
        raise HTTPException(403, "Invalid API key")
