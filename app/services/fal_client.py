# app/services/fal_client.py
import base64
import httpx

SUPPORTED_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9", "21:9", "4:5"]

RATIO_MAP = {
    "21:9": "21:9",
    "4:5":  "4:5",
}

# Global quality modifiers appended to every prompt
POSITIVE_SUFFIX = (
    "natural eye contact between subjects, anatomically correct hands and fingers, "
    "neutral color grading, no color cast, professional editorial framing, "
    "wide shot with environmental context, subjects occupy center two-thirds of frame, "
    "generous negative space, room to breathe around subjects"
)

# Negative prompt applied to every generation
NEGATIVE_PROMPT = (
    "distorted hands, extra fingers, missing fingers, crossed eyes, lazy eye, "
    "blue color cast, teal color cast, visible feet in portrait shots, posed stock photo look, "
    "watermark, text on clothing, name badge, logo, signature, oversaturated, plastic skin, "
    "holding hands, intertwined hands, hands touching between subjects, "
    "extreme close-up, faces filling frame, no background visible, "
    "hands in frame, fingers visible, human body parts, hand reaching into frame"
)

# Keywords that indicate people are present — route to Imagen 4 for better anatomy
PEOPLE_KEYWORDS = [
    # body parts / anatomy
    "hands", "fingers", "forearms",
    # actions implying hands
    "pouring", "shaping", "gripping", "lifting the lid",
    "opening a", "pressing", "crafting", "unboxing", "handshake", "shaking hands",
    # people roles
    "person", "people", "man", "woman", "men", "women",
    "patient", "doctor", "dentist", "nurse", "therapist",
    "chef", "barista", "waiter", "waitress",
    "trainer", "instructor", "coach",
    "client", "agent", "lawyer", "attorney", "advisor",
    "team", "group", "couple", "friends", "family",
    "professional", "worker", "employee", "staff",
    "yogis", "runner", "athlete", "jogger",
    "customer", "artisan", "model", "shopper",
    "receptionist", "scientist", "researcher",
    # people descriptors
    "smiling", "seated", "standing", "walking", "running",
    "mid-stride", "mid-run", "mid-laugh",
]

def requires_hands(prompt_text: str) -> bool:
    """Return True if the prompt features people — route to Imagen 4."""
    lower = prompt_text.lower()
    return any(kw in lower for kw in PEOPLE_KEYWORDS)


def build_prompt(user_prompt: str) -> str:
    return f"{user_prompt.rstrip(', ')}. {POSITIVE_SUFFIX}"


# Trained LoRA — pvstyle trigger word baked into every generation
LORA_URL = "https://v3b.fal.media/files/b/0a9283ec/1QVm7y033qRAs8kbnqYUM_pytorch_lora_weights.safetensors"
LORA_SCALE = 0.85


class FalClient:
    BASE_URL = "https://fal.run/fal-ai/flux-lora"

    def __init__(self, api_key: str):
        # fal.ai key format: "key_id:key_secret"
        self.api_key = api_key

    async def _post(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Key {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    def _base_payload(self, prompt: str, ratio: str, count: int) -> dict:
        return {
            "prompt": f"pvstyle {build_prompt(prompt)}",
            "negative_prompt": NEGATIVE_PROMPT,
            "loras": [{"path": LORA_URL, "scale": LORA_SCALE}],
            "aspect_ratio": ratio if ratio in SUPPORTED_RATIOS else "16:9",
            "num_images": count,
            "output_format": "jpeg",
            "safety_tolerance": "2",
        }

    async def generate_image(self, prompt: str, ratio: str = "16:9") -> dict:
        payload = self._base_payload(prompt, ratio, 1)
        result = await self._post(payload)
        image_url = result["images"][0]["url"]
        async with httpx.AsyncClient(timeout=60) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
        return {"image_bytes": img_resp.content, "mime_type": "image/jpeg"}

    async def generate_batch(self, prompt: str, ratio: str = "16:9", count: int = 3) -> list[dict]:
        count = min(count, 5)
        payload = self._base_payload(prompt, ratio, count)
        result = await self._post(payload)
        images = []
        async with httpx.AsyncClient(timeout=60) as client:
            for img in result["images"]:
                img_resp = await client.get(img["url"])
                img_resp.raise_for_status()
                images.append({"image_bytes": img_resp.content, "mime_type": "image/jpeg"})
        return images
