from fastapi import APIRouter, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from fastapi import Depends
from app.database import get_sync_db as get_db
from app.models import Image, Tag, image_tags
from app.schemas import ImageOut

router = APIRouter(tags=["public"])


@router.get("/public/images")
def list_public_images(
    industry: str | None = None,
    style: str | None = None,
    ratio: str | None = None,
    tags: str | None = None,
    tag_mode: str = Query("or", regex="^(and|or)$"),
    search: str | None = None,
    sort: str = Query("newest", regex="^(newest|oldest|name|usage)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Public image browsing endpoint — NO authentication required.

    Only returns images where status='approved' and is_official=True.
    Supports filtering by industry, style, ratio, tags, and full-text search.
    """
    q = (
        db.query(Image)
        .options(joinedload(Image.tags))
        .filter(Image.status == "approved", Image.is_official == True)
    )

    if industry:
        q = q.filter(Image.industry == industry)
    if style:
        q = q.filter(Image.style == style)
    if ratio:
        q = q.filter(Image.ratio == ratio)
    if search:
        search_pattern = f"%{search.lower()}%"
        q = q.filter(
            (func.lower(Image.description).like(search_pattern))
            | (func.lower(Image.filename).like(search_pattern))
            | (func.lower(Image.industry).like(search_pattern))
            | (func.lower(Image.style).like(search_pattern))
        )

    # Multi-tag filter.
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            if tag_mode == "and":
                for t_name in tag_list:
                    tag_sub = (
                        db.query(image_tags.c.image_id)
                        .join(Tag)
                        .filter(Tag.name == t_name)
                        .subquery()
                    )
                    q = q.filter(Image.id.in_(db.query(tag_sub.c.image_id)))
            else:
                q = q.join(image_tags).join(Tag).filter(Tag.name.in_(tag_list))
                q = q.distinct()

    # Sorting.
    sort_map = {
        "newest": Image.created_at.desc(),
        "oldest": Image.created_at.asc(),
        "name": Image.filename.asc(),
        "usage": Image.usage_count.desc(),
    }
    q = q.order_by(sort_map.get(sort, Image.created_at.desc()))

    # Total count for pagination metadata.
    total = q.count()

    images = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "images": [ImageOut.from_image(img) for img in images],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/public/filters")
def get_public_filters(db: Session = Depends(get_db)):
    """
    Return available filter values for the public gallery.

    Only counts images where status='approved' and is_official=True,
    so the frontend never shows empty filter options.
    """
    base = db.query(Image).filter(
        Image.status == "approved", Image.is_official == True
    )

    # Industries with counts.
    industries = (
        base.with_entities(Image.industry, func.count(Image.id))
        .group_by(Image.industry)
        .order_by(func.count(Image.id).desc())
        .all()
    )

    # Tags with counts (only tags attached to public images).
    tag_counts = (
        db.query(Tag.name, func.count(image_tags.c.image_id))
        .join(image_tags)
        .join(Image)
        .filter(Image.status == "approved", Image.is_official == True)
        .group_by(Tag.name)
        .order_by(func.count(image_tags.c.image_id).desc())
        .all()
    )

    return {
        "industries": [
            {"value": ind, "count": cnt} for ind, cnt in industries
        ],
        "tags": [
            {"value": name, "count": cnt} for name, cnt in tag_counts
        ],
    }
