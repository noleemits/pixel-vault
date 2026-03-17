import httpx

RATIO_TO_SIZE = {
    "16:9": {"width": 1920, "height": 1080},
    "4:3":  {"width": 1440, "height": 1080},
    "1:1":  {"width": 1024, "height": 1024},
    "4:5":  {"width": 1024, "height": 1280},
    "9:16": {"width": 1080, "height": 1920},
    "21:9": {"width": 2560, "height": 1080},
}

class FalClient:
    BASE_URL = "https://fal.run/fal-ai/flux-pro/v1.1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _post(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def generate_image(self, prompt: str, ratio: str = "16:9") -> dict:
        size = RATIO_TO_SIZE.get(ratio, RATIO_TO_SIZE["16:9"])
        payload = {
            "prompt": prompt,
            "image_size": size,
            "num_images": 1,
            "safety_tolerance": "2",
        }
        result = await self._post(payload)
        img = result["images"][0]
        return {"url": img["url"], "width": img.get("width", size["width"]), "height": img.get("height", size["height"])}

    async def generate_batch(self, prompt: str, ratio: str = "16:9", count: int = 4) -> list[dict]:
        size = RATIO_TO_SIZE.get(ratio, RATIO_TO_SIZE["16:9"])
        payload = {
            "prompt": prompt,
            "image_size": size,
            "num_images": count,
            "safety_tolerance": "2",
        }
        result = await self._post(payload)
        return [
            {"url": img["url"], "width": img.get("width", size["width"]), "height": img.get("height", size["height"])}
            for img in result["images"]
        ]
