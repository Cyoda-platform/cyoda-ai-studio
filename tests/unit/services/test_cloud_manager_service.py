"""Unit tests for CloudManagerService."""

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from application.services.cloud_manager_service import (
    CloudManagerService,
    get_cloud_manager_service,
    reset_cloud_manager_service,
)


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for cloud manager."""
    with patch.dict(
        os.environ,
        {
            "CLOUD_MANAGER_HOST": "cloud.example.com",
            "CLOUD_MANAGER_API_KEY": "dGVzdC1rZXk=",  # base64: test-key
            "CLOUD_MANAGER_API_SECRET": "dGVzdC1zZWNyZXQ=",  # base64: test-secret
        },
    ):
        yield


@pytest.fixture
def client():
    """Create a fresh CloudManagerService for testing."""
    return CloudManagerService()


class TestCloudManagerService:
    """Test CloudManagerService class."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_env_vars, client):
        """Test client initializes correctly."""
        assert client._client is None
        assert client._token is None
        assert client._token_expiry == 0

    @pytest.mark.asyncio
    async def test_ensure_client_initialized(self, mock_env_vars, client):
        """Test HTTP client initialization."""
        http_client = await client._ensure_client_initialized()

        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)
        assert client._client is http_client
        assert "cloud.example.com" in str(http_client.base_url)
        assert "https://" in str(http_client.base_url)

    @pytest.mark.asyncio
    async def test_ensure_client_initialized_localhost(self, client):
        """Test HTTP client uses http for localhost."""
        with patch.dict(os.environ, {"CLOUD_MANAGER_HOST": "localhost:8080"}):
            http_client = await client._ensure_client_initialized()

            assert "localhost:8080" in str(http_client.base_url)
            assert "http://" in str(http_client.base_url)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, mock_env_vars, client):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-access-token-123"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            token = await client._authenticate()

            assert token == "test-access-token-123"

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self, client):
        """Test authentication fails with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception, match="Cloud manager credentials not configured"):
                await client._authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_no_token_in_response(self, mock_env_vars, client):
        """Test authentication fails when no token in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No token field
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(Exception, match="Failed to authenticate.*no token"):
                await client._authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_http_error(self, mock_env_vars, client):
        """Test authentication handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response),
        ):
            with pytest.raises(Exception, match="authentication failed.*401"):
                await client._authenticate()

    @pytest.mark.asyncio
    async def test_is_token_valid(self, client):
        """Test token validity checking."""
        # No token
        assert not client._is_token_valid()

        # Token expired
        client._token = "expired-token"
        client._token_expiry = time.time() - 100
        assert not client._is_token_valid()

        # Token within buffer zone (5 minutes before expiry)
        client._token = "soon-expired-token"
        client._token_expiry = time.time() + 200  # Less than 5 min buffer
        assert not client._is_token_valid()

        # Valid token
        client._token = "valid-token"
        client._token_expiry = time.time() + 3600  # 1 hour from now
        assert client._is_token_valid()

    @pytest.mark.asyncio
    async def test_get_token_caches_token(self, mock_env_vars, client):
        """Test that get_token caches and reuses tokens."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "cached-token-123"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            # First call: should authenticate
            token1 = await client.get_token()
            assert token1 == "cached-token-123"
            assert mock_post.call_count == 1

            # Second call: should reuse cached token
            token2 = await client.get_token()
            assert token2 == "cached-token-123"
            assert mock_post.call_count == 1  # No additional auth call

            # Verify token is cached
            assert client._token == "cached-token-123"
            assert client._is_token_valid()

    @pytest.mark.asyncio
    async def test_get_token_refreshes_expired_token(self, mock_env_vars, client):
        """Test that get_token refreshes expired tokens."""
        mock_response1 = MagicMock()
        mock_response1.json.return_value = {"token": "first-token"}
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.json.return_value = {"token": "refreshed-token"}
        mock_response2.raise_for_status = MagicMock()

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=[mock_response1, mock_response2]
        ) as mock_post:
            # First call
            token1 = await client.get_token()
            assert token1 == "first-token"
            assert mock_post.call_count == 1

            # Expire the token manually
            client._token_expiry = time.time() - 100

            # Second call: should refresh
            token2 = await client.get_token()
            assert token2 == "refreshed-token"
            assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_request_adds_auth_header(self, mock_env_vars, client):
        """Test that request() adds authorization header."""
        # Mock authentication
        client._token = "test-token"
        client._token_expiry = time.time() + 3600

        mock_response = AsyncMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            await client.request("GET", "/api/test")

            # Verify authorization header was added
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_request_retries_on_401(self, mock_env_vars, client):
        """Test that request() retries on 401 Unauthorized."""
        # Mock initial auth
        mock_auth_response = MagicMock()
        mock_auth_response.json.return_value = {"token": "initial-token"}
        mock_auth_response.raise_for_status = MagicMock()

        # Mock 401 response
        mock_401_response = MagicMock()
        mock_401_response.status_code = 401

        # Mock successful retry response
        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {"data": "success"}
        mock_success_response.raise_for_status = MagicMock()

        # Mock token refresh
        mock_refresh_response = MagicMock()
        mock_refresh_response.json.return_value = {"token": "refreshed-token"}
        mock_refresh_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=[mock_auth_response, mock_refresh_response]):
            with patch(
                "httpx.AsyncClient.request",
                new_callable=AsyncMock,
                side_effect=[
                    httpx.HTTPStatusError("401", request=MagicMock(), response=mock_401_response),
                    mock_success_response,
                ],
            ) as mock_request:
                response = await client.request("GET", "/api/test")

                # Should have retried (2 calls to request)
                assert mock_request.call_count == 2
                assert response == mock_success_response

    @pytest.mark.asyncio
    async def test_get_post_put_delete_methods(self, mock_env_vars, client):
        """Test convenience methods (get, post, put, delete)."""
        client._token = "test-token"
        client._token_expiry = time.time() + 3600

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            await client.get("/api/test")
            mock_request.assert_called_with("GET", "/api/test", headers={"Authorization": "Bearer test-token"})

            await client.post("/api/test", json={"key": "value"})
            assert mock_request.call_args[0][0] == "POST"

            await client.put("/api/test")
            assert mock_request.call_args[0][0] == "PUT"

            await client.delete("/api/test")
            assert mock_request.call_args[0][0] == "DELETE"

    @pytest.mark.asyncio
    async def test_close(self, mock_env_vars, client):
        """Test client cleanup."""
        # Initialize client
        await client._ensure_client_initialized()
        client._token = "test-token"
        client._token_expiry = time.time() + 3600

        assert client._client is not None
        assert client._token is not None

        # Close client
        await client.close()

        assert client._client is None
        assert client._token is None
        assert client._token_expiry == 0

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_env_vars):
        """Test async context manager support."""
        async with CloudManagerService() as client:
            assert client._client is not None

        # Client should be closed after context exit
        assert client._client is None


class TestGlobalClient:
    """Test global client singleton."""

    pass


class TestThreadSafety:
    """Test thread safety of token refresh."""

    @pytest.mark.asyncio
    async def test_concurrent_token_refresh(self, mock_env_vars, client):
        """Test that concurrent token requests don't cause multiple auth calls."""
        call_count = 0

        async def mock_authenticate():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow auth
            return f"token-{call_count}"

        with patch.object(client, "_authenticate", side_effect=mock_authenticate):
            # Simulate 5 concurrent requests for token
            tokens = await asyncio.gather(
                client.get_token(),
                client.get_token(),
                client.get_token(),
                client.get_token(),
                client.get_token(),
            )

            # Should only authenticate once due to locking
            assert call_count == 1
            # All tokens should be the same
            assert all(t == tokens[0] for t in tokens)
