import os
from io import BytesIO
import httpx
from PIL import Image as PILImage

class ImageProcessor:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def build_filename(self, industry: str, style: str, number: int, ratio_label: str) -> str:
        return f"{industry}-{style}-{number:03d}-{ratio_label}.jpg"

    def save_from_pil(self, img: PILImage.Image, industry: str, style: str, number: int, ratio_label: str) -> dict:
        filename = self.build_filename(industry, style, number, ratio_label)
        filepath = os.path.join(self.storage_path, filename)
        img.save(filepath, "JPEG", quality=92)
        file_size = os.path.getsize(filepath)
        return {"filename": filename, "filepath": filepath, "file_size": file_size, "width": img.width, "height": img.height}

    def save_from_bytes(self, image_bytes: bytes, industry: str, style: str, number: int, ratio_label: str) -> dict:
        img = PILImage.open(BytesIO(image_bytes))
        return self.save_from_pil(img, industry, style, number, ratio_label)

    async def download_and_save(self, url: str, industry: str, style: str, number: int, ratio_label: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        img = PILImage.open(BytesIO(resp.content))
        return self.save_from_pil(img, industry, style, number, ratio_label)
