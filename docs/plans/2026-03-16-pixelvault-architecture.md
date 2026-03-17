# PixelVault Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build PixelVault — an AI image bank platform that generates images via Google Imagen 4, serves them via REST API, integrates with WordPress plugins via a PHP bridge, and logs all work to Obsidian.

**Architecture:** FastAPI backend with SQLite (upgradeable to PostgreSQL) for metadata. Google Imagen 4 API for image generation (switched from FLUX 1.1 Pro after first batch review showed superior quality). Local file storage for images (`/storage/images/`). WordPress PHP bridge class using `wp_remote_*` functions. Obsidian integration via its Local REST API for work logging. Small-batch workflow: generate 3-5 images → manual review → prompt refinement → scale up.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, httpx (Google Imagen 4 API), Pydantic, SQLite, Pillow (image processing), PHP (WordPress bridge), Obsidian Local REST API.

---

## Project Structure

```
pixel-vault/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings & env vars
│   ├── database.py              # SQLAlchemy engine & session
│   ├── models.py                # DB models (Image, Prompt, Batch, Tag)
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── images.py            # GET/search/filter images
│   │   ├── generation.py        # POST generate batch, check status
│   │   ├── prompts.py           # CRUD master prompts
│   │   └── tags.py              # Tag management
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fal_client.py        # FLUX 1.1 Pro via fal.ai
│   │   ├── image_processor.py   # Resize, format, thumbnails
│   │   └── obsidian_logger.py   # Log to Obsidian vault
│   └── seed/
│       └── master_prompts.py    # 48 master prompts from the doc
├── storage/
│   └── images/                  # Generated images land here
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Fixtures (test DB, test client)
│   ├── test_models.py
│   ├── test_fal_client.py
│   ├── test_generation.py
│   ├── test_images_api.py
│   ├── test_prompts_api.py
│   └── test_obsidian_logger.py
├── wordpress/
│   └── class-pixelvault-bridge.php  # Drop-in PHP class for WP plugins
├── docs/
│   └── plans/
├── .env.example                 # Template for secrets
├── requirements.txt
└── README.md
```

---

## Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create requirements.txt**

```txt
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy==2.0.48
pydantic==2.12.5
pydantic-settings==2.13.1
httpx==0.28.1
pillow==12.1.0
python-multipart==0.0.20
aiofiles==24.1.0
pytest==8.4.1
pytest-asyncio==1.0.0
```

**Step 2: Create .env.example**

```env
FAL_KEY=your_fal_ai_api_key_here
OBSIDIAN_API_URL=https://127.0.0.1:27124
OBSIDIAN_API_KEY=your_obsidian_api_key_here
PIXELVAULT_API_KEY=your_api_key_for_wp_bridge
DATABASE_URL=sqlite:///./pixelvault.db
STORAGE_PATH=./storage/images
```

**Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
pixelvault.db
storage/images/*
!storage/images/.gitkeep
.pytest_cache/
```

**Step 4: Install dependencies**

Run: `pip install fastapi uvicorn[standard] python-multipart aiofiles pytest pytest-asyncio`
Expected: All packages install successfully.

**Step 5: Create empty init files and storage dir**

```bash
mkdir -p app/routers app/services app/seed tests storage/images
touch app/__init__.py app/routers/__init__.py app/services/__init__.py app/seed/__init__.py tests/__init__.py storage/images/.gitkeep
```

**Step 6: Init git repo and commit**

```bash
git init
git add -A
git commit -m "chore: scaffold project structure and dependencies"
```

---

## Task 2: Config & Database Foundation

**Files:**
- Create: `app/config.py`
- Create: `app/database.py`
- Create: `app/models.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, Image, Prompt, Batch, Tag

def test_create_tables():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    table_names = Base.metadata.tables.keys()
    assert "images" in table_names
    assert "prompts" in table_names
    assert "batches" in table_names
    assert "tags" in table_names

def test_create_prompt_and_image():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        prompt = Prompt(
            industry="healthcare",
            name="Modern Dental Clinic — Hero",
            prompt_text="Bright modern dental clinic interior...",
            use_case="Homepage hero, about page banner",
            ratios="16:9,4:3",
            kontext_variations="Change season lighting / swap to female dentist",
        )
        session.add(prompt)
        session.flush()

        batch = Batch(status="completed", prompt_id=prompt.id, image_count=4)
        session.add(batch)
        session.flush()

        image = Image(
            filename="healthcare-hero-01-16x9.jpg",
            filepath="storage/images/healthcare-hero-01-16x9.jpg",
            industry="healthcare",
            style="hero",
            ratio="16:9",
            prompt_id=prompt.id,
            batch_id=batch.id,
            status="approved",
            quality_score=8,
        )
        session.add(image)
        session.commit()

        assert image.id is not None
        assert image.prompt.name == "Modern Dental Clinic — Hero"
        assert batch.images[0].filename == "healthcare-hero-01-16x9.jpg"
```

**Step 2: Run test to verify it fails**

Run: `cd c:/Users/PC/Documents/noleemits-pixel-vault && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

**Step 3: Write config.py**

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    fal_key: str = ""
    obsidian_api_url: str = "https://127.0.0.1:27124"
    obsidian_api_key: str = ""
    pixelvault_api_key: str = ""
    database_url: str = "sqlite:///./pixelvault.db"
    storage_path: str = "./storage/images"

    model_config = {"env_file": ".env"}

settings = Settings()
```

**Step 4: Write database.py**

```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 5: Write models.py**

```python
# app/models.py
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

image_tags = Table(
    "image_tags",
    Base.metadata,
    Column("image_id", Integer, ForeignKey("images.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    industry: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(200))
    prompt_text: Mapped[str] = mapped_column(Text)
    use_case: Mapped[str] = mapped_column(String(500), default="")
    ratios: Mapped[str] = mapped_column(String(100), default="")
    kontext_variations: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    images: Mapped[list["Image"]] = relationship(back_populates="prompt")
    batches: Mapped[list["Batch"]] = relationship(back_populates="prompt")

class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, generating, completed, failed
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"))
    image_count: Mapped[int] = mapped_column(Integer, default=4)
    ratio: Mapped[str] = mapped_column(String(10), default="16:9")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    prompt: Mapped["Prompt"] = relationship(back_populates="batches")
    images: Mapped[list["Image"]] = relationship(back_populates="batch")

class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(300), unique=True)
    filepath: Mapped[str] = mapped_column(String(500))
    industry: Mapped[str] = mapped_column(String(50), index=True)
    style: Mapped[str] = mapped_column(String(50), index=True)  # hero, lifestyle, team, abstract, product
    ratio: Mapped[str] = mapped_column(String(10))
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"))
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    quality_score: Mapped[int | None] = mapped_column(Integer, default=None)
    fal_request_id: Mapped[str | None] = mapped_column(String(200), default=None)
    width: Mapped[int | None] = mapped_column(Integer, default=None)
    height: Mapped[int | None] = mapped_column(Integer, default=None)
    file_size: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    prompt: Mapped["Prompt"] = relationship(back_populates="images")
    batch: Mapped["Batch"] = relationship(back_populates="images")
    tags: Mapped[list["Tag"]] = relationship(secondary=image_tags, back_populates="images")

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    images: Mapped[list["Image"]] = relationship(secondary=image_tags, back_populates="tags")
```

**Step 6: Run test to verify it passes**

Run: `cd c:/Users/PC/Documents/noleemits-pixel-vault && python -m pytest tests/test_models.py -v`
Expected: 2 PASSED

**Step 7: Commit**

```bash
git add app/config.py app/database.py app/models.py tests/test_models.py
git commit -m "feat: add database models for images, prompts, batches, tags"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `app/schemas.py`

**Step 1: Write schemas.py**

```python
# app/schemas.py
from datetime import datetime
from pydantic import BaseModel

# --- Prompts ---
class PromptOut(BaseModel):
    id: int
    industry: str
    name: str
    prompt_text: str
    use_case: str
    ratios: str
    kontext_variations: str
    created_at: datetime
    model_config = {"from_attributes": True}

class PromptUpdate(BaseModel):
    name: str | None = None
    prompt_text: str | None = None
    use_case: str | None = None
    ratios: str | None = None
    kontext_variations: str | None = None

# --- Batches ---
class BatchCreate(BaseModel):
    prompt_id: int
    image_count: int = 4
    ratio: str = "16:9"

class BatchOut(BaseModel):
    id: int
    status: str
    prompt_id: int
    image_count: int
    ratio: str
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}

# --- Images ---
class ImageOut(BaseModel):
    id: int
    filename: str
    filepath: str
    industry: str
    style: str
    ratio: str
    status: str
    quality_score: int | None
    width: int | None
    height: int | None
    file_size: int | None
    prompt_id: int
    batch_id: int
    tags: list[str] = []
    created_at: datetime
    model_config = {"from_attributes": True}

class ImageReview(BaseModel):
    status: str  # approved / rejected
    quality_score: int | None = None

class ImageFilter(BaseModel):
    industry: str | None = None
    style: str | None = None
    ratio: str | None = None
    status: str | None = None
    tag: str | None = None
    page: int = 1
    per_page: int = 20

# --- Generation ---
class GenerateBatchRequest(BaseModel):
    prompt_id: int
    count: int = 4       # images per batch (default 4, recommend 3-5 for review)
    ratio: str = "16:9"

class GenerateBatchResponse(BaseModel):
    batch_id: int
    status: str
    message: str

# --- Tags ---
class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}
```

**Step 2: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add Pydantic schemas for API request/response"
```

---

## Task 4: fal.ai Client Service

**Files:**
- Create: `app/services/fal_client.py`
- Test: `tests/test_fal_client.py`

**Step 1: Write the failing test**

```python
# tests/test_fal_client.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.fal_client import FalClient

@pytest.mark.asyncio
async def test_generate_image_returns_url():
    mock_response = {
        "images": [{"url": "https://fal.media/files/test/image1.jpg", "width": 1920, "height": 1080}]
    }
    client = FalClient(api_key="test-key")
    with patch.object(client, "_post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.generate_image(
            prompt="A bright modern dental clinic",
            ratio="16:9",
        )
    assert result["url"] == "https://fal.media/files/test/image1.jpg"
    assert result["width"] == 1920

@pytest.mark.asyncio
async def test_generate_image_batch():
    mock_response = {
        "images": [{"url": f"https://fal.media/files/test/img{i}.jpg", "width": 1920, "height": 1080} for i in range(3)]
    }
    client = FalClient(api_key="test-key")
    with patch.object(client, "_post", new_callable=AsyncMock, return_value=mock_response):
        results = await client.generate_batch(
            prompt="A bright modern dental clinic",
            ratio="16:9",
            count=3,
        )
    assert len(results) == 3
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fal_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write fal_client.py**

```python
# app/services/fal_client.py
import httpx

RATIO_TO_SIZE = {
    "16:9": {"width": 1920, "height": 1080},
    "4:3":  {"width": 1440, "height": 1080},
    "1:1":  {"width": 1024, "height": 1024},
    "4:5":  {"width": 1024, "height": 1280},
    "9:16": {"width": 1080, "height": 1920},
    "21:9": {"width": 2560, "height": 1080},
}

class FalClient:
    BASE_URL = "https://fal.run/fal-ai/flux-pro/v1.1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _post(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def generate_image(self, prompt: str, ratio: str = "16:9") -> dict:
        size = RATIO_TO_SIZE.get(ratio, RATIO_TO_SIZE["16:9"])
        payload = {
            "prompt": prompt,
            "image_size": size,
            "num_images": 1,
            "safety_tolerance": "2",
        }
        result = await self._post(payload)
        img = result["images"][0]
        return {"url": img["url"], "width": img.get("width", size["width"]), "height": img.get("height", size["height"])}

    async def generate_batch(self, prompt: str, ratio: str = "16:9", count: int = 4) -> list[dict]:
        size = RATIO_TO_SIZE.get(ratio, RATIO_TO_SIZE["16:9"])
        payload = {
            "prompt": prompt,
            "image_size": size,
            "num_images": count,
            "safety_tolerance": "2",
        }
        result = await self._post(payload)
        return [
            {"url": img["url"], "width": img.get("width", size["width"]), "height": img.get("height", size["height"])}
            for img in result["images"]
        ]
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fal_client.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add app/services/fal_client.py tests/test_fal_client.py
git commit -m "feat: add Google Imagen 4 client for image generation image generation"
```

---

## Task 5: Image Processor Service

**Files:**
- Create: `app/services/image_processor.py`
- Test: `tests/test_image_processor.py`

**Step 1: Write the failing test**

```python
# tests/test_image_processor.py
import os
import tempfile
import pytest
from PIL import Image as PILImage
from app.services.image_processor import ImageProcessor

def test_download_and_save(tmp_path):
    # Create a fake image in memory, save it, verify
    processor = ImageProcessor(storage_path=str(tmp_path))
    fake_img = PILImage.new("RGB", (1920, 1080), color="blue")
    saved = processor.save_from_pil(fake_img, "healthcare", "hero", 1, "16x9")
    assert os.path.exists(saved["filepath"])
    assert saved["filename"] == "healthcare-hero-001-16x9.jpg"
    assert saved["file_size"] > 0

def test_filename_convention():
    processor = ImageProcessor(storage_path="/tmp")
    name = processor.build_filename("real_estate", "lifestyle", 12, "4x3")
    assert name == "real_estate-lifestyle-012-4x3.jpg"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_image_processor.py -v`
Expected: FAIL

**Step 3: Write image_processor.py**

```python
# app/services/image_processor.py
import os
from io import BytesIO
import httpx
from PIL import Image as PILImage

class ImageProcessor:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def build_filename(self, industry: str, style: str, number: int, ratio_label: str) -> str:
        return f"{industry}-{style}-{number:03d}-{ratio_label}.jpg"

    def save_from_pil(self, img: PILImage.Image, industry: str, style: str, number: int, ratio_label: str) -> dict:
        filename = self.build_filename(industry, style, number, ratio_label)
        filepath = os.path.join(self.storage_path, filename)
        img.save(filepath, "JPEG", quality=92)
        file_size = os.path.getsize(filepath)
        return {"filename": filename, "filepath": filepath, "file_size": file_size, "width": img.width, "height": img.height}

    async def download_and_save(self, url: str, industry: str, style: str, number: int, ratio_label: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        img = PILImage.open(BytesIO(resp.content))
        return self.save_from_pil(img, industry, style, number, ratio_label)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_image_processor.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add app/services/image_processor.py tests/test_image_processor.py
git commit -m "feat: add image processor for download, save, naming"
```

---

## Task 6: Obsidian Logger Service

**Files:**
- Create: `app/services/obsidian_logger.py`
- Test: `tests/test_obsidian_logger.py`

**Step 1: Write the failing test**

```python
# tests/test_obsidian_logger.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.obsidian_logger import ObsidianLogger

@pytest.mark.asyncio
async def test_log_batch_creates_note():
    logger = ObsidianLogger(api_url="https://127.0.0.1:27124", api_key="test-key")
    mock_resp = AsyncMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.put", new_callable=AsyncMock, return_value=mock_resp) as mock_put:
        await logger.log_batch(
            batch_id=1,
            industry="healthcare",
            prompt_name="Modern Dental Clinic",
            prompt_text="Bright modern dental clinic...",
            image_count=4,
            status="completed",
        )
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        assert "PixelVault/Batches/" in str(call_args)

@pytest.mark.asyncio
async def test_log_review_appends_to_note():
    logger = ObsidianLogger(api_url="https://127.0.0.1:27124", api_key="test-key")
    mock_resp = AsyncMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        await logger.log_review(
            batch_id=1,
            approved=["img1.jpg", "img2.jpg"],
            rejected=["img3.jpg"],
            notes="Good lighting, hands need work on img3",
        )
        mock_post.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_obsidian_logger.py -v`
Expected: FAIL

**Step 3: Write obsidian_logger.py**

```python
# app/services/obsidian_logger.py
from datetime import datetime, timezone
import httpx

class ObsidianLogger:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "text/markdown"}

    async def log_batch(self, batch_id: int, industry: str, prompt_name: str, prompt_text: str, image_count: int, status: str):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = f"""---
batch_id: {batch_id}
industry: {industry}
status: {status}
date: {now}
---

# Batch {batch_id}: {prompt_name}

**Industry:** {industry}
**Status:** {status}
**Images:** {image_count}
**Generated:** {now}

## Prompt
```
{prompt_text}
```

## Review
_Pending review_
"""
        path = f"PixelVault/Batches/batch-{batch_id:04d}.md"
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            await client.put(
                f"{self.api_url}/vault/{path}",
                headers=self._headers(),
                content=content,
            )

    async def log_review(self, batch_id: int, approved: list[str], rejected: list[str], notes: str):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = f"""

## Review — {now}
**Approved:** {', '.join(approved)}
**Rejected:** {', '.join(rejected)}
**Notes:** {notes}
"""
        path = f"PixelVault/Batches/batch-{batch_id:04d}.md"
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            await client.post(
                f"{self.api_url}/vault/{path}",
                headers={**self._headers(), "Content-Type": "text/markdown", "Content-Insertion-Position": "end"},
                content=content,
            )

    async def log_prompt_change(self, prompt_id: int, prompt_name: str, old_text: str, new_text: str, reason: str):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = f"""---
prompt_id: {prompt_id}
date: {now}
---

# Prompt Edit: {prompt_name}

**Date:** {now}
**Reason:** {reason}

## Before
```
{old_text}
```

## After
```
{new_text}
```
"""
        path = f"PixelVault/Prompt-History/prompt-{prompt_id:03d}-{now[:10]}.md"
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            await client.put(
                f"{self.api_url}/vault/{path}",
                headers=self._headers(),
                content=content,
            )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_obsidian_logger.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add app/services/obsidian_logger.py tests/test_obsidian_logger.py
git commit -m "feat: add Obsidian logger for batch/review/prompt tracking"
```

---

## Task 7: Seed Master Prompts

**Files:**
- Create: `app/seed/master_prompts.py`

**Step 1: Write the seed file with all 48 prompts**

```python
# app/seed/master_prompts.py
"""
48 master prompts from PixelVault_ImageBankPlan.docx.
Each entry: (industry, name, prompt_text, use_case, ratios, kontext_variations)
"""

MASTER_PROMPTS = [
    # --- Healthcare & Dental (8) ---
    ("healthcare", "Modern Dental Clinic — Hero",
     "Bright modern dental clinic interior, friendly dentist in white coat speaking with a relaxed patient seated in a dental chair, large windows with soft natural daylight, clean white and teal color palette, potted plant in background, shallow depth of field, professional editorial photography, cinematic lighting, 16:9 web hero image",
     "Homepage hero, about page banner", "16:9,4:3",
     "Change season lighting / swap to female dentist / add child patient"),

    ("healthcare", "Medical Team Collaboration",
     "Three diverse healthcare professionals in scrubs reviewing a digital tablet together in a bright hospital corridor, warm neutral tones, candid documentary style, natural window light, no harsh shadows, soft bokeh background, modern hospital setting, editorial photography",
     "Team section, about us, careers", "16:9,1:1",
     "Change to 2-person / outdoor courtyard / conference room"),

    ("healthcare", "Patient Consultation — Trust",
     "Warm one-on-one consultation between a caring female doctor and an elderly male patient in a clean modern office, doctor leaning slightly forward showing empathy, indirect warm lighting, muted blue and white tones, photorealistic, shallow depth of field, editorial healthcare photography",
     "Services page, testimonials section", "4:3,4:5",
     "Younger patient / pediatric setting / phone consultation"),

    ("healthcare", "Clean Equipment — Abstract",
     "Close-up abstract composition of polished modern dental or medical equipment, soft focus, cool blue-gray tones, studio product photography style, ultra clean background, subtle reflections, professional and reassuring, minimalist aesthetic",
     "Background texture, section divider", "16:9,1:1",
     "Warm tones / surgical instruments / lab setting"),

    ("healthcare", "Wellness & Prevention",
     "Young healthy woman doing yoga meditation at sunrise on a wooden deck surrounded by greenery, golden hour warm light, peaceful expression, soft bokeh, lifestyle editorial photography, wellness and preventive health theme, clean composition",
     "Wellness services, preventive care sections", "16:9,4:5",
     "Male subject / indoor yoga / senior wellness"),

    ("healthcare", "Reception & First Impressions",
     "Welcoming dental or medical reception area with a smiling receptionist at a modern desk, contemporary interior design, warm white and wood tones, plants, natural light from skylights, inviting atmosphere, real estate photography style, sharp focus",
     "Contact page, location section", "16:9,4:3",
     "Evening lighting / busy waiting room / pediatric waiting area"),

    ("healthcare", "Healthy Smile — Outcome",
     "Close-up portrait of a confident young woman with a genuine bright smile, soft studio lighting, clean white background, shallow depth of field on face, warm skin tones, professional beauty editorial style, dental health aspirational theme",
     "Results section, testimonials, social proof", "1:1,4:5",
     "Male subject / older demographic / diverse ethnicities"),

    ("healthcare", "Lab & Research",
     "Medical laboratory technician examining samples under a microscope in a clean modern lab, blue and white color palette, technical precision, shallow depth of field, documentary science photography, professional clinical environment, subtle lens flare",
     "Technology section, credentials, research", "16:9,4:3",
     "Female technician / different equipment / data on screens"),

    # --- Real Estate (8) ---
    ("real_estate", "Modern Living Room — Hero",
     "Bright spacious modern living room with floor-to-ceiling windows, late afternoon golden sunlight streaming in, minimal Scandinavian furniture in warm neutrals, indoor plants, hardwood floors, no people, architectural interior photography, ultra sharp, wide angle",
     "Homepage hero, listing header", "16:9,4:3",
     "Night mood lighting / urban apartment style / coastal aesthetic"),

    ("real_estate", "Luxury Kitchen",
     "High-end open-plan kitchen with white marble countertops, pendant lights, stainless steel appliances, bowl of fresh fruit, natural light from a large window, architectural photography style, no people, ultra clean, warm tones",
     "Property features section", "16:9,4:3",
     "Dark moody tones / rustic wood / breakfast scene with person"),

    ("real_estate", "Agent Meeting — Trust",
     "Professional real estate agent shaking hands with a young couple in front of a modern home exterior, sunny day, genuine smiles, well-dressed casual attire, shallow depth of field on handshake, editorial lifestyle photography, aspirational and trustworthy",
     "About page, agent profile, testimonials", "16:9,4:5",
     "Document signing at table / outdoor coffee meeting / single buyer"),

    ("real_estate", "Aerial — Neighborhood",
     "Aerial drone photography of a clean suburban neighborhood with tree-lined streets, well-maintained homes with varied architecture, green lawns, blue sky with few clouds, golden hour light, wide establishing shot, no text or watermarks",
     "Location section, neighborhood guide", "16:9,21:9",
     "Urban cityscape / coastal suburb / rural acreage"),

    ("real_estate", "Bedroom — Lifestyle",
     "Serene master bedroom with white linen bedding, wood-framed windows with sheer curtains, morning light filtering in, potted plant on nightstand, minimalist decor, real estate photography, no people, aspirational lifestyle feel",
     "Property gallery, blog", "16:9,4:3",
     "Cozy dark palette / kids bedroom / master with en-suite view"),

    ("real_estate", "Outdoor Living Space",
     "Modern outdoor patio with teak furniture, string lights, lush garden backdrop, sunset warm tones, lifestyle editorial photography, relaxed entertaining atmosphere, shallow depth of field on foreground table with drinks, no people",
     "Outdoor features, lifestyle section", "16:9,4:3",
     "Pool area / urban rooftop / winter firepit"),

    ("real_estate", "For Sale — Curb Appeal",
     "Beautiful family home exterior with manicured front lawn, flowers in bloom, blue sky, warm sunlight, freshly painted facade, welcoming front door, no for sale sign, architectural photography, eye-level perspective, symmetrical composition",
     "Listings, featured properties", "4:3,16:9",
     "Night exterior / autumn foliage / contemporary minimalist style"),

    ("real_estate", "Home Office",
     "Bright ergonomic home office with a clean white desk, large monitor, bookshelves, natural daylight from a side window, indoor plants, minimal distractions, editorial lifestyle photography, productivity and work-from-home theme",
     "Property features, remote work appeal", "16:9,4:3",
     "Cozy library style / creative studio / corner nook"),

    # --- Restaurant & Food (8) ---
    ("food", "Hero Dish — Fine Dining",
     "Elegant plated gourmet dish on a dark slate plate, soft dramatic side lighting, shallow depth of field, garnished with microgreens and a sauce reduction, dark moody restaurant background slightly out of focus, professional food photography, ultra detailed textures, appetizing colors",
     "Menu hero, homepage feature", "1:1,4:3",
     "Change dish type / bright editorial style / rustic wooden table"),

    ("food", "Restaurant Ambiance — Dinner",
     "Warm inviting restaurant interior at dinner service, soft candlelight and warm pendant lights, blurred happy diners in background, beautifully set table in foreground with wine glasses and folded napkins, bokeh, shallow depth of field, editorial food lifestyle photography",
     "Homepage hero, about page", "16:9,4:3",
     "Lunch service / outdoor terrace / bar seating"),

    ("food", "Chef in Action",
     "Confident chef in white coat plating a dish in a professional stainless steel kitchen, motion blur on hands showing skill and speed, dramatic overhead lighting, documentary style photography, warm ambient kitchen tones, authentic culinary atmosphere",
     "About us, team, story section", "16:9,4:5",
     "Female chef / pastry section / open kitchen with customer view"),

    ("food", "Casual Brunch — Lifestyle",
     "Overhead flat lay of a Sunday brunch table with pancakes, fresh berries, orange juice, coffee, scattered flowers, warm natural light from a window, lifestyle editorial photography, linen napkins, clean white marble surface, inviting and relaxed",
     "Brunch menu, social, catering", "1:1,4:3",
     "Healthy bowls / cocktails / hands reaching for food"),

    ("food", "Artisan Coffee",
     "Barista's hands pouring latte art into a ceramic mug on a wooden counter, steam rising, warm coffee shop ambiance in background, shallow depth of field on mug, editorial coffee photography, natural morning light, close-up macro style",
     "Coffee section, breakfast menu", "1:1,4:5",
     "Cold brew setup / full cafe scene / to-go cup outdoor"),

    ("food", "Fresh Ingredients",
     "Rustic wooden table with an artful arrangement of fresh colorful vegetables, herbs, and seasonal produce, natural soft daylight, slight shadows, editorial food photography, farm-to-table theme, no processed foods, organic and wholesome aesthetic",
     "Philosophy section, farm-to-table claims", "16:9,1:1",
     "Seafood / meat charcuterie / pastry and baked goods"),

    ("food", "Group Dining — Social",
     "Four friends laughing and sharing food at a restaurant table, natural candid moment, warm bokeh lights in background, genuine emotion, diverse group, editorial lifestyle photography, celebration atmosphere, wine and shared plates on table",
     "Social proof, events, group bookings", "16:9,4:3",
     "Family dinner / romantic date / business lunch"),

    ("food", "Takeaway — Modern Fast Casual",
     "Stylish kraft paper takeaway bag with a logo area, next to a stacked burger and crispy fries on a clean white surface, bright natural light, product photography style, modern fast casual aesthetic, minimal props, sharp focus",
     "Takeaway section, delivery feature", "1:1,4:3",
     "Pizza box / sushi takeout / healthy bowl packaging"),

    # --- Professional Services: Law & Finance (8) ---
    ("legal_finance", "Modern Law Office Interior",
     "Sleek contemporary law office with floor-to-ceiling windows overlooking a city skyline, dark wood paneling, leather chairs, a clean glass desk with a laptop, warm diffused light, no people, architectural interior photography, authoritative and modern",
     "Homepage hero, about us", "16:9,4:3",
     "Evening city lights / traditional library style / meeting room"),

    ("legal_finance", "Client Consultation — Confidence",
     "Professional lawyer or financial advisor in a navy suit having a confident focused conversation with a client across a glass table, executive office setting, city view in background, editorial business photography, warm window light, eye contact and engagement",
     "Services, consultation section", "16:9,4:5",
     "Female attorney / virtual call / signing documents"),

    ("legal_finance", "Team — Diversity & Authority",
     "Three business professionals of different backgrounds standing confidently in a modern glass office building lobby, business formal attire, genuine expressions, editorial corporate photography, warm neutral tones, shallow depth of field",
     "Team page, about us", "16:9,4:3",
     "Outdoor city backdrop / conference room / headshot style"),

    ("legal_finance", "Data & Strategy",
     "Business professional reviewing financial charts and data on a large curved monitor in a dark modern office, dramatic side lighting, data visualizations on screen, focused intense expression, cinematic editorial style, blue and white screen glow",
     "Technology, data analytics service section", "16:9,4:3",
     "Multiple monitors / tablet on boardroom table / team reviewing"),

    ("legal_finance", "Handshake — Partnership",
     "Close-up of two professionals shaking hands across a boardroom table, shallow depth of field on hands, business formal attire, warm natural light from windows, signed documents visible on table edge, editorial corporate photography, trust and partnership theme",
     "About us, partnerships, results", "4:3,1:1",
     "Contract signing / key handover / digital agreement on tablet"),

    ("legal_finance", "City Architecture — Prestige",
     "Modern glass office tower reflecting blue sky and clouds, street level view looking upward, wide angle architectural photography, clean lines and geometric shapes, no text or signs, corporate prestige theme, sharp focus across entire frame",
     "Background image, location, credibility", "4:5,9:16",
     "Interior atrium / courthouse exterior / financial district skyline"),

    ("legal_finance", "Research & Precision",
     "Attorney or analyst in reading glasses carefully reviewing printed documents at a tidy desk, afternoon warm light from window, selective focus on documents, deliberate and meticulous atmosphere, editorial documentary style, books and folders in background",
     "Expertise section, process description", "4:3,4:5",
     "Digital document review / legal library / annotating contract"),

    ("legal_finance", "Growth — Finance Concept",
     "Abstract close-up of a physical wooden desk with a small green plant growing from a handful of coins, selective focus, soft warm studio lighting, financial growth metaphor, minimal conceptual photography, clean white background, hopeful and forward-looking",
     "Investment services, wealth management", "1:1,4:3",
     "Graph on paper / seeds in soil / stairs ascending"),

    # --- Fitness & Wellness (8) ---
    ("fitness", "Gym Training — Hero",
     "Athletic person in workout clothes performing a determined weightlifting exercise in a modern gym, natural daylight from large industrial windows, dramatic side lighting, motion blur on movement, editorial fitness photography, cinematic crop, genuine effort not posed",
     "Homepage hero, services", "16:9,4:5",
     "Female athlete / cardio training / group class"),

    ("fitness", "Outdoor Running — Lifestyle",
     "Young woman running along an urban park path at golden hour, motion blur on legs showing speed, determined expression, city trees in background bokeh, editorial lifestyle photography, aspirational fitness, warm morning tones, loose active wear",
     "Running programs, outdoor fitness", "16:9,4:5",
     "Male runner / trail running / beach running at sunrise"),

    ("fitness", "Yoga & Mindfulness",
     "Woman in warrior yoga pose on a wooden studio floor, large windows with soft morning light, minimal white and wood interior, calm focused expression, editorial wellness photography, clean lines, no clutter, serene and intentional atmosphere",
     "Yoga, mindfulness, mind-body programs", "4:5,1:1",
     "Outdoor rooftop / beach setting / group class / meditation pose"),

    ("fitness", "Personal Training — Connection",
     "Personal trainer giving encouragement to a client mid-exercise in a bright modern gym, trainer showing proper form with a hand on shoulder, both genuinely focused, documentary fitness photography, warm natural light, no cheesy poses",
     "Personal training services, coaching", "16:9,4:3",
     "Female trainer / outdoor training session / senior client"),

    ("fitness", "Healthy Nutrition",
     "Top-down flat lay of a balanced healthy meal prep on a clean white marble surface, colorful vegetables, grilled protein, quinoa, fruit on the side, morning natural light, editorial food and wellness photography, no processed foods, vibrant colors",
     "Nutrition section, meal planning services", "1:1,4:3",
     "Smoothie bowls / supplement setup / grocery haul"),

    ("fitness", "Community — Group Class",
     "Energetic group fitness class doing synchronized exercises in a bright studio, diverse participants of varying fitness levels, genuine smiles and effort, overhead or side angle, editorial documentary style, natural light and studio lighting mix",
     "Group classes, community, memberships", "16:9,4:3",
     "Spin class / bootcamp outdoor / dance fitness"),

    ("fitness", "Recovery & Wellness",
     "Person in a peaceful recovery pose in a spa-like wellness room, warm candle and ambient lighting, white towels and natural materials, serene expression, editorial spa photography, post-workout recovery theme, minimal and calming aesthetic",
     "Recovery services, spa, premium tiers", "4:3,4:5",
     "Ice bath / massage therapy / sauna interior"),

    ("fitness", "Transformation — Before Journey",
     "Confident diverse person standing tall in athletic wear looking out a large window at an urban landscape, contemplative hopeful expression, morning golden light, documentary lifestyle photography, beginning of a fitness journey theme, motivational",
     "Transformation stories, program intro", "4:5,9:16",
     "Celebration finish / looking in mirror / couple starting together"),

    # --- E-commerce & Retail (8) ---
    ("ecommerce", "Lifestyle Product — Hero",
     "Modern reusable water bottle on a marble countertop next to a green plant, soft natural side lighting from a window, clean white background, product photography with lifestyle context, minimal styling, sharp focus on product, editorial and aspirational",
     "Product hero, homepage feature", "1:1,4:5",
     "Change product type / outdoor setting / hands holding product"),

    ("ecommerce", "Fashion Lifestyle",
     "Young stylish woman in a neutral outfit browsing clothing racks in a minimal boutique store, warm natural light from street-facing windows, candid editorial style, blurred clothing in background, authentic shopping experience, no branding visible",
     "Fashion category, shopping experience", "4:5,16:9",
     "Male shopper / online shopping on phone / checkout moment"),

    ("ecommerce", "Unboxing — Premium Feel",
     "Hands carefully opening a premium matte black product box revealing a wrapped item with tissue paper, clean marble surface, soft warm studio lighting, close-up product photography, aspirational unboxing experience, luxury packaging aesthetic",
     "Packaging section, gifting, premium tier", "1:1,4:3",
     "Colorful festive packaging / subscription box / beauty product reveal"),

    ("ecommerce", "Home Products — In Situ",
     "Beautifully styled living room corner with a ceramic vase, coffee table book, and a decorative item on a wooden side table, natural morning light, Scandinavian minimal interior, editorial home decor photography, no people, clean and aspirational",
     "Home decor category, interior lifestyle", "4:3,1:1",
     "Kitchen product placement / bedroom / bathroom shelf"),

    ("ecommerce", "Satisfied Customer",
     "Genuine happy young woman holding a shopping bag and smiling on a sunny city street, casual stylish outfit, candid editorial lifestyle photography, urban background bokeh, authentic not posed, positive retail experience, warm tones",
     "Social proof, testimonials, ad creative", "4:5,1:1",
     "Man with bag / couple shopping / delivery at door"),

    ("ecommerce", "Tech Product — Clean",
     "Minimalist product shot of a sleek wireless earbuds case on a smooth gray surface, dramatic studio side lighting creating shadows and depth, sharp focus, product photography, premium tech aesthetic, no text, advertising quality image",
     "Tech category, product details", "1:1,4:3",
     "Smartwatch / laptop / phone / portable speaker"),

    ("ecommerce", "Small Business — Artisan",
     "Artisan maker's hands crafting a small handmade ceramic item in a cozy workshop, warm workshop lighting, clay and tools visible, shallow depth of field, editorial documentary style, authentic craft and small business theme, earthy warm tones",
     "Artisan brand, about us, process section", "4:3,4:5",
     "Jewelry making / candle pouring / textile weaving"),

    ("ecommerce", "Sale & Urgency",
     "Colorful retail store interior with neatly organized product displays, bright clean lighting, no people, wide angle shot showing store depth, modern organized retail aesthetic, visual merchandising photography, inviting and accessible atmosphere",
     "Sale events, store section, category pages", "16:9,4:3",
     "Seasonal display / food retail / boutique accessories"),
]

def seed_prompts(db_session):
    """Insert all 48 master prompts into the database."""
    from app.models import Prompt
    existing = db_session.query(Prompt).count()
    if existing > 0:
        return existing
    for industry, name, prompt_text, use_case, ratios, kontext in MASTER_PROMPTS:
        db_session.add(Prompt(
            industry=industry,
            name=name,
            prompt_text=prompt_text,
            use_case=use_case,
            ratios=ratios,
            kontext_variations=kontext,
        ))
    db_session.commit()
    return len(MASTER_PROMPTS)
```

**Step 2: Commit**

```bash
git add app/seed/master_prompts.py
git commit -m "feat: add 48 master prompts seed data from build plan"
```

---

## Task 8: FastAPI App & Routers

**Files:**
- Create: `app/main.py`
- Create: `app/routers/prompts.py`
- Create: `app/routers/images.py`
- Create: `app/routers/generation.py`
- Create: `app/routers/tags.py`
- Create: `tests/conftest.py`
- Test: `tests/test_prompts_api.py`

**Step 1: Write conftest.py (shared test fixtures)**

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

**Step 2: Write the failing test**

```python
# tests/test_prompts_api.py
from app.seed.master_prompts import seed_prompts

def test_list_prompts(client, db):
    seed_prompts(db)
    resp = client.get("/api/v1/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 48

def test_list_prompts_by_industry(client, db):
    seed_prompts(db)
    resp = client.get("/api/v1/prompts?industry=healthcare")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    assert all(p["industry"] == "healthcare" for p in data)

def test_get_prompt(client, db):
    seed_prompts(db)
    resp = client.get("/api/v1/prompts/1")
    assert resp.status_code == 200
    assert "Modern Dental Clinic" in resp.json()["name"]

def test_update_prompt(client, db):
    seed_prompts(db)
    resp = client.patch("/api/v1/prompts/1", json={"prompt_text": "Updated prompt text"})
    assert resp.status_code == 200
    assert resp.json()["prompt_text"] == "Updated prompt text"
```

**Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_prompts_api.py -v`
Expected: FAIL

**Step 4: Write main.py**

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.routers import prompts, images, generation, tags
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title="PixelVault API", version="0.1.0", lifespan=lifespan)

app.include_router(prompts.router, prefix="/api/v1")
app.include_router(images.router, prefix="/api/v1")
app.include_router(generation.router, prefix="/api/v1")
app.include_router(tags.router, prefix="/api/v1")
app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Step 5: Write prompts router**

```python
# app/routers/prompts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Prompt
from app.schemas import PromptOut, PromptUpdate

router = APIRouter(tags=["prompts"])

@router.get("/prompts", response_model=list[PromptOut])
def list_prompts(industry: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Prompt)
    if industry:
        q = q.filter(Prompt.industry == industry)
    return q.all()

@router.get("/prompts/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    return prompt

@router.patch("/prompts/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, body: PromptUpdate, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prompt, field, value)
    db.commit()
    db.refresh(prompt)
    return prompt
```

**Step 6: Write images router**

```python
# app/routers/images.py
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
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
def get_image(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    return image

@router.get("/images/{image_id}/file")
def get_image_file(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    return FileResponse(image.filepath, media_type="image/jpeg")

@router.patch("/images/{image_id}/review", response_model=ImageOut)
def review_image(image_id: int, body: ImageReview, db: Session = Depends(get_db)):
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
```

**Step 7: Write generation router**

```python
# app/routers/generation.py
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Prompt, Batch, Image
from app.schemas import GenerateBatchRequest, GenerateBatchResponse, BatchOut
from app.services.fal_client import FalClient
from app.services.image_processor import ImageProcessor
from app.services.obsidian_logger import ObsidianLogger
from app.config import settings

router = APIRouter(tags=["generation"])

async def _run_generation(batch_id: int, prompt_text: str, industry: str, style: str, ratio: str, count: int):
    """Background task: call fal.ai, download images, update DB, log to Obsidian."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        batch = db.get(Batch, batch_id)
        batch.status = "generating"
        db.commit()

        fal = FalClient(api_key=settings.fal_key)
        processor = ImageProcessor(storage_path=settings.storage_path)

        results = await fal.generate_batch(prompt=prompt_text, ratio=ratio, count=count)

        ratio_label = ratio.replace(":", "x")
        existing_count = db.query(Image).filter(Image.industry == industry, Image.style == style).count()

        for i, result in enumerate(results):
            number = existing_count + i + 1
            saved = await processor.download_and_save(result["url"], industry, style, number, ratio_label)
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
                fal_request_id=None,
            )
            db.add(image)

        batch.status = "completed"
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()

        # Log to Obsidian
        prompt = db.get(Prompt, batch.prompt_id)
        obsidian = ObsidianLogger(api_url=settings.obsidian_api_url, api_key=settings.obsidian_api_key)
        await obsidian.log_batch(
            batch_id=batch.id,
            industry=industry,
            prompt_name=prompt.name,
            prompt_text=prompt_text,
            image_count=count,
            status="completed",
        )

    except Exception as e:
        batch = db.get(Batch, batch_id)
        if batch:
            batch.status = "failed"
            db.commit()
        raise
    finally:
        db.close()

@router.post("/generate", response_model=GenerateBatchResponse)
async def generate_batch(body: GenerateBatchRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, body.prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")

    batch = Batch(prompt_id=prompt.id, image_count=body.count, ratio=body.ratio, status="pending")
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Derive style from prompt name (e.g. "Modern Dental Clinic — Hero" -> "hero")
    style = prompt.name.split("—")[-1].strip().lower().split()[0] if "—" in prompt.name else "general"

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

@router.get("/batches", response_model=list[BatchOut])
def list_batches(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Batch).order_by(Batch.id.desc())
    if status:
        q = q.filter(Batch.status == status)
    return q.all()

@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    return batch
```

**Step 8: Write tags router**

```python
# app/routers/tags.py
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
```

**Step 9: Run test to verify it passes**

Run: `python -m pytest tests/test_prompts_api.py -v`
Expected: 4 PASSED

**Step 10: Commit**

```bash
git add app/main.py app/routers/ tests/conftest.py tests/test_prompts_api.py
git commit -m "feat: add FastAPI app with prompts, images, generation, tags routers"
```

---

## Task 9: API Key Authentication Middleware

**Files:**
- Modify: `app/main.py`
- Create: `app/auth.py`

**Step 1: Write auth.py**

```python
# app/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    if not settings.pixelvault_api_key:
        return  # No key configured = open access (dev mode)
    if api_key != settings.pixelvault_api_key:
        raise HTTPException(403, "Invalid API key")
```

This is used as a dependency on the routers. The WordPress bridge will send `X-API-Key` header.

**Step 2: Commit**

```bash
git add app/auth.py
git commit -m "feat: add API key auth for WordPress bridge access"
```

---

## Task 10: WordPress PHP Bridge

**Files:**
- Create: `wordpress/class-pixelvault-bridge.php`

**Step 1: Write the PHP bridge**

```php
<?php
/**
 * PixelVault Bridge — Drop-in class for WordPress plugins.
 *
 * Usage in any WP plugin:
 *   require_once 'class-pixelvault-bridge.php';
 *   $pv = new PixelVault_Bridge('https://your-server.com', 'your-api-key');
 *   $images = $pv->get_images(['industry' => 'healthcare', 'status' => 'approved']);
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class PixelVault_Bridge {

    private string $api_url;
    private string $api_key;
    private int $cache_ttl;

    /**
     * @param string $api_url  Base URL of your PixelVault API (e.g. https://your-server.com)
     * @param string $api_key  API key matching PIXELVAULT_API_KEY in .env
     * @param int    $cache_ttl Transient cache TTL in seconds (default 5 min)
     */
    public function __construct( string $api_url, string $api_key, int $cache_ttl = 300 ) {
        $this->api_url   = rtrim( $api_url, '/' );
        $this->api_key   = $api_key;
        $this->cache_ttl = $cache_ttl;
    }

    // ─── Images ──────────────────────────────────────────────

    /**
     * Get images with optional filters.
     *
     * @param array $filters {
     *     @type string $industry  e.g. 'healthcare', 'real_estate'
     *     @type string $style     e.g. 'hero', 'lifestyle'
     *     @type string $ratio     e.g. '16:9', '1:1'
     *     @type string $status    e.g. 'approved', 'pending'
     *     @type string $tag       e.g. 'featured'
     *     @type int    $page      Page number (default 1)
     *     @type int    $per_page  Items per page (default 20)
     * }
     * @return array|WP_Error
     */
    public function get_images( array $filters = [] ) {
        $cache_key = 'pv_images_' . md5( wp_json_encode( $filters ) );
        $cached    = get_transient( $cache_key );
        if ( false !== $cached ) {
            return $cached;
        }

        $result = $this->request( 'GET', '/api/v1/images', $filters );
        if ( ! is_wp_error( $result ) ) {
            set_transient( $cache_key, $result, $this->cache_ttl );
        }
        return $result;
    }

    /**
     * Get a single image by ID.
     */
    public function get_image( int $image_id ) {
        return $this->request( 'GET', "/api/v1/images/{$image_id}" );
    }

    /**
     * Get the direct file URL for an image.
     */
    public function get_image_url( int $image_id ): string {
        return $this->api_url . "/api/v1/images/{$image_id}/file";
    }

    /**
     * Review an image (approve/reject).
     */
    public function review_image( int $image_id, string $status, ?int $quality_score = null ) {
        $body = [ 'status' => $status ];
        if ( null !== $quality_score ) {
            $body['quality_score'] = $quality_score;
        }
        return $this->request( 'PATCH', "/api/v1/images/{$image_id}/review", [], $body );
    }

    // ─── Prompts ─────────────────────────────────────────────

    /**
     * List prompts, optionally filtered by industry.
     */
    public function get_prompts( ?string $industry = null ) {
        $params = $industry ? [ 'industry' => $industry ] : [];
        return $this->request( 'GET', '/api/v1/prompts', $params );
    }

    /**
     * Update a prompt's text.
     */
    public function update_prompt( int $prompt_id, array $fields ) {
        return $this->request( 'PATCH', "/api/v1/prompts/{$prompt_id}", [], $fields );
    }

    // ─── Generation ──────────────────────────────────────────

    /**
     * Trigger a small batch generation.
     *
     * @param int    $prompt_id  ID of the master prompt
     * @param int    $count      Number of images (3-5 recommended)
     * @param string $ratio      Aspect ratio e.g. '16:9'
     */
    public function generate_batch( int $prompt_id, int $count = 4, string $ratio = '16:9' ) {
        return $this->request( 'POST', '/api/v1/generate', [], [
            'prompt_id' => $prompt_id,
            'count'     => $count,
            'ratio'     => $ratio,
        ] );
    }

    /**
     * Check batch status.
     */
    public function get_batch( int $batch_id ) {
        return $this->request( 'GET', "/api/v1/batches/{$batch_id}" );
    }

    /**
     * List all batches.
     */
    public function get_batches( ?string $status = null ) {
        $params = $status ? [ 'status' => $status ] : [];
        return $this->request( 'GET', '/api/v1/batches', $params );
    }

    // ─── Tags ────────────────────────────────────────────────

    public function add_tag( int $image_id, string $tag_name ) {
        return $this->request( 'POST', "/api/v1/images/{$image_id}/tags/{$tag_name}" );
    }

    public function remove_tag( int $image_id, string $tag_name ) {
        return $this->request( 'DELETE', "/api/v1/images/{$image_id}/tags/{$tag_name}" );
    }

    // ─── Stats ───────────────────────────────────────────────

    public function get_stats() {
        return $this->request( 'GET', '/api/v1/stats' );
    }

    // ─── Internal ────────────────────────────────────────────

    /**
     * Make an authenticated request to the PixelVault API.
     *
     * @return array|WP_Error
     */
    private function request( string $method, string $endpoint, array $query = [], array $body = [] ) {
        $url = $this->api_url . $endpoint;
        if ( ! empty( $query ) ) {
            $url = add_query_arg( $query, $url );
        }

        $args = [
            'method'  => $method,
            'headers' => [
                'X-API-Key'   => $this->api_key,
                'Content-Type' => 'application/json',
                'Accept'       => 'application/json',
            ],
            'timeout' => 30,
        ];

        if ( ! empty( $body ) ) {
            $args['body'] = wp_json_encode( $body );
        }

        $response = wp_remote_request( $url, $args );

        if ( is_wp_error( $response ) ) {
            return $response;
        }

        $code = wp_remote_retrieve_response_code( $response );
        $data = json_decode( wp_remote_retrieve_body( $response ), true );

        if ( $code >= 400 ) {
            return new \WP_Error(
                'pixelvault_api_error',
                $data['detail'] ?? "API error: HTTP {$code}",
                [ 'status' => $code ]
            );
        }

        return $data;
    }
}
```

**Step 2: Commit**

```bash
git add wordpress/class-pixelvault-bridge.php
git commit -m "feat: add WordPress PHP bridge class for plugin integration"
```

---

## Task 11: Seed Command & First Run

**Files:**
- Create: `app/cli.py`

**Step 1: Write the CLI seed command**

```python
# app/cli.py
"""
CLI commands for PixelVault.
Run: python -m app.cli seed
Run: python -m app.cli serve
"""
import sys
from app.database import Base, engine, SessionLocal
from app.seed.master_prompts import seed_prompts

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "seed":
        Base.metadata.create_all(engine)
        db = SessionLocal()
        count = seed_prompts(db)
        db.close()
        print(f"Seeded {count} prompts.")

    elif cmd == "serve":
        import uvicorn
        Base.metadata.create_all(engine)
        db = SessionLocal()
        seed_prompts(db)
        db.close()
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

    else:
        print("Usage: python -m app.cli [seed|serve]")

if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add app/cli.py
git commit -m "feat: add CLI for seeding prompts and running server"
```

---

## Task 12: Create .env and First Manual Test

**Step 1: Create .env from template**

```bash
cp .env.example .env
# Edit .env with real values:
# FAL_KEY=<your fal.ai key>
# OBSIDIAN_API_KEY=34d1965a5700ccd2eeebcc5b0e2774f5c6d6516128f0ab9bd7bd5c187bfb798e
# PIXELVAULT_API_KEY=<generate a random key for WP bridge>
```

**Step 2: Run the server**

Run: `python -m app.cli serve`
Expected: Server starts on http://localhost:8000, seeds 48 prompts.

**Step 3: Verify endpoints**

```bash
# Health check
curl http://localhost:8000/health

# List all prompts
curl http://localhost:8000/api/v1/prompts

# List healthcare prompts
curl http://localhost:8000/api/v1/prompts?industry=healthcare

# Stats
curl http://localhost:8000/api/v1/stats
```

**Step 4: Test a small batch (3 images) — REQUIRES FAL_KEY**

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": 1, "count": 3, "ratio": "16:9"}'
```

Expected: Returns `{"batch_id": 1, "status": "pending", "message": "Generating 3 images for 'Modern Dental Clinic — Hero'"}`. Images appear in `storage/images/` after ~30 seconds.

---

## API Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/prompts` | List prompts (filter: `?industry=`) |
| GET | `/api/v1/prompts/{id}` | Get single prompt |
| PATCH | `/api/v1/prompts/{id}` | Update prompt text |
| POST | `/api/v1/generate` | Generate small batch |
| GET | `/api/v1/batches` | List batches (filter: `?status=`) |
| GET | `/api/v1/batches/{id}` | Get batch status |
| GET | `/api/v1/images` | List images (filter: industry, style, ratio, status, tag) |
| GET | `/api/v1/images/{id}` | Get image metadata |
| GET | `/api/v1/images/{id}/file` | Download image file |
| PATCH | `/api/v1/images/{id}/review` | Approve/reject image |
| POST | `/api/v1/images/{id}/tags/{name}` | Add tag |
| DELETE | `/api/v1/images/{id}/tags/{name}` | Remove tag |
| GET | `/api/v1/tags` | List all tags |
| GET | `/api/v1/stats` | Image bank statistics |

## WordPress Bridge Usage

```php
// In any WordPress plugin:
require_once 'class-pixelvault-bridge.php';
$pv = new PixelVault_Bridge( 'https://your-pixelvault-server.com', 'your-api-key' );

// Get approved healthcare hero images
$images = $pv->get_images( [ 'industry' => 'healthcare', 'style' => 'hero', 'status' => 'approved' ] );

// Trigger a small test batch
$batch = $pv->generate_batch( prompt_id: 1, count: 3, ratio: '16:9' );

// Check progress
$status = $pv->get_batch( $batch['batch_id'] );
```

## Obsidian Vault Structure (auto-created)

```
Your Vault/
└── PixelVault/
    ├── Batches/
    │   ├── batch-0001.md
    │   ├── batch-0002.md
    │   └── ...
    └── Prompt-History/
        ├── prompt-001-2026-03-16.md
        └── ...
```
