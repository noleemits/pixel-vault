from datetime import datetime, timezone
import httpx

class ObsidianLogger:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "text/markdown"}

    async def log_batch(self, batch_id: int, industry: str, prompt_name: str, prompt_text: str, image_count: int, status: str):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = f"""---
batch_id: {batch_id}
industry: {industry}
status: {status}
date: {now}
---

# Batch {batch_id}: {prompt_name}

**Industry:** {industry}
**Status:** {status}
**Images:** {image_count}
**Generated:** {now}

## Prompt
```
{prompt_text}
```

## Review
_Pending review_
"""
        path = f"PixelVault/Batches/batch-{batch_id:04d}.md"
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            await client.put(
                f"{self.api_url}/vault/{path}",
                headers=self._headers(),
                content=content,
            )

    async def log_review(self, batch_id: int, approved: list[str], rejected: list[str], notes: str):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = f"""

## Review — {now}
**Approved:** {', '.join(approved)}
**Rejected:** {', '.join(rejected)}
**Notes:** {notes}
"""
        path = f"PixelVault/Batches/batch-{batch_id:04d}.md"
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            await client.post(
                f"{self.api_url}/vault/{path}",
                headers={**self._headers(), "Content-Type": "text/markdown", "Content-Insertion-Position": "end"},
                content=content,
            )

    async def log_prompt_change(self, prompt_id: int, prompt_name: str, old_text: str, new_text: str, reason: str):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = f"""---
prompt_id: {prompt_id}
date: {now}
---

# Prompt Edit: {prompt_name}

**Date:** {now}
**Reason:** {reason}

## Before
```
{old_text}
```

## After
```
{new_text}
```
"""
        path = f"PixelVault/Prompt-History/prompt-{prompt_id:03d}-{now[:10]}.md"
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            await client.put(
                f"{self.api_url}/vault/{path}",
                headers=self._headers(),
                content=content,
            )
