import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.obsidian_logger import ObsidianLogger

@pytest.mark.asyncio
async def test_log_batch_creates_note():
    logger = ObsidianLogger(api_url="https://127.0.0.1:27124", api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client_instance = AsyncMock()
    mock_client_instance.put = AsyncMock(return_value=mock_resp)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        await logger.log_batch(
            batch_id=1,
            industry="healthcare",
            prompt_name="Modern Dental Clinic",
            prompt_text="Bright modern dental clinic...",
            image_count=4,
            status="completed",
        )
        mock_client_instance.put.assert_called_once()
        call_args = mock_client_instance.put.call_args
        assert "PixelVault/Batches/" in str(call_args)

@pytest.mark.asyncio
async def test_log_review_appends_to_note():
    logger = ObsidianLogger(api_url="https://127.0.0.1:27124", api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_resp)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        await logger.log_review(
            batch_id=1,
            approved=["img1.jpg", "img2.jpg"],
            rejected=["img3.jpg"],
            notes="Good lighting, hands need work on img3",
        )
        mock_client_instance.post.assert_called_once()
