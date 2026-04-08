from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_sync_db as get_db
from app.models import Tag, Image, image_tags
from app.schemas import TagOut, TagUpdate
from app.services.auto_tagger import PREDEFINED_TAGS, seed_tags

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).order_by(Tag.category, Tag.name).all()


@router.get("/tags/grouped")
def list_tags_grouped(db: Session = Depends(get_db)):
    """Return tags grouped by category with image counts."""
    tags = db.query(Tag).order_by(Tag.category, Tag.name).all()

    # Get counts via a single query.
    counts_q = (
        db.query(image_tags.c.tag_id, func.count(image_tags.c.image_id))
        .group_by(image_tags.c.tag_id)
        .all()
    )
    count_map = dict(counts_q)

    grouped: dict[str, list[dict]] = {}
    for tag in tags:
        cat = tag.category or "other"
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "id": tag.id,
            "name": tag.name,
            "count": count_map.get(tag.id, 0),
        })
    return grouped


@router.post("/tags/seed")
def seed_predefined_tags(db: Session = Depends(get_db)):
    """Create all predefined tags if they don't exist yet."""
    created = seed_tags(db)
    total = db.query(Tag).count()
    return {"created": created, "total": total}


@router.patch("/images/{image_id}/tags")
def update_image_tags(image_id: str, body: TagUpdate, db: Session = Depends(get_db)):
    """Add and/or remove tags from an image in one call."""
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")

    # Remove tags.
    for tag_name in body.remove:
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if tag and tag in image.tags:
            image.tags.remove(tag)

    # Add tags.
    for tag_name in body.add:
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            # Auto-create with category lookup.
            from app.services.auto_tagger import TAG_CATEGORY
            tag = Tag(name=tag_name, category=TAG_CATEGORY.get(tag_name))
            db.add(tag)
            db.flush()
        if tag not in image.tags:
            image.tags.append(tag)

    db.commit()
    db.refresh(image)
    return {"ok": True, "tags": [t.name for t in image.tags]}


@router.post("/images/{image_id}/tags/{tag_name}", response_model=TagOut)
def add_tag(image_id: str, tag_name: str, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if not tag:
        from app.services.auto_tagger import TAG_CATEGORY
        tag = Tag(name=tag_name, category=TAG_CATEGORY.get(tag_name))
        db.add(tag)
        db.flush()
    if tag not in image.tags:
        image.tags.append(tag)
    db.commit()
    return tag


@router.delete("/images/{image_id}/tags/{tag_name}")
def remove_tag(image_id: str, tag_name: str, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if tag and tag in image.tags:
        image.tags.remove(tag)
        db.commit()
    return {"ok": True}
