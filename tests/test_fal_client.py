import pytest
from unittest.mock import AsyncMock, patch
from app.services.fal_client import FalClient

@pytest.mark.asyncio
async def test_generate_image_returns_url():
    mock_response = {
        "images": [{"url": "https://fal.media/files/test/image1.jpg", "width": 1920, "height": 1080}]
    }
    client = FalClient(api_key="test-key")
    with patch.object(client, "_post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.generate_image(
            prompt="A bright modern dental clinic",
            ratio="16:9",
        )
    assert result["url"] == "https://fal.media/files/test/image1.jpg"
    assert result["width"] == 1920

@pytest.mark.asyncio
async def test_generate_image_batch():
    mock_response = {
        "images": [{"url": f"https://fal.media/files/test/img{i}.jpg", "width": 1920, "height": 1080} for i in range(3)]
    }
    client = FalClient(api_key="test-key")
    with patch.object(client, "_post", new_callable=AsyncMock, return_value=mock_response):
        results = await client.generate_batch(
            prompt="A bright modern dental clinic",
            ratio="16:9",
            count=3,
        )
    assert len(results) == 3
