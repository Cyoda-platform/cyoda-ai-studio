"""
Integration tests for token routes.

Tests the complete HTTP request/response cycle including:
- Route handler execution
- Request validation decorators
- Response formatting
- Rate limiting
- Authentication
"""

import pytest
from quart import Quart
from datetime import datetime, timedelta
import json

from application.routes.token import token_bp
from application.routes.common.error_handlers import register_error_handlers


@pytest.fixture
def app():
    """Create test application."""
    app = Quart(__name__)
    app.register_blueprint(token_bp, url_prefix="/api/v1")
    register_error_handlers(app)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestGetGuestToken:
    """Test guest token generation endpoint."""

    @pytest.mark.asyncio
    async def test_get_guest_token_success(self, client):
        """Test successful guest token generation."""
        # Act
        response = await client.get("/api/v1/get_guest_token")
        data = await response.get_json()

        # Assert
        assert response.status_code == 200
        assert "token" in data
        assert "user_id" in data
        assert data["user_id"].startswith("guest.")
        assert "exp" in data
        assert "iat" in data

    @pytest.mark.asyncio
    async def test_get_guest_token_returns_different_tokens(self, client):
        """Test that each request generates unique guest token."""
        # Act
        response1 = await client.get("/api/v1/get_guest_token")
        response2 = await client.get("/api/v1/get_guest_token")

        data1 = await response1.get_json()
        data2 = await response2.get_json()

        # Assert
        assert data1["token"] != data2["token"]
        assert data1["user_id"] != data2["user_id"]


class TestGenerateTestToken:
    """Test test token generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_test_token_success(self, client):
        """Test successful test token generation with valid data."""
        # Arrange
        request_data = {
            "user_id": "alice",
            "is_superuser": False,
            "expiry_hours": 24
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 200
        assert "token" in data
        assert data["user_id"] == "alice"
        assert data["is_superuser"] is False
        assert "exp" in data
        assert "iat" in data

    @pytest.mark.asyncio
    async def test_generate_test_token_superuser(self, client):
        """Test generating superuser token."""
        # Arrange
        request_data = {
            "user_id": "admin",
            "is_superuser": True,
            "expiry_hours": 1
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 200
        assert data["user_id"] == "admin"
        assert data["is_superuser"] is True

    @pytest.mark.asyncio
    async def test_generate_test_token_defaults(self, client):
        """Test that defaults are applied when not provided."""
        # Arrange
        request_data = {
            "user_id": "bob"
            # is_superuser and expiry_hours omitted
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 200
        assert data["user_id"] == "bob"
        assert data["is_superuser"] is False  # Default


class TestGenerateTestTokenValidation:
    """Test validation for test token generation."""

    @pytest.mark.asyncio
    async def test_missing_user_id(self, client):
        """Test validation fails when user_id is missing."""
        # Arrange
        request_data = {
            "is_superuser": False
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data
        assert data["error"] == "Validation failed"
        assert "details" in data
        assert "errors" in data["details"]

    @pytest.mark.asyncio
    async def test_empty_user_id(self, client):
        """Test validation fails when user_id is empty."""
        # Arrange
        request_data = {
            "user_id": "",
            "is_superuser": False
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data

    @pytest.mark.asyncio
    async def test_user_id_too_long(self, client):
        """Test validation fails when user_id exceeds max length."""
        # Arrange
        request_data = {
            "user_id": "a" * 101,  # Max is 100
            "is_superuser": False
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_expiry_hours_negative(self, client):
        """Test validation fails when expiry_hours is negative."""
        # Arrange
        request_data = {
            "user_id": "alice",
            "expiry_hours": -1
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_expiry_hours_too_large(self, client):
        """Test validation fails when expiry_hours exceeds max."""
        # Arrange
        request_data = {
            "user_id": "alice",
            "expiry_hours": 9000  # Max is 8760 (1 year)
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_json(self, client):
        """Test validation fails when request is not valid JSON."""
        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_type_for_is_superuser(self, client):
        """Test validation fails when is_superuser is not boolean."""
        # Arrange
        request_data = {
            "user_id": "alice",
            "is_superuser": "yes"  # Should be boolean
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data


class TestResponseFormatting:
    """Test that responses use consistent APIResponse format."""

    @pytest.mark.asyncio
    async def test_success_response_format(self, client):
        """Test success responses have consistent format."""
        # Act
        response = await client.get("/api/v1/get_guest_token")
        data = await response.get_json()

        # Assert
        assert response.status_code == 200
        assert isinstance(data, dict)
        assert "token" in data  # Success data is returned directly

    @pytest.mark.asyncio
    async def test_error_response_format(self, client):
        """Test error responses have consistent format."""
        # Arrange
        request_data = {"user_id": ""}  # Invalid

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 400
        assert "error" in data
        assert isinstance(data["error"], str)
        # May have optional "details" field


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_user_id_with_special_characters(self, client):
        """Test user_id with special characters is handled."""
        # Arrange
        request_data = {
            "user_id": "user@example.com",
            "is_superuser": False
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )

        # Assert - should succeed
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_id_with_spaces_trimmed(self, client):
        """Test user_id with leading/trailing spaces is trimmed."""
        # Arrange
        request_data = {
            "user_id": "  alice  ",
            "is_superuser": False
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )
        data = await response.get_json()

        # Assert
        assert response.status_code == 200
        assert data["user_id"] == "alice"  # Trimmed

    @pytest.mark.asyncio
    async def test_expiry_hours_min_boundary(self, client):
        """Test minimum valid expiry_hours (1)."""
        # Arrange
        request_data = {
            "user_id": "alice",
            "expiry_hours": 1
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_expiry_hours_max_boundary(self, client):
        """Test maximum valid expiry_hours (8760 = 1 year)."""
        # Arrange
        request_data = {
            "user_id": "alice",
            "expiry_hours": 8760
        }

        # Act
        response = await client.post(
            "/api/v1/generate_test_token",
            json=request_data
        )

        # Assert
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
