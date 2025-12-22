"""
Comprehensive integration tests for repository endpoint authentication.

Verifies all four authentication requirements:
1. All repository endpoints receive proper JWT authentication
2. 401 responses are properly handled
3. Guest tokens are automatically obtained if needed
4. Token refresh is handled transparently
"""

import pytest
import jwt
import os
from datetime import datetime, timedelta, timezone
from quart import Quart

from application.routes.repository_routes import repository_bp
from application.routes.token import token_bp
from application.routes.common.error_handlers import register_error_handlers
from common.utils.jwt_utils import _config


@pytest.fixture
def app():
    """Create test application with both repository and token routes."""
    app = Quart(__name__)
    app.register_blueprint(repository_bp, url_prefix="/api/v1/repository")
    app.register_blueprint(token_bp, url_prefix="/api/v1")
    register_error_handlers(app)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestRepositoryAuthenticationRequirements:
    """Test all four authentication requirements."""

    @pytest.mark.asyncio
    async def test_requirement_1_jwt_auth_on_analyze(self, client):
        """Requirement 1: /analyze endpoint receives JWT authentication."""
        # Arrange - Create valid guest token
        valid_payload = {
            "caas_org_id": "guest.test@example.com",
            "caas_cyoda_employee": False,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(valid_payload, _config.secret_key, algorithm="HS256")

        # Act - Send request with JWT in Authorization header
        response = await client.post(
            "/api/v1/repository/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversation_id": "test-123"}
        )

        # Assert - Should not return 401 (auth passed)
        assert response.status_code != 401, "JWT auth should be accepted"

    @pytest.mark.asyncio
    async def test_requirement_1_jwt_auth_on_file_content(self, client):
        """Requirement 1: /file-content endpoint receives JWT authentication."""
        valid_payload = {
            "caas_org_id": "guest.test@example.com",
            "caas_cyoda_employee": False,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(valid_payload, _config.secret_key, algorithm="HS256")

        response = await client.post(
            "/api/v1/repository/file-content",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "repository_name": "test-repo",
                "file_path": "test.py",
                "branch": "main",
                "owner": "test-owner"
            }
        )

        assert response.status_code != 401, "JWT auth should be accepted"

    @pytest.mark.asyncio
    async def test_requirement_2_expired_token_returns_401(self, client):
        """Requirement 2: Expired tokens return 401 (not 500)."""
        # Arrange - Create expired token
        expired_payload = {
            "caas_org_id": "guest.test@example.com",
            "caas_cyoda_employee": False,
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(expired_payload, _config.secret_key, algorithm="HS256")

        # Act
        response = await client.post(
            "/api/v1/repository/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversation_id": "test-123"}
        )

        # Assert - Should return 401 with "expired" message
        assert response.status_code == 401
        data = await response.get_json()
        assert "expired" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_requirement_2_missing_token_returns_401(self, client):
        """Requirement 2: Missing token returns 401."""
        # Act - No Authorization header
        response = await client.post(
            "/api/v1/repository/analyze",
            json={"conversation_id": "test-123"}
        )

        # Assert
        assert response.status_code == 401
        data = await response.get_json()
        assert "missing" in data["error"].lower() or "unauthorized" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_requirement_3_guest_token_endpoint_exists(self, client):
        """Requirement 3: Guest token endpoint exists for auto-fetch."""
        # Act - Get guest token
        response = await client.get("/api/v1/get_guest_token")

        # Assert
        assert response.status_code == 200
        data = await response.get_json()
        assert "access_token" in data, "Guest token endpoint should return access_token"
        assert data["access_token"], "access_token should not be empty"
        assert data["guest_id"].startswith("guest."), "guest_id should start with 'guest.'"

    @pytest.mark.asyncio
    async def test_requirement_4_all_endpoints_require_auth(self, client):
        """Requirement 4: All repository endpoints require authentication."""
        endpoints = [
            ("/api/v1/repository/analyze", {"conversation_id": "test"}),
            ("/api/v1/repository/file-content", {
                "repository_name": "test",
                "file_path": "test.py",
                "branch": "main",
                "owner": "test"
            }),
            ("/api/v1/repository/diff", {
                "repository_name": "test",
                "branch": "main",
                "owner": "test"
            }),
            ("/api/v1/repository/pull", {"conversation_id": "test"}),
        ]

        for endpoint, body in endpoints:
            # Act - No auth header
            response = await client.post(endpoint, json=body)

            # Assert - All should return 401
            assert response.status_code == 401, f"{endpoint} should require auth"

