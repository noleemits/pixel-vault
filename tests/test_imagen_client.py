# tests/test_imagen_client.py
import base64
import pytest
from unittest.mock import AsyncMock, patch
from app.services.imagen_client import ImagenClient, normalize_ratio

def test_normalize_ratio():
    assert normalize_ratio("16:9") == "16:9"
    assert normalize_ratio("4:5") == "3:4"
    assert normalize_ratio("21:9") == "16:9"
    assert normalize_ratio("1:1") == "1:1"

@pytest.mark.asyncio
async def test_generate_image_returns_bytes():
    fake_image = base64.b64encode(b"fake-png-data").decode()
    mock_response = {
        "predictions": [{"bytesBase64Encoded": fake_image, "mimeType": "image/png"}]
    }
    client = ImagenClient(api_key="test-key")
    with patch.object(client, "_post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.generate_image(prompt="A dental clinic", ratio="16:9")
    assert result["image_bytes"] == b"fake-png-data"
    assert result["mime_type"] == "image/png"

@pytest.mark.asyncio
async def test_generate_batch():
    fake_image = base64.b64encode(b"fake-png-data").decode()
    mock_response = {
        "predictions": [
            {"bytesBase64Encoded": fake_image, "mimeType": "image/png"},
            {"bytesBase64Encoded": fake_image, "mimeType": "image/png"},
            {"bytesBase64Encoded": fake_image, "mimeType": "image/png"},
        ]
    }
    client = ImagenClient(api_key="test-key")
    with patch.object(client, "_post", new_callable=AsyncMock, return_value=mock_response):
        results = await client.generate_batch(prompt="A dental clinic", ratio="16:9", count=3)
    assert len(results) == 3
    assert results[0]["image_bytes"] == b"fake-png-data"
