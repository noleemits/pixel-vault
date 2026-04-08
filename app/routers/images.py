from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.database import get_sync_db as get_db
from app.models import Image, Tag, image_tags
from app.schemas import ImageOut, ImageReview

router = APIRouter(tags=["images"])

@router.get("/images")
def list_images(
    industry: str | None = None,
    style: str | None = None,
    ratio: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    tags: str | None = None,
    tag_mode: str = Query("or", regex="^(and|or)$"),
    batch_id: int | None = None,
    search: str | None = None,
    sort: str = Query("newest", regex="^(newest|oldest|name|usage)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List images with optional filters.

    - tag: single tag filter (backward compat)
    - tags: comma-separated list of tag names
    - tag_mode: "and" (all tags must match) or "or" (any tag matches, default)
    - batch_id: filter by generation batch
    - search: full-text search across description, filename, industry, style
    - sort: newest (default), oldest, name, usage
    """
    q = db.query(Image).options(joinedload(Image.tags))
    if industry:
        q = q.filter(Image.industry == industry)
    if style:
        q = q.filter(Image.style == style)
    if ratio:
        q = q.filter(Image.ratio == ratio)
    if status:
        q = q.filter(Image.status == status)
    if batch_id:
        q = q.filter(Image.batch_id == batch_id)
    if search:
        search_pattern = f"%{search.lower()}%"
        q = q.filter(
            (func.lower(Image.description).like(search_pattern))
            | (func.lower(Image.filename).like(search_pattern))
            | (func.lower(Image.industry).like(search_pattern))
            | (func.lower(Image.style).like(search_pattern))
        )

    # Single tag filter (backward compat).
    if tag:
        q = q.join(image_tags).join(Tag).filter(Tag.name == tag)
    # Multi-tag filter.
    elif tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            if tag_mode == "and":
                # AND: image must have ALL specified tags.
                for t_name in tag_list:
                    tag_sub = db.query(image_tags.c.image_id).join(Tag).filter(Tag.name == t_name).subquery()
                    q = q.filter(Image.id.in_(db.query(tag_sub.c.image_id)))
            else:
                # OR: image must have ANY of the specified tags.
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

    images = q.offset((page - 1) * per_page).limit(per_page).all()
    return [ImageOut.from_image(img) for img in images]

@router.get("/images/{image_id}")
def get_image(image_id: str, db: Session = Depends(get_db)):
    image = db.query(Image).options(joinedload(Image.tags)).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(404, "Image not found")
    return ImageOut.from_image(image)

@router.get("/images/{image_id}/file")
def get_image_file(image_id: str, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    return FileResponse(image.filepath, media_type="image/jpeg")

@router.patch("/images/{image_id}/review")
def review_image(image_id: str, body: ImageReview, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    image.status = body.status
    if body.quality_score is not None:
        image.quality_score = body.quality_score
    db.commit()
    # Re-query with tags loaded.
    image = db.query(Image).options(joinedload(Image.tags)).filter(Image.id == image_id).first()
    return ImageOut.from_image(image)

@router.get("/stats")
def image_stats(db: Session = Depends(get_db)):
    total = db.query(Image).count()
    approved = db.query(Image).filter(Image.status == "approved").count()
    rejected = db.query(Image).filter(Image.status == "rejected").count()
    pending = db.query(Image).filter(Image.status == "pending").count()
    by_industry = {}
    for industry in ["healthcare", "real_estate", "food", "legal_finance", "fitness", "ecommerce"]:
        by_industry[industry] = db.query(Image).filter(Image.industry == industry).count()
    # Tag stats: count images per tag.
    tag_counts_q = (
        db.query(Tag.name, func.count(image_tags.c.image_id))
        .join(image_tags)
        .group_by(Tag.name)
        .all()
    )
    by_tag = {name: count for name, count in tag_counts_q}

    return {
        "total": total, "approved": approved, "rejected": rejected,
        "pending": pending, "by_industry": by_industry, "by_tag": by_tag,
    }

@router.get("/billing")
def billing_stats(db: Session = Depends(get_db)):
    from app.models import Batch, ImageDeployment
    from sqlalchemy import func

    total_batches = db.query(Batch).filter(Batch.status == "completed").count()
    total_images = db.query(Image).count()

    # Count by model (estimate from filename patterns or model_used field).
    flux_count = db.query(Image).filter(Image.model_used == "flux").count()
    imagen_count = db.query(Image).filter(Image.model_used == "imagen4").count()
    # If model_used not tracked, estimate from all images.
    if flux_count == 0 and imagen_count == 0:
        # Rough split: count images without model_used field
        untracked = db.query(Image).filter(Image.model_used == None).count()
        # Use 80/20 split as estimate (38 Imagen prompts vs 10 FLUX)
        imagen_count = int(untracked * 0.8)
        flux_count = untracked - imagen_count

    flux_cost = flux_count * 0.04
    imagen_cost = imagen_count * 0.04
    total_cost = flux_cost + imagen_cost

    total_deployments = db.query(ImageDeployment).filter(ImageDeployment.is_active == True).count()

    return {
        "batches": total_batches,
        "images": total_images,
        "flux_count": flux_count,
        "imagen_count": imagen_count,
        "flux_cost": round(flux_cost, 2),
        "imagen_cost": round(imagen_cost, 2),
        "total_cost": round(total_cost, 2),
        "deployments": total_deployments,
    }
