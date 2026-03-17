from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tag, Image
from app.schemas import TagOut

router = APIRouter(tags=["tags"])

@router.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).order_by(Tag.name).all()

@router.post("/images/{image_id}/tags/{tag_name}", response_model=TagOut)
def add_tag(image_id: int, tag_name: str, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if not tag:
        tag = Tag(name=tag_name)
        db.add(tag)
        db.flush()
    if tag not in image.tags:
        image.tags.append(tag)
    db.commit()
    return tag

@router.delete("/images/{image_id}/tags/{tag_name}")
def remove_tag(image_id: int, tag_name: str, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if tag and tag in image.tags:
        image.tags.remove(tag)
        db.commit()
    return {"ok": True}
