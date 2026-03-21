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

    When test_mode=True, returns the full prompt that WOULD be sent to the
    model, plus matched library images, but does NOT trigger generation.
    """

    # 1. Build search keywords from post context.
    search_terms = _extract_search_terms(body)

    # 2. Query approved images, filtered by industry if provided.
    q = db.query(Image).filter(Image.status == "approved")
    if body.industry:
        q = q.filter(Image.industry == body.industry)

    candidates = q.all()

    # 3. Score each candidate against search terms.
    scored = []
    for img in candidates:
        score = _score_image(img, search_terms, body)
        if score > 0:
            scored.append((img, score))

    # Sort by score descending.
    scored.sort(key=lambda x: x[1], reverse=True)

    # Top 5 matches.
    matches = []
    for img, score in scored[:5]:
        confidence = min(score / 10.0, 1.0)  # Normalize to 0-1
        matches.append(MatchResult(
            image_id=str(img.id),
            filename=img.filename,
            industry=img.industry,
            style=img.style,
            confidence=round(confidence, 2),
            preview_url=f"/api/v1/images/{img.id}/file",
        ))

    # 4. Build suggested prompt if no high-confidence match.
    suggested_prompt = None
    final_prompt = None
    negative_preview = None

    if not matches or matches[0].confidence < 0.8:
        suggested_prompt = _build_suggested_prompt(body)

    # 5. In test mode, always show the full prompt that would be used.
    if body.test_mode:
        raw_prompt = suggested_prompt or _build_suggested_prompt(body)
        # Layer 1: global positive suffix
        final_prompt = f"{raw_prompt.rstrip(', ')}. {POSITIVE_SUFFIX}"
        # Layer 2: site style prefix
        if body.style_prefix:
            final_prompt = f"{final_prompt} {body.style_prefix.rstrip(', ')}."
        # Negative: global + site-specific
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
    """Pull keywords from post context."""
    terms = []

    # Focus keyword is highest signal.
    if body.focus_keyword:
        terms.extend(body.focus_keyword.lower().split())

    # Title words.
    if body.title:
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "for", "and", "or", "to", "in", "on", "at", "of", "with", "how", "what", "why", "when", "your", "you", "this", "that"}
        title_words = [w.lower().strip(".,!?:;\"'()") for w in body.title.split()]
        terms.extend(w for w in title_words if w and w not in stop_words and len(w) > 2)

    # Categories and tags.
    terms.extend(c.lower() for c in body.categories)
    terms.extend(t.lower() for t in body.tags)

    # Business type.
    if body.business_type:
        terms.extend(body.business_type.lower().split())

    return list(set(terms))


def _score_image(img: Image, search_terms: list[str], body: MatchRequest) -> float:
    """Score an image against search terms. Higher = better match."""
    score = 0.0

    # Match against filename.
    fname = img.filename.lower()
    for term in search_terms:
        if term in fname:
            score += 2.0

    # Match against style.
    style = (img.style or "").lower()
    for term in search_terms:
        if term in style:
            score += 3.0

    # Match against industry.
    if body.industry and img.industry == body.industry:
        score += 2.0

    # Match against prompt text (through the prompt relationship).
    # We check the prompt_id to look up the prompt text.
    # For performance, we match against filename patterns instead.
    for term in search_terms:
        if term in (img.industry or "").lower():
            score += 1.0

    # Penalize heavily-used images (prefer fresh ones).
    if img.usage_count and img.usage_count > 5:
        score -= 1.0

    return score


def _build_suggested_prompt(body: MatchRequest) -> str:
    """Build a generation prompt from post context + site profile."""
    parts = []

    # Business context.
    if body.business_type:
        parts.append(body.business_type)

    # From title.
    if body.title:
        parts.append(f"scene related to: {body.title}")

    # Focus keyword.
    if body.focus_keyword:
        parts.append(f"featuring {body.focus_keyword}")

    # Mood tags.
    if body.mood_tags:
        parts.append(", ".join(body.mood_tags) + " atmosphere")

    if not parts:
        parts.append("professional business photography")

    return ", ".join(parts)
