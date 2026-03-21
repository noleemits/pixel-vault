# app/services/imagen_client.py
import base64
import httpx

# Imagen 4 Standard — supports all aspect ratios natively (16:9, 1:1, 4:5, 3:4, 9:16)
# Used for people/hands prompts where FLUX anatomy fails
MODEL = "imagen-4.0-generate-001"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

SUPPORTED_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]

def normalize_ratio(ratio: str) -> str:
    mapping = {"4:5": "3:4", "21:9": "16:9"}
    return mapping.get(ratio, ratio if ratio in SUPPORTED_RATIOS else "16:9")


class ImagenClient:

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _post(self, payload: dict) -> dict:
        url = f"{BASE_URL}/{MODEL}:predict"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def generate_image(self, prompt: str, ratio: str = "16:9") -> dict:
        result = await self._post({
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": normalize_ratio(ratio)},
        })
        img = result["predictions"][0]
        return {"image_bytes": base64.b64decode(img["bytesBase64Encoded"]), "mime_type": img.get("mimeType", "image/png")}

    async def generate_batch(self, prompt: str, ratio: str = "16:9", count: int = 4) -> list[dict]:
        count = min(count, 4)
        result = await self._post({
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": count, "aspectRatio": normalize_ratio(ratio)},
        })
        return [
            {"image_bytes": base64.b64decode(img["bytesBase64Encoded"]), "mime_type": img.get("mimeType", "image/png")}
            for img in result["predictions"]
        ]
