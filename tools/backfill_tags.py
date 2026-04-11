"""
tools/backfill_tags.py — Tag all existing images based on their prompt text + industry.

Usage:
    python -m tools.backfill_tags          # dry-run (shows what would be tagged)
    python -m tools.backfill_tags --apply  # actually write tags to DB

Requires the app to be importable (run from project root).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models import Image, Prompt
from app.services.auto_tagger import auto_tag_image, seed_tags


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()

    # Ensure all predefined tags exist.
    created = seed_tags(db)
    if created:
        print(f"Seeded {created} new predefined tags.")

    images = db.query(Image).all()
    print(f"Found {len(images)} images to process.\n")

    total_tagged = 0
    min_tags = float("inf")

    for img in images:
        # Get prompt text for this image.
        prompt = db.query(Prompt).filter(Prompt.id == img.prompt_id).first()
        prompt_text = prompt.prompt_text if prompt else img.filename

        existing_tags = [t.name for t in img.tags]
        assigned = auto_tag_image(db, img, prompt_text, img.industry)

        all_tags = set(existing_tags) | set(assigned)
        tag_count = len(all_tags)

        if tag_count < min_tags:
            min_tags = tag_count

        if assigned:
            total_tagged += 1
            if not apply:
                print(f"  {img.filename}: +{len(assigned)} tags -> {sorted(all_tags)}")

    if apply:
        db.commit()
        print(f"\nApplied tags to {total_tagged} images.")
    else:
        db.rollback()
        print(f"\n[DRY RUN] Would tag {total_tagged} images. Use --apply to write.")

    # Summary.
    print(f"Total images: {len(images)}")
    print(f"Minimum tags per image: {min_tags if min_tags != float('inf') else 0}")

    # Check acceptance criteria: all images should have >= 2 tags.
    under_2 = 0
    for img in images:
        if apply:
            db.refresh(img)
        if len(img.tags) < 2:
            under_2 += 1
            if under_2 <= 10:
                print(f"  WARNING: {img.filename} has only {len(img.tags)} tag(s)")

    if under_2:
        print(f"\n{under_2} images have fewer than 2 tags. Consider adding more keywords to auto_tagger.py.")
    else:
        print(f"\nAll images have at least 2 tags.")

    db.close()


if __name__ == "__main__":
    main()
