import os
from PIL import Image as PILImage
from app.services.image_processor import ImageProcessor

def test_download_and_save(tmp_path):
    processor = ImageProcessor(storage_path=str(tmp_path))
    fake_img = PILImage.new("RGB", (1920, 1080), color="blue")
    saved = processor.save_from_pil(fake_img, "healthcare", "hero", 1, "16x9")
    assert os.path.exists(saved["filepath"])
    assert saved["filename"] == "healthcare-hero-001-16x9.jpg"
    assert saved["file_size"] > 0

def test_filename_convention():
    processor = ImageProcessor(storage_path="/tmp")
    name = processor.build_filename("real_estate", "lifestyle", 12, "4x3")
    assert name == "real_estate-lifestyle-012-4x3.jpg"
