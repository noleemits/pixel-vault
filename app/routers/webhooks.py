"""
app/routers/webhooks.py — Freemius webhook handler.

Freemius sends POST requests when subscriptions change.
We update the account accordingly.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.models import Account

router = APIRouter(tags=["webhooks"])


# Freemius plan ID → internal plan name.
# TODO: Fill in real Freemius plan IDs after creating plans in Freemius dashboard.
FREEMIUS_PLAN_MAP = {
    # "12345": "solo",
    # "12346": "pro",
    # "12347": "agency",
}

# Plan limits — imported from accounts router to stay DRY.
# Imported lazily to avoid circular imports.


def _resolve_plan(freemius_plan_id: str | None) -> str:
    """Map a Freemius plan ID to our internal plan name."""
    return FREEMIUS_PLAN_MAP.get(str(freemius_plan_id), "free")


def _get_plan_limits(plan: str) -> dict:
    """Get limits for a plan."""
    from app.routers.accounts import PLAN_LIMITS
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


@router.post("/webhooks/freemius")
async def freemius_webhook(request: Request, db: Session = Depends(get_sync_db)):
    """
    Handle Freemius webhook events.

    Events:
    - install.installed → new free account
    - subscription.created → paid subscription started
    - subscription.upgraded → plan upgraded
    - subscription.downgraded → plan downgraded
    - subscription.cancelled → cancel (downgrade at period end)
    - subscription.renewed → reset monthly generation counter
    - license.activated → record site activation
    """
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})

    # Find the Freemius user ID from various payload shapes.
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
        limits = _get_plan_limits("free")
        account = Account(
            email=user_data.get("email", f"freemius-{freemius_user_id}@unknown"),
            name=(user_data.get("first", "") + " " + user_data.get("last", "")).strip(),
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
        limits = _get_plan_limits(plan)

        account.plan = plan
        account.freemius_plan_id = plan_id
        account.generations_limit = limits["generations_limit"]
        account.sync_limit = limits["sync_limit"]
        account.license_key = data.get("license_key") or account.license_key

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
        limits = _get_plan_limits(plan)

        account.plan = plan
        account.freemius_plan_id = plan_id
        account.generations_limit = limits["generations_limit"]
        account.sync_limit = limits["sync_limit"]
        db.commit()
        return {"ok": True, "action": f"plan_downgraded_to_{plan}"}

    # --- subscription.cancelled ---
    if event_type == "subscription.cancelled":
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

    # Unknown event — acknowledge.
    return {"ok": True, "action": "ignored", "event": event_type}
