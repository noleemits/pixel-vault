from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    fal_api_key: str = ""
    google_api_key: str = ""  # Imagen 4 — used for hand-featured prompts
    obsidian_api_url: str = "https://127.0.0.1:27124"
    obsidian_api_key: str = ""
    pixelvault_api_key: str = ""
    database_url: str = "sqlite:///./pixelvault.db"
    storage_path: str = "./storage/images"

    # Cloudflare R2 (S3-compatible object storage)
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "pixelvault"
    r2_endpoint: str = ""  # https://<account_id>.r2.cloudflarestorage.com
    cdn_domain: str = ""   # e.g. images.noleemits.com

    # Supabase JWT auth (dashboard)
    supabase_jwt_secret: str = ""

    model_config = {"env_file": ".env"}

settings = Settings()
