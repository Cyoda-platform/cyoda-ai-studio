"""Test for the send_request function 401 status code fix."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from common.exception.exceptions import InvalidTokenException
from common.utils.utils import send_request


@pytest.mark.asyncio
async def test_send_request_raises_invalid_token_exception_on_401_get():
    """Test that send_request raises InvalidTokenException when HTTP status is 401 for GET."""

    # Mock httpx.AsyncClient and response
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.headers.get.return_value = "application/json"
    mock_response.json.return_value = {"error": "Unauthorized"}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(InvalidTokenException) as exc_info:
            await send_request(
                headers={"Authorization": "Bearer test_token"},
                url="https://test.example.com/api/v1",
                method="GET",
            )

        # Verify the exception message contains the URL
        assert "https://test.example.com/api/v1" in str(exc_info.value)
        assert "Unauthorized access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_request_raises_invalid_token_exception_on_401_post():
    """Test that send_request raises InvalidTokenException for POST requests with 401."""

    # Mock httpx.AsyncClient and response
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json = AsyncMock(return_value={"error": "Unauthorized"})
    mock_response.text = "text response"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(InvalidTokenException) as exc_info:
            await send_request(
                headers={"Authorization": "Bearer test_token"},
                url="https://test.example.com/api/v1",
                method="POST",
                json={"test": "data"},
            )

        # Verify the exception message contains the URL
        assert "https://test.example.com/api/v1" in str(exc_info.value)
        assert "Unauthorized access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_request_raises_invalid_token_exception_on_401_put():
    """Test that send_request raises InvalidTokenException for PUT requests with 401."""

    # Mock httpx.AsyncClient and response
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.headers = {"Content-Type": "application/json"}

    mock_client = AsyncMock()
    mock_client.put.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(InvalidTokenException) as exc_info:
            await send_request(
                headers={"Authorization": "Bearer test_token"},
                url="https://test.example.com/api/v1",
                method="PUT",
                json={"test": "data"},
            )

        # Verify the exception message contains the URL
        assert "https://test.example.com/api/v1" in str(exc_info.value)
        assert "Unauthorized access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_request_raises_invalid_token_exception_on_401_delete():
    """Test that send_request raises InvalidTokenException for DELETE requests with 401."""

    # Mock httpx.AsyncClient and response
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.headers = {"Content-Type": "application/json"}

    mock_client = AsyncMock()
    mock_client.delete.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(InvalidTokenException) as exc_info:
            await send_request(
                headers={"Authorization": "Bearer test_token"},
                url="https://test.example.com/api/v1",
                method="DELETE",
            )

        # Verify the exception message contains the URL
        assert "https://test.example.com/api/v1" in str(exc_info.value)
        assert "Unauthorized access" in str(exc_info.value)
