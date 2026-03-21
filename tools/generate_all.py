"""
generate_all.py — Fire batch generation for all 48 prompts sequentially.
Usage: python tools/generate_all.py
"""
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

API = "http://localhost:8000/api/v1"
IMAGES_PER_PROMPT = 10
RATIO = "16:9"


def main():
    # Get all prompts
    resp = httpx.get(f"{API}/prompts", timeout=30)
    resp.raise_for_status()
    prompts = resp.json()
    print(f"Found {len(prompts)} prompts. Generating {IMAGES_PER_PROMPT} images each.\n")

    for i, p in enumerate(prompts, 1):
        print(f"[{i:>2}/{len(prompts)}] {p['industry']:<15} {p['name'][:50]}")

        try:
            r = httpx.post(
                f"{API}/generate",
                json={"prompt_id": p["id"], "count": IMAGES_PER_PROMPT, "ratio": RATIO},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            print(f"         Batch #{data['batch_id']} started")
        except Exception as e:
            print(f"         FAILED: {e}")
            continue

        # Wait for batch to complete before starting next one
        batch_id = data["batch_id"]
        for attempt in range(60):  # max 5 minutes per batch
            time.sleep(5)
            try:
                status_resp = httpx.get(f"{API}/batches/{batch_id}", timeout=10)
                status = status_resp.json().get("status", "unknown")
                if status == "completed":
                    print(f"         Completed!")
                    break
                elif status == "failed":
                    print(f"         FAILED (batch marked failed)")
                    break
            except Exception:
                pass
        else:
            print(f"         TIMEOUT — moving to next prompt")

        # Small delay between batches to be nice to APIs
        time.sleep(2)

    print("\n=== DONE ===")
    # Final stats
    try:
        stats = httpx.get(f"{API}/stats", timeout=10).json()
        print(f"Total images: {stats['total']}")
        print(f"By industry: {stats['by_industry']}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
