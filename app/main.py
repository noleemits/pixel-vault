from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import Base, sync_engine as engine
from app.routers import prompts, images, generation, tags, sites
from app.config import settings
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title="PixelVault API", version="0.1.0", lifespan=lifespan)

app.include_router(prompts.router, prefix="/api/v1")
app.include_router(images.router, prefix="/api/v1")
app.include_router(generation.router, prefix="/api/v1")
app.include_router(tags.router, prefix="/api/v1")
app.include_router(sites.router, prefix="/api/v1")

os.makedirs(settings.storage_path, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def dashboard():
    return FileResponse("static/index.html")
