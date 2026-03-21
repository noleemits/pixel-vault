from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_sync_db as get_db
from app.models import Image, Tag, image_tags
from app.schemas import ImageOut, ImageReview

router = APIRouter(tags=["images"])

@router.get("/images", response_model=list[ImageOut])
def list_images(
    industry: str | None = None,
    style: str | None = None,
    ratio: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Image)
    if industry:
        q = q.filter(Image.industry == industry)
    if style:
        q = q.filter(Image.style == style)
    if ratio:
        q = q.filter(Image.ratio == ratio)
    if status:
        q = q.filter(Image.status == status)
    if tag:
        q = q.join(image_tags).join(Tag).filter(Tag.name == tag)
    return q.offset((page - 1) * per_page).limit(per_page).all()

@router.get("/images/{image_id}", response_model=ImageOut)
def get_image(image_id: str, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    return image

@router.get("/images/{image_id}/file")
def get_image_file(image_id: str, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    return FileResponse(image.filepath, media_type="image/jpeg")

@router.patch("/images/{image_id}/review", response_model=ImageOut)
def review_image(image_id: str, body: ImageReview, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    image.status = body.status
    if body.quality_score is not None:
        image.quality_score = body.quality_score
    db.commit()
    db.refresh(image)
    return image

@router.get("/stats")
def image_stats(db: Session = Depends(get_db)):
    total = db.query(Image).count()
    approved = db.query(Image).filter(Image.status == "approved").count()
    rejected = db.query(Image).filter(Image.status == "rejected").count()
    pending = db.query(Image).filter(Image.status == "pending").count()
    by_industry = {}
    for industry in ["healthcare", "real_estate", "food", "legal_finance", "fitness", "ecommerce"]:
        by_industry[industry] = db.query(Image).filter(Image.industry == industry).count()
    return {"total": total, "approved": approved, "rejected": rejected, "pending": pending, "by_industry": by_industry}
