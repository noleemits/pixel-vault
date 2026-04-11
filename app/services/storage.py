"""
app/services/storage.py — Cloudflare R2 object storage (S3-compatible).

Handles upload, URL generation, and deletion for the PixelVault image library.
Falls back gracefully when R2 is not configured (local-only mode).
"""

import logging
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class R2Storage:
    """Cloudflare R2 storage client using the S3-compatible API."""

    def __init__(self):
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(settings.r2_access_key and settings.r2_endpoint)

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint,
                aws_access_key_id=settings.r2_access_key,
                aws_secret_access_key=settings.r2_secret_key,
                config=BotoConfig(signature_version="s3v4"),
                region_name="auto",
            )
        return self._client

    def build_key(self, filename: str) -> str:
        """Build the R2 object key from a filename. e.g. images/healthcare-clinic-001-16x9.jpg"""
        return f"images/{filename}"

    def build_cdn_url(self, key: str) -> str:
        """Build the public CDN URL for an object key."""
        domain = settings.cdn_domain.rstrip("/")
        return f"https://{domain}/{key}"

    def upload_file(self, filepath: str, key: str) -> str:
        """
        Upload a local file to R2.

        Returns the CDN URL of the uploaded object.
        Raises if R2 is not configured.
        """
        if not self.enabled:
            raise RuntimeError("R2 storage is not configured")

        content_type = "image/jpeg"
        if filepath.lower().endswith(".png"):
            content_type = "image/png"
        elif filepath.lower().endswith(".webp"):
            content_type = "image/webp"

        self.client.upload_file(
            Filename=filepath,
            Bucket=settings.r2_bucket,
            Key=key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "public, max-age=31536000, immutable",
            },
        )
        logger.info("Uploaded %s → r2://%s/%s", filepath, settings.r2_bucket, key)
        return self.build_cdn_url(key)

    def upload_bytes(self, data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        """Upload raw bytes to R2. Returns the CDN URL."""
        if not self.enabled:
            raise RuntimeError("R2 storage is not configured")

        self.client.put_object(
            Bucket=settings.r2_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        logger.info("Uploaded %d bytes → r2://%s/%s", len(data), settings.r2_bucket, key)
        return self.build_cdn_url(key)

    def delete(self, key: str) -> None:
        """Delete an object from R2."""
        if not self.enabled:
            return
        try:
            self.client.delete_object(Bucket=settings.r2_bucket, Key=key)
            logger.info("Deleted r2://%s/%s", settings.r2_bucket, key)
        except ClientError as e:
            logger.warning("Failed to delete r2://%s/%s: %s", settings.r2_bucket, key, e)

    def exists(self, key: str) -> bool:
        """Check if an object exists in R2."""
        if not self.enabled:
            return False
        try:
            self.client.head_object(Bucket=settings.r2_bucket, Key=key)
            return True
        except ClientError:
            return False


# Module-level singleton — import and use directly.
r2 = R2Storage()
