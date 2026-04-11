"""
app/routers/community.py — Community gallery endpoints.

Public browsing (no auth): GET /community/images
Authenticated: submit, vote, my-submissions
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_account
from app.database import get_sync_db as get_db
from app.models import Account, CommunityVote, Image, Tag, image_tags
from app.schemas import CommunityImageOut, ImageOut

router = APIRouter(prefix="/community", tags=["community"])


# ---------------------------------------------------------------------------
# POST /community/submit/{image_id}  (authenticated)
# ---------------------------------------------------------------------------

@router.post("/submit/{image_id}")
def submit_to_community(
    image_id: str,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    if account is None:
        raise HTTPException(401, "Authentication required")

    image = (
        db.query(Image)
        .options(joinedload(Image.tags))
        .filter(Image.id == image_id)
        .first()
    )
    if not image:
        raise HTTPException(404, "Image not found")
    if image.account_id != account.id:
        raise HTTPException(403, "You can only submit your own images")
    if image.status != "approved":
        raise HTTPException(400, "Image must be approved before community submission")
    if image.is_community and image.community_status is not None:
        raise HTTPException(400, "Image already submitted to community")

    image.is_community = True
    image.community_status = "pending_review"
    image.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(image)

    return ImageOut.from_image(image)


# ---------------------------------------------------------------------------
# GET /community/images  (public — optional auth for user_voted)
# ---------------------------------------------------------------------------

@router.get("/images")
def list_community_images(
    industry: str | None = None,
    style: str | None = None,
    tags: str | None = None,
    search: str | None = None,
    sort: str = Query("newest", regex="^(newest|oldest|most_voted|trending)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    from sqlalchemy import func

    q = (
        db.query(Image)
        .options(joinedload(Image.tags))
        .filter(Image.is_community == True, Image.community_status == "approved")
    )

    if industry:
        q = q.filter(Image.industry == industry)
    if style:
        q = q.filter(Image.style == style)
    if search:
        pattern = f"%{search.lower()}%"
        q = q.filter(
            (func.lower(Image.description).like(pattern))
            | (func.lower(Image.filename).like(pattern))
            | (func.lower(Image.industry).like(pattern))
            | (func.lower(Image.style).like(pattern))
        )
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            q = q.join(image_tags).join(Tag).filter(Tag.name.in_(tag_list)).distinct()

    sort_map = {
        "newest": Image.submitted_at.desc(),
        "oldest": Image.submitted_at.asc(),
        "most_voted": Image.community_votes.desc(),
        "trending": Image.community_votes.desc(),
    }
    q = q.order_by(sort_map.get(sort, Image.submitted_at.desc()))

    images = q.offset((page - 1) * per_page).limit(per_page).all()

    # Build account name lookup.
    account_ids = {img.account_id for img in images if img.account_id}
    account_names = {}
    if account_ids:
        accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
        account_names = {a.id: a.name for a in accounts}

    # Check which images the current user has voted on.
    voted_ids: set = set()
    if account is not None:
        image_ids = [img.id for img in images]
        if image_ids:
            votes = (
                db.query(CommunityVote.image_id)
                .filter(
                    CommunityVote.account_id == account.id,
                    CommunityVote.image_id.in_(image_ids),
                )
                .all()
            )
            voted_ids = {v.image_id for v in votes}

    return [
        CommunityImageOut.from_image(
            img,
            account_name=account_names.get(img.account_id, "Anonymous"),
            user_voted=img.id in voted_ids,
        )
        for img in images
    ]


# ---------------------------------------------------------------------------
# POST /community/{image_id}/vote  (authenticated)
# ---------------------------------------------------------------------------

@router.post("/{image_id}/vote")
def vote_community_image(
    image_id: str,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    if account is None:
        raise HTTPException(401, "Authentication required")

    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(404, "Image not found")
    if not image.is_community or image.community_status != "approved":
        raise HTTPException(400, "Image is not in the community gallery")

    existing = (
        db.query(CommunityVote)
        .filter(CommunityVote.image_id == image.id, CommunityVote.account_id == account.id)
        .first()
    )
    if existing:
        raise HTTPException(400, "Already voted")

    vote = CommunityVote(image_id=image.id, account_id=account.id)
    db.add(vote)
    image.community_votes += 1
    db.commit()

    return {"votes": image.community_votes}


# ---------------------------------------------------------------------------
# DELETE /community/{image_id}/vote  (authenticated)
# ---------------------------------------------------------------------------

@router.delete("/{image_id}/vote")
def unvote_community_image(
    image_id: str,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    if account is None:
        raise HTTPException(401, "Authentication required")

    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(404, "Image not found")

    vote = (
        db.query(CommunityVote)
        .filter(CommunityVote.image_id == image.id, CommunityVote.account_id == account.id)
        .first()
    )
    if not vote:
        raise HTTPException(400, "No vote to remove")

    db.delete(vote)
    image.community_votes = max(0, image.community_votes - 1)
    db.commit()

    return {"votes": image.community_votes}


# ---------------------------------------------------------------------------
# GET /community/my-submissions  (authenticated)
# ---------------------------------------------------------------------------

@router.get("/my-submissions")
def my_submissions(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    if account is None:
        raise HTTPException(401, "Authentication required")

    images = (
        db.query(Image)
        .options(joinedload(Image.tags))
        .filter(
            Image.account_id == account.id,
            Image.is_community == True,
            Image.community_status != None,
        )
        .order_by(Image.submitted_at.desc())
        .all()
    )

    return [
        CommunityImageOut.from_image(img, account_name=account.name)
        for img in images
    ]
