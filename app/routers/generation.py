import os
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_sync_db
from app.models import Prompt, Batch, Image
from app.schemas import GenerateBatchRequest, GenerateBatchResponse, GenerateFromPromptRequest, BatchOut
from app.services.fal_client import FalClient, requires_hands
from app.services.imagen_client import ImagenClient
from app.services.image_processor import ImageProcessor
from app.services.obsidian_logger import ObsidianLogger
from app.services.auto_tagger import auto_tag_image
from app.config import settings
from app.auth import get_current_account
from app.services.plan_enforcer import check_generation_limit, increment_generation_count

router = APIRouter(tags=["generation"])

async def _run_generation(batch_id: int, prompt_text: str, industry: str, style: str, ratio: str, count: int):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        batch = db.get(Batch, batch_id)
        batch.status = "generating"
        db.commit()

        processor = ImageProcessor(storage_path=settings.storage_path)

        if requires_hands(prompt_text):
            client = ImagenClient(api_key=settings.google_api_key)
            results = await client.generate_batch(prompt=prompt_text, ratio=ratio, count=count, size="2K")
        else:
            client = FalClient(api_key=settings.fal_api_key)
            results = await client.generate_batch(prompt=prompt_text, ratio=ratio, count=count)

        ratio_label = ratio.replace(":", "x")
        existing_count = db.query(Image).filter(Image.industry == industry, Image.style == style).count()

        for i, result in enumerate(results):
            number = existing_count + i + 1
            saved = processor.save_from_bytes(result["image_bytes"], industry, style, number, ratio_label)
            image = Image(
                filename=saved["filename"],
                filepath=saved["filepath"],
                industry=industry,
                style=style,
                ratio=ratio,
                prompt_id=batch.prompt_id,
                batch_id=batch.id,
                status="approved",
                width=saved["width"],
                height=saved["height"],
                file_size=saved["file_size"],
                description=prompt_text,
                model_used="imagen4" if requires_hands(prompt_text) else "flux",
                router_reason="people_detected" if requires_hands(prompt_text) else "environment",
            )
            db.add(image)
            db.flush()
            auto_tag_image(db, image, prompt_text, industry)

        batch.status = "completed"
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()

        prompt = db.get(Prompt, batch.prompt_id)
        if settings.obsidian_api_key:
            try:
                obsidian = ObsidianLogger(api_url=settings.obsidian_api_url, api_key=settings.obsidian_api_key)
                await obsidian.log_batch(
                    batch_id=batch.id,
                    industry=industry,
                    prompt_name=prompt.name,
                    prompt_text=prompt_text,
                    image_count=count,
                    status="completed",
                )
            except Exception:
                pass  # Obsidian logging is optional

    except Exception as e:
        batch = db.get(Batch, batch_id)
        if batch:
            batch.status = "failed"
            db.commit()
        raise
    finally:
        db.close()

@router.post("/generate", response_model=GenerateBatchResponse)
async def generate_batch(body: GenerateBatchRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_sync_db), account = Depends(get_current_account)):
    check_generation_limit(account)

    prompt = db.get(Prompt, body.prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")

    batch = Batch(prompt_id=prompt.id, account_id=account.id if account else None, image_count=body.count, ratio=body.ratio, status="pending")
    db.add(batch)
    db.commit()
    db.refresh(batch)

    increment_generation_count(account, body.count)
    db.commit()

    style = prompt.name.split("\u2014")[-1].strip().lower().split()[0] if "\u2014" in prompt.name else "general"

    background_tasks.add_task(
        _run_generation,
        batch_id=batch.id,
        prompt_text=prompt.prompt_text,
        industry=prompt.industry,
        style=style,
        ratio=body.ratio,
        count=body.count,
    )

    return GenerateBatchResponse(batch_id=batch.id, status="pending", message=f"Generating {body.count} images for '{prompt.name}'")

def _infer_industry(prompt_text: str) -> str:
    """Infer the best industry from prompt content. Returns the top match, never 'custom'."""
    lower = prompt_text.lower()
    industry_keywords = {
        "healthcare": ["dental", "clinic", "doctor", "patient", "medical", "nurse", "hospital", "therapy", "health", "dentist", "wellness", "surgery", "pharmaceutical", "care", "treatment"],
        "real_estate": ["house", "home", "apartment", "property", "real estate", "kitchen", "bedroom", "living room", "neighborhood", "curb appeal", "agent", "condo", "mortgage", "interior"],
        "food": ["restaurant", "food", "dish", "chef", "kitchen", "dining", "brunch", "coffee", "cuisine", "meal", "ingredient", "bar", "bakery", "catering"],
        "legal_finance": ["law", "legal", "attorney", "lawyer", "finance", "office", "consulting", "corporate", "investment", "bank", "accounting", "insurance", "advisory"],
        "fitness": ["gym", "fitness", "workout", "exercise", "yoga", "running", "training", "muscle", "strength", "flexibility", "athlete", "crossfit", "pilates", "sport"],
        "ecommerce": ["product", "shop", "store", "ecommerce", "fashion", "unboxing", "delivery", "package", "retail", "customer", "shopping", "brand", "merchandise"],
        "pet_care": ["dog", "cat", "pet", "veterinary", "vet", "grooming", "groomer", "puppy", "kitten", "animal", "kennel", "pet care", "pet salon"],
        "beauty": ["salon", "beauty", "spa", "hair", "nail", "skincare", "makeup", "cosmetic", "facial", "barber", "stylist", "manicure"],
        "education": ["school", "education", "university", "student", "teacher", "classroom", "tutor", "learning", "academy", "college", "course", "training center"],
        "home_services": ["plumber", "plumbing", "electrician", "hvac", "roofing", "contractor", "handyman", "landscaping", "cleaning", "renovation", "remodel", "repair"],
        "automotive": ["car", "auto", "vehicle", "mechanic", "dealership", "garage", "tire", "oil change", "automotive", "truck"],
        "technology": ["software", "tech", "startup", "app", "saas", "coding", "developer", "server", "cloud", "ai", "digital"],
    }
    scores = {}
    for industry, keywords in industry_keywords.items():
        scores[industry] = sum(1 for kw in keywords if kw in lower)
    best = max(scores, key=scores.get)
    # Always return a real industry — "custom" only as absolute last resort.
    return best if scores[best] > 0 else "ecommerce"


def _infer_all_industries(prompt_text: str) -> list[str]:
    """Return ALL industries that match the prompt (for multi-tag assignment)."""
    lower = prompt_text.lower()
    industry_keywords = {
        "healthcare": ["dental", "clinic", "doctor", "patient", "medical", "nurse", "hospital", "therapy", "health", "dentist", "wellness", "surgery"],
        "real_estate": ["house", "home", "apartment", "property", "real estate", "kitchen", "bedroom", "living room", "neighborhood"],
        "food": ["restaurant", "food", "dish", "chef", "dining", "brunch", "coffee", "cuisine", "meal", "bar", "bakery"],
        "legal_finance": ["law", "legal", "attorney", "lawyer", "finance", "office", "consulting", "corporate", "investment", "bank"],
        "fitness": ["gym", "fitness", "workout", "exercise", "yoga", "running", "training", "muscle", "strength", "athlete"],
        "ecommerce": ["product", "shop", "store", "ecommerce", "fashion", "unboxing", "retail", "customer", "shopping"],
        "pet_care": ["dog", "cat", "pet", "veterinary", "vet", "grooming", "groomer", "puppy", "kitten", "animal"],
        "beauty": ["salon", "beauty", "spa", "hair", "nail", "skincare", "makeup", "cosmetic", "facial", "barber"],
        "education": ["school", "education", "university", "student", "teacher", "classroom", "tutor", "learning"],
        "home_services": ["plumber", "plumbing", "electrician", "hvac", "roofing", "contractor", "handyman", "landscaping", "cleaning"],
        "automotive": ["car", "auto", "vehicle", "mechanic", "dealership", "garage", "tire", "automotive"],
        "technology": ["software", "tech", "startup", "app", "saas", "coding", "developer", "cloud", "ai"],
    }
    matched = []
    for industry, keywords in industry_keywords.items():
        if any(kw in lower for kw in keywords):
            matched.append(industry)
    return matched if matched else ["ecommerce"]


@router.post("/generate-from-prompt")
async def generate_from_prompt(body: GenerateFromPromptRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_sync_db), account = Depends(get_current_account)):
    """Generate images directly from a raw prompt string (used by WordPress plugin)."""
    check_generation_limit(account)

    # Infer industry from prompt content.
    industry = _infer_industry(body.prompt)

    # Create an ad-hoc prompt record so we can reuse the existing pipeline.
    prompt = Prompt(
        industry=industry,
        name=f"WP — {body.prompt[:60]} ({uuid4().hex[:8]})",
        prompt_text=body.prompt,
        use_case="wordpress",
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    batch = Batch(prompt_id=prompt.id, account_id=account.id if account else None, image_count=body.count, ratio=body.ratio, status="pending")
    db.add(batch)
    db.commit()
    db.refresh(batch)

    increment_generation_count(account, body.count)
    db.commit()

    # Determine size tier from quality.
    size = "2K" if body.quality == "hq" else "1K"

    background_tasks.add_task(
        _run_generation,
        batch_id=batch.id,
        prompt_text=body.prompt,
        industry=industry,
        style="general",
        ratio=body.ratio,
        count=body.count,
    )

    return {"batch_id": batch.id, "status": "pending", "message": f"Generating {body.count} image(s)"}


@router.get("/batches", response_model=list[BatchOut])
def list_batches(status: str | None = None, db: Session = Depends(get_sync_db)):
    q = db.query(Batch).order_by(Batch.id.desc())
    if status:
        q = q.filter(Batch.status == status)
    return q.all()

@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, db: Session = Depends(get_sync_db)):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    result = {
        "id": batch.id,
        "status": batch.status,
        "prompt_id": batch.prompt_id,
        "image_count": batch.image_count,
        "ratio": batch.ratio,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }

    # Include image details when batch is completed.
    if batch.status == "completed":
        images = db.query(Image).filter(Image.batch_id == batch_id).all()
        result["images"] = [
            {
                "id": str(img.id),
                "filename": img.filename,
                "url": f"/api/v1/images/{img.id}/file",
                "description": img.description,
                "width": img.width,
                "height": img.height,
                "industry": img.industry,
                "status": img.status,
            }
            for img in images
        ]

    return result
