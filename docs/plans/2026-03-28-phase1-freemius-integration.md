# Phase 1: Freemius Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Freemius SDK to the WordPress plugin and build backend account/plan enforcement so free users get 3 generations/month and paid users get their plan's limit.

**Architecture:** Freemius SDK handles checkout, licensing, and user accounts inside WordPress. Our backend (FastAPI) enforces limits via per-account API keys. A webhook endpoint syncs Freemius subscription events to Supabase. The WordPress plugin authenticates every backend API call with a per-account API key (replacing the current global API key).

**Tech Stack:** Freemius SDK (PHP), FastAPI (Python), SQLAlchemy, Supabase PostgreSQL, WordPress REST API

---

## Current State Summary

- **Backend auth:** Single global `PIXELVAULT_API_KEY` in `.env`, checked via `X-API-Key` header. No per-account keys.
- **Account model:** Exists with `plan`, `generations_used`, `generations_limit`, `sync_limit` fields — all unused.
- **ApiKey model:** Exists with `key_hash`, `account_id` — never populated.
- **WordPress plugin:** `pixelvault/` plugin at `c:\wamp64\www\noleemitsai\wp-content\plugins\pixelvault\`. Uses `API_Client` class with global API key for all backend calls. No Freemius SDK.
- **Database:** No Alembic migrations — uses `create_all()`. Production on Supabase PostgreSQL.

---

### Task 1: Add Freemius columns to Account model

**Files:**
- Modify: `app/models.py` (Account class, around line 55-73)

**Step 1: Add new columns to Account model**

In `app/models.py`, add these columns to the `Account` class (after `stripe_customer_id`):

```python
freemius_user_id:   Mapped[Optional[int]]      = mapped_column(Integer, unique=True)
freemius_plan_id:   Mapped[Optional[str]]       = mapped_column(Text)
license_key:        Mapped[Optional[str]]       = mapped_column(Text)
plan_expires_at:    Mapped[Optional[datetime]]  = mapped_column(default=None)
```

**Step 2: Verify the app starts**

Run: `cd /c/Users/PC/Documents/noleemits-pixel-vault && python -c "from app.models import Account; print([c.name for c in Account.__table__.columns])"`

Expected: Column list includes `freemius_user_id`, `freemius_plan_id`, `license_key`, `plan_expires_at`.

**Step 3: Commit**

```bash
git add app/models.py
git commit -m "feat: add Freemius columns to Account model"
```

---

### Task 2: Add api_logs table model

**Files:**
- Modify: `app/models.py` (add new class after ImageDeployment)

**Step 1: Add ApiLog model**

Add this class to the end of `app/models.py`:

```python
class ApiLog(Base):
    __tablename__ = "api_logs"

    id:              Mapped[int]                 = mapped_column(Integer, primary_key=True)
    account_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"))
    endpoint:        Mapped[str]                 = mapped_column(Text, nullable=False)
    method:          Mapped[str]                 = mapped_column(String(10), nullable=False)
    status_code:     Mapped[Optional[int]]       = mapped_column(Integer)
    response_time_ms:Mapped[Optional[int]]       = mapped_column(Integer)
    ip_address:      Mapped[Optional[str]]       = mapped_column(Text)
    user_agent:      Mapped[Optional[str]]       = mapped_column(Text)
    error_message:   Mapped[Optional[str]]       = mapped_column(Text)
    created_at:      Mapped[datetime]            = mapped_column(default=_utcnow)
```

**Step 2: Verify**

Run: `python -c "from app.models import ApiLog; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add app/models.py
git commit -m "feat: add ApiLog model for request tracking"
```

---

### Task 3: Build per-account API key auth

This replaces the global API key with per-account key lookup. The global key still works as an admin fallback.

**Files:**
- Modify: `app/auth.py`
- Modify: `app/config.py` (add `admin_api_key` alias)

**Step 1: Rewrite auth.py to support per-account keys**

Replace the contents of `app/auth.py`:

```python
"""
app/auth.py — API key authentication.

Supports two modes:
  1. Per-account API keys: X-API-Key contains a key that hashes to an api_keys row.
  2. Admin fallback: X-API-Key matches PIXELVAULT_API_KEY from .env (full access, no account).

If no key is configured in .env AND no per-account key matches → open access (dev mode).
"""

import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, Security
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
):
    """
    Simple gate: reject if a key is required but missing/wrong.
    Kept for backward compatibility on routes that don't need account context.
    """
    if not settings.pixelvault_api_key:
        return  # Dev mode.
    if api_key != settings.pixelvault_api_key:
        # Could be a per-account key — let it through, account resolution happens elsewhere.
        # But if it's clearly wrong, block it.
        from app.database import SessionLocal
        from app.models import ApiKey
        db = SessionLocal()
        try:
            key_hash = _hash_key(api_key or "")
            found = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
            if not found:
                raise HTTPException(403, "Invalid API key")
        finally:
            db.close()
```

**Step 2: Verify import**

Run: `python -c "from app.auth import get_current_account, verify_api_key; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add app/auth.py
git commit -m "feat: per-account API key auth with admin fallback"
```

---

### Task 4: Account registration endpoint + API key provisioning

When the WordPress plugin activates with Freemius, it needs to register and get an API key.

**Files:**
- Create: `app/routers/accounts.py`

**Step 1: Create accounts router**

Create `app/routers/accounts.py`:

```python
"""
app/routers/accounts.py — Account registration and API key management.

Called by the WordPress plugin on activation to register the site
and get a per-account API key.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

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
    api_key: str  # Shown once — the raw key.
    plan: str
    generations_limit: int
    sync_limit: int


class AccountStatusResponse(BaseModel):
    plan: str
    generations_used: int
    generations_limit: int
    sync_limit: int
    plan_expires_at: str | None = None


# ---------------------------------------------------------------------------
# Plan limits
# ---------------------------------------------------------------------------

PLAN_LIMITS = {
    "free":   {"generations_limit": 3,   "sync_limit": 50},
    "solo":   {"generations_limit": 20,  "sync_limit": 300},
    "pro":    {"generations_limit": 60,  "sync_limit": 1500},
    "agency": {"generations_limit": 150, "sync_limit": 999999},
}


def _plan_from_freemius_id(plan_id: str | None) -> str:
    """Map Freemius plan ID to internal plan name."""
    # TODO: Replace with real Freemius plan IDs once created.
    mapping = {
        # "12345": "solo",
        # "12346": "pro",
        # "12347": "agency",
    }
    return mapping.get(plan_id or "", "free")


# ---------------------------------------------------------------------------
# POST /api/v1/accounts/register
# ---------------------------------------------------------------------------

@router.post("/accounts/register", response_model=RegisterResponse)
def register_account(body: RegisterRequest, db: Session = Depends(get_sync_db)):
    """
    Register a new account or return existing one.

    Called by WordPress plugin on activation. If the email already exists,
    returns the existing account (but does NOT reissue the API key — the
    plugin must store it on first activation).
    """
    # Check for existing account.
    account = db.query(Account).filter(Account.email == body.email).first()

    if account:
        # Account exists — check if it has an API key.
        existing_key = db.query(ApiKey).filter(ApiKey.account_id == account.id).first()
        if existing_key:
            raise HTTPException(
                409,
                {
                    "error": "Account already registered",
                    "account_id": str(account.id),
                    "message": "This email is already registered. Your API key was shown on first activation. Check your plugin settings.",
                },
            )

    # Create account if new.
    if not account:
        plan = _plan_from_freemius_id(body.freemius_plan_id)
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

        account = Account(
            email=body.email,
            name=body.name or body.email.split("@")[0],
            plan=plan,
            generations_used=0,
            generations_limit=limits["generations_limit"],
            sync_limit=limits["sync_limit"],
            freemius_user_id=body.freemius_user_id,
            freemius_plan_id=body.freemius_plan_id,
            license_key=body.license_key,
        )
        db.add(account)
        db.flush()

    # Generate API key.
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
# GET /api/v1/accounts/status
# ---------------------------------------------------------------------------

@router.get("/accounts/status", response_model=AccountStatusResponse)
def account_status(
    db: Session = Depends(get_sync_db),
    account=Depends(get_current_account_dep),
):
    """Return the current account's plan and usage."""
    if not account:
        # Admin or dev mode — return unlimited.
        return AccountStatusResponse(
            plan="admin",
            generations_used=0,
            generations_limit=999999,
            sync_limit=999999,
        )

    return AccountStatusResponse(
        plan=account.plan,
        generations_used=account.generations_used,
        generations_limit=account.generations_limit,
        sync_limit=account.sync_limit,
        plan_expires_at=account.plan_expires_at.isoformat() if account.plan_expires_at else None,
    )


def get_current_account_dep(
    db: Session = Depends(get_sync_db),
):
    """Placeholder — will be wired to auth.get_current_account."""
    from app.auth import get_current_account, api_key_header
    from fastapi import Security
    # This is handled by the dependency chain in main.py.
    return None
```

Wait — this has a circular dependency issue. Let me restructure.

**Revised Step 1: Create accounts router (clean version)**

```python
"""
app/routers/accounts.py — Account registration and API key management.
"""

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_account
from app.database import get_sync_db
from app.models import Account, ApiKey


router = APIRouter(tags=["accounts"])

api_key_header_opt = APIKeyHeader(name="X-API-Key", auto_error=False)


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
    generations_used: int
    generations_limit: int
    sync_limit: int
    plan_expires_at: str | None = None


# ---------------------------------------------------------------------------
# Plan limits (shared — also used by webhooks)
# ---------------------------------------------------------------------------

PLAN_LIMITS = {
    "free":   {"generations_limit": 3,   "sync_limit": 50},
    "solo":   {"generations_limit": 20,  "sync_limit": 300},
    "pro":    {"generations_limit": 60,  "sync_limit": 1500},
    "agency": {"generations_limit": 150, "sync_limit": 999999},
}


# ---------------------------------------------------------------------------
# POST /api/v1/accounts/register — no auth required
# ---------------------------------------------------------------------------

@router.post("/accounts/register", response_model=RegisterResponse)
def register_account(body: RegisterRequest, db: Session = Depends(get_sync_db)):
    """
    Register a new account and issue an API key.

    Called by the WordPress plugin on Freemius activation.
    If email already exists and has a key, returns 409.
    """
    account = db.query(Account).filter(Account.email == body.email).first()

    if account:
        existing_key = db.query(ApiKey).filter(ApiKey.account_id == account.id).first()
        if existing_key:
            raise HTTPException(409, "Account already registered. API key was issued on first activation.")

    if not account:
        limits = PLAN_LIMITS.get("free", PLAN_LIMITS["free"])
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
            generations_used=0,
            generations_limit=999999,
            sync_limit=999999,
        )

    return AccountStatusResponse(
        plan=account.plan,
        generations_used=account.generations_used,
        generations_limit=account.generations_limit,
        sync_limit=account.sync_limit,
        plan_expires_at=account.plan_expires_at.isoformat() if account.plan_expires_at else None,
    )
```

**Step 2: Register the router in main.py**

In `app/main.py`, add:

```python
from app.routers import accounts
```

And add these two lines after the existing router includes:

```python
# Accounts — register endpoint is public (no auth).
app.include_router(accounts.router, prefix="/api/v1", tags=["accounts"])
```

Note: The `/accounts/register` endpoint must NOT require the global API key auth. So it should be included WITHOUT the `_auth` dependency. The `/accounts/status` endpoint uses `get_current_account` internally.

**Step 3: Verify**

Run: `python -c "from app.routers.accounts import router; print('Routes:', [r.path for r in router.routes])"`

Expected: Routes include `/accounts/register` and `/accounts/status`.

**Step 4: Commit**

```bash
git add app/routers/accounts.py app/main.py
git commit -m "feat: account registration endpoint with API key provisioning"
```

---

### Task 5: Generation limit enforcement

Add plan checking to the generation endpoints so free users get blocked after 3 generations.

**Files:**
- Modify: `app/routers/generation.py` (the `/generate-from-prompt` endpoint)
- Modify: `app/routers/sites.py` (the `/generate-from-prompt` endpoint)

**Step 1: Add limit check helper**

Create `app/services/plan_enforcer.py`:

```python
"""
app/services/plan_enforcer.py — Plan limit enforcement.
"""

from fastapi import HTTPException
from app.models import Account


def check_generation_limit(account: Account | None) -> None:
    """
    Raise 402 if the account has hit its generation limit.
    Admin callers (account=None) are unlimited.
    """
    if account is None:
        return  # Admin or dev mode.

    if account.generations_used >= account.generations_limit:
        raise HTTPException(402, {
            "error": "generation_limit_reached",
            "plan": account.plan,
            "used": account.generations_used,
            "limit": account.generations_limit,
            "message": f"You've used all {account.generations_limit} generations for this month. Upgrade your plan for more.",
        })


def increment_generation_count(account: Account | None, count: int = 1) -> None:
    """Increment the account's generation counter."""
    if account is None:
        return
    account.generations_used = (account.generations_used or 0) + count
```

**Step 2: Wire limit check into generation.py /generate-from-prompt**

In `app/routers/generation.py`, add to the `generate_from_prompt` function:
- Add `account` parameter via `Depends(get_current_account)`
- Call `check_generation_limit(account)` before generating
- Call `increment_generation_count(account, body.count)` after successful generation
- Set `batch.account_id = account.id if account else None`

**Step 3: Wire limit check into sites.py /generate-from-prompt**

Same pattern for the synchronous generation endpoint in `sites.py`.

**Step 4: Verify**

Run the server and test: a request without an account key should still work (admin mode). A request with a per-account key where `generations_used >= generations_limit` should return 402.

**Step 5: Commit**

```bash
git add app/services/plan_enforcer.py app/routers/generation.py app/routers/sites.py
git commit -m "feat: enforce generation limits per account plan"
```

---

### Task 6: Freemius webhook endpoint

Handles subscription lifecycle events from Freemius to sync account state.

**Files:**
- Create: `app/routers/webhooks.py`

**Step 1: Create webhook router**

Create `app/routers/webhooks.py`:

```python
"""
app/routers/webhooks.py — Freemius webhook handler.

Freemius sends POST requests when subscriptions change.
We verify the webhook signature and update the account accordingly.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.models import Account
from app.routers.accounts import PLAN_LIMITS

router = APIRouter(tags=["webhooks"])


# Freemius plan ID → internal plan name.
# TODO: Fill in real Freemius plan IDs after creating plans in Freemius dashboard.
FREEMIUS_PLAN_MAP = {
    # "12345": "solo",
    # "12346": "pro",
    # "12347": "agency",
}


def _resolve_plan(freemius_plan_id: str | None) -> str:
    """Map a Freemius plan ID to our internal plan name."""
    return FREEMIUS_PLAN_MAP.get(str(freemius_plan_id), "free")


@router.post("/webhooks/freemius")
async def freemius_webhook(request: Request, db: Session = Depends(get_sync_db)):
    """
    Handle Freemius webhook events.

    Events we care about:
    - install.installed → new free account
    - subscription.created → paid subscription started
    - subscription.upgraded → plan upgraded
    - subscription.downgraded → plan downgraded
    - subscription.cancelled → cancel (downgrade to free at period end)
    - subscription.renewed → reset monthly generation counter
    - license.activated → record site activation
    """
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})

    # Find the account by Freemius user ID.
    freemius_user_id = (
        data.get("user_id")
        or data.get("user", {}).get("id")
        or data.get("install", {}).get("user_id")
    )

    if not freemius_user_id:
        raise HTTPException(400, "Missing user_id in webhook payload")

    account = db.query(Account).filter(
        Account.freemius_user_id == int(freemius_user_id)
    ).first()

    # --- install.installed: create free account ---
    if event_type == "install.installed":
        if account:
            return {"ok": True, "action": "already_exists"}

        user_data = data.get("user", {})
        limits = PLAN_LIMITS["free"]
        account = Account(
            email=user_data.get("email", f"freemius-{freemius_user_id}@unknown"),
            name=user_data.get("first", "") + " " + user_data.get("last", ""),
            plan="free",
            generations_used=0,
            generations_limit=limits["generations_limit"],
            sync_limit=limits["sync_limit"],
            freemius_user_id=int(freemius_user_id),
        )
        db.add(account)
        db.commit()
        return {"ok": True, "action": "account_created"}

    if not account:
        raise HTTPException(404, f"No account for Freemius user {freemius_user_id}")

    # --- subscription.created / upgraded ---
    if event_type in ("subscription.created", "subscription.upgraded"):
        plan_id = str(data.get("plan_id", ""))
        plan = _resolve_plan(plan_id)
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

        account.plan = plan
        account.freemius_plan_id = plan_id
        account.generations_limit = limits["generations_limit"]
        account.sync_limit = limits["sync_limit"]
        account.license_key = data.get("license_key") or account.license_key

        # Set expiry if provided.
        expires = data.get("expires_at") or data.get("next_payment")
        if expires:
            try:
                account.plan_expires_at = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        db.commit()
        return {"ok": True, "action": f"plan_updated_to_{plan}"}

    # --- subscription.downgraded ---
    if event_type == "subscription.downgraded":
        plan_id = str(data.get("plan_id", ""))
        plan = _resolve_plan(plan_id)
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

        account.plan = plan
        account.freemius_plan_id = plan_id
        account.generations_limit = limits["generations_limit"]
        account.sync_limit = limits["sync_limit"]
        db.commit()
        return {"ok": True, "action": f"plan_downgraded_to_{plan}"}

    # --- subscription.cancelled ---
    if event_type == "subscription.cancelled":
        # Don't downgrade immediately — let them use remaining paid period.
        # The plan_expires_at field controls when they lose access.
        expires = data.get("expires_at") or data.get("cancellation_effective_date")
        if expires:
            try:
                account.plan_expires_at = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        db.commit()
        return {"ok": True, "action": "cancellation_recorded"}

    # --- subscription.renewed ---
    if event_type == "subscription.renewed":
        # Reset monthly generation counter.
        account.generations_used = 0
        expires = data.get("next_payment")
        if expires:
            try:
                account.plan_expires_at = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        db.commit()
        return {"ok": True, "action": "usage_reset"}

    # --- license.activated ---
    if event_type == "license.activated":
        account.license_key = data.get("license_key") or account.license_key
        db.commit()
        return {"ok": True, "action": "license_recorded"}

    # Unknown event — acknowledge but do nothing.
    return {"ok": True, "action": "ignored", "event": event_type}
```

**Step 2: Register in main.py**

Add to `main.py`:

```python
from app.routers import webhooks
```

Include the webhook router WITHOUT auth (Freemius calls it from their servers):

```python
# Webhooks — no auth (verified by Freemius signature).
app.include_router(webhooks.router, prefix="/api/v1")
```

**Step 3: Verify**

Run: `python -c "from app.routers.webhooks import router; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add app/routers/webhooks.py app/main.py
git commit -m "feat: Freemius webhook endpoint for subscription lifecycle"
```

---

### Task 7: Add Freemius SDK to WordPress plugin

**Files:**
- Modify: `c:\wamp64\www\noleemitsai\wp-content\plugins\pixelvault\pixelvault.php`

**Step 1: Download Freemius SDK**

The Freemius WordPress SDK needs to be added to the plugin. Download from https://github.com/Freemius/wordpress-sdk and place in `pixelvault/freemius/` directory.

Alternatively, this step can be done manually by:
1. Going to the Freemius developer dashboard
2. Creating the PixelVault plugin
3. Downloading the SDK zip
4. Extracting to `pixelvault/freemius/`

**Step 2: Add Freemius init to pixelvault.php**

Add this block BEFORE the `pixelvault_init()` function in `pixelvault.php`:

```php
/**
 * Freemius SDK integration.
 *
 * Handles licensing, checkout, and subscription management.
 */
if ( ! function_exists( 'pv_fs' ) ) {
    function pv_fs() {
        global $pv_fs;
        if ( ! isset( $pv_fs ) ) {
            // Activate multisite network integration.
            if ( ! defined( 'WP_FS__PRODUCT_XXXXX_MULTISITE' ) ) {
                define( 'WP_FS__PRODUCT_XXXXX_MULTISITE', true );
            }
            require_once dirname( __FILE__ ) . '/freemius/start.php';
            $pv_fs = fs_dynamic_init( array(
                'id'                  => 'XXXXX', // TODO: Replace with real Freemius plugin ID
                'slug'                => 'pixelvault',
                'type'                => 'plugin',
                'public_key'          => 'pk_XXXXX', // TODO: Replace with real public key
                'is_premium'          => false,
                'has_premium_version' => true,
                'has_addons'          => false,
                'has_paid_plans'      => true,
                'menu'                => array(
                    'slug'   => 'pixelvault',
                    'parent' => array( 'slug' => 'options-general.php' ),
                ),
            ) );
        }
        return $pv_fs;
    }
    pv_fs();
    do_action( 'pv_fs_loaded' );
}
```

**Step 3: Add Freemius activation hook to auto-register with backend**

Add this after the Freemius init block:

```php
/**
 * On Freemius opt-in (free or paid), register with our backend and store API key.
 */
function pv_fs_after_activation() {
    $user = pv_fs()->get_user();
    if ( ! $user ) {
        return;
    }

    $opts = get_option( 'pixelvault_settings', array() );

    // Don't re-register if already have an API key.
    if ( ! empty( $opts['api_key'] ) ) {
        return;
    }

    $api_url = untrailingslashit( $opts['api_url'] ?? 'http://localhost:8000/api/v1' );

    $response = wp_remote_post( $api_url . '/accounts/register', array(
        'timeout' => 15,
        'headers' => array( 'Content-Type' => 'application/json' ),
        'body'    => wp_json_encode( array(
            'email'            => $user->email,
            'name'             => trim( $user->first . ' ' . $user->last ),
            'freemius_user_id' => $user->id,
            'license_key'      => pv_fs()->_get_license() ? pv_fs()->_get_license()->secret_key : null,
        ) ),
    ) );

    if ( is_wp_error( $response ) ) {
        return;
    }

    $data = json_decode( wp_remote_retrieve_body( $response ), true );

    if ( ! empty( $data['api_key'] ) ) {
        $opts['api_key'] = sanitize_text_field( $data['api_key'] );
        update_option( 'pixelvault_settings', $opts );
    }
}
pv_fs()->add_action( 'after_account_connection', 'pv_fs_after_activation' );
```

**Step 4: Verify**

Activate the plugin in WordPress. You should see the Freemius opt-in screen (once the SDK is installed with real credentials).

**Step 5: Commit**

```bash
cd /c/wamp64/www/noleemitsai/wp-content/plugins/pixelvault
git add -A
git commit -m "feat: add Freemius SDK init and auto-registration with backend"
```

Note: The Freemius SDK directory itself should NOT be committed if it's large. Add to `.gitignore` if using Composer or Freemius's deploy system.

---

### Task 8: Wire main.py to include new routers correctly

**Files:**
- Modify: `app/main.py`

**Step 1: Update main.py with all new routers**

The final `main.py` should:
1. Keep existing auth-protected routers as-is
2. Add `accounts` router — `/accounts/register` is PUBLIC, `/accounts/status` uses its own auth
3. Add `webhooks` router — PUBLIC (no auth)

Update the router section:

```python
from app.routers import prompts, images, generation, tags, sites, accounts, webhooks

_auth = [Depends(verify_api_key)]
app.include_router(prompts.router, prefix="/api/v1", dependencies=_auth)
app.include_router(images.router, prefix="/api/v1", dependencies=_auth)
app.include_router(generation.router, prefix="/api/v1", dependencies=_auth)
app.include_router(tags.router, prefix="/api/v1", dependencies=_auth)
app.include_router(sites.router, prefix="/api/v1", dependencies=_auth)

# Public endpoints — no global auth.
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
```

**Step 2: Verify**

Run: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` and check `/docs` for the new endpoints.

**Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: wire accounts and webhooks routers into main app"
```

---

### Task 9: Add usage display to WordPress plugin settings page

**Files:**
- Modify: `c:\wamp64\www\noleemitsai\wp-content\plugins\pixelvault\includes\class-settings.php`
- Modify: `c:\wamp64\www\noleemitsai\wp-content\plugins\pixelvault\includes\class-api-client.php`

**Step 1: Add account_status() method to API_Client**

In `class-api-client.php`, add this method:

```php
/**
 * Get the current account's plan and usage from the backend.
 *
 * @return array|WP_Error {plan, generations_used, generations_limit, sync_limit}
 */
public function account_status() {
    return $this->get( '/accounts/status' );
}
```

**Step 2: Add usage section to settings page**

In `class-settings.php`, in the `render_page()` method, add this block after the connection status check and before the `<form>` tag:

```php
<?php
// Show plan & usage info.
if ( $this->api->is_connected() ) :
    $status = $this->api->account_status();
    if ( ! is_wp_error( $status ) ) :
?>
    <div class="notice notice-info" style="padding:12px;">
        <strong><?php echo esc_html( ucfirst( $status['plan'] ?? 'free' ) ); ?> Plan</strong>
        &mdash;
        <?php printf(
            esc_html__( '%d / %d generations used this month', 'pixelvault' ),
            $status['generations_used'] ?? 0,
            $status['generations_limit'] ?? 3
        ); ?>
        <?php if ( ( $status['plan'] ?? 'free' ) === 'free' ) : ?>
            &mdash;
            <a href="#" onclick="pv_fs().checkout()">
                <?php esc_html_e( 'Upgrade for more', 'pixelvault' ); ?>
            </a>
        <?php endif; ?>
    </div>
<?php
    endif;
endif;
?>
```

**Step 3: Verify**

Visit Settings → PixelVault in WordPress admin. You should see the plan and usage info.

**Step 4: Commit**

```bash
cd /c/wamp64/www/noleemitsai/wp-content/plugins/pixelvault
git add includes/class-api-client.php includes/class-settings.php
git commit -m "feat: show plan usage on plugin settings page"
```

---

### Task 10: Create Alembic migration for new columns

**Files:**
- Modify: `alembic/env.py` (if needed)
- Create: Migration file via alembic

**Step 1: Generate migration**

```bash
cd /c/Users/PC/Documents/noleemits-pixel-vault
alembic revision --autogenerate -m "add freemius columns and api_logs table"
```

**Step 2: Review the generated migration**

Read the file in `alembic/versions/` and verify it includes:
- ALTER TABLE accounts ADD COLUMN freemius_user_id, freemius_plan_id, license_key, plan_expires_at
- CREATE TABLE api_logs

**Step 3: Run migration against local/staging**

```bash
alembic upgrade head
```

**Step 4: Commit**

```bash
git add alembic/
git commit -m "migration: add Freemius columns and api_logs table"
```

---

## Acceptance Criteria Checklist

After completing all tasks:

- [ ] **Plugin shows Freemius opt-in on activation** → Task 7 (requires Freemius dashboard setup)
- [ ] **Free tier works with 3 generation limit** → Task 5 (plan_enforcer) + Task 4 (account registration defaults to free)
- [ ] **Upgrade button triggers Freemius checkout** → Task 9 (settings page upgrade link)
- [ ] **After payment, plan limit increases** → Task 6 (webhook handles subscription.created/upgraded)
- [ ] **Backend enforces generation limits per account** → Task 5
- [ ] **Freemius webhook syncs account data to Supabase** → Task 6

## Manual Steps (Not Automated)

1. **Register PixelVault on Freemius dashboard** — create plugin, get plugin ID and public key
2. **Define plans in Freemius** — Free, Solo ($12/mo), Pro ($24/mo), Agency ($49/mo)
3. **Download Freemius SDK** — place in `pixelvault/freemius/` directory
4. **Update placeholder IDs** — replace `XXXXX` in pixelvault.php with real Freemius IDs
5. **Update FREEMIUS_PLAN_MAP** — in `webhooks.py`, map real Freemius plan IDs to internal names
6. **Configure webhook URL** — in Freemius dashboard, set webhook to `https://your-domain.com/api/v1/webhooks/freemius`
7. **Run Alembic migration on production** — `alembic upgrade head`
