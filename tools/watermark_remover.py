"""
tools/watermark_remover.py

Removes the Gemini sparkle watermark (✦) from AI-generated images
before LoRA training.

Usage:
    # Single image
    python tools/watermark_remover.py image.jpg

    # Whole folder
    python tools/watermark_remover.py lora-inputs/

    # Custom output folder
    python tools/watermark_remover.py lora-inputs/ --out lora-inputs/cleaned/
"""

import sys
import argparse
import numpy as np
import cv2
from pathlib import Path
from PIL import Image

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}

# Inpaint radius around detected sparkle
INPAINT_RADIUS = 14
MASK_PADDING   = 22


def find_sparkle(img_bgr: np.ndarray) -> tuple[int, int] | None:
    """
    Scan the full image for the Gemini sparkle (✦).
    The sparkle is a small bright cross/star shape — isolated, near-white.
    Returns (cx, cy) center of sparkle, or None if not found.
    """
    h, w = img_bgr.shape[:2]

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Threshold: keep near-white pixels
    _, bright = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # Morphological open to remove noise, then find blobs
    kernel_open  = np.ones((3, 3), np.uint8)
    kernel_close = np.ones((5, 5), np.uint8)
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN,  kernel_open)
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, kernel_close)

    contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 15 or area > 3000:
            continue

        M = cv2.moments(c)
        if M["m00"] == 0:
            continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        # Sparkle is isolated — check surroundings are darker
        pad = 30
        x1, y1 = max(0, cx - pad), max(0, cy - pad)
        x2, y2 = min(w, cx + pad), min(h, cy + pad)
        region = gray[y1:y2, x1:x2]
        local_mean = float(region.mean())

        # The sparkle blob should be significantly brighter than its neighbourhood
        blob_mask   = np.zeros_like(gray)
        cv2.drawContours(blob_mask, [c], -1, 255, -1)
        blob_pixels = gray[blob_mask == 255]
        blob_mean   = float(blob_pixels.mean()) if len(blob_pixels) else 0

        isolation_score = blob_mean - local_mean

        # Only accept if clearly brighter than surroundings and small enough to be a watermark
        if isolation_score > 30 and area < 2500:
            # Prefer candidates in the outer 20% of the image (edges)
            edge_dist = min(cx, w - cx, cy, h - cy) / min(w, h)
            candidates.append((isolation_score, edge_dist, cx, cy, area))

    if not candidates:
        return None

    # Sort by: highest isolation first, then closest to edge
    candidates.sort(key=lambda x: (-x[0], x[1]))
    _, _, cx, cy, _ = candidates[0]
    return (cx, cy)


def build_mask(img_bgr: np.ndarray, cx: int, cy: int) -> np.ndarray:
    h, w = img_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (cx, cy), MASK_PADDING, 255, -1)
    return mask


def remove_watermark(image_path: Path, out_path: Path) -> bool:
    """Process a single image. Returns True if watermark was found and removed."""
    pil = Image.open(image_path).convert("RGB")
    img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    result = find_sparkle(img)

    if result is None:
        pil.save(out_path, quality=95)
        print(f"  [ ] No sparkle found, copied as-is: {image_path.name}")
        return False

    cx, cy = result
    mask    = build_mask(img, cx, cy)
    cleaned = cv2.inpaint(img, mask, INPAINT_RADIUS, cv2.INPAINT_TELEA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_pil = Image.fromarray(cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB))
    result_pil.save(out_path, quality=95)
    print(f"  [+] Sparkle removed at ({cx},{cy}): {image_path.name}")
    return True


def process(input_path: Path, out_dir: Path | None):
    if input_path.is_file():
        files = [input_path]
        default_out = input_path.parent / "cleaned"
    else:
        files = [
            f for f in input_path.iterdir()
            if f.suffix.lower() in SUPPORTED and f.parent == input_path
        ]
        files.sort()
        default_out = input_path / "cleaned"

    out_dir = out_dir or default_out
    out_dir.mkdir(parents=True, exist_ok=True)

    removed = 0
    for f in files:
        out_path = out_dir / f.name
        if remove_watermark(f, out_path):
            removed += 1

    print(f"\n  Done: {removed}/{len(files)} watermarks removed -> {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="Remove Gemini sparkle watermark from images")
    parser.add_argument("input", help="Image file or folder")
    parser.add_argument("--out", help="Output folder (default: input/cleaned/)", default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} does not exist")
        sys.exit(1)

    out_dir = Path(args.out) if args.out else None
    process(input_path, out_dir)


if __name__ == "__main__":
    main()
