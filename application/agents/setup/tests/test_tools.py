"""Tests for Setup agent tools."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from application.agents.setup.tools import (
    check_project_structure,
    get_env_deploy_status,
    validate_environment,
    validate_workflow_file,
)


@pytest.mark.asyncio
async def test_validate_environment_all_present(monkeypatch):
    """Test validation when all vars are present."""
    monkeypatch.setenv("CYODA_HOST", "localhost")
    monkeypatch.setenv("CYODA_PORT", "8080")
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-2.0-flash-exp")

    result = await validate_environment(["CYODA_HOST", "CYODA_PORT", "GOOGLE_MODEL"])

    assert result["CYODA_HOST"] is True
    assert result["CYODA_PORT"] is True
    assert result["GOOGLE_MODEL"] is True


@pytest.mark.asyncio
async def test_validate_environment_some_missing(monkeypatch):
    """Test validation when some vars are missing."""
    monkeypatch.setenv("CYODA_HOST", "localhost")
    monkeypatch.delenv("CYODA_PORT", raising=False)

    result = await validate_environment(["CYODA_HOST", "CYODA_PORT"])

    assert result["CYODA_HOST"] is True
    assert result["CYODA_PORT"] is False


@pytest.mark.asyncio
async def test_validate_environment_default_vars(monkeypatch):
    """Test validation with default variable list."""
    monkeypatch.setenv("CYODA_HOST", "localhost")
    monkeypatch.setenv("CYODA_PORT", "8080")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = await validate_environment()

    assert "CYODA_HOST" in result
    assert "CYODA_PORT" in result
    assert "GOOGLE_MODEL" in result
    assert "GOOGLE_API_KEY" in result


@pytest.mark.asyncio
async def test_check_project_structure_valid(tmp_path, monkeypatch):
    """Test project structure check with valid structure."""
    # Create required items
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "application").mkdir()
    (tmp_path / "common").mkdir()
    (tmp_path / ".env").touch()
    (tmp_path / ".venv").mkdir()

    monkeypatch.chdir(tmp_path)

    result = await check_project_structure()

    assert result["is_valid"] is True
    assert len(result["missing_items"]) == 0
    assert "pyproject.toml" in result["present_items"]
    assert "application" in result["present_items"]


@pytest.mark.asyncio
async def test_check_project_structure_missing_items(tmp_path, monkeypatch):
    """Test project structure check with missing items."""
    # Create only some items
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "application").mkdir()

    monkeypatch.chdir(tmp_path)

    result = await check_project_structure()

    assert result["is_valid"] is False
    assert "common" in result["missing_items"]
    assert ".env" in result["missing_items"]
    assert ".venv" in result["missing_items"]
    assert len(result["recommendations"]) > 0


@pytest.mark.asyncio
async def test_validate_workflow_file_valid():
    """Test workflow file validation with valid file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        workflow_data = {
            "name": "test_workflow",
            "states": ["DRAFT", "VALIDATED"],
            "transitions": [{"from": "DRAFT", "to": "VALIDATED"}],
        }
        json.dump(workflow_data, f)
        temp_path = f.name

    try:
        result = await validate_workflow_file(temp_path)

        assert result["is_valid"] is True
        assert result["exists"] is True
        assert result["error"] is None
        assert result["workflow_name"] == "test_workflow"
        assert result["num_states"] == 2
        assert result["num_transitions"] == 1
    finally:
        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_validate_workflow_file_missing():
    """Test workflow file validation with missing file."""
    result = await validate_workflow_file("/nonexistent/workflow.json")

    assert result["is_valid"] is False
    assert result["exists"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_validate_workflow_file_invalid_json():
    """Test workflow file validation with invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json }")
        temp_path = f.name

    try:
        result = await validate_workflow_file(temp_path)

        assert result["is_valid"] is False
        assert result["exists"] is True
        assert "Invalid JSON" in result["error"]
    finally:
        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_validate_workflow_file_missing_fields():
    """Test workflow file validation with missing required fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        workflow_data = {"name": "test_workflow"}  # Missing states and transitions
        json.dump(workflow_data, f)
        temp_path = f.name

    try:
        result = await validate_workflow_file(temp_path)

        assert result["is_valid"] is False
        assert result["exists"] is True
        assert "Missing required fields" in result["error"]
    finally:
        Path(temp_path).unlink()


# Tests for get_env_deploy_status


@pytest.mark.asyncio
async def test_get_env_deploy_status_success(monkeypatch):
    """Test successful deployment status check with authentication."""
    # Set up environment variables
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.setenv("CLIENT_HOST", "cyoda.cloud")
    monkeypatch.setenv("CYODA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CYODA_CLIENT_SECRET", "test-client-secret")

    # Mock HTTP client
    mock_client = AsyncMock()
    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {"token": "test-jwt-token"}
    mock_auth_response.raise_for_status = MagicMock()

    mock_status_response = MagicMock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {
        "state": "COMPLETED",
        "status": "SUCCESS"
    }
    mock_status_response.raise_for_status = MagicMock()

    # Set up mock to return different responses for auth and status calls
    mock_client.post.return_value = mock_auth_response
    mock_client.get.return_value = mock_status_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await get_env_deploy_status("build-123")

        # Verify authentication was called
        mock_client.post.assert_called_once()
        auth_call_args = mock_client.post.call_args
        assert "cloud-manager-cyoda.cyoda.cloud/api/auth/login" in auth_call_args[0][0]
        assert auth_call_args[1]["json"]["username"] == "test-client-id"
        assert auth_call_args[1]["json"]["password"] == "test-client-secret"

        # Verify status check was called with token
        mock_client.get.assert_called_once()
        status_call_args = mock_client.get.call_args
        assert "build_id=build-123" in status_call_args[0][0]
        assert status_call_args[1]["headers"]["Authorization"] == "Bearer test-jwt-token"

        # Verify result
        assert "COMPLETED" in result
        assert "SUCCESS" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_auth_failure_401(monkeypatch):
    """Test deployment status check when authentication fails with 401."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.setenv("CLIENT_HOST", "cyoda.cloud")
    monkeypatch.setenv("CYODA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CYODA_CLIENT_SECRET", "wrong-secret")

    # Mock HTTP client
    mock_client = AsyncMock()
    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 401
    mock_auth_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=mock_auth_response
    )

    mock_client.post.return_value = mock_auth_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await get_env_deploy_status("build-123")

        # Verify error message
        assert "HTTP error" in result
        assert "401 Unauthorized" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_missing_token_in_response(monkeypatch):
    """Test when authentication succeeds but no token is returned."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.setenv("CLIENT_HOST", "cyoda.cloud")
    monkeypatch.setenv("CYODA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CYODA_CLIENT_SECRET", "test-client-secret")

    # Mock HTTP client
    mock_client = AsyncMock()
    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {"message": "Logged in"}  # No token field
    mock_auth_response.raise_for_status = MagicMock()

    mock_client.post.return_value = mock_auth_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await get_env_deploy_status("build-123")

        # Verify error message
        assert "Error: No token returned from authentication endpoint" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_status_check_401(monkeypatch):
    """Test when status check fails with 401 (expired/invalid token)."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.setenv("CLIENT_HOST", "cyoda.cloud")
    monkeypatch.setenv("CYODA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CYODA_CLIENT_SECRET", "test-client-secret")

    # Mock HTTP client
    mock_client = AsyncMock()
    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {"token": "expired-token"}
    mock_auth_response.raise_for_status = MagicMock()

    mock_status_response = MagicMock()
    mock_status_response.status_code = 401
    mock_status_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=mock_status_response
    )

    mock_client.post.return_value = mock_auth_response
    mock_client.get.return_value = mock_status_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await get_env_deploy_status("build-123")

        # Verify error message
        assert "HTTP error" in result
        assert "401 Unauthorized" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_missing_cloud_manager_host(monkeypatch):
    """Test when CLOUD_MANAGER_HOST is not configured."""
    monkeypatch.delenv("CLOUD_MANAGER_HOST", raising=False)

    result = await get_env_deploy_status("build-123")

    assert "Error: CLOUD_MANAGER_HOST environment variable not configured" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_missing_client_host(monkeypatch):
    """Test when CLIENT_HOST is not configured."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.delenv("CLIENT_HOST", raising=False)

    result = await get_env_deploy_status("build-123")

    assert "Error: CLIENT_HOST environment variable not configured" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_missing_credentials(monkeypatch):
    """Test when CYODA_CLIENT_ID or CYODA_CLIENT_SECRET is not configured."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.setenv("CLIENT_HOST", "cyoda.cloud")
    monkeypatch.delenv("CYODA_CLIENT_ID", raising=False)
    monkeypatch.delenv("CYODA_CLIENT_SECRET", raising=False)

    result = await get_env_deploy_status("build-123")

    assert "Error: CYODA_CLIENT_ID and CYODA_CLIENT_SECRET environment variables must be configured" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_localhost_uses_http(monkeypatch):
    """Test that localhost uses HTTP protocol instead of HTTPS."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "localhost:8080")
    monkeypatch.setenv("CLIENT_HOST", "localhost")
    monkeypatch.setenv("CYODA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CYODA_CLIENT_SECRET", "test-client-secret")

    # Mock HTTP client
    mock_client = AsyncMock()
    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {"token": "test-jwt-token"}
    mock_auth_response.raise_for_status = MagicMock()

    mock_status_response = MagicMock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {
        "state": "IN_PROGRESS",
        "status": "DEPLOYING"
    }
    mock_status_response.raise_for_status = MagicMock()

    mock_client.post.return_value = mock_auth_response
    mock_client.get.return_value = mock_status_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await get_env_deploy_status("build-123")

        # Verify HTTP protocol was used
        auth_call_args = mock_client.post.call_args
        assert auth_call_args[0][0].startswith("http://")
        assert "IN_PROGRESS" in result
        assert "DEPLOYING" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_with_access_token_field(monkeypatch):
    """Test when auth response returns 'access_token' instead of 'token'."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.setenv("CLIENT_HOST", "cyoda.cloud")
    monkeypatch.setenv("CYODA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CYODA_CLIENT_SECRET", "test-client-secret")

    # Mock HTTP client
    mock_client = AsyncMock()
    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {"access_token": "test-jwt-token"}  # Different field name
    mock_auth_response.raise_for_status = MagicMock()

    mock_status_response = MagicMock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {
        "state": "COMPLETED",
        "status": "SUCCESS"
    }
    mock_status_response.raise_for_status = MagicMock()

    mock_client.post.return_value = mock_auth_response
    mock_client.get.return_value = mock_status_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await get_env_deploy_status("build-123")

        # Verify it works with access_token field
        assert "COMPLETED" in result
        assert "SUCCESS" in result


@pytest.mark.asyncio
async def test_get_env_deploy_status_network_error(monkeypatch):
    """Test when network error occurs during authentication."""
    monkeypatch.setenv("CLOUD_MANAGER_HOST", "cloud-manager.example.com")
    monkeypatch.setenv("CLIENT_HOST", "cyoda.cloud")
    monkeypatch.setenv("CYODA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CYODA_CLIENT_SECRET", "test-client-secret")

    # Mock HTTP client to raise network error
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await get_env_deploy_status("build-123")

        # Verify error handling
        assert "HTTP error" in result or "Error" in result
