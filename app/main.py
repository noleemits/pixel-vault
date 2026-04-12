from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import Base, sync_engine as engine
from app.routers import prompts, images, generation, tags, sites, accounts, webhooks, public, community, admin
from app.auth import verify_api_key
from app.services.admin_guard import require_admin
from app.config import settings
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    # Seed predefined tags on startup.
    from app.database import SessionLocal
    from app.services.auto_tagger import seed_tags
    db = SessionLocal()
    try:
        seed_tags(db)
    finally:
        db.close()
    yield

app = FastAPI(title="PixelVault API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_auth = [Depends(verify_api_key)]
app.include_router(prompts.router, prefix="/api/v1", dependencies=_auth)
app.include_router(images.router, prefix="/api/v1", dependencies=_auth)
app.include_router(generation.router, prefix="/api/v1", dependencies=_auth)
app.include_router(tags.router, prefix="/api/v1", dependencies=_auth)
app.include_router(sites.router, prefix="/api/v1", dependencies=_auth)

# Public endpoints — no global auth required.
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")
app.include_router(community.router, prefix="/api/v1")

# Admin endpoints — require admin role.
_admin_auth = [Depends(require_admin)]
app.include_router(admin.router, prefix="/api/v1", dependencies=_admin_auth)

os.makedirs(settings.storage_path, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def dashboard():
    return FileResponse("static/index.html")
