"""
app/services/admin_guard.py — Admin role guard for protected endpoints.

Usage:
    Apply as a router-level dependency so all admin endpoints are protected.
    Allows admin API key passthrough (account=None) for backward compat.
"""

from fastapi import Depends, HTTPException

from app.auth import get_current_account


async def require_admin(account=Depends(get_current_account)):
    if account is None:
        # Admin key passthrough — allow (backward compat)
        return account
    if account.role != "admin":
        raise HTTPException(403, "Admin access required")
    return account
