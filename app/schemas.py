from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

# --- Prompts ---
class PromptOut(BaseModel):
    id: int
    industry: str
    name: str
    prompt_text: str
    use_case: str | None = None
    ratios: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}

class PromptUpdate(BaseModel):
    name: str | None = None
    prompt_text: str | None = None
    use_case: str | None = None
    ratios: str | None = None

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
    id: UUID | int
    filename: str
    filepath: str
    industry: str
    style: str
    ratio: str
    status: str
    quality_score: float | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    prompt_id: int
    batch_id: int
    model_used: str | None = None
    router_reason: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}

class ImageReview(BaseModel):
    status: str
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
    count: int = 4
    ratio: str = "16:9"

class GenerateBatchResponse(BaseModel):
    batch_id: int
    status: str
    message: str

class GenerateFromPromptRequest(BaseModel):
    prompt: str
    count: int = 1
    ratio: str = "16:9"
    quality: str = "sd"
    style_prefix: str = ""
    negative_keywords: str = ""

# --- Tags ---
class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}
