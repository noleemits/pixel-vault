# app/services/imagen_client.py
"""
Google Imagen 4 client.

Models:
  - imagen-4.0-generate-001    (Standard)  ~$0.04/image
  - imagen-4.0-ultra-generate-001 (Ultra)  ~$0.06/image

Resolution tiers:
  - "1K" → 1408x768 (16:9)  — SD tier
  - "2K" → 2816x1536 (16:9) — HD/default tier (same cost as 1K!)
"""

import base64
import httpx

MODEL_STANDARD = "imagen-4.0-generate-001"
MODEL_ULTRA = "imagen-4.0-ultra-generate-001"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

SUPPORTED_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]


def normalize_ratio(ratio: str) -> str:
    mapping = {"4:5": "3:4", "21:9": "16:9"}
    return mapping.get(ratio, ratio if ratio in SUPPORTED_RATIOS else "16:9")


class ImagenClient:

    def __init__(self, api_key: str, quality: str = "standard"):
        """
        Args:
            api_key: Google API key.
            quality: "standard" or "ultra". Controls which model is used.
        """
        self.api_key = api_key
        self.model = MODEL_ULTRA if quality == "ultra" else MODEL_STANDARD

    async def _post(self, payload: dict) -> dict:
        url = f"{BASE_URL}/{self.model}:predict"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    def _build_params(self, count: int, ratio: str, size: str = "2K") -> dict:
        """Build the parameters dict with native 2K resolution by default."""
        return {
            "sampleCount": count,
            "aspectRatio": normalize_ratio(ratio),
            "sampleImageSize": size,
        }

    async def generate_image(self, prompt: str, ratio: str = "16:9", size: str = "2K") -> dict:
        result = await self._post({
            "instances": [{"prompt": prompt}],
            "parameters": self._build_params(1, ratio, size),
        })
        img = result["predictions"][0]
        return {
            "image_bytes": base64.b64decode(img["bytesBase64Encoded"]),
            "mime_type": img.get("mimeType", "image/png"),
        }

    async def generate_batch(self, prompt: str, ratio: str = "16:9", count: int = 4, size: str = "2K") -> list[dict]:
        count = min(count, 4)
        result = await self._post({
            "instances": [{"prompt": prompt}],
            "parameters": self._build_params(count, ratio, size),
        })
        return [
            {
                "image_bytes": base64.b64decode(img["bytesBase64Encoded"]),
                "mime_type": img.get("mimeType", "image/png"),
            }
            for img in result["predictions"]
        ]
