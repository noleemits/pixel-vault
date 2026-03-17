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

# --- Tags ---
class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}
