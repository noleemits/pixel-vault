from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    if not settings.pixelvault_api_key:
        return  # No key configured = open access (dev mode)
    if api_key != settings.pixelvault_api_key:
        raise HTTPException(403, "Invalid API key")
