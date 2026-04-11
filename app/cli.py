"""
CLI commands for PixelVault.
Run: python -m app.cli seed
Run: python -m app.cli serve
"""
import sys
from dotenv import load_dotenv
load_dotenv()

import app.models  # noqa: F401 — register models with Base before create_all
from app.database import Base, sync_engine as engine, SessionLocal
from app.seed.master_prompts import seed_prompts


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "seed":
        Base.metadata.create_all(engine)
        db = SessionLocal()
        count = seed_prompts(db)
        db.close()
        print(f"Seeded {count} prompts.")

    elif cmd == "serve":
        import uvicorn
        Base.metadata.create_all(engine)
        db = SessionLocal()
        seed_prompts(db)
        db.close()
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

    elif cmd == "migrate-r2":
        from app.models import Image
        from app.services.storage import r2
        import os

        if not r2.enabled:
            print("ERROR: R2 is not configured. Set R2_ACCESS_KEY, R2_SECRET_KEY, R2_ENDPOINT, and CDN_DOMAIN in .env")
            sys.exit(1)

        db = SessionLocal()
        images = db.query(Image).filter(Image.cdn_url == None).all()
        print(f"Found {len(images)} images without CDN URL.")

        migrated = 0
        skipped = 0
        failed = 0

        for img in images:
            if not os.path.exists(img.filepath):
                print(f"  SKIP {img.filename} — local file not found at {img.filepath}")
                skipped += 1
                continue

            key = r2.build_key(img.filename)
            try:
                cdn_url = r2.upload_file(img.filepath, key)
                img.storage_key_web = key
                img.cdn_url = cdn_url
                db.commit()
                migrated += 1
                print(f"  OK   {img.filename} → {cdn_url}")
            except Exception as e:
                failed += 1
                print(f"  FAIL {img.filename} — {e}")

        db.close()
        print(f"\nDone: {migrated} migrated, {skipped} skipped, {failed} failed.")

    else:
        print("Usage: python -m app.cli [seed|serve|migrate-r2]")


if __name__ == "__main__":
    main()
