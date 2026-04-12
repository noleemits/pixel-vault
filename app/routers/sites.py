"""
app/routers/sites.py — Site profile, image matching, and deployment endpoints.

Used by the WordPress plugin to:
  1. Sync site style profile
  2. Match images to post context (with test/dry-run mode)
  3. Record and check image deployments (anti-duplicate)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.models import Image, Prompt, Site, ImageDeployment, Account
from app.services.fal_client import requires_hands, build_prompt, POSITIVE_SUFFIX, NEGATIVE_PROMPT
from app.services.auto_tagger import auto_tag_image
from app.auth import get_current_account
from app.services.plan_enforcer import check_generation_limit, increment_generation_count
from app.services.storage import r2

router = APIRouter(tags=["sites"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SiteProfilePayload(BaseModel):
    url: str
    name: str
    industry: str = ""
    business_type: str = ""
    location: str = ""
    mood_tags: list[str] = []
    style_prefix: str = ""
    negative_keywords: str = ""


class MatchRequest(BaseModel):
    title: str
    slug: str = ""
    content: str = ""
    categories: list[str] = []
    tags: list[str] = []
    focus_keyword: str = ""
    # Site profile (sent by plugin)
    industry: str = ""
    business_type: str = ""
    style_prefix: str = ""
    negative_keywords: str = ""
    mood_tags: list[str] = []
    # Test mode — returns prompt + matches but does NOT generate
    test_mode: bool = False


class MatchResult(BaseModel):
    image_id: str
    filename: str
    industry: str
    style: str
    confidence: float
    preview_url: str


class MatchResponse(BaseModel):
    matches: list[MatchResult]
    suggested_prompt: str | None = None
    final_prompt_preview: str | None = None
    negative_prompt_preview: str | None = None
    test_mode: bool = False


class GenerateFromPromptRequest(BaseModel):
    prompt: str
    count: int = 1
    ratio: str = "16:9"
    quality: str = "sd"
    style_prefix: str = ""
    negative_keywords: str = ""


class DeployPayload(BaseModel):
    site_url: str
    post_id: int
    post_title: str = ""
    local_filename: str = ""
    local_path: str = ""


class DeploymentOut(BaseModel):
    site_url: str
    post_id: int | None = None
    post_title: str = ""
    local_filename: str = ""


# ---------------------------------------------------------------------------
# GET /api/v1/sites — list all sites for the current account
# ---------------------------------------------------------------------------

@router.get("/sites")
def list_sites(
    db: Session = Depends(get_sync_db),
    account=Depends(get_current_account),
):
    """List all sites for the current account."""
    from app.models import Site, ImageDeployment
    from sqlalchemy import func

    if account is None:
        # Admin: return all sites
        sites = db.query(Site).order_by(Site.created_at.desc()).all()
    else:
        sites = (
            db.query(Site)
            .filter(Site.account_id == account.id)
            .order_by(Site.created_at.desc())
            .all()
        )

    result = []
    for site in sites:
        deployment_count = (
            db.query(func.count(ImageDeployment.id))
            .filter(
                ImageDeployment.site_id == site.id,
                ImageDeployment.is_active == True,
            )
            .scalar()
        )
        result.append(
            {
                "id": str(site.id),
                "name": site.name,
                "url": site.url,
                "industry": site.industry,
                "business_type": site.business_type,
                "location": site.location,
                "mood_tags": site.mood_tags or [],
                "style_prefix": site.style_prefix,
                "serve_from": site.serve_from,
                "active_deployments": deployment_count,
                "created_at": site.created_at.isoformat(),
            }
        )
    return result


# ---------------------------------------------------------------------------
# POST /api/v1/sites/profile — sync site style from WordPress plugin
# ---------------------------------------------------------------------------

@router.post("/sites/profile")
def sync_site_profile(body: SiteProfilePayload, db: Session = Depends(get_sync_db)):
    # Find or create site by URL.
    site = db.query(Site).filter(Site.url == body.url).first()
    if not site:
        site = Site(
            url=body.url,
            name=body.name,
            industry=body.industry,
        )
        db.add(site)
        db.flush()

    site.name = body.name
    site.industry = body.industry
    site.business_type = body.business_type
    site.location = body.location
    site.mood_tags = body.mood_tags
    site.style_prefix = body.style_prefix
    site.negative_keywords = body.negative_keywords
    db.commit()

    return {"ok": True, "site_id": str(site.id)}


# ---------------------------------------------------------------------------
# POST /api/v1/match — find images for a post context
# ---------------------------------------------------------------------------

@router.post("/match", response_model=MatchResponse)
def match_images(body: MatchRequest, db: Session = Depends(get_sync_db)):
    """
    Match library images to a post's context.

    Rules:
    - Only return matches with confidence >= 0.5 (50%).
    - Do NOT force site industry onto every post — use post content to
      determine the best industry match.
    - Suggested prompt is based on post content, not business type
      (business type only added when relevant).
    - test_mode=True shows prompt previews without triggering generation.
    """

    # 1. Extract search terms from POST CONTENT only (not business type).
    search_terms = _extract_search_terms(body)

    # 2. Determine which industry best fits the post content.
    #    Try the site industry first, but also search across ALL industries.
    q = db.query(Image).filter(Image.status == "approved")
    candidates = q.all()

    # 3. Score each candidate against search terms.
    scored = []
    for img in candidates:
        score = _score_image(img, search_terms, body)
        if score > 0:
            scored.append((img, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    # 4. Only keep matches above 50% confidence threshold.
    MIN_CONFIDENCE = 0.5
    matches = []
    for img, score in scored[:10]:
        confidence = min(score / 10.0, 1.0)
        if confidence < MIN_CONFIDENCE:
            break
        matches.append(MatchResult(
            image_id=str(img.id),
            filename=img.filename,
            industry=img.industry,
            style=img.style,
            confidence=round(confidence, 2),
            preview_url=img.cdn_url or f"/api/v1/images/{img.id}/file",
        ))

    # Cap at 5.
    matches = matches[:5]

    # 5. Build suggested prompt from POST CONTEXT (not business type).
    suggested_prompt = _build_suggested_prompt(body)
    final_prompt = None
    negative_preview = None

    if body.test_mode:
        final_prompt = f"{suggested_prompt.rstrip(', ')}. {POSITIVE_SUFFIX}"
        if body.style_prefix:
            final_prompt = f"{final_prompt} {body.style_prefix.rstrip(', ')}."
        negative_preview = NEGATIVE_PROMPT
        if body.negative_keywords:
            negative_preview = f"{negative_preview}, {body.negative_keywords}"

    return MatchResponse(
        matches=matches,
        suggested_prompt=suggested_prompt,
        final_prompt_preview=final_prompt,
        negative_prompt_preview=negative_preview,
        test_mode=body.test_mode,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/generate-from-prompt — generate image from raw prompt text
# ---------------------------------------------------------------------------

@router.post("/generate-from-prompt")
def generate_from_prompt(body: GenerateFromPromptRequest, db: Session = Depends(get_sync_db), account = Depends(get_current_account)):
    """
    Generate images from a raw prompt string (used by the WordPress plugin).

    This creates a temporary prompt record, then kicks off generation via
    the same pipeline as /generate.
    """
    check_generation_limit(account)

    import asyncio
    from app.models import Batch
    from app.services.fal_client import FalClient, requires_hands, build_prompt as fal_build_prompt
    from app.services.imagen_client import ImagenClient
    from app.services.image_processor import ImageProcessor
    from app.config import settings
    from datetime import datetime, timezone

    # Build the full prompt with style prefix.
    raw_prompt = body.prompt.strip()
    if body.style_prefix:
        raw_prompt = f"{raw_prompt}. {body.style_prefix}"

    # Find or create a prompt record for tracking.
    prompt_record = db.query(Prompt).filter(Prompt.name == "plugin-generated").first()
    if not prompt_record:
        prompt_record = Prompt(
            industry="custom",
            name="plugin-generated",
            prompt_text="Generated via WordPress plugin",
            use_case="plugin",
            ratios=body.ratio,
        )
        db.add(prompt_record)
        db.flush()

    # Create batch record.
    batch = Batch(
        prompt_id=prompt_record.id,
        account_id=account.id if account else None,
        image_count=body.count,
        ratio=body.ratio,
        status="generating",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Generate synchronously (plugin waits for result).
    try:
        # Quality mapping: sd=Standard 1K, hd=Standard 2K, premium=Ultra 2K
        quality_map = {
            "sd": ("standard", "1K"),
            "hd": ("standard", "2K"),
            "premium": ("ultra", "2K"),
        }
        model_quality, image_size = quality_map.get(body.quality, ("standard", "2K"))

        if requires_hands(raw_prompt):
            client = ImagenClient(api_key=settings.google_api_key, quality=model_quality)
            gen_coro = client.generate_batch(prompt=raw_prompt, ratio=body.ratio, count=body.count, size=image_size)
        else:
            client = FalClient(api_key=settings.fal_api_key)
            gen_coro = client.generate_batch(prompt=raw_prompt, ratio=body.ratio, count=body.count)

        # Run async generation in sync context.
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(gen_coro)
        loop.close()

        processor = ImageProcessor(storage_path=settings.storage_path)
        ratio_label = body.ratio.replace(":", "x")
        image_ids = []

        for i, result in enumerate(results):
            saved = processor.save_from_bytes(result["image_bytes"], "custom", "plugin", i + 1, ratio_label)

            # Upload to R2 if configured.
            storage_key = None
            cdn_url = None
            if r2.enabled:
                try:
                    storage_key = r2.build_key(saved["filename"])
                    cdn_url = r2.upload_file(saved["filepath"], storage_key)
                except Exception:
                    storage_key = None
                    cdn_url = None

            from app.models import Image as ImageModel
            image = ImageModel(
                filename=saved["filename"],
                filepath=saved["filepath"],
                storage_key_web=storage_key,
                cdn_url=cdn_url,
                industry="custom",
                style="plugin",
                ratio=body.ratio,
                prompt_id=prompt_record.id,
                batch_id=batch.id,
                status="approved",
                width=saved["width"],
                height=saved["height"],
                file_size=saved["file_size"],
                model_used="imagen4" if requires_hands(raw_prompt) else "flux",
                router_reason="people_detected" if requires_hands(raw_prompt) else "environment",
            )
            db.add(image)
            db.flush()
            auto_tag_image(db, image, raw_prompt, "custom")
            image_ids.append(str(image.id))

        # Free plan: images are automatically public (community).
        if account and account.plan == "free":
            for img in db.query(ImageModel).filter(ImageModel.batch_id == batch.id).all():
                img.is_community = True
                img.community_status = "pending_review"
                img.submitted_at = datetime.now(timezone.utc)

        batch.status = "completed"
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()

        increment_generation_count(account, body.count)
        db.commit()

        return {
            "ok": True,
            "batch_id": batch.id,
            "image_ids": image_ids,
            "count": len(image_ids),
            "message": f"Generated {len(image_ids)} image(s).",
        }

    except Exception as e:
        batch.status = "failed"
        db.commit()
        raise HTTPException(500, f"Generation failed: {str(e)}")


# ---------------------------------------------------------------------------
# GET /api/v1/images/{image_id}/deployments — anti-duplicate check
# ---------------------------------------------------------------------------

@router.get("/images/{image_id}/deployments")
def get_deployments(image_id: str, db: Session = Depends(get_sync_db)):
    deployments = (
        db.query(ImageDeployment)
        .filter(ImageDeployment.image_id == image_id, ImageDeployment.is_active == True)
        .all()
    )

    deployed_on = []
    for d in deployments:
        site = db.query(Site).filter(Site.id == d.site_id).first()
        deployed_on.append(DeploymentOut(
            site_url=site.url if site else "unknown",
            post_id=d.post_id,
            post_title=d.post_title or "",
            local_filename=d.local_filename or "",
        ))

    return {"deployed_on": deployed_on, "count": len(deployed_on)}


# ---------------------------------------------------------------------------
# POST /api/v1/images/{image_id}/deploy — record a deployment
# ---------------------------------------------------------------------------

@router.post("/images/{image_id}/deploy")
def record_deployment(image_id: str, body: DeployPayload, db: Session = Depends(get_sync_db)):
    # Find or create site.
    site = db.query(Site).filter(Site.url == body.site_url).first()
    if not site:
        site = Site(url=body.site_url, name=body.site_url)
        db.add(site)
        db.flush()

    # Check image exists.
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")

    # Record deployment.
    deployment = ImageDeployment(
        image_id=image.id,
        site_id=site.id,
        post_id=body.post_id,
        post_title=body.post_title,
        local_filename=body.local_filename,
        local_path=body.local_path,
    )
    db.add(deployment)

    # Increment usage count.
    image.usage_count = (image.usage_count or 0) + 1
    db.commit()

    return {"ok": True, "deployment_id": str(deployment.id)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_search_terms(body: MatchRequest) -> list[str]:
    """Pull keywords from POST CONTENT only — not from business profile."""
    terms = []

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "for", "and", "or",
        "to", "in", "on", "at", "of", "with", "how", "what", "why", "when",
        "your", "you", "this", "that", "can", "will", "its", "our", "their",
        "from", "about", "into", "more", "also", "than", "very", "just",
        "but", "not", "all", "been", "have", "has", "had", "they", "them",
        "some", "each", "which", "would", "could", "should", "does", "did",
        "get", "got", "make", "made", "way", "these", "those",
    }

    # Focus keyword is highest signal.
    if body.focus_keyword:
        terms.extend(body.focus_keyword.lower().split())

    # Title words (strongest signal after focus keyword).
    if body.title:
        title_words = [w.lower().strip(".,!?:;\"'()") for w in body.title.split()]
        terms.extend(w for w in title_words if w and w not in stop_words and len(w) > 2)

    # Categories and tags.
    terms.extend(c.lower() for c in body.categories)
    terms.extend(t.lower() for t in body.tags)

    # Content snippet — extract meaningful words.
    if body.content:
        content_words = [w.lower().strip(".,!?:;\"'()") for w in body.content.split()]
        content_terms = [w for w in content_words if w and w not in stop_words and len(w) > 3]
        # Only take most frequent content words (top 10).
        from collections import Counter
        common = Counter(content_terms).most_common(10)
        terms.extend(w for w, _ in common)

    # NOTE: business_type is intentionally NOT included here.
    # It would pollute results for posts that don't match the business.

    return list(set(terms))


def _score_image(img: Image, search_terms: list[str], body: MatchRequest) -> float:
    """
    Score an image against search terms. Higher = better match.

    Scoring is based ONLY on how well the image matches the post content,
    not on site industry (which could be wrong for a specific post).
    Now also checks image tags for stronger semantic matching.
    """
    score = 0.0
    if not search_terms:
        return 0.0

    fname = img.filename.lower()
    style = (img.style or "").lower()
    industry = (img.industry or "").lower()

    # Collect tag names for tag-based matching.
    tag_names = {t.name.lower() for t in img.tags} if img.tags else set()

    for term in search_terms:
        # Tag match (strongest signal — semantic labels).
        if term in tag_names:
            score += 5.0

        # Filename match (e.g. "fitness-yoga-001" matches "yoga").
        if term in fname:
            score += 3.0

        # Style match (e.g. style "yoga" matches term "yoga").
        if term in style:
            score += 4.0

        # Industry name match (e.g. "fitness" in terms matches fitness images).
        if term in industry:
            score += 2.0

    # Bonus if site industry matches image industry (mild preference, not forced).
    if body.industry and img.industry == body.industry:
        score += 1.0

    # Bonus for tag overlap with post categories/tags.
    if body.categories or body.tags:
        post_labels = {c.lower() for c in body.categories} | {t.lower() for t in body.tags}
        tag_overlap = tag_names & post_labels
        score += len(tag_overlap) * 3.0

    # Penalize heavily-used images (prefer fresh ones).
    if img.usage_count and img.usage_count > 5:
        score -= 0.5

    return score


def _build_suggested_prompt(body: MatchRequest) -> str:
    """
    Build a generation prompt from POST CONTEXT.

    Business type is only included when relevant to the post content.
    The prompt should describe what an ideal image for THIS post looks like.
    """
    parts = []

    # From title — this is the primary signal.
    if body.title:
        parts.append(f"professional photography related to: {body.title}")

    # Focus keyword adds specificity.
    if body.focus_keyword:
        parts.append(f"featuring {body.focus_keyword}")

    # Business context ONLY if it's relevant (appears in title/content).
    if body.business_type:
        bt_lower = body.business_type.lower()
        title_lower = (body.title or "").lower()
        content_lower = (body.content or "").lower()
        if any(word in title_lower or word in content_lower for word in bt_lower.split()):
            parts.append(f"{body.business_type} setting")

    # Mood tags for visual style.
    if body.mood_tags:
        parts.append(", ".join(body.mood_tags) + " atmosphere")

    if not parts:
        parts.append("professional editorial photography")

    return ", ".join(parts)
