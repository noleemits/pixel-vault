"""
CLI commands for PixelVault.
Run: python -m app.cli seed
Run: python -m app.cli serve
"""
import sys
import app.models  # noqa: F401 — register models with Base before create_all
from app.database import Base, engine, SessionLocal
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

    else:
        print("Usage: python -m app.cli [seed|serve]")


if __name__ == "__main__":
    main()
