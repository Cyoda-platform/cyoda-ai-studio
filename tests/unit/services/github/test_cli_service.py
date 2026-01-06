"""Unit tests for GitHubCLIService."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.github.cli_service import GitHubCLIService
from application.services.github.operations_service import GitHubOperationsService


@pytest.fixture
def mock_git_service():
    """Create a mock GitHubOperationsService."""
    return AsyncMock(spec=GitHubOperationsService)


@pytest.fixture
def cli_service(mock_git_service):
    """Create a GitHubCLIService instance for testing."""
    return GitHubCLIService(git_service=mock_git_service)


class TestGitHubCLIServiceInit:
    """Test GitHubCLIService initialization."""

    def test_initialization(self, mock_git_service):
        """Test service initializes with git service."""
        service = GitHubCLIService(git_service=mock_git_service)
        assert service.git_service is mock_git_service
        assert isinstance(service._background_tasks, set)
        assert len(service._background_tasks) == 0

    def test_initialization_with_real_git_service(self):
        """Test service initializes with real GitHubOperationsService."""
        git_service = GitHubOperationsService()
        service = GitHubCLIService(git_service=git_service)
        assert service.git_service is git_service


class TestGetCliConfig:
    """Test _get_cli_config method."""

    def test_get_cli_config_augment_provider(self, cli_service):
        """Test getting CLI config for augment provider."""
        script_path, model = cli_service._get_cli_config("augment")
        assert model == "haiku4.5"
        assert script_path.exists() or "augment_build" in script_path.name

    def test_get_cli_config_claude_provider(self, cli_service):
        """Test getting CLI config for claude provider."""
        script_path, model = cli_service._get_cli_config("claude")
        # In test mode, all scripts point to mock
        assert script_path.exists() or "build" in script_path.name

    def test_get_cli_config_gemini_provider(self, cli_service):
        """Test getting CLI config for gemini provider."""
        script_path, model = cli_service._get_cli_config("gemini")
        # Model comes from environment variable
        assert model is not None
        assert script_path.exists() or "build" in script_path.name

    def test_get_cli_config_default_provider(self, cli_service):
        """Test getting CLI config with default provider."""
        script_path, model = cli_service._get_cli_config()
        assert model == "haiku4.5"


class TestLoadInformationalPromptTemplate:
    """Test _load_informational_prompt_template method."""

    @pytest.mark.asyncio
    async def test_load_template_success(self, cli_service):
        """Test successfully loading a prompt template."""
        with patch("application.services.github.cli_service.load_template") as mock_load:
            mock_load.return_value = "Test template content"
            result = await cli_service._load_informational_prompt_template("python")
            assert result == "Test template content"
            mock_load.assert_called_once_with("github_cli_python_instructions")

    @pytest.mark.asyncio
    async def test_load_template_fallback(self, cli_service):
        """Test template loading with fallback."""
        def load_template_side_effect(name):
            if "github_cli" in name:
                raise FileNotFoundError()
            return "Fallback template"

        with patch("application.services.github.cli_service.load_template") as mock_load:
            mock_load.side_effect = load_template_side_effect
            result = await cli_service._load_informational_prompt_template("python")
            assert result == "Fallback template"
            assert mock_load.call_count == 2

    @pytest.mark.asyncio
    async def test_load_template_error(self, cli_service):
        """Test template loading error handling."""
        with patch("application.services.github.cli_service.load_template") as mock_load:
            mock_load.side_effect = Exception("Template error")
            with pytest.raises(Exception, match="Template error"):
                await cli_service._load_informational_prompt_template("python")


class TestCleanupTempFiles:
    """Test _cleanup_temp_files method."""

    def test_cleanup_logs_file_path(self, cli_service):
        """Test cleanup logs the temp file path."""
        with patch("application.services.github.cli_service.logger") as mock_logger:
            cli_service._cleanup_temp_files("/tmp/test_prompt.txt")
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "Prompt file preserved for audit" in call_args
            assert "/tmp/test_prompt.txt" in call_args

    def test_cleanup_with_none(self, cli_service):
        """Test cleanup with None does nothing."""
        with patch("application.services.github.cli_service.logger") as mock_logger:
            cli_service._cleanup_temp_files(None)
            mock_logger.info.assert_not_called()


class TestTrackBackgroundTask:
    """Test _track_background_task method."""

    @pytest.mark.asyncio
    async def test_track_background_task(self, cli_service):
        """Test tracking a background task."""
        async def dummy_task():
            await asyncio.sleep(0.01)

        task = asyncio.create_task(dummy_task())
        cli_service._track_background_task(task)

        # Verify task is tracked
        background_tasks = getattr(asyncio, '_background_tasks', set())
        assert task in background_tasks

        # Cleanup
        await task


class TestStartCodeGeneration:
    """Test start_code_generation method."""

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_repository_path(self, cli_service):
        """Test code generation fails without repository_path."""
        with pytest.raises(ValueError, match="repository_path is required"):
            await cli_service.start_code_generation(
                repository_path="",
                branch_name="main",
                user_request="Generate code",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={}
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_branch_name(self, cli_service):
        """Test code generation fails without branch_name."""
        with pytest.raises(ValueError, match="branch_name is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="",
                user_request="Generate code",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={}
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
                repo_auth_config={}
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_language(self, cli_service):
        """Test code generation fails without language."""
        with pytest.raises(ValueError, match="language is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="main",
                user_request="Generate code",
                language="",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={}
            )

class TestStartCodeGenerationValidation:
    """Test input validation for code generation."""

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_repository_path(self, cli_service):
        """Test code generation fails when repository_path is missing."""
        with pytest.raises(ValueError, match="repository_path is required"):
            await cli_service.start_code_generation(
                repository_path="",
                branch_name="main",
                user_request="Generate code",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={}
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_branch_name(self, cli_service):
        """Test code generation fails when branch_name is missing."""
        with pytest.raises(ValueError, match="branch_name is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="",
                user_request="Generate code",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={}
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_user_request(self, cli_service):
        """Test code generation fails when user_request is missing."""
        with pytest.raises(ValueError, match="user_request is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="main",
                user_request="",
                language="python",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={}
            )

    @pytest.mark.asyncio
    async def test_start_code_generation_missing_language(self, cli_service):
        """Test code generation fails when language is missing."""
        with pytest.raises(ValueError, match="language is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="main",
                user_request="Generate code",
                language="",
                user_id="user123",
                conversation_id="conv123",
                repo_auth_config={}
            )


class TestStartApplicationBuild:
    """Test start_application_build method."""

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
                repo_auth_config={}
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
                repo_auth_config={}
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
                repo_auth_config={}
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
                repo_auth_config={}
            )


class TestHandleSuccessCompletion:
    """Test _handle_success_completion method."""

    @pytest.mark.asyncio
    async def test_handle_success_completion_with_changes(self, cli_service, mock_git_service):
        """Test successful completion with file changes."""
        mock_task_service = AsyncMock()
        mock_git_service.commit_and_push.return_value = {
            "success": True,
            "changed_files": ["file1.py", "file2.py"],
            "canvas_resources": {"entities": ["Entity1"]}
        }

        await cli_service._handle_success_completion(
            task_id="task123",
            repository_path="/tmp/repo",
            branch_name="main",
            repo_auth_config={},
            task_service=mock_task_service,
            conversation_id="conv123",
            repository_name="test-repo",
            repository_owner="test-owner"
        )

        # Verify final commit was called
        mock_git_service.commit_and_push.assert_called_once()

        # Verify task status was updated
        mock_task_service.update_task_status.assert_called_once()
        call_args = mock_task_service.update_task_status.call_args
        assert call_args[1]["status"] == "completed"
        assert call_args[1]["progress"] == 100

    @pytest.mark.asyncio
    async def test_handle_success_completion_commit_timeout(self, cli_service, mock_git_service):
        """Test successful completion when final commit times out."""
        mock_task_service = AsyncMock()
        mock_git_service.commit_and_push.side_effect = asyncio.TimeoutError()

        await cli_service._handle_success_completion(
            task_id="task123",
            repository_path="/tmp/repo",
            branch_name="main",
            repo_auth_config={},
            task_service=mock_task_service,
            conversation_id="conv123",
            repository_name="test-repo",
            repository_owner="test-owner"
        )

        # Verify task was still marked as completed
        mock_task_service.update_task_status.assert_called_once()
        call_args = mock_task_service.update_task_status.call_args
        assert call_args[1]["status"] == "completed"
        assert "timed out" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_handle_success_completion_commit_error(self, cli_service, mock_git_service):
        """Test successful completion when final commit fails."""
        mock_task_service = AsyncMock()
        mock_git_service.commit_and_push.side_effect = Exception("Commit failed")

        await cli_service._handle_success_completion(
            task_id="task123",
            repository_path="/tmp/repo",
            branch_name="main",
            repo_auth_config={},
            task_service=mock_task_service,
            conversation_id="conv123",
            repository_name="test-repo",
            repository_owner="test-owner"
        )

        # Verify task was still marked as completed
        mock_task_service.update_task_status.assert_called_once()
        call_args = mock_task_service.update_task_status.call_args
        assert call_args[1]["status"] == "completed"
        assert "failed" in call_args[1]["message"]


class TestHandleFailureCompletion:
    """Test _handle_failure_completion method."""

    @pytest.mark.asyncio
    async def test_handle_failure_completion_timeout(self, cli_service):
        """Test failure completion due to timeout."""
        mock_task_service = AsyncMock()

        await cli_service._handle_failure_completion(
            task_id="task123",
            return_code=None,
            elapsed_time=3700,
            timeout_seconds=3600,
            task_service=mock_task_service
        )

        mock_task_service.update_task_status.assert_called_once()
        call_args = mock_task_service.update_task_status.call_args
        assert call_args[1]["status"] == "failed"
        assert "Timeout exceeded" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_handle_failure_completion_exit_code(self, cli_service):
        """Test failure completion with non-zero exit code."""
        mock_task_service = AsyncMock()

        await cli_service._handle_failure_completion(
            task_id="task123",
            return_code=1,
            elapsed_time=100,
            timeout_seconds=3600,
            task_service=mock_task_service
        )

        mock_task_service.update_task_status.assert_called_once()
        call_args = mock_task_service.update_task_status.call_args
        assert call_args[1]["status"] == "failed"
        assert "exit code 1" in call_args[1]["message"]


class TestMonitorCliProcess:
    """Test _monitor_cli_process method."""

    @pytest.mark.asyncio
    async def test_monitor_cli_process_initial_commit(self, cli_service, mock_git_service):
        """Test monitoring process with initial commit."""
        mock_task_service = AsyncMock()
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = 0
        mock_process.wait = AsyncMock()

        mock_git_service.commit_and_push.return_value = {
            "success": True,
            "changed_files": ["file1.py"],
            "canvas_resources": {}
        }

        with patch("application.services.github.cli_service.get_task_service") as mock_ts:
            mock_ts.return_value = mock_task_service
            with patch("application.agents.shared.process_manager.get_process_manager") as mock_pm:
                mock_pm.return_value = AsyncMock()
                with patch.object(cli_service, "_handle_success_completion") as mock_success:
                    await cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/repo",
                        branch_name="main",
                        timeout_seconds=3600,
                        task_id="task123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        commit_interval=30
                    )

                    # Verify initial commit was called
                    assert mock_git_service.commit_and_push.called

    @pytest.mark.asyncio
    async def test_monitor_cli_process_initial_commit_timeout(self, cli_service, mock_git_service):
        """Test monitoring when initial commit times out."""
        mock_task_service = AsyncMock()
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = 0

        # Make wait() timeout first time, then complete
        async def wait_side_effect():
            raise asyncio.TimeoutError()

        mock_process.wait = AsyncMock(side_effect=wait_side_effect)
        mock_git_service.commit_and_push.side_effect = asyncio.TimeoutError()

        with patch("application.services.github.cli_service.get_task_service") as mock_ts:
            mock_ts.return_value = mock_task_service
            with patch("application.agents.shared.process_manager.get_process_manager") as mock_pm:
                mock_pm.return_value = AsyncMock()
                with patch("application.agents.shared.process_utils._is_process_running") as mock_running:
                    mock_running.return_value = False
                    with patch.object(cli_service, "_handle_success_completion"):
                        await cli_service._monitor_cli_process(
                            process=mock_process,
                            repository_path="/tmp/repo",
                            branch_name="main",
                            timeout_seconds=3600,
                            task_id="task123",
                            prompt_file="/tmp/prompt.txt",
                            output_file="/tmp/output.log",
                            repo_auth_config={},
                            commit_interval=30
                        )

                        # Should have logged the timeout warning
                        assert mock_git_service.commit_and_push.called

    @pytest.mark.asyncio
    async def test_monitor_cli_process_failure(self, cli_service, mock_git_service):
        """Test monitoring process that fails."""
        mock_task_service = AsyncMock()
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = 1
        mock_process.wait = AsyncMock()

        mock_git_service.commit_and_push.return_value = {
            "success": True,
            "changed_files": [],
            "canvas_resources": {}
        }

        with patch("application.services.github.cli_service.get_task_service") as mock_ts:
            mock_ts.return_value = mock_task_service
            with patch("application.agents.shared.process_manager.get_process_manager") as mock_pm:
                mock_pm.return_value = AsyncMock()
                with patch("application.services.github.cli.monitor._handle_failure_completion") as mock_failure:
                    await cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/repo",
                        branch_name="main",
                        timeout_seconds=3600,
                        task_id="task123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        commit_interval=30
                    )

                    # Verify failure handler was called
                    mock_failure.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_with_none(self, cli_service):
        """Test cleanup with None prompt file."""
        with patch("application.services.github.cli_service.logger") as mock_logger:
            cli_service._cleanup_temp_files(None)
            # Should not log anything for None
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_with_path(self, cli_service):
        """Test cleanup with actual prompt file path."""
        with patch("application.services.github.cli_service.logger") as mock_logger:
            cli_service._cleanup_temp_files("/tmp/prompt.txt")
            # Should log the cleanup
            mock_logger.info.assert_called_once()

    def test_track_background_task(self, cli_service):
        """Test background task tracking."""
        mock_task = MagicMock(spec=asyncio.Task)
        cli_service._track_background_task(mock_task)

        # Verify task was added to background tasks
        assert mock_task.add_done_callback.called

    @pytest.mark.asyncio
    async def test_get_cli_config_with_explicit_provider(self, cli_service):
        """Test getting CLI config with explicit provider."""
        script_path, model = cli_service._get_cli_config("augment")
        assert model == "haiku4.5"
        assert script_path is not None

    @pytest.mark.asyncio
    async def test_load_template_with_fallback(self, cli_service):
        """Test template loading with fallback mechanism."""
        with patch("application.services.github.cli_service.load_template") as mock_load:
            def side_effect(name):
                if "github_cli" in name:
                    raise FileNotFoundError()
                return "Fallback template"

            mock_load.side_effect = side_effect
            result = await cli_service._load_informational_prompt_template("python")
            assert result == "Fallback template"
            assert mock_load.call_count == 2

    @pytest.mark.asyncio
    async def test_load_template_error_handling(self, cli_service):
        """Test template loading error handling."""
        with patch("application.services.github.cli_service.load_template") as mock_load:
            mock_load.side_effect = Exception("Template load failed")

            with pytest.raises(Exception, match="Template load failed"):
                await cli_service._load_informational_prompt_template("python")

    @pytest.mark.asyncio
    async def test_handle_success_completion_with_hook_data(self, cli_service, mock_git_service):
        """Test success completion with hook data generation."""
        mock_task_service = AsyncMock()
        mock_git_service.commit_and_push.return_value = {
            "success": True,
            "changed_files": ["file1.py", "file2.py"],
            "canvas_resources": {"entities": ["Entity1"], "workflows": ["Workflow1"]}
        }

        await cli_service._handle_success_completion(
            task_id="task123",
            repository_path="/tmp/repo",
            branch_name="main",
            repo_auth_config={},
            task_service=mock_task_service,
            conversation_id="conv123",
            repository_name="test-repo",
            repository_owner="test-owner"
        )

        # Verify hook data was included
        call_args = mock_task_service.update_task_status.call_args
        assert call_args[1]["metadata"]["hook_data"] is not None
        assert call_args[1]["metadata"]["hook_data"]["conversation_id"] == "conv123"

    @pytest.mark.asyncio
    async def test_handle_success_completion_without_hook_data(self, cli_service, mock_git_service):
        """Test success completion without hook data (missing canvas resources)."""
        mock_task_service = AsyncMock()
        mock_git_service.commit_and_push.return_value = {
            "success": True,
            "changed_files": ["file1.py"],
            "canvas_resources": {}
        }

        await cli_service._handle_success_completion(
            task_id="task123",
            repository_path="/tmp/repo",
            branch_name="main",
            repo_auth_config={},
            task_service=mock_task_service,
            conversation_id="conv123",
            repository_name="test-repo",
            repository_owner="test-owner"
        )

        # Verify hook data was NOT included
        call_args = mock_task_service.update_task_status.call_args
        assert "hook_data" not in call_args[1]["metadata"]

    @pytest.mark.asyncio
    async def test_handle_success_completion_commit_timeout(self, cli_service, mock_git_service):
        """Test success completion when final commit times out."""
        mock_task_service = AsyncMock()

        async def timeout_commit(*args, **kwargs):
            raise asyncio.TimeoutError()

        mock_git_service.commit_and_push.side_effect = timeout_commit

        await cli_service._handle_success_completion(
            task_id="task123",
            repository_path="/tmp/repo",
            branch_name="main",
            repo_auth_config={},
            task_service=mock_task_service,
            conversation_id="conv123",
            repository_name="test-repo",
            repository_owner="test-owner"
        )

        # Verify task was marked as completed with timeout message
        call_args = mock_task_service.update_task_status.call_args
        assert call_args[1]["status"] == "completed"
        assert "timed out" in call_args[1]["message"]


class TestStartApplicationBuildExtended:
    """Extended tests for start_application_build covering all code paths."""

    @pytest.mark.asyncio
    async def test_start_application_build_success_with_template(self, cli_service, mock_git_service):
        """Test successful start_application_build with template loading."""
        with patch("application.services.github.cli_service.load_template") as mock_load, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.services.github.cli_service.get_task_service") as mock_ts, \
             patch("application.services.github.cli.utils.get_task_service") as mock_ts_utils, \
             patch("application.services.github.cli_service.asyncio.create_subprocess_exec") as mock_exec, \
             patch("application.services.github.cli_service.os.path.join", side_effect=os.path.join), \
             patch("application.services.github.cli_service.Path.exists", return_value=True):

            mock_load.side_effect = lambda x: "Template for " + x if "instructions" in x else "Patterns"

            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=True)
            mock_pm_instance.register_process = AsyncMock(return_value=True)
            mock_pm.return_value = mock_pm_instance

            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_exec.return_value = mock_process

            mock_ts_instance = AsyncMock()
            mock_task = MagicMock()
            mock_task.technical_id = "task-123"
            mock_ts_instance.create_task = AsyncMock(return_value=mock_task)
            mock_ts_instance.update_task_status = AsyncMock()
            mock_ts.return_value = mock_ts_instance
            mock_ts_utils.return_value = mock_ts_instance

            result = await cli_service.start_application_build(
                repository_path="/test/repo",
                branch_name="test-branch",
                requirements="Build an app",
                language="python",
                user_id="user-123",
                conversation_id="conv-123",
                repo_auth_config={"type": "public", "url": "https://github.com/test/repo"}
            )

            assert result["task_id"] == "task-123"
            assert result["pid"] == 12345
            assert "output_file" in result
            mock_ts_instance.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_application_build_script_not_found(self, cli_service):
        """Test start_application_build when script is not found."""
        with patch("application.services.github.cli_service.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError) as exc_info:
                await cli_service.start_application_build(
                    repository_path="/test/repo",
                    branch_name="test-branch",
                    requirements="Build",
                    language="python",
                    user_id="user-123",
                    conversation_id="conv-123",
                    repo_auth_config={}
                )
            assert "CLI script not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_application_build_process_limit_exceeded(self, cli_service):
        """Test start_application_build when process limit is exceeded."""
        with patch("application.services.github.cli_service.load_template") as mock_load, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.services.github.cli_service.Path.exists", return_value=True):

            mock_load.return_value = "Template"
            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=False)
            mock_pm.return_value = mock_pm_instance

            with pytest.raises(RuntimeError) as exc_info:
                await cli_service.start_application_build(
                    repository_path="/test/repo",
                    branch_name="test-branch",
                    requirements="Build",
                    language="python",
                    user_id="user-123",
                    conversation_id="conv-123",
                    repo_auth_config={}
                )
            assert "Maximum concurrent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_application_build_register_failure(self, cli_service, mock_git_service):
        """Test start_application_build when process registration fails."""
        with patch("application.services.github.cli_service.load_template") as mock_load, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.services.github.cli_service.asyncio.create_subprocess_exec") as mock_exec, \
             patch("application.services.github.cli_service.Path.exists", return_value=True), \
             patch("application.services.github.cli_service.get_task_service") as mock_task_service:

            mock_load.return_value = "Template"
            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=True)
            mock_pm_instance.register_process = AsyncMock(return_value=False)
            mock_pm.return_value = mock_pm_instance

            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.terminate = MagicMock()
            mock_exec.return_value = mock_process

            mock_task_service.return_value = AsyncMock()

            with pytest.raises(RuntimeError) as exc_info:
                await cli_service.start_application_build(
                    repository_path="/test/repo",
                    branch_name="test-branch",
                    requirements="Build",
                    language="python",
                    user_id="user-123",
                    conversation_id="conv-123",
                    repo_auth_config={}
                )
            assert "Process limit exceeded" in str(exc_info.value)
            mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_application_build_template_fallback(self, cli_service):
        """Test start_application_build with template fallback."""
        def load_template_side_effect(name):
            if "optimized" in name:
                raise FileNotFoundError()
            return f"Template for {name}"

        with patch("application.services.github.cli_service.load_template") as mock_load, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.services.github.cli_service.get_task_service") as mock_ts, \
             patch("application.services.github.cli.utils.get_task_service") as mock_ts_utils, \
             patch("application.services.github.cli_service.asyncio.create_subprocess_exec") as mock_exec, \
             patch("application.services.github.cli_service.Path.exists", return_value=True):

            mock_load.side_effect = load_template_side_effect

            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=True)
            mock_pm_instance.register_process = AsyncMock(return_value=True)
            mock_pm.return_value = mock_pm_instance

            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_exec.return_value = mock_process

            mock_ts_instance = AsyncMock()
            mock_task = MagicMock()
            mock_task.technical_id = "task-123"
            mock_ts_instance.create_task = AsyncMock(return_value=mock_task)
            mock_ts_instance.update_task_status = AsyncMock()
            mock_ts.return_value = mock_ts_instance
            mock_ts_utils.return_value = mock_ts_instance

            result = await cli_service.start_application_build(
                repository_path="/test/repo",
                branch_name="test-branch",
                requirements="Build",
                language="python",
                user_id="user-123",
                conversation_id="conv-123",
                repo_auth_config={}
            )

            assert result["task_id"] == "task-123"
            # Verify fallback was used
            assert mock_load.call_count >= 2


class TestStartCodeGenerationExtended:
    """Extended tests for start_code_generation covering validation and error paths."""

    @pytest.mark.asyncio
    async def test_start_code_generation_validation_missing_request(self, cli_service):
        """Test start_code_generation rejects empty user request."""
        with pytest.raises(ValueError) as exc_info:
            await cli_service.start_code_generation(
                repository_path="/test/repo",
                branch_name="test",
                user_request="",
                language="python",
                user_id="user-123",
                conversation_id="conv-123",
                repo_auth_config={}
            )
        assert "user_request is required" in str(exc_info.value)


class TestMonitorCliProcessExtended:
    """Extended tests for _monitor_cli_process covering all code paths."""

    @pytest.mark.asyncio
    async def test_monitor_initial_commit_timeout(self, cli_service, mock_git_service):
        """Test monitor with initial commit timeout."""
        mock_process = AsyncMock()
        mock_process.pid = 111
        mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.returncode = 0

        mock_git_service.commit_and_push = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        with patch("application.services.github.cli_service.get_task_service") as mock_ts, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.services.github.cli_service.asyncio.get_event_loop") as mock_loop:

            mock_loop_instance = MagicMock()
            mock_loop_instance.time = MagicMock(return_value=1000)
            mock_loop.return_value = mock_loop_instance

            mock_ts_instance = AsyncMock()
            mock_ts_instance.update_task_status = AsyncMock()
            mock_ts_instance.add_progress_update = AsyncMock()
            mock_ts.return_value = mock_ts_instance

            mock_pm_instance = AsyncMock()
            mock_pm_instance.unregister_process = AsyncMock()
            mock_pm.return_value = mock_pm_instance

            await cli_service._monitor_cli_process(
                process=mock_process,
                repository_path="/test",
                branch_name="test",
                timeout_seconds=30,
                task_id="task-1",
                prompt_file="/tmp/prompt.txt",
                output_file="/tmp/output.log",
                repo_auth_config={}
            )

            # Initial commit should have been attempted
            mock_git_service.commit_and_push.assert_called()


    @pytest.mark.asyncio
    async def test_monitor_process_exit_early(self, cli_service, mock_git_service):
        """Test monitor when process completes early."""
        mock_process = AsyncMock()
        mock_process.pid = 333
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0

        mock_git_service.commit_and_push = AsyncMock(return_value={})

        with patch("application.services.github.cli_service.get_task_service") as mock_ts, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.services.github.cli_service.asyncio.get_event_loop") as mock_loop:

            mock_loop_instance = MagicMock()
            mock_loop_instance.time = MagicMock(return_value=1000)
            mock_loop.return_value = mock_loop_instance

            mock_ts_instance = AsyncMock()
            mock_ts_instance.update_task_status = AsyncMock()
            mock_ts.return_value = mock_ts_instance

            mock_pm_instance = AsyncMock()
            mock_pm_instance.unregister_process = AsyncMock()
            mock_pm.return_value = mock_pm_instance

            await cli_service._monitor_cli_process(
                process=mock_process,
                repository_path="/test",
                branch_name="test",
                timeout_seconds=100,
                task_id="task-3",
                prompt_file="/tmp/prompt.txt",
                output_file="/tmp/output.log",
                repo_auth_config={}
            )

            # Task should be marked as completed
            completed_calls = [call for call in mock_ts_instance.update_task_status.call_args_list
                             if call[1].get("status") == "completed"]
            assert len(completed_calls) > 0

    @pytest.mark.asyncio
    async def test_monitor_timeout_exceeded(self, cli_service, mock_git_service):
        """Test monitor when timeout is exceeded."""
        mock_process = AsyncMock()
        mock_process.pid = 444
        mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.returncode = 1

        mock_git_service.commit_and_push = AsyncMock(return_value={})

        with patch("application.services.github.cli_service.get_task_service") as mock_ts, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.agents.shared.process_utils._is_process_running") as mock_running, \
             patch("application.services.github.cli_service.asyncio.get_event_loop") as mock_loop:

            mock_loop_instance = MagicMock()
            # Time progresses beyond timeout
            mock_loop_instance.time = MagicMock(side_effect=[1000, 1000, 2000, 2000])
            mock_loop.return_value = mock_loop_instance

            mock_running.return_value = False

            mock_ts_instance = AsyncMock()
            mock_ts_instance.update_task_status = AsyncMock()
            mock_ts.return_value = mock_ts_instance

            mock_pm_instance = AsyncMock()
            mock_pm_instance.unregister_process = AsyncMock()
            mock_pm.return_value = mock_pm_instance

            await cli_service._monitor_cli_process(
                process=mock_process,
                repository_path="/test",
                branch_name="test",
                timeout_seconds=100,
                task_id="task-4",
                prompt_file="/tmp/prompt.txt",
                output_file="/tmp/output.log",
                repo_auth_config={}
            )

            # Task should be marked as failed/timed out
            failed_calls = [call for call in mock_ts_instance.update_task_status.call_args_list
                          if call[1].get("status") == "failed"]
            assert len(failed_calls) > 0

    @pytest.mark.asyncio
    async def test_monitor_commit_error_handling(self, cli_service, mock_git_service):
        """Test monitor handles commit errors gracefully."""
        mock_process = AsyncMock()
        mock_process.pid = 555
        mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.returncode = 0

        # Commit throws exception
        mock_git_service.commit_and_push = AsyncMock(
            side_effect=Exception("Commit failed")
        )

        with patch("application.services.github.cli_service.get_task_service") as mock_ts, \
             patch("application.agents.shared.process_manager.get_process_manager") as mock_pm, \
             patch("application.agents.shared.process_utils._is_process_running") as mock_running, \
             patch("application.services.github.cli_service.asyncio.get_event_loop") as mock_loop:

            mock_loop_instance = MagicMock()
            mock_loop_instance.time = MagicMock(side_effect=[1000, 1000, 1010, 1010])
            mock_loop.return_value = mock_loop_instance

            mock_running.return_value = False

            mock_ts_instance = AsyncMock()
            mock_ts_instance.update_task_status = AsyncMock()
            mock_ts.return_value = mock_ts_instance

            mock_pm_instance = AsyncMock()
            mock_pm_instance.unregister_process = AsyncMock()
            mock_pm.return_value = mock_pm_instance

            # Should not raise exception, should complete despite commit error
            await cli_service._monitor_cli_process(
                process=mock_process,
                repository_path="/test",
                branch_name="test",
                timeout_seconds=100,
                task_id="task-5",
                prompt_file="/tmp/prompt.txt",
                output_file="/tmp/output.log",
                repo_auth_config={}
            )

            # Task should still be updated despite error
            assert mock_ts_instance.update_task_status.called

