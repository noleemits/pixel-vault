"""
app/routers/accounts.py — Account registration and API key management.
"""

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_account
from app.database import get_sync_db
from app.models import Account, ApiKey


router = APIRouter(tags=["accounts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    name: str = ""
    freemius_user_id: int | None = None
    freemius_plan_id: str | None = None
    license_key: str | None = None


class RegisterResponse(BaseModel):
    account_id: str
    api_key: str
    plan: str
    generations_limit: int
    sync_limit: int


class AccountStatusResponse(BaseModel):
    plan: str
    role: str = "user"
    generations_used: int
    generations_limit: int
    sync_limit: int
    plan_expires_at: str | None = None


# ---------------------------------------------------------------------------
# Plan limits (shared — also used by webhooks)
# ---------------------------------------------------------------------------

PLAN_LIMITS = {
    "free":   {"generations_limit": 3,   "sync_limit": 50},
    "solo":   {"generations_limit": 10,  "sync_limit": 100},
    "pro":    {"generations_limit": 40,  "sync_limit": 500},
    "agency": {"generations_limit": 120, "sync_limit": 999999},
}


# ---------------------------------------------------------------------------
# POST /api/v1/accounts/register — no auth required
# ---------------------------------------------------------------------------

@router.post("/accounts/register", response_model=RegisterResponse)
def register_account(body: RegisterRequest, db: Session = Depends(get_sync_db)):
    """
    Register a new account and issue an API key.

    Called by the WordPress plugin on Freemius activation.
    If email already has a key, returns 409.
    If email has an account but no key (dashboard-created), issues a key.
    """
    account = db.query(Account).filter(Account.email == body.email).first()

    if account:
        existing_key = db.query(ApiKey).filter(ApiKey.account_id == account.id).first()
        if existing_key:
            raise HTTPException(409, "Account already registered. API key was issued on first activation.")
        # Dashboard-created account with no API key — link Freemius data
        if body.freemius_user_id:
            account.freemius_user_id = body.freemius_user_id
        if body.freemius_plan_id:
            account.freemius_plan_id = body.freemius_plan_id
        if body.name:
            account.name = body.name
    else:
        limits = PLAN_LIMITS["free"]
        account = Account(
            email=body.email,
            name=body.name or body.email.split("@")[0],
            plan="free",
            generations_used=0,
            generations_limit=limits["generations_limit"],
            sync_limit=limits["sync_limit"],
            freemius_user_id=body.freemius_user_id,
            freemius_plan_id=body.freemius_plan_id,
            license_key=body.license_key,
        )
        db.add(account)
        db.flush()

    raw_key = f"pv_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        account_id=account.id,
        key_hash=key_hash,
        name="auto-generated",
    )
    db.add(api_key)
    db.commit()

    return RegisterResponse(
        account_id=str(account.id),
        api_key=raw_key,
        plan=account.plan,
        generations_limit=account.generations_limit,
        sync_limit=account.sync_limit,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/accounts/status — requires per-account auth
# ---------------------------------------------------------------------------

@router.get("/accounts/status", response_model=AccountStatusResponse)
def account_status(
    db: Session = Depends(get_sync_db),
    account: Account | None = Depends(get_current_account),
):
    """Return the caller's plan and usage."""
    if not account:
        return AccountStatusResponse(
            plan="admin",
            role="admin",
            generations_used=0,
            generations_limit=999999,
            sync_limit=999999,
        )

    return AccountStatusResponse(
        plan=account.plan,
        role=account.role,
        generations_used=account.generations_used,
        generations_limit=account.generations_limit,
        sync_limit=account.sync_limit,
        plan_expires_at=account.plan_expires_at.isoformat() if account.plan_expires_at else None,
    )
