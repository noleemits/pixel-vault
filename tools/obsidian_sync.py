"""
Push all PixelVault session updates to Obsidian.
Run after opening Obsidian with the Local REST API plugin active.
Usage: python tools/obsidian_sync.py
"""
import httpx, os, sys
from dotenv import load_dotenv
load_dotenv()

API_URL = os.environ.get("OBSIDIAN_API_URL", "https://127.0.0.1:27124")
API_KEY = os.environ.get("OBSIDIAN_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "text/markdown"}

NOTES = {
    "PixelVault/Architecture/image-generation-models.md": """---
type: architecture
updated: 2026-03-17
---

# Image Generation Models

## Current Setup — Hybrid Router

The router in `app/routers/generation.py` automatically picks the model based on prompt content.

### FLUX 1.1 Pro (fal.ai) — Environment & Product Shots
- **Endpoint:** `fal-ai/flux-lora` (with pvstyle LoRA)
- **Used for:** All prompts WITHOUT people or hands
- **Cost:** $0.04/image
- **LoRA:** `pvstyle` trigger word, trained on 22 CC0/AI reference images
- **LoRA URL:** `https://v3b.fal.media/files/b/0a9283ec/1QVm7y033qRAs8kbnqYUM_pytorch_lora_weights.safetensors`
- **LoRA Scale:** 0.85
- **Strengths:** Interiors, exteriors, products, food, abstract, environments
- **Weaknesses:** Hands, faces in close-up, human interactions

### Imagen 4 Standard (Google) — People & Hands
- **Model:** `imagen-4.0-generate-001`
- **Endpoint:** `generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict`
- **Used for:** All prompts with people, hands, handshakes, consultations
- **Cost:** $0.04/image
- **Aspect ratios supported:** 1:1, 3:4, 4:3, 9:16, 16:9 ✅
- **Strengths:** Anatomy, hand positioning, natural eye contact, prompt adherence
- **Why not Gemini 2.5 Flash Image:** Tested — does NOT support aspect ratios (always 1024x1024 square). Rejected.

## Routing Logic
Keyword detection in `app/services/fal_client.py` → `requires_hands()` function.
If prompt contains: hands, fingers, pouring, shaping, gripping, barista, handshake, etc. → Imagen 4
Otherwise → FLUX

## Models Available for Future Upgrade (same API key)
- `gemini-3-pro-image-preview` — Premium quality, higher cost
- `nano-banana-pro-preview` — Google's internal codename model
- `gemini-2.5-flash-image` — Good quality but NO aspect ratio support
- `imagen-4.0-fast-generate-001` — $0.02/image, lower quality, for batch bank building
- `imagen-4.0-ultra-generate-001` — Higher quality, higher cost

## FLUX LoRA Training
- **Training set:** 22 images (CC0 + AI-generated) across 6 industries
- **Training cost:** $2 on fal.ai
- **Trigger word:** `pvstyle`
- **ZIP source:** https://github.com/noleemits/pixel-vault/releases/tag/v0.1-lora

## AI Upscaler — HQ Tier (Phase 2)
- **Model:** fal.ai `aura-sr` or `creative-upscaler`
- **Purpose:** Post-generation upscale from native (~1408px) to 2500px+
- **Cost:** ~$0.03/image (raw), sold at $0.03-0.08 depending on plan tier
- **When:** Optional step triggered by user selecting HQ quality before generation
- **Pipeline:** Generate at native res -> AI upscale -> save both SD + HQ versions
""",

    "PixelVault/Architecture/product-model.md": """---
type: architecture
updated: 2026-03-17
---

# Product Model

## Core Concept
**Plugin-first, not dashboard-first.**

The WordPress plugin IS the product. The dashboard is back-office infrastructure.
Most users never visit the dashboard — they find and insert images from within WordPress.

## Acquisition Flow
Install plugin → works in limited free mode → user sees value → creates account → converts to paid

## Pricing Tiers
| Plan | Price | Generations/mo | Sync Limit | HQ Upscale |
|---|---|---|---|---|
| Free | $0 | 3 | 50 images | Not available |
| Solo | $12/mo | 20 | 300 images | $0.08/image |
| Pro | $24/mo | 60 | 1,500 images | $0.05/image |
| Agency | $49/mo | 150 | Unlimited | $0.03/image |

**Top-ups:** $0.10/generation
**Benchmark:** Freepik Premium $12-24/mo — must be at or below for Solo tier

## Image Quality Tiers
- **SD (Standard):** Native model resolution (~1408x768 for 16:9). Included in plan.
- **HQ (High Quality):** AI upscaled to 2500px+. Per-image cost above. Uses fal.ai upscaler post-generation.
- Raw upscale cost ~$0.03/image. HQ pricing includes margin that decreases with plan tier.

## Sync Limit Model
Users think in images, not GB. Sync limit = number of images actively tracked across all connected sites.
When limit hit → images still work, just not monitored by anti-duplicate system.
This creates natural upgrade incentive.

## Key Differentiator
**Anti-duplicate system** — "Images that don't repeat between your clients' sites."
The plugin tracks which image is deployed on which site. No competing sites get the same image.

## Two-Layer Naming
- `canonical_name` in PixelVault library — stable, never changes (e.g. `healthcare-dentist-hero-01`)
- `local_filename` at deployment — SEO-optimized from post keywords (e.g. `affordable-dental-implants-miami-hero.jpg`)
""",

    "PixelVault/Architecture/storage-infrastructure.md": """---
type: architecture
updated: 2026-03-17
status: Phase 2 — not yet implemented
---

# Storage Infrastructure (Phase 2)

## Current State
Local file storage at `./storage/images/` — MVP only, not scalable.

## Target Architecture

### Storage: Cloudflare R2
- $0.015/GB/month storage
- $0 egress (critical — S3 charges $0.09/GB egress)
- Integrated with Cloudflare CDN natively

### Delivery: Cloudflare CDN
- Custom domain: `images.pixelvault.io`
- 300+ edge nodes globally
- Images cached at the edge — instant load in plugin sidebar

### Optimization: Cloudflare Images
- On-the-fly resizing: `?w=200&f=webp` for thumbnails
- `?w=1200&f=webp` for full insertions
- ~$5/mo base + $1 per 1,000 transformations

### Image Versions
- **Original:** PNG/JPEG 100%, up to 2048px — cold/warm storage, owner-only download
- **Web:** WebP 85%, max 2048px — hot storage + CDN
- **Thumbnail:** Generated on-the-fly, not stored permanently

### Storage Tiers
- **HOT:** Official bank + images used 10+ times in 30 days → R2 + CDN
- **WARM:** Community images, recent user generations → R2
- **COLD:** Unused 90+ days, originals → Backblaze B2 ($0.006/GB)

### Serving Options (user choice)
- **CDN (default):** `src` points to `images.pixelvault.io` — fast globally
- **Local:** Plugin downloads to `/wp-content/uploads/pixelvault/` at insertion
- **Fallback:** Local copy always created at insertion regardless of serving choice

## Cost Projections
| Stage | Images | Storage/mo |
|---|---|---|
| Launch | 500 | ~$5 |
| 50 users | 10,000 | ~$7 |
| 500 users | 100,000 | ~$21 |
| 2,000 users | 500,000 | ~$60 |
""",

    "PixelVault/Architecture/database-schema.md": """---
type: architecture
updated: 2026-03-19
status: LIVE on Supabase
---

# Database Schema

## Current Setup — Supabase (PostgreSQL 17)

**Project:** nolemits pixel vault
**Region:** East US (North Virginia) — us-east-1
**Host:** aws-1-us-east-1.pooler.supabase.com (Session pooler, port 6543)
**Direct host:** db.rnfinyrluxokvdzxhvuv.supabase.co (IPv6 only)
**Plan:** Free tier (Nano)

Migrated from SQLite on 2026-03-19. All 48 prompts transferred successfully.

## Tables (7)

| Table | Purpose |
|---|---|
| accounts | Multi-tenant user accounts, plan limits, Stripe ID |
| api_keys | Hashed API keys per account |
| sites | WordPress sites connected per account |
| prompts | 48 master prompts (8 per industry, 6 industries) |
| batches | Generation batch tracking |
| images | Master image records with model/router metadata |
| image_deployments | Anti-duplicate tracking — which image on which site |

## Key Indexes
- `idx_images_industry_style_ratio` — fast filtering by industry/style/ratio
- `idx_images_usage_count` — popularity sorting
- `idx_image_deployments_image_account` — anti-duplicate lookups
- `idx_image_deployments_account_active` — sync limit counting

## Key Queries

```sql
-- Anti-duplicate check
SELECT site_id, local_filename, post_title
FROM image_deployments
WHERE image_id = $1 AND account_id = $2 AND is_active = true;

-- Sync limit count
SELECT COUNT(DISTINCT image_id)
FROM image_deployments
WHERE account_id = $1 AND is_active = true;
```

## Connection Notes
- Direct connection is IPv6 only — use Session pooler for local dev on Windows
- App uses asyncpg (async) + psycopg2 (sync for Alembic)
- DATABASE_URL in .env, auto-normalized by app/database.py
""",

    "PixelVault/Sessions/2026-03-17-session.md": """---
type: session-log
date: 2026-03-17
---

# Session Log — 2026-03-17

## Decisions Made

### Image Generation
- Switched from FLUX-only to hybrid routing (FLUX + Imagen 4)
- Imagen 4 for people/hands prompts, FLUX for environments/products
- Routing via keyword detection in `requires_hands()` function
- Tested Gemini 2.5 Flash Image — rejected due to no aspect ratio support (always 1024x1024)
- Confirmed Imagen 4 Standard as people/hands model — supports all ratios

### FLUX LoRA Training
- Trained `pvstyle` LoRA on 22 reference images
- Training cost: $2 on fal.ai
- Hosted training set on GitHub: pixel-vault/releases/v0.1-lora
- LoRA wired into all FLUX generations at scale 0.85

### Prompt Engineering
- Applied ROLE/CONTEXT/CONSTRAINTS/OUTPUT framework to 22 people-interaction prompts
- Rules: exact subject count, explicit gaze, explicit hand positions, wide shot specified
- Installed `prompt-engineering` skill from skills.ws

### FLUX Global Negative Prompt Updated
Added: `hands in frame, fingers visible, human body parts, hand reaching into frame`
This prevents FLUX adding uninvited hands to food/product shots.

### Google API Key Updated
New key: (stored in .env as GOOGLE_API_KEY)

## Product Direction (from chat-claude.md review)
- Plugin-first product model confirmed
- Pricing tiers defined (Free/$0, Solo/$12, Pro/$24, Agency/$49)
- Sync limit model (not GB storage)
- Anti-duplicate system is core differentiator
- Two-layer naming system (canonical + local SEO)
- Cloudflare R2 + CDN for Phase 2 storage
""",

    "PixelVault/Sessions/2026-03-19-session.md": """---
type: session-log
date: 2026-03-19
---

# Session Log — 2026-03-19

## Supabase Migration Completed

### Database Setup
- Created Supabase project: **nolemits pixel vault** (Free/Nano tier)
- Region: East US (North Virginia) — us-east-1
- PostgreSQL 17.6.1.084
- RLS disabled for now (will enable per-table when building multi-tenant API)

### Schema Deployed
- 7 tables created via SQL Editor: accounts, api_keys, sites, prompts, batches, images, image_deployments
- 4 indexes for performance (industry/style/ratio, usage_count, anti-duplicate, sync limit)

### Data Migration
- 48 prompts migrated from SQLite to Supabase (8 per industry, 6 industries)
- Migration script: `tools/migrate_to_supabase.py`

### Connection
- Direct host (IPv6 only): db.rnfinyrluxokvdzxhvuv.supabase.co:5432
- Session pooler (IPv4): aws-1-us-east-1.pooler.supabase.com:6543
- Windows local dev requires Session pooler due to IPv6 DNS resolution issues
- App uses asyncpg (async) + psycopg2 (sync for Alembic)

### Code Updated
- `app/database.py` — async PostgreSQL engine replacing SQLite
- `app/models.py` — expanded with Account, ApiKey, Site, ImageDeployment models
- `alembic.ini` + `alembic/env.py` — migration tooling configured
- Dependencies installed: asyncpg, psycopg2-binary

## Next Steps
- [ ] Generate image bank (~480 images across 48 prompts)
- [ ] Top up fal.ai balance for FLUX generations
- [ ] Clean old generated images (keep last 6)
- [ ] Admin billing/token tracking dashboard (Phase 2)
- [ ] Cloudflare R2 storage migration (Phase 2)
- [ ] WordPress plugin development (Phase 2)
""",

    "PixelVault/Sessions/2026-03-20-session.md": """---
type: session-log
date: 2026-03-20
---

# Session Log -- 2026-03-20

## Image Bank Generated
- 194 images generated across all 48 prompts (6 industries)
- 166 approved, 28 rejected after manual curation
- Hybrid routing confirmed working: 38 prompts -> Imagen 4 (people), 10 -> FLUX (environments)
- Current resolutions: 1408x768 (FLUX), 1024x768 (Imagen 4)

## Supabase Connection Fixed
- Session pooler URL: aws-1-us-east-1.pooler.supabase.com:6543
- Fixed DATABASE_URL loading (added dotenv to CLI entry point)
- Fixed async engine error in main.py lifespan (switched to sync_engine for create_all)
- Fixed all routers to use get_sync_db instead of async get_db

## Schema Fixes
- ImageOut schema updated: UUID id, removed tags field, added model_used/router_reason
- Review UI pagination added (50 per page)
- Obsidian logging made non-fatal (try/except around obsidian.log_batch)

## Image Quality Decision
- Native resolution too low for production use (~1408px max)
- Decision: Offer SD (Standard) and HQ (High Quality) tiers
- SD = native resolution, included in plan
- HQ = AI upscaled to 2500px+, per-image cost ($0.03-0.08 depending on plan)
- Upscaler: fal.ai aura-sr or creative-upscaler (~$0.03/image raw cost)
- HQ pricing decreases with higher plan tiers

## Updated Pricing (HQ column added)
| Plan | HQ Price |
|---|---|
| Free | Not available |
| Solo | $0.08/image |
| Pro | $0.05/image |
| Agency | $0.03/image |

## Next Steps
- [ ] Wire up AI upscaler in generation pipeline (SD/HQ toggle)
- [ ] Cloudflare R2 storage migration
- [ ] WordPress plugin development
- [ ] API auth layer (accounts, API keys, usage limits)
""",
}

def push():
    print("Pushing updates to Obsidian...\n")
    ok, fail = 0, 0
    with httpx.Client(verify=False, timeout=15) as client:
        for path, content in NOTES.items():
            resp = client.put(
                f"{API_URL}/vault/{path}",
                headers=HEADERS,
                content=content.encode()
            )
            if resp.status_code in (200, 204):
                print(f"  OK {path}")
                ok += 1
            else:
                print(f"  FAIL {path} -- {resp.status_code}: {resp.text[:80]}")
                fail += 1
    print(f"\nDone -- {ok} updated, {fail} failed.")

if __name__ == "__main__":
    push()
