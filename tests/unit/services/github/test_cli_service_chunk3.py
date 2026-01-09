"""Tests for cli_service.py functions (Chunk 3)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.github.cli_service import GitHubCLIService


class TestStartCodeGeneration:
    """Test start_code_generation method."""

    @pytest.fixture
    def cli_service(self):
        """Create GitHubCLIService instance."""
        git_service = MagicMock()
        return GitHubCLIService(git_service)

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_repository_path(self, cli_service):
        """Test code generation fails without repository_path."""
        with pytest.raises(ValueError, match="repository_path is required"):
            await cli_service.start_code_generation(
                repository_path="",
                branch_name="main",
                user_request="Add feature",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_branch_name(self, cli_service):
        """Test code generation fails without branch_name."""
        with pytest.raises(ValueError, match="branch_name is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="",
                user_request="Add feature",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_user_request(self, cli_service):
        """Test code generation fails without user_request."""
        with pytest.raises(ValueError, match="user_request is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="main",
                user_request="",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_language(self, cli_service):
        """Test code generation fails without language."""
        with pytest.raises(ValueError, match="language is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="main",
                user_request="Add feature",
                language="",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_script_not_found(self, cli_service):
        """Test code generation fails when script not found."""
        with patch.object(cli_service, "_get_cli_config") as mock_config:
            with patch("pathlib.Path.exists", return_value=False):
                mock_config.return_value = (Path("/nonexistent/script.sh"), "haiku4.5")

                with pytest.raises(FileNotFoundError):
                    await cli_service.start_code_generation(
                        repository_path="/tmp/repo",
                        branch_name="main",
                        user_request="Add feature",
                        language="python",
                        user_id="user123",
                        conversation_id="conv123",
                        repo_auth_config={},
                    )

    @pytest.mark.asyncio
    async def test_start_code_generation_returns_dict(self, cli_service):
        """Test start_code_generation returns dict with task_id and pid."""
        with patch.object(cli_service, "_get_cli_config") as mock_config:
            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(
                    cli_service, "_load_informational_prompt_template"
                ) as mock_template:
                    with patch("asyncio.create_subprocess_exec") as mock_exec:
                        with patch(
                            "application.agents.shared.process_manager.get_process_manager"
                        ) as mock_pm:
                            with patch(
                                "application.services.github.cli_service.get_task_service"
                            ) as mock_task_service_cli:
                                with patch(
                                    "application.services.github.cli.utils.get_task_service"
                                ) as mock_task_service_utils:
                                    mock_config.return_value = (
                                        Path("/tmp/script.sh"),
                                        "haiku4.5",
                                    )
                                    mock_template.return_value = "Template"
                                    mock_process = AsyncMock()
                                    mock_process.pid = 12345
                                    mock_exec.return_value = mock_process

                                    mock_pm_instance = AsyncMock()
                                    mock_pm_instance.can_start_process.return_value = (
                                        True
                                    )
                                    mock_pm_instance.register_process.return_value = (
                                        True
                                    )
                                    mock_pm.return_value = mock_pm_instance

                                    mock_task_service_instance = AsyncMock()
                                    mock_task_service_instance.create_task.return_value = MagicMock(
                                        technical_id="task-123"
                                    )
                                    mock_task_service_instance.update_task_status = (
                                        AsyncMock()
                                    )
                                    mock_task_service_cli.return_value = (
                                        mock_task_service_instance
                                    )
                                    mock_task_service_utils.return_value = (
                                        mock_task_service_instance
                                    )

                                    result = await cli_service.start_code_generation(
                                        repository_path="/tmp/repo",
                                        branch_name="main",
                                        user_request="Add feature",
                                        language="python",
                                        user_id="user123",
                                        conversation_id="conv123",
                                        repo_auth_config={},
                                    )

                                    assert isinstance(result, dict)
                                    assert "task_id" in result
                                    assert "pid" in result


class TestStartApplicationBuild:
    """Test start_application_build method."""

    @pytest.fixture
    def cli_service(self):
        """Create GitHubCLIService instance."""
        git_service = MagicMock()
        return GitHubCLIService(git_service)

    @pytest.mark.asyncio
    async def test_start_build_missing_repository_path(self, cli_service):
        """Test build fails without repository_path."""
        with pytest.raises(ValueError, match="repository_path is required"):
            await cli_service.start_application_build(
                repository_path="",
                branch_name="main",
                requirements="Build app",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_start_build_missing_branch_name(self, cli_service):
        """Test build fails without branch_name."""
        with pytest.raises(ValueError, match="branch_name is required"):
            await cli_service.start_application_build(
                repository_path="/tmp/repo",
                branch_name="",
                requirements="Build app",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_start_build_missing_requirements(self, cli_service):
        """Test build fails without requirements."""
        with pytest.raises(ValueError, match="requirements are required"):
            await cli_service.start_application_build(
                repository_path="/tmp/repo",
                branch_name="main",
                requirements="",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_start_build_missing_language(self, cli_service):
        """Test build fails without language."""
        with pytest.raises(ValueError, match="language is required"):
            await cli_service.start_application_build(
                repository_path="/tmp/repo",
                branch_name="main",
                requirements="Build app",
                language="",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={},
            )
