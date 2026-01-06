"""Unit tests for DeploymentService."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from application.services.deployment.service import (
    DeploymentResult,
    DeploymentService,
    get_deployment_service,
)


@pytest.fixture
def deployment_service():
    """Create a DeploymentService instance for testing."""
    return DeploymentService(client_host="test.cyoda.cloud")


class TestDeploymentService:
    """Test DeploymentService class."""

    def test_initialization_default_client_host(self):
        """Test service initializes with default client host from env."""
        with patch.dict(os.environ, {"CLIENT_HOST": "custom.cyoda.cloud"}):
            service = DeploymentService()
            assert service.client_host == "custom.cyoda.cloud"

    def test_initialization_custom_client_host(self):
        """Test service initializes with custom client host."""
        service = DeploymentService(client_host="custom.example.com")
        assert service.client_host == "custom.example.com"

    def test_initialization_default_fallback(self):
        """Test service falls back to cyoda.cloud if no env var."""
        with patch.dict(os.environ, {}, clear=True):
            service = DeploymentService()
            assert service.client_host == "cyoda.cloud"

    def test_normalize_for_keyspace(self):
        """Test keyspace normalization (alphanumeric + underscores)."""
        assert DeploymentService._normalize_for_keyspace("Test-User.123") == "test_user_123"
        assert DeploymentService._normalize_for_keyspace("user@example.com") == "user_example_com"
        assert DeploymentService._normalize_for_keyspace("My-App") == "my_app"
        assert DeploymentService._normalize_for_keyspace("valid_name") == "valid_name"

    def test_normalize_for_namespace(self):
        """Test namespace normalization (alphanumeric + hyphens)."""
        assert DeploymentService._normalize_for_namespace("Test_User.123") == "test-user-123"
        assert DeploymentService._normalize_for_namespace("user@example.com") == "user-example-com"
        assert DeploymentService._normalize_for_namespace("My_App") == "my-app"
        assert DeploymentService._normalize_for_namespace("valid-name") == "valid-name"

    @pytest.mark.asyncio
    async def test_deploy_cyoda_environment_success(self, deployment_service):
        """Test successful Cyoda environment deployment."""
        # Mock Cloud Manager response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "build_id": "build-abc123",
            "build_namespace": "client-testuser-dev",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            result = await deployment_service.deploy_cyoda_environment(
                user_id="test-user",
                conversation_id="conv-123",
                env_name="dev-environment",
                build_id="build-xyz",
            )

            # Verify result
            assert isinstance(result, DeploymentResult)
            assert result.build_id == "build-abc123"
            assert result.namespace == "client-testuser-dev"
            assert result.env_url == "https://client-testuser-dev.test.cyoda.cloud"
            assert result.keyspace == "c_test_user_dev_enviro"  # Truncated to 10 chars

            # Verify API call
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "/deploy/cyoda-env"

            payload = call_args[1]["json"]
            assert payload["user_name"] == "test-user"
            assert payload["chat_id"] == "conv-123"
            assert payload["user_defined_namespace"] == "client-test-user-dev-enviro"
            assert payload["user_defined_keyspace"] == "c_test_user_dev_enviro"
            assert payload["build_id"] == "build-xyz"

    @pytest.mark.asyncio
    async def test_deploy_cyoda_environment_without_build_id(self, deployment_service):
        """Test Cyoda environment deployment without optional build_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "build_id": "build-generated",
            "build_namespace": "client-user-prod",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            result = await deployment_service.deploy_cyoda_environment(
                user_id="user",
                conversation_id="conv-456",
                env_name="production",
            )

            # Verify build_id not in payload
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert "build_id" not in payload

            # Verify result uses generated build_id
            assert result.build_id == "build-generated"

    @pytest.mark.asyncio
    async def test_deploy_cyoda_environment_truncates_env_name(self, deployment_service):
        """Test that env_name is truncated to 10 characters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "build_id": "build-123",
            "build_namespace": "client-user-verylongen",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            result = await deployment_service.deploy_cyoda_environment(
                user_id="user",
                conversation_id="conv-789",
                env_name="very-long-environment-name",  # 28 chars
            )

            # Verify namespace contains truncated name (10 chars)
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert "very-long-" in payload["user_defined_namespace"]
            assert len("very-long-") == 10

    @pytest.mark.asyncio
    async def test_deploy_cyoda_environment_missing_build_id(self, deployment_service):
        """Test deployment fails when API response missing build_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            # Missing build_id
            "build_namespace": "client-user-dev",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            with pytest.raises(ValueError, match="missing build information"):
                await deployment_service.deploy_cyoda_environment(
                    user_id="user",
                    conversation_id="conv-123",
                    env_name="dev",
                )

    @pytest.mark.asyncio
    async def test_deploy_cyoda_environment_missing_namespace(self, deployment_service):
        """Test deployment fails when API response missing namespace."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "build_id": "build-123",
            # Missing build_namespace
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            with pytest.raises(ValueError, match="missing build information"):
                await deployment_service.deploy_cyoda_environment(
                    user_id="user",
                    conversation_id="conv-123",
                    env_name="dev",
                )

    @pytest.mark.asyncio
    async def test_deploy_cyoda_environment_http_error(self, deployment_service):
        """Test deployment handles HTTP errors from Cloud Manager."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await deployment_service.deploy_cyoda_environment(
                    user_id="user",
                    conversation_id="conv-123",
                    env_name="dev",
                )

    @pytest.mark.asyncio
    async def test_deploy_user_application_success(self, deployment_service):
        """Test successful user application deployment."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "build_id": "app-build-123",
            "build_namespace": "client-1-test-user-dev-my-app",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            result = await deployment_service.deploy_user_application(
                user_id="test-user",
                conversation_id="conv-abc",
                env_name="dev",
                app_name="my-app",
                repository_url="https://github.com/user/repo",
                branch_name="main",
                cyoda_client_id="client-123",
                cyoda_client_secret="secret-456",
                is_public=True,
                installation_id="789",
            )

            # Verify result
            assert isinstance(result, DeploymentResult)
            assert result.build_id == "app-build-123"
            assert result.namespace == "client-1-test-user-dev-my-app"

            # Verify API call
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "/deploy/user-app"

            payload = call_args[1]["json"]
            assert payload["user_name"] == "test-user"
            assert payload["chat_id"] == "conv-abc"
            assert payload["repository_url"] == "https://github.com/user/repo"
            assert payload["branch_name"] == "main"
            assert payload["cyoda_client_id"] == "client-123"
            assert payload["cyoda_client_secret"] == "secret-456"
            assert payload["is_public"] == "true"
            assert payload["app_namespace"] == "client-1-test-user-dev-my-app"
            assert payload["cyoda_namespace"] == "client-test-user-dev"
            assert payload["installation_id"] == "789"

    @pytest.mark.asyncio
    async def test_deploy_user_application_without_optional_params(self, deployment_service):
        """Test user app deployment without optional installation_id."""
        import os

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "build_id": "app-build-456",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        # Mock os.getenv to not return installation_id from environment
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "application.services.deployment.service.get_cloud_manager_service",
                return_value=mock_client,
            ):
                result = await deployment_service.deploy_user_application(
                    user_id="user",
                    conversation_id="conv-123",
                    env_name="prod",
                    app_name="app",
                    repository_url="https://github.com/user/repo",
                    branch_name="release",
                    cyoda_client_id="client-id",
                    cyoda_client_secret="client-secret",
                    is_public=True,
                    # installation_id not provided
                )

                # Verify installation_id not in payload when not provided and not in env
                call_args = mock_client.post.call_args
                payload = call_args[1]["json"]
                assert "installation_id" not in payload

                assert result.build_id == "app-build-456"

    @pytest.mark.asyncio
    async def test_deploy_user_application_truncates_names(self, deployment_service):
        """Test that env_name and app_name are truncated to 10 characters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "build_id": "build-123",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            result = await deployment_service.deploy_user_application(
                user_id="user",
                conversation_id="conv-123",
                env_name="very-long-environment-name",  # 28 chars
                app_name="extremely-long-application-name",  # 33 chars
                repository_url="https://github.com/user/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret",
            )

            # Verify truncation in namespaces
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            app_namespace = payload["app_namespace"]
            cyoda_namespace = payload["cyoda_namespace"]

            # Should contain truncated names (10 chars each)
            assert "very-long-" in app_namespace
            assert "very-long-" in cyoda_namespace
            assert "extremely-" in app_namespace

    @pytest.mark.asyncio
    async def test_deploy_user_application_missing_build_id(self, deployment_service):
        """Test user app deployment fails when API response missing build_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # Missing build_id

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "application.services.deployment.service.get_cloud_manager_service",
            return_value=mock_client,
        ):
            with pytest.raises(ValueError, match="missing build_id"):
                await deployment_service.deploy_user_application(
                    user_id="user",
                    conversation_id="conv-123",
                    env_name="dev",
                    app_name="app",
                    repository_url="https://github.com/user/repo",
                    branch_name="main",
                    cyoda_client_id="client-id",
                    cyoda_client_secret="client-secret",
                )


class TestDeploymentResult:
    """Test DeploymentResult dataclass."""

    def test_deployment_result_minimal(self):
        """Test DeploymentResult with minimal required fields."""
        result = DeploymentResult(
            build_id="build-123",
            namespace="client-user-dev",
        )

        assert result.build_id == "build-123"
        assert result.namespace == "client-user-dev"
        assert result.task_id is None
        assert result.env_url is None
        assert result.keyspace is None

    def test_deployment_result_full(self):
        """Test DeploymentResult with all fields."""
        result = DeploymentResult(
            build_id="build-456",
            namespace="client-user-prod",
            task_id="task-789",
            env_url="https://client-user-prod.cyoda.cloud",
            keyspace="c_user_prod",
        )

        assert result.build_id == "build-456"
        assert result.namespace == "client-user-prod"
        assert result.task_id == "task-789"
        assert result.env_url == "https://client-user-prod.cyoda.cloud"
        assert result.keyspace == "c_user_prod"


class TestGetDeploymentService:
    """Test get_deployment_service factory function."""

    def test_get_deployment_service(self):
        """Test that get_deployment_service returns a DeploymentService instance."""
        service = get_deployment_service()
        assert isinstance(service, DeploymentService)

    def test_get_deployment_service_creates_new_instances(self):
        """Test that get_deployment_service creates new instances (not singleton)."""
        service1 = get_deployment_service()
        service2 = get_deployment_service()

        # Should be different instances
        assert service1 is not service2
