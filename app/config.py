from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    fal_api_key: str = ""
    google_api_key: str = ""  # Imagen 4 — used for hand-featured prompts
    obsidian_api_url: str = "https://127.0.0.1:27124"
    obsidian_api_key: str = ""
    pixelvault_api_key: str = ""
    database_url: str = "sqlite:///./pixelvault.db"
    storage_path: str = "./storage/images"

    model_config = {"env_file": ".env"}

settings = Settings()
