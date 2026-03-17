# app/services/imagen_client.py
import base64
import httpx

SUPPORTED_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]

def normalize_ratio(ratio: str) -> str:
    """Map custom ratios to Imagen-supported ones."""
    mapping = {
        "4:5": "3:4",
        "21:9": "16:9",
    }
    return mapping.get(ratio, ratio if ratio in SUPPORTED_RATIOS else "16:9")

class ImagenClient:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str = "imagen-4.0-generate-001"):
        self.api_key = api_key
        self.model = model

    async def _post(self, payload: dict) -> dict:
        url = f"{self.BASE_URL}/{self.model}:predict"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def generate_image(self, prompt: str, ratio: str = "16:9") -> dict:
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": normalize_ratio(ratio),
            },
        }
        result = await self._post(payload)
        img_data = result["predictions"][0]
        return {"image_bytes": base64.b64decode(img_data["bytesBase64Encoded"]), "mime_type": img_data.get("mimeType", "image/png")}

    async def generate_batch(self, prompt: str, ratio: str = "16:9", count: int = 4) -> list[dict]:
        count = min(count, 4)  # Imagen max is 4 per request
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": count,
                "aspectRatio": normalize_ratio(ratio),
            },
        }
        result = await self._post(payload)
        return [
            {"image_bytes": base64.b64decode(img["bytesBase64Encoded"]), "mime_type": img.get("mimeType", "image/png")}
            for img in result["predictions"]
        ]
