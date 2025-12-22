"""
Integration tests for expired token handling.

Tests that expired tokens return 401 with proper error message,
not 500 internal server error.
"""

import pytest
import jwt
import os
from datetime import datetime, timedelta, timezone
from quart import Quart

from application.routes.repository_routes import repository_bp
from application.routes.common.error_handlers import register_error_handlers
from common.utils.jwt_utils import _config


@pytest.fixture
def app():
    """Create test application."""
    app = Quart(__name__)
    app.register_blueprint(repository_bp, url_prefix="/api/v1/repository")
    register_error_handlers(app)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestExpiredTokenHandling:
    """Test that expired tokens return 401, not 500."""

    @pytest.mark.asyncio
    async def test_expired_guest_token_returns_401(self, client):
        """Test that expired guest token returns 401 with token expired message."""
        # Arrange - Create an expired guest token using the configured secret
        expired_payload = {
            "caas_org_id": "guest.test@example.com",
            "caas_cyoda_employee": False,
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        }
        expired_token = jwt.encode(expired_payload, _config.secret_key, algorithm="HS256")

        # Act - Send request with expired token
        response = await client.post(
            "/api/v1/repository/analyze",
            headers={"Authorization": f"Bearer {expired_token}"},
            json={"conversation_id": "test-123"}
        )

        # Assert
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = await response.get_json()
        assert "error" in data
        assert "expired" in data["error"].lower(), f"Expected 'expired' in error message, got: {data['error']}"

    @pytest.mark.asyncio
    async def test_valid_guest_token_passes_auth(self, client):
        """Test that valid guest token passes authentication."""
        # Arrange - Create a valid guest token using the configured secret
        valid_payload = {
            "caas_org_id": "guest.test@example.com",
            "caas_cyoda_employee": False,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        valid_token = jwt.encode(valid_payload, _config.secret_key, algorithm="HS256")

        # Act - Send request with valid token
        response = await client.post(
            "/api/v1/repository/analyze",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"conversation_id": "test-123"}
        )

        # Assert - Should not return 401 (may return 400 or other error due to missing data, but not 401)
        assert response.status_code != 401, f"Valid token should not return 401, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self, client):
        """Test that missing token returns 401."""
        # Act - Send request without token
        response = await client.post(
            "/api/v1/repository/analyze",
            json={"conversation_id": "test-123"}
        )

        # Assert
        assert response.status_code == 401
        data = await response.get_json()
        assert "error" in data
        assert "missing" in data["error"].lower() or "unauthorized" in data["error"].lower()

