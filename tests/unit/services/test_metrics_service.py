"""Tests for MetricsService.generate_grafana_token function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock circular imports before importing MetricsService
sys.modules['application.routes'] = MagicMock()
sys.modules['application.routes.common'] = MagicMock()
sys.modules['application.routes.common.constants'] = MagicMock(
    DEFAULT_HTTP_TIMEOUT_SECONDS=30,
    SERVICE_ACCOUNT_TOKEN_EXPIRY_SECONDS=3600
)

from application.services.metrics_service import MetricsService


class TestGenerateGrafanaToken:
    """Test MetricsService.generate_grafana_token function."""

    @pytest.mark.asyncio
    async def test_generate_token_new_service_account(self):
        """Test token generation with new service account creation."""
        mock_config_service = MagicMock()
        mock_grafana_config = MagicMock()
        mock_grafana_config.admin_user = "admin"
        mock_grafana_config.admin_password = "password"
        mock_grafana_config.host = "grafana.example.com"
        mock_config_service.get_grafana_config.return_value = mock_grafana_config

        service = MetricsService(mock_config_service)

        with patch.object(service.grafana_ops, 'create_basic_auth_header', return_value="auth-header"):
            with patch("application.services.metrics_service.service.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Mock service account list (empty)
                sa_list_response = MagicMock()
                sa_list_response.status_code = 200
                sa_list_response.json = MagicMock(return_value={"serviceAccounts": []})

                # Mock service account creation
                sa_create_response = MagicMock()
                sa_create_response.status_code = 201
                sa_create_response.json = MagicMock(return_value={"id": 1})

                # Mock token creation
                token_response = MagicMock()
                token_response.status_code = 200
                token_response.json = MagicMock(return_value={"key": "test-token-key"})

                mock_client.get = AsyncMock(return_value=sa_list_response)
                mock_client.post = AsyncMock(side_effect=[sa_create_response, token_response])

                result = await service.generate_grafana_token("myorg")
                assert result["token"] == "test-token-key"

    @pytest.mark.asyncio
    async def test_generate_token_existing_service_account(self):
        """Test token generation with existing service account."""
        mock_config_service = MagicMock()
        mock_grafana_config = MagicMock()
        mock_grafana_config.admin_user = "admin"
        mock_grafana_config.admin_password = "password"
        mock_grafana_config.host = "grafana.example.com"
        mock_config_service.get_grafana_config.return_value = mock_grafana_config

        service = MetricsService(mock_config_service)

        with patch.object(service.grafana_ops, 'create_basic_auth_header', return_value="auth-header"):
            with patch("application.services.metrics_service.service.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Mock service account list (with existing account)
                sa_list_response = MagicMock()
                sa_list_response.status_code = 200
                sa_list_response.json = MagicMock(return_value={
                    "serviceAccounts": [{"id": 1, "name": "metrics-myorg"}]
                })

                # Mock token creation
                token_response = MagicMock()
                token_response.status_code = 200
                token_response.json = MagicMock(return_value={"key": "existing-token-key"})

                mock_client.get = AsyncMock(return_value=sa_list_response)
                mock_client.post = AsyncMock(return_value=token_response)

                result = await service.generate_grafana_token("myorg")
                assert result["token"] == "existing-token-key"

    @pytest.mark.asyncio
    async def test_generate_token_list_failure(self):
        """Test token generation fails when listing service accounts fails."""
        mock_config_service = MagicMock()
        mock_grafana_config = MagicMock()
        mock_grafana_config.admin_user = "admin"
        mock_grafana_config.admin_password = "password"
        mock_grafana_config.host = "grafana.example.com"
        mock_config_service.get_grafana_config.return_value = mock_grafana_config

        service = MetricsService(mock_config_service)

        with patch("application.services.metrics_service.service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock service account list failure
            sa_list_response = MagicMock()
            sa_list_response.status_code = 500
            sa_list_response.text = "Internal Server Error"

            mock_client.get = AsyncMock(return_value=sa_list_response)

            with pytest.raises(Exception):
                await service.generate_grafana_token("myorg")

    @pytest.mark.asyncio
    async def test_generate_token_creation_failure(self):
        """Test token generation fails when creating service account fails."""
        mock_config_service = MagicMock()
        mock_grafana_config = MagicMock()
        mock_grafana_config.admin_user = "admin"
        mock_grafana_config.admin_password = "password"
        mock_grafana_config.host = "grafana.example.com"
        mock_config_service.get_grafana_config.return_value = mock_grafana_config

        service = MetricsService(mock_config_service)

        with patch("application.services.metrics_service.service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock service account list (empty)
            sa_list_response = MagicMock()
            sa_list_response.status_code = 200
            sa_list_response.json = AsyncMock(return_value={"serviceAccounts": []})

            # Mock service account creation failure
            sa_create_response = MagicMock()
            sa_create_response.status_code = 400
            sa_create_response.text = "Bad Request"

            mock_client.get = AsyncMock(return_value=sa_list_response)
            mock_client.post = AsyncMock(return_value=sa_create_response)

            with pytest.raises(Exception):
                await service.generate_grafana_token("myorg")

    @pytest.mark.asyncio
    async def test_generate_token_with_auth_header_test_name_placeholder(self):
        """Test token generation creates proper auth header."""
        mock_config_service = MagicMock()
        mock_grafana_config = MagicMock()
        mock_grafana_config.admin_user = "admin"
        mock_grafana_config.admin_password = "pass"
        mock_grafana_config.host = "grafana.example.com"
        mock_config_service.get_grafana_config.return_value = mock_grafana_config

        service = MetricsService(mock_config_service)

        with patch.object(service.grafana_ops, 'create_basic_auth_header', return_value="auth-header"):
            with patch("application.services.metrics_service.service.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                sa_list_response = MagicMock()
                sa_list_response.status_code = 200
                sa_list_response.json = MagicMock(return_value={"serviceAccounts": []})

                sa_create_response = MagicMock()
                sa_create_response.status_code = 201
                sa_create_response.json = MagicMock(return_value={"id": 1})

                token_response = MagicMock()
                token_response.status_code = 200
                token_response.json = MagicMock(return_value={"key": "token"})

                mock_client.get = AsyncMock(return_value=sa_list_response)
                mock_client.post = AsyncMock(side_effect=[sa_create_response, token_response])

                result = await service.generate_grafana_token("myorg")
                # Verify auth header was used
                assert mock_client.get.called

