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
