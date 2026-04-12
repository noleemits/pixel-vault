"""
app/routers/admin.py — Admin endpoints for platform management.

All endpoints are protected by require_admin at the router level (see main.py).
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, case, extract
from sqlalchemy.orm import Session, joinedload

from app.database import get_sync_db as get_db
from app.models import Account, ApiKey, ApiLog, Image, Site, Batch
from app.routers.accounts import PLAN_LIMITS
from app.schemas import ImageOut

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AccountListItem(BaseModel):
    id: str
    email: str
    name: str
    plan: str
    role: str
    generations_used: int
    generations_limit: int
    sync_limit: int
    site_count: int
    image_count: int
    created_at: str


class AccountDetail(AccountListItem):
    freemius_user_id: int | None = None
    plan_expires_at: str | None = None
    license_key: str | None = None
    sites: list[dict] = []
    recent_images: list[dict] = []
    api_keys: list[dict] = []


class AccountUpdate(BaseModel):
    plan: str | None = None
    generations_limit: int | None = None
    sync_limit: int | None = None
    role: str | None = None


class BulkReviewRequest(BaseModel):
    image_ids: list[str]
    status: str  # "approved" or "rejected"
    quality_score: float | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_account(acct: Account, db: Session) -> dict:
    site_count = db.query(func.count(Site.id)).filter(Site.account_id == acct.id).scalar() or 0
    image_count = db.query(func.count(Image.id)).filter(Image.account_id == acct.id).scalar() or 0
    return {
        "id": str(acct.id),
        "email": acct.email,
        "name": acct.name,
        "plan": acct.plan,
        "role": acct.role,
        "generations_used": acct.generations_used,
        "generations_limit": acct.generations_limit,
        "sync_limit": acct.sync_limit,
        "site_count": site_count,
        "image_count": image_count,
        "created_at": acct.created_at.isoformat() if acct.created_at else "",
    }


# ---------------------------------------------------------------------------
# GET /admin/dashboard — Overview stats
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db)):
    # Accounts by plan
    plan_counts = (
        db.query(Account.plan, func.count(Account.id))
        .group_by(Account.plan)
        .all()
    )
    accounts_by_plan = {plan: count for plan, count in plan_counts}
    total_accounts = sum(accounts_by_plan.values())

    # Images by status
    status_counts = (
        db.query(Image.status, func.count(Image.id))
        .group_by(Image.status)
        .all()
    )
    images_by_status = {status: count for status, count in status_counts}
    total_images = sum(images_by_status.values())

    # Generations this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    generations_this_month = (
        db.query(func.count(Image.id))
        .filter(Image.created_at >= month_start)
        .scalar()
    ) or 0

    # Estimated MRR
    plan_prices = {p: info["price"] for p, info in PLAN_LIMITS.items()}
    mrr = 0.0
    for plan, count in accounts_by_plan.items():
        mrr += plan_prices.get(plan, 0) * count

    # Top 10 accounts by usage
    top_accounts = (
        db.query(Account.email, Account.generations_used, Account.plan)
        .order_by(Account.generations_used.desc())
        .limit(10)
        .all()
    )
    top_accounts_list = [
        {"email": email, "generations_used": used, "plan": plan}
        for email, used, plan in top_accounts
    ]

    # Recent API errors
    recent_errors = (
        db.query(ApiLog)
        .filter(ApiLog.status_code >= 400)
        .order_by(ApiLog.created_at.desc())
        .limit(20)
        .all()
    )
    errors_list = [
        {
            "id": log.id,
            "account_id": str(log.account_id) if log.account_id else None,
            "endpoint": log.endpoint,
            "method": log.method,
            "status_code": log.status_code,
            "response_time_ms": log.response_time_ms,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else "",
        }
        for log in recent_errors
    ]

    return {
        "total_accounts": total_accounts,
        "accounts_by_plan": accounts_by_plan,
        "total_images": total_images,
        "images_by_status": images_by_status,
        "generations_this_month": generations_this_month,
        "estimated_mrr": round(mrr, 2),
        "top_accounts": top_accounts_list,
        "recent_errors": errors_list,
    }


# ---------------------------------------------------------------------------
# GET /admin/accounts — List all accounts
# ---------------------------------------------------------------------------

@router.get("/accounts")
def list_accounts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    plan: str | None = None,
    search: str | None = None,
    sort: str = Query("newest", regex="^(newest|usage|name)$"),
    db: Session = Depends(get_db),
):
    q = db.query(Account)

    if plan:
        q = q.filter(Account.plan == plan)
    if search:
        pattern = f"%{search.lower()}%"
        q = q.filter(
            (func.lower(Account.email).like(pattern))
            | (func.lower(Account.name).like(pattern))
        )

    total = q.count()

    sort_map = {
        "newest": Account.created_at.desc(),
        "usage": Account.generations_used.desc(),
        "name": Account.name.asc(),
    }
    q = q.order_by(sort_map.get(sort, Account.created_at.desc()))

    accounts = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_account(a, db) for a in accounts],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# GET /admin/accounts/{id} — Account detail
# ---------------------------------------------------------------------------

@router.get("/accounts/{account_id}")
def get_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")

    base = _serialize_account(account, db)

    # Sites
    sites = db.query(Site).filter(Site.account_id == account.id).all()
    sites_list = [
        {
            "id": str(s.id),
            "name": s.name,
            "url": s.url,
            "industry": s.industry,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in sites
    ]

    # Recent images
    recent_images = (
        db.query(Image)
        .options(joinedload(Image.tags))
        .filter(Image.account_id == account.id)
        .order_by(Image.created_at.desc())
        .limit(20)
        .all()
    )
    images_list = [ImageOut.from_image(img).model_dump() for img in recent_images]

    # API keys (masked)
    api_keys = db.query(ApiKey).filter(ApiKey.account_id == account.id).all()
    keys_list = [
        {
            "id": str(k.id),
            "name": k.name,
            "key_preview": k.key_hash[:8] + "...",
            "created_at": k.created_at.isoformat() if k.created_at else "",
            "last_used": k.last_used.isoformat() if k.last_used else None,
        }
        for k in api_keys
    ]

    base.update({
        "freemius_user_id": account.freemius_user_id,
        "plan_expires_at": account.plan_expires_at.isoformat() if account.plan_expires_at else None,
        "license_key": account.license_key[:8] + "..." if account.license_key else None,
        "sites": sites_list,
        "recent_images": images_list,
        "api_keys": keys_list,
    })

    return base


# ---------------------------------------------------------------------------
# PATCH /admin/accounts/{id} — Update account
# ---------------------------------------------------------------------------

@router.patch("/accounts/{account_id}")
def update_account(account_id: str, body: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")

    if body.plan is not None:
        account.plan = body.plan
        # Auto-update limits when plan changes
        if body.plan in PLAN_LIMITS:
            limits = PLAN_LIMITS[body.plan]
            if body.generations_limit is None:
                account.generations_limit = limits["generations_limit"]
            if body.sync_limit is None:
                account.sync_limit = limits["sync_limit"]

    if body.generations_limit is not None:
        account.generations_limit = body.generations_limit
    if body.sync_limit is not None:
        account.sync_limit = body.sync_limit
    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise HTTPException(400, "Role must be 'user' or 'admin'")
        account.role = body.role

    db.commit()
    return _serialize_account(account, db)


# ---------------------------------------------------------------------------
# GET /admin/images/review-queue — Pending images
# ---------------------------------------------------------------------------

@router.get("/images/review-queue")
def review_queue(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Image).options(joinedload(Image.tags))

    # Images pending regular review OR community review (if column exists)
    has_community = hasattr(Image, "community_status")
    if has_community:
        q = q.filter(
            (Image.status == "pending")
            | (Image.community_status == "pending_review")
        )
    else:
        q = q.filter(Image.status == "pending")

    total = q.count()
    images = (
        q.order_by(Image.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = []
    for img in images:
        data = ImageOut.from_image(img).model_dump()
        # Include account info for context
        if img.account:
            data["account_email"] = img.account.email
            data["account_name"] = img.account.name
        else:
            data["account_email"] = None
            data["account_name"] = None
        items.append(data)

    return {"items": items, "total": total, "page": page, "per_page": per_page}


# ---------------------------------------------------------------------------
# POST /admin/images/bulk-review — Bulk approve/reject
# ---------------------------------------------------------------------------

@router.post("/images/bulk-review")
def bulk_review(body: BulkReviewRequest, db: Session = Depends(get_db)):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "Status must be 'approved' or 'rejected'")

    images = db.query(Image).filter(Image.id.in_(body.image_ids)).all()
    if not images:
        raise HTTPException(404, "No images found for the given IDs")

    for img in images:
        img.status = body.status
        if body.quality_score is not None:
            img.quality_score = body.quality_score
        # Also update community_status if applicable (from Task 018)
        if hasattr(img, "community_status") and img.community_status == "pending_review":
            img.community_status = body.status

    db.commit()
    return {"updated": len(images)}


# ---------------------------------------------------------------------------
# GET /admin/logs — API usage logs
# ---------------------------------------------------------------------------

@router.get("/logs")
def api_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    account_id: str | None = None,
    endpoint: str | None = None,
    status_min: int | None = None,
    status_max: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ApiLog)

    if account_id:
        q = q.filter(ApiLog.account_id == account_id)
    if endpoint:
        q = q.filter(ApiLog.endpoint.like(f"%{endpoint}%"))
    if status_min is not None:
        q = q.filter(ApiLog.status_code >= status_min)
    if status_max is not None:
        q = q.filter(ApiLog.status_code <= status_max)
    if date_from:
        q = q.filter(ApiLog.created_at >= date_from)
    if date_to:
        q = q.filter(ApiLog.created_at <= date_to)

    total = q.count()

    logs = (
        q.order_by(ApiLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Resolve account emails for display
    account_ids = {log.account_id for log in logs if log.account_id}
    account_map = {}
    if account_ids:
        accounts = db.query(Account.id, Account.email).filter(Account.id.in_(account_ids)).all()
        account_map = {str(aid): email for aid, email in accounts}

    items = [
        {
            "id": log.id,
            "account_id": str(log.account_id) if log.account_id else None,
            "account_email": account_map.get(str(log.account_id)) if log.account_id else None,
            "endpoint": log.endpoint,
            "method": log.method,
            "status_code": log.status_code,
            "response_time_ms": log.response_time_ms,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else "",
        }
        for log in logs
    ]

    return {"items": items, "total": total, "page": page, "per_page": per_page}


# ---------------------------------------------------------------------------
# GET /admin/revenue — Revenue breakdown
# ---------------------------------------------------------------------------

@router.get("/revenue")
def revenue(db: Session = Depends(get_db)):
    plan_prices = {p: info["price"] for p, info in PLAN_LIMITS.items()}

    # Plan breakdown
    plan_counts = (
        db.query(Account.plan, func.count(Account.id))
        .group_by(Account.plan)
        .all()
    )
    plan_breakdown = []
    total_accounts = 0
    paying_accounts = 0
    mrr = 0.0
    for plan, count in plan_counts:
        price = plan_prices.get(plan, 0)
        revenue = price * count
        plan_breakdown.append({
            "plan": plan,
            "count": count,
            "price": price,
            "revenue": round(revenue, 2),
        })
        total_accounts += count
        if price > 0:
            paying_accounts += count
        mrr += revenue

    # New accounts this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = (
        db.query(func.count(Account.id))
        .filter(Account.created_at >= month_start)
        .scalar()
    ) or 0

    # Churned: accounts whose plan expired this month
    churned_this_month = (
        db.query(func.count(Account.id))
        .filter(
            Account.plan_expires_at.isnot(None),
            Account.plan_expires_at >= month_start,
            Account.plan_expires_at <= now,
        )
        .scalar()
    ) or 0

    return {
        "mrr": round(mrr, 2),
        "total_accounts": total_accounts,
        "paying_accounts": paying_accounts,
        "plan_breakdown": plan_breakdown,
        "new_this_month": new_this_month,
        "churned_this_month": churned_this_month,
    }
