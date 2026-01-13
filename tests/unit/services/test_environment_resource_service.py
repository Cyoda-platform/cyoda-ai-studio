"""Tests for EnvironmentResourceService."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from application.services.environment.auth import CloudManagerAuthService
from application.services.environment.resources import EnvironmentResourceService


@pytest.fixture
def mock_auth_service():
    """Create mock auth service."""
    auth_service = MagicMock(spec=CloudManagerAuthService)
    auth_service.cloud_manager_host = "cloud-manager.test.com"
    auth_service.protocol = "https"
    auth_service.get_token = AsyncMock(return_value="test-token-123")
    return auth_service


@pytest.fixture
def resource_service(mock_auth_service):
    """Create resource service with mocked auth."""
    return EnvironmentResourceService(mock_auth_service)


class TestUserAppOperations:
    """Test user application operations."""

    @pytest.mark.asyncio
    async def test_scale_user_app_success(self, resource_service):
        """Test successful user app scaling."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"replicas": 3, "status": "scaled"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.scale_user_app(
                user_id="test-user",
                env_name="test-env",
                app_name="test-app",
                replicas=3,
            )

            assert result == {"replicas": 3, "status": "scaled"}
            mock_client.return_value.__aenter__.return_value.patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_scale_user_app_with_deployment_name(self, resource_service):
        """Test scaling with explicit deployment name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"replicas": 5, "status": "scaled"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.scale_user_app(
                user_id="test-user",
                env_name="test-env",
                app_name="test-app",
                replicas=5,
                deployment_name="custom-deployment",
            )

            assert result["replicas"] == 5
            # Verify deployment_name was used in URL
            call_args = mock_client.return_value.__aenter__.return_value.patch.call_args
            assert "custom-deployment" in str(call_args)

    @pytest.mark.asyncio
    async def test_scale_user_app_auto_detect_on_404(self, resource_service):
        """Test auto-detection of deployment name on 404."""
        # Mock the entire async client context manager
        mock_client_instance = MagicMock()

        # First call returns 404
        mock_404_response = MagicMock()
        mock_404_response.status_code = 404

        # Second call to list deployments
        mock_list_response = MagicMock()
        mock_list_response.status_code = 200
        mock_list_response.json.return_value = {
            "deployments": [{"name": "detected-deployment"}]
        }

        # Third call succeeds with detected deployment
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"replicas": 3, "status": "scaled"}
        mock_success_response.raise_for_status = MagicMock()

        # Setup async client mock
        mock_client_instance.patch = AsyncMock(
            side_effect=[mock_404_response, mock_success_response]
        )
        mock_client_instance.get = AsyncMock(return_value=mock_list_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = AsyncMock()

            result = await resource_service.scale_user_app(
                user_id="test-user",
                env_name="test-env",
                app_name="test-app",
                replicas=3,
            )

            assert result == {"replicas": 3, "status": "scaled"}
            # Verify get was called to list deployments
            mock_client_instance.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_user_app_success(self, resource_service):
        """Test successful user app restart."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "restarted"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.restart_user_app(
                user_id="test-user", env_name="test-env", app_name="test-app"
            )

            assert result == {"status": "restarted"}

    @pytest.mark.asyncio
    async def test_update_user_app_image_success(self, resource_service):
        """Test successful image update."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"image": "myapp:v2", "status": "updated"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.update_user_app_image(
                user_id="test-user",
                env_name="test-env",
                app_name="test-app",
                image="myapp:v2",
            )

            assert result["image"] == "myapp:v2"

    @pytest.mark.asyncio
    async def test_update_user_app_image_with_container(self, resource_service):
        """Test image update with specific container."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"image": "myapp:v2", "container": "api"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.update_user_app_image(
                user_id="test-user",
                env_name="test-env",
                app_name="test-app",
                image="myapp:v2",
                container="api",
            )

            assert result["container"] == "api"
            # Verify container was sent in payload
            call_args = mock_client.return_value.__aenter__.return_value.patch.call_args
            assert call_args[1]["json"]["container"] == "api"

    @pytest.mark.asyncio
    async def test_get_user_app_status_success(self, resource_service):
        """Test getting user app status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "replicas": 3}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.get_user_app_status(
                user_id="test-user", env_name="test-env", app_name="test-app"
            )

            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_user_app_metrics_success(self, resource_service):
        """Test getting user app metrics."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"cpu": "50%", "memory": "256Mi"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.get_user_app_metrics(
                user_id="test-user", env_name="test-env", app_name="test-app"
            )

            assert "cpu" in result
            assert "memory" in result

    @pytest.mark.asyncio
    async def test_get_user_app_pods_success(self, resource_service):
        """Test getting user app pods."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pods": [{"name": "pod-1"}, {"name": "pod-2"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.get_user_app_pods(
                user_id="test-user", env_name="test-env", app_name="test-app"
            )

            assert len(result["pods"]) == 2

    @pytest.mark.asyncio
    async def test_delete_user_app_success(self, resource_service):
        """Test deleting user app."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "deleted"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.delete_user_app(
                user_id="test-user", env_name="test-env", app_name="test-app"
            )

            assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_namespace_sanitization(self, resource_service):
        """Test that namespace sanitization is applied."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"replicas": 3}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
                return_value=mock_response
            )

            await resource_service.scale_user_app(
                user_id="Test_User@123",  # Should be sanitized
                env_name="Test-Env",
                app_name="Test.App",
                replicas=3,
            )

            # Verify the URL contains sanitized namespace
            call_args = mock_client.return_value.__aenter__.return_value.patch.call_args
            url = call_args[0][0]
            # Sanitized should be lowercase and use hyphens
            assert "test-user" in url.lower()
            assert "@" not in url
            assert "." not in url.split("/")[-1]  # No dots in last segment

    @pytest.mark.asyncio
    async def test_http_error_handling(self, resource_service):
        """Test HTTP error handling."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Error", request=MagicMock(), response=MagicMock()
                )
            )

            with pytest.raises(httpx.HTTPStatusError):
                await resource_service.scale_user_app(
                    user_id="test-user",
                    env_name="test-env",
                    app_name="test-app",
                    replicas=3,
                )


class TestPlatformAppOperations:
    """Test platform application operations."""

    @pytest.mark.asyncio
    async def test_list_environments_success(self, resource_service):
        """Test listing environments."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "namespaces": [
                {"name": "client-testuser-dev", "status": "Active"},
                {"name": "client-testuser-prod", "status": "Active"},
                {
                    "name": "client-1-testuser-dev-app1",
                    "status": "Active",
                },  # Should be filtered
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.list_environments(user_id="testuser")

            # Should only return environments, not app namespaces
            assert len(result) == 2
            assert result[0]["name"] == "dev"
            assert result[1]["name"] == "prod"

    @pytest.mark.asyncio
    async def test_describe_environment_success(self, resource_service):
        """Test describing an environment."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "deployments": [
                {"name": "api", "replicas": 3},
                {"name": "worker", "replicas": 2},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await resource_service.describe_environment(
                user_id="testuser", env_name="dev"
            )

            assert result["environment"] == "dev"
            assert result["count"] == 2
            assert len(result["applications"]) == 2
