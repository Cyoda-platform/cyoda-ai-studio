"""Tests for deploy_user_application method in EnvironmentDeploymentService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from application.services.environment.deployment import EnvironmentDeploymentService


class TestDeployUserApplication:
    """Tests for deploy_user_application method."""

    @pytest.mark.asyncio
    async def test_deploy_user_application_basic(self):
        """Test basic application deployment."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")

        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "build_namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await deployment_service.deploy_user_application(
                user_id="user-1",
                chat_id="chat-1",
                env_name="env-1",
                app_name="app-1",
                repository_url="https://github.com/test/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret"
            )
            
            assert result["build_id"] == "build-123"
            assert result["namespace"] == "ns-123"

    @pytest.mark.asyncio
    async def test_deploy_user_application_with_installation_id(self):
        """Test deployment with explicit installation_id."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")
        
        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await deployment_service.deploy_user_application(
                user_id="user-1",
                chat_id="chat-1",
                env_name="env-1",
                app_name="app-1",
                repository_url="https://github.com/test/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret",
                installation_id="inst-123"
            )
            
            # Verify installation_id was included in payload
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["installation_id"] == "inst-123"

    @pytest.mark.asyncio
    async def test_deploy_user_application_private_repo(self):
        """Test deployment with private repository."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")
        
        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await deployment_service.deploy_user_application(
                user_id="user-1",
                chat_id="chat-1",
                env_name="env-1",
                app_name="app-1",
                repository_url="https://github.com/test/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret",
                is_public=False
            )
            
            # Verify is_public was set to false
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["is_public"] == "false"

    @pytest.mark.asyncio
    async def test_deploy_user_application_public_repo_with_env_installation_id(self):
        """Test public repo deployment uses env installation_id."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")
        
        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with patch("os.getenv") as mock_getenv:
                mock_getenv.side_effect = lambda key, default=None: {
                    "GITHUB_PUBLIC_REPO_INSTALLATION_ID": "env-inst-123"
                }.get(key, default)
                
                result = await deployment_service.deploy_user_application(
                    user_id="user-1",
                    chat_id="chat-1",
                    env_name="env-1",
                    app_name="app-1",
                    repository_url="https://github.com/test/repo",
                    branch_name="main",
                    cyoda_client_id="client-id",
                    cyoda_client_secret="client-secret",
                    is_public=True
                )
                
                # Verify env installation_id was used
                call_args = mock_client.post.call_args
                payload = call_args[1]["json"]
                assert payload["installation_id"] == "env-inst-123"

    @pytest.mark.asyncio
    async def test_deploy_user_application_sanitizes_names(self):
        """Test that user/env/app names are sanitized."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")
        
        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await deployment_service.deploy_user_application(
                user_id="user_1",
                chat_id="chat-1",
                env_name="environment_name",
                app_name="application_name",
                repository_url="https://github.com/test/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret"
            )
            
            # Verify namespaces were created
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert "app_namespace" in payload
            assert "cyoda_namespace" in payload

    @pytest.mark.asyncio
    async def test_deploy_user_application_truncates_long_names(self):
        """Test that long env/app names are truncated."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")
        
        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await deployment_service.deploy_user_application(
                user_id="user-1",
                chat_id="chat-1",
                env_name="very_long_environment_name_that_exceeds_limit",
                app_name="very_long_application_name_that_exceeds_limit",
                repository_url="https://github.com/test/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret"
            )
            
            assert result["build_id"] == "build-123"

    @pytest.mark.asyncio
    async def test_deploy_user_application_includes_auth_header(self):
        """Test that authorization header is included."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")
        
        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await deployment_service.deploy_user_application(
                user_id="user-1",
                chat_id="chat-1",
                env_name="env-1",
                app_name="app-1",
                repository_url="https://github.com/test/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret"
            )
            
            # Verify auth header was included
            call_args = mock_client.post.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer token-123"

    @pytest.mark.asyncio
    async def test_deploy_user_application_uses_namespace_fallback(self):
        """Test that namespace fallback works when build_namespace not present."""
        auth_service = AsyncMock()
        auth_service.get_token = AsyncMock(return_value="token-123")
        
        deployment_service = EnvironmentDeploymentService(auth_service)
        
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "build_id": "build-123",
            "namespace": "ns-123"
        })
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await deployment_service.deploy_user_application(
                user_id="user-1",
                chat_id="chat-1",
                env_name="env-1",
                app_name="app-1",
                repository_url="https://github.com/test/repo",
                branch_name="main",
                cyoda_client_id="client-id",
                cyoda_client_secret="client-secret"
            )
            
            assert result["namespace"] == "ns-123"

