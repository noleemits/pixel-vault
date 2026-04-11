"""Tests for dual auth: API key + JWT."""
import os
import sys
from unittest.mock import patch, MagicMock

# Set DATABASE_URL before any app module import to avoid RuntimeError
os.environ.setdefault("DATABASE_URL", "postgresql://fake:fake@localhost/fake")

from jose import jwt

TEST_JWT_SECRET = "test-secret-at-least-32-characters-long!!"


def _make_test_jwt(email: str, secret: str = TEST_JWT_SECRET) -> str:
    return jwt.encode(
        {"email": email, "sub": "test-user-uuid", "role": "authenticated"},
        secret,
        algorithm="HS256",
    )


def test_verify_supabase_jwt_valid():
    from app.auth import verify_supabase_jwt
    with patch("app.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_JWT_SECRET
        email = verify_supabase_jwt(_make_test_jwt("user@example.com"))
        assert email == "user@example.com"


def test_verify_supabase_jwt_invalid():
    from app.auth import verify_supabase_jwt
    with patch("app.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_JWT_SECRET
        assert verify_supabase_jwt("garbage-token") is None


def test_verify_supabase_jwt_wrong_secret():
    from app.auth import verify_supabase_jwt
    token = _make_test_jwt("user@example.com", secret="wrong-secret-that-is-long-enough!!!!!!")
    with patch("app.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_JWT_SECRET
        assert verify_supabase_jwt(token) is None


def test_verify_supabase_jwt_no_secret_configured():
    from app.auth import verify_supabase_jwt
    with patch("app.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = ""
        assert verify_supabase_jwt(_make_test_jwt("user@example.com")) is None
