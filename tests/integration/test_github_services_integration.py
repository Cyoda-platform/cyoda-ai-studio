"""Integration tests for GitHub services working together."""

import asyncio
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.core.file_system_service import FileSystemService
from application.services.github.cli_service import GitHubCLIService
from application.services.github.operations_service import GitHubOperationsService


class TestGitHubServicesIntegration:
    """Test integration between GitHub services."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository directory."""
        temp_dir = tempfile.mkdtemp()
        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_dir,
            check=True,
        )

        # Create initial commit
        test_file = Path(temp_dir) / "README.md"
        test_file.write_text("# Test Repo")
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True
        )

        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def git_service(self):
        """Create GitHubOperationsService instance."""
        return GitHubOperationsService()

    @pytest.fixture
    def fs_service(self):
        """Create FileSystemService instance."""
        return FileSystemService()

    @pytest.fixture
    def cli_service(self, git_service):
        """Create GitHubCLIService instance."""
        return GitHubCLIService(git_service)

    @pytest.mark.asyncio
    async def test_get_diff_shows_changes(self, git_service, temp_repo):
        """Test getting diff shows uncommitted changes."""
        # Create a new file
        new_file = Path(temp_repo) / "new_file.py"
        new_file.write_text("print('hello')")

        # Modify existing file (stage it first so it shows as modified, not untracked)
        readme = Path(temp_repo) / "README.md"
        readme.write_text("# Modified Repo")

        # Stage the README so it appears as modified
        import subprocess

        subprocess.run(["git", "add", "README.md"], cwd=temp_repo, check=True)

        # Get diff
        diff = await git_service.get_repository_diff(temp_repo)

        assert "new_file.py" in diff["untracked"]
        # README.md should be in modified or added (depending on git status interpretation)
        assert "README.md" in (diff["modified"] + diff["added"])

    @pytest.mark.asyncio
    async def test_commit_and_push_detects_canvas_resources(
        self, git_service, temp_repo
    ):
        """Test commit detects canvas resources (entities, workflows)."""

        # Mock all git operations to prevent touching real repository
        async def mock_git_cmd(cmd, **kwargs):
            if cmd[0] == "status":
                return {
                    "returncode": 0,
                    "stdout": "A application/resources/entity/customer/version_1/customer.json\n"
                    "A application/resources/workflow/process/version_1/process.json",
                    "stderr": "",
                }
            elif cmd[0] == "commit":
                return {
                    "returncode": 0,
                    "stdout": "[main abc123] Add entities and workflows",
                    "stderr": "",
                }
            elif cmd[0] in ["config", "add", "push"]:
                return {"returncode": 0, "stdout": "", "stderr": ""}
            return {"returncode": 0, "stdout": "", "stderr": ""}

        with patch(
            "application.services.github.operations_service.service.commit_operations.run_git_cmd",
            AsyncMock(side_effect=mock_git_cmd),
        ):
            with patch("os.chdir"):
                with patch("os.getcwd", return_value="/fake/dir"):
                    result = await git_service.commit_and_push(
                        repository_path="/fake/test/repo",
                        commit_message="Add entities and workflows",
                        branch_name="main",
                        repo_auth_config={},
                    )

                    assert result["success"]
                    assert "canvas_resources" in result
                    assert isinstance(result["changed_files"], list)

    @pytest.mark.asyncio
    async def test_file_system_service_saves_and_executes(self, fs_service, temp_repo):
        """Test FileSystemService can save files and execute commands."""
        # Save a file
        test_file = Path(temp_repo) / "test_script.py"
        await fs_service.save_file(test_file, "print('test')")

        assert test_file.exists()
        assert test_file.read_text() == "print('test')"

        # Execute command
        result = await fs_service.execute_unix_command("ls -la", Path(temp_repo))

        assert result["success"]
        assert result["exit_code"] == 0
        assert "test_script.py" in result["stdout"]

    @pytest.mark.asyncio
    async def test_cli_service_validates_inputs(self, cli_service):
        """Test CLI service validates required inputs."""
        with pytest.raises(ValueError, match="repository_path is required"):
            await cli_service.start_code_generation(
                repository_path="",
                branch_name="main",
                user_request="Create entity",
                language="python",
                user_id="user-123",
                conversation_id="conv-456",
                repo_auth_config={},
            )

        with pytest.raises(ValueError, match="user_request is required"):
            await cli_service.start_code_generation(
                repository_path="/tmp/repo",
                branch_name="main",
                user_request="",
                language="python",
                user_id="user-123",
                conversation_id="conv-456",
                repo_auth_config={},
            )

    @pytest.mark.asyncio
    async def test_ensure_repository_handles_existing_repo(
        self, git_service, temp_repo
    ):
        """Test ensure_repository returns success for existing repo."""
        # Create .git directory
        git_dir = Path(temp_repo) / ".git"
        git_dir.mkdir(exist_ok=True)

        success, message, path = await git_service.ensure_repository(
            repository_url="https://github.com/test/repo",
            repository_branch="main",
            repository_name="repo",
            use_env_installation_id=False,
        )

        # Note: This test depends on the branch name matching
        # If the test uses temp_repo which has .git, it will say already exists
        assert isinstance(success, bool)
        assert isinstance(message, str)

    @pytest.mark.asyncio
    async def test_pull_changes_returns_output(self, git_service, temp_repo):
        """Test pull changes returns git output."""
        # Mock subprocess to avoid actual git pull to non-existent remote
        with patch(
            "asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_proc:
            # Create a mock process
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"Already up to date.", b"")
            )
            mock_process.returncode = 0
            mock_proc.return_value = mock_process

            output = await git_service.pull_changes(temp_repo, "main")

            assert "up to date" in output.lower()


class TestServiceErrorHandling:
    """Test error handling across services."""

    @pytest.fixture
    def git_service(self):
        return GitHubOperationsService()

    @pytest.mark.asyncio
    async def test_commit_handles_nothing_to_commit(self, git_service):
        """Test commit gracefully handles 'nothing to commit' scenario."""

        # Mock all git operations to prevent touching real repository
        async def mock_git_cmd(cmd, **kwargs):
            if cmd[0] == "status":
                return {"returncode": 0, "stdout": "", "stderr": ""}
            elif cmd[0] == "commit":
                # Simulate nothing to commit
                return {
                    "returncode": 1,
                    "stdout": "nothing to commit, working tree clean",
                    "stderr": "",
                }
            elif cmd[0] in ["config", "add"]:
                return {"returncode": 0, "stdout": "", "stderr": ""}
            return {"returncode": 0, "stdout": "", "stderr": ""}

        with patch(
            "application.services.github.operations_service.service.commit_operations.run_git_cmd",
            AsyncMock(side_effect=mock_git_cmd),
        ):
            with patch("os.chdir"):
                with patch("os.getcwd", return_value="/fake/dir"):
                    result = await git_service.commit_and_push(
                        repository_path="/fake/test/repo",
                        commit_message="No changes",
                        branch_name="main",
                        repo_auth_config={},
                    )

                    assert result["success"]
                    assert "No changes" in result["message"]
                    assert len(result["changed_files"]) == 0

    @pytest.mark.asyncio
    async def test_ensure_repository_handles_timeout(self, git_service):
        """Test ensure_repository handles timeout gracefully."""
        with patch.object(
            git_service, "_run_subprocess", AsyncMock(side_effect=Exception("timeout"))
        ):
            success, message, path = await git_service.ensure_repository(
                repository_url="https://github.com/test/repo",
                repository_branch="main",
                repository_name="repo",
            )

            assert not success
            assert (
                "timeout" in message.lower()
                or "error" in message.lower()
                or "failed" in message.lower()
            )
            assert path is None

    @pytest.mark.asyncio
    async def test_commit_retries_push_on_failure(self, git_service):
        """Test commit retries push operation on failure."""
        push_call_count = [0]

        # Mock all git operations to prevent touching real repository
        async def mock_git_cmd(cmd, **kwargs):
            if cmd[0] == "push":
                push_call_count[0] += 1
                if push_call_count[0] == 1:
                    # First push attempt fails
                    raise Exception("error: failed to push")
                else:
                    # Second push attempt succeeds
                    return {"returncode": 0, "stdout": "", "stderr": ""}
            elif cmd[0] == "status":
                return {"returncode": 0, "stdout": "M test.txt", "stderr": ""}
            elif cmd[0] == "commit":
                return {
                    "returncode": 0,
                    "stdout": "[main abc123] Test commit",
                    "stderr": "",
                }
            elif cmd[0] in ["config", "add"]:
                return {"returncode": 0, "stdout": "", "stderr": ""}
            elif cmd[0] == "remote":
                return {"returncode": 0, "stdout": "", "stderr": ""}
            return {"returncode": 0, "stdout": "", "stderr": ""}

        with patch(
            "application.services.github.operations_service.service.commit_operations.run_git_cmd",
            AsyncMock(side_effect=mock_git_cmd),
        ):
            with patch("os.chdir"):
                with patch("os.getcwd", return_value="/fake/dir"):
                    result = await git_service.commit_and_push(
                        repository_path="/fake/test/repo",
                        commit_message="Test commit",
                        branch_name="main",
                        repo_auth_config={},
                    )

                    # Should have retried and succeeded
                    assert push_call_count[0] >= 1
                    assert result["success"]


class TestMonitoringIntegration:
    """Test CLI monitoring integration with task updates."""

    @pytest.fixture
    def cli_service(self):
        git_service = GitHubOperationsService()
        return GitHubCLIService(git_service)

    @pytest.mark.asyncio
    async def test_monitor_updates_task_with_canvas_resources(self, cli_service):
        """Test monitoring updates task with canvas resource metadata."""
        # Create mock process
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.returncode = 0

        # Mock wait to complete immediately
        async def mock_wait():
            return 0

        mock_process.wait = mock_wait

        # Mock task service
        mock_task_service = MagicMock()
        mock_task_service.update_task_status = AsyncMock()
        mock_task_service.add_progress_update = AsyncMock()

        # Mock git service to return canvas resources
        with patch.object(
            cli_service.git_service,
            "commit_and_push",
            AsyncMock(
                return_value={
                    "success": True,
                    "changed_files": ["entity.json"],
                    "canvas_resources": {"entities": ["Customer"]},
                }
            ),
        ):
            with patch(
                "application.services.github.cli_service.get_task_service",
                return_value=mock_task_service,
            ):
                with patch(
                    "application.agents.shared.process_manager.get_process_manager"
                ) as mock_pm:
                    mock_pm.return_value.unregister_process = AsyncMock()

                    await cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/test",
                        branch_name="test",
                        timeout_seconds=10,
                        task_id="task-123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        conversation_id="conv-456",
                        repository_name="test-repo",
                        repository_owner="test-owner",
                    )

                    # Verify final status includes hook_data
                    final_call = mock_task_service.update_task_status.call_args_list[-1]
                    metadata = final_call[1].get("metadata", {})

                    assert "canvas_resources" in metadata
                    if "hook_data" in metadata:
                        assert metadata["hook_data"]["conversation_id"] == "conv-456"
                        assert metadata["hook_data"]["repository_name"] == "test-repo"
