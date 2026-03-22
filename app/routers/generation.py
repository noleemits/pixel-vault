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
from app.config import settings

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
                status="pending",
                width=saved["width"],
                height=saved["height"],
                file_size=saved["file_size"],
            )
            db.add(image)

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
async def generate_batch(body: GenerateBatchRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_sync_db)):
    prompt = db.get(Prompt, body.prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")

    batch = Batch(prompt_id=prompt.id, image_count=body.count, ratio=body.ratio, status="pending")
    db.add(batch)
    db.commit()
    db.refresh(batch)

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

@router.post("/generate-from-prompt")
async def generate_from_prompt(body: GenerateFromPromptRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_sync_db)):
    """Generate images directly from a raw prompt string (used by WordPress plugin)."""

    # Create an ad-hoc prompt record so we can reuse the existing pipeline.
    prompt = Prompt(
        industry="custom",
        name=f"WP — {body.prompt[:60]} ({uuid4().hex[:8]})",
        prompt_text=body.prompt,
        use_case="wordpress",
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    batch = Batch(prompt_id=prompt.id, image_count=body.count, ratio=body.ratio, status="pending")
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Determine size tier from quality.
    size = "2K" if body.quality == "hq" else "1K"

    background_tasks.add_task(
        _run_generation,
        batch_id=batch.id,
        prompt_text=body.prompt,
        industry="custom",
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

@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: int, db: Session = Depends(get_sync_db)):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    return batch
