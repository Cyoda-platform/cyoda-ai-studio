"""Service for GitHub CLI operations (code generation and building).

Internal organization:
- cli/validation.py: Input validation functions
- cli/utils.py: Utility functions
- cli/monitor.py: Process monitoring and completion handling
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Set

from common.config.config import CLI_PROVIDER, AUGMENT_MODEL, CLAUDE_MODEL, GEMINI_MODEL
from application.agents.shared.prompt_loader import load_template
from application.services.github.operations_service import GitHubOperationsService
from services.services import get_task_service

# Re-export from cli modules for backward compatibility
from .cli.validation import (
    _validate_cli_inputs,
    _validate_script_path,
    _validate_cli_provider_config,
)
from .cli.utils import (
    _create_prompt_file,
    _create_output_log_file,
    _write_log_header,
    _start_subprocess,
    _finalize_output_file,
    _register_process_and_create_task,
    _extract_repo_metadata,
)
from .cli.monitor import (
    _perform_initial_commit,
    _check_process_running,
    _perform_periodic_commit,
    _update_progress_status,
    _unregister_process,
    _perform_final_commit,
    _build_completion_metadata,
    _handle_success_completion,
    _handle_failure_completion,
    PROCESS_CHECK_INTERVAL,
    PROGRESS_UPDATE_CAP,
)

logger = logging.getLogger(__name__)

# Resource paths
_MODULE_DIR = Path(__file__).parent.parent.parent / "agents" / "github"
_BUILD_MODE = os.getenv("BUILD_MODE", "production").lower()

if _BUILD_MODE == "test":
    _DEFAULT_AUGGIE_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build_mock.sh"
    _DEFAULT_CLAUDE_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build_mock.sh"
    _DEFAULT_GEMINI_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build_mock.sh"
else:
    _DEFAULT_AUGGIE_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build.sh"
    _DEFAULT_CLAUDE_SCRIPT = _MODULE_DIR.parent / "shared" / "claude_build.sh"
    _DEFAULT_GEMINI_SCRIPT = _MODULE_DIR.parent / "shared" / "gemini_build.sh"

AUGGIE_CLI_SCRIPT = os.getenv("AUGMENT_CLI_SCRIPT", str(_DEFAULT_AUGGIE_SCRIPT))

# Constants for monitoring
DEFAULT_CODEGEN_TIMEOUT = 3600  # 1 hour
DEFAULT_BUILD_TIMEOUT = 1800    # 30 minutes
CODEGEN_COMMIT_INTERVAL = 30    # seconds
BUILD_COMMIT_INTERVAL = 60      # seconds


class GitHubCLIService:
    """Service for handling GitHub CLI operations."""

    def __init__(self, git_service: GitHubOperationsService):
        self.git_service = git_service
        self._background_tasks: Set[asyncio.Task] = set()

    def _get_cli_config(self, provider: str = None) -> tuple[Path, str]:
        """Get CLI script path and model based on provider."""
        provider = provider or CLI_PROVIDER

        if provider == "claude":
            return _DEFAULT_CLAUDE_SCRIPT, CLAUDE_MODEL
        elif provider == "gemini":
            return _DEFAULT_GEMINI_SCRIPT, GEMINI_MODEL
        else:
            return _DEFAULT_AUGGIE_SCRIPT, AUGMENT_MODEL

    async def _load_informational_prompt_template(self, language: str) -> str:
        """Load informational prompt template."""
        try:
            template_name = f"github_cli_{language}_instructions"
            try:
                return load_template(template_name)
            except FileNotFoundError:
                return load_template(f"build_{language}_instructions")
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            raise

    def _cleanup_temp_files(self, prompt_file: Optional[str]) -> None:
        """Cleanup temp files."""
        if prompt_file:
            logger.info(f"📝 Prompt file preserved for audit: {prompt_file}")

    async def start_code_generation(
        self,
        repository_path: str,
        branch_name: str,
        user_request: str,
        language: str,
        user_id: str,
        conversation_id: str,
        repo_auth_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start code generation process.

        Args:
            repository_path: Path to repository
            branch_name: Git branch name
            user_request: User's code generation request
            language: Programming language
            user_id: User ID
            conversation_id: Conversation ID
            repo_auth_config: Repository authentication config

        Returns:
            Dictionary with task_id, pid, and output_file
        """
        # Step 1: Validate inputs
        _validate_cli_inputs(repository_path, branch_name, language, user_request=user_request)

        # Step 2: Get and validate CLI configuration
        script_path, cli_model = self._get_cli_config()
        _validate_script_path(script_path)
        _validate_cli_provider_config(CLI_PROVIDER, cli_model)

        # Step 3: Create prompt file
        prompt_template = await self._load_informational_prompt_template(language)
        full_prompt = f"{prompt_template}\n\n## User Request:\n{user_request}"
        prompt_file = await _create_prompt_file(full_prompt)

        # Step 4: Setup process manager
        from application.agents.shared.process_manager import get_process_manager
        process_manager = get_process_manager()
        if not await process_manager.can_start_process():
            raise RuntimeError("Maximum concurrent CLI processes reached")

        # Step 5: Create and configure output log file
        output_file, output_fd = _create_output_log_file(CLI_PROVIDER, branch_name, "codegen")
        _write_log_header(output_fd, branch_name, "codegen", cli_model)

        # Step 6: Start subprocess
        process = await _start_subprocess(
            script_path, prompt_file, cli_model,
            repository_path, branch_name, output_fd
        )

        # Step 7: Finalize log file
        final_output_file = _finalize_output_file(output_file, process.pid)

        # Step 8: Register process and create task
        try:
            task_id = await _register_process_and_create_task(
                process.pid, get_task_service(),
                user_id, "code_generation",
                f"Generate code: {user_request[:50]}...",
                f"Generating code: {user_request[:200]}...",
                branch_name, language, user_request,
                conversation_id, repository_path, repo_auth_config,
                final_output_file
            )
        except RuntimeError as e:
            # Terminate process if registration fails
            process.terminate()
            raise

        # Step 9: Extract repository metadata
        repository_owner, repository_name = _extract_repo_metadata(repo_auth_config)

        # Step 10: Start monitoring task
        monitoring_task = asyncio.create_task(
            self._monitor_cli_process(
                process=process,
                repository_path=repository_path,
                branch_name=branch_name,
                timeout_seconds=DEFAULT_CODEGEN_TIMEOUT,
                task_id=task_id,
                prompt_file=prompt_file,
                output_file=final_output_file,
                repo_auth_config=repo_auth_config,
                commit_interval=CODEGEN_COMMIT_INTERVAL,
                conversation_id=conversation_id,
                repository_name=repository_name,
                repository_owner=repository_owner
            )
        )

        self._track_background_task(monitoring_task)

        return {
            "task_id": task_id,
            "pid": process.pid,
            "output_file": final_output_file
        }

    async def _load_build_prompt_template(self, language: str) -> str:
        """Load build prompt template with patterns for language.

        Args:
            language: Programming language

        Returns:
            Combined prompt template with patterns
        """
        template_name = f"build_{language.lower()}_instructions_optimized"
        try:
            template = load_template(template_name)
        except FileNotFoundError:
            template = load_template(f"build_{language.lower()}_instructions")

        pattern_catalog = ""
        if language.lower() == "python":
            try:
                pattern_catalog = load_template("python_patterns")
            except Exception:
                pass

        if pattern_catalog:
            return f"{template}\n\n---\n\n{pattern_catalog}"
        return template

    async def start_application_build(
        self,
        repository_path: str,
        branch_name: str,
        requirements: str,
        language: str,
        user_id: str,
        conversation_id: str,
        repo_auth_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start application build process.

        Args:
            repository_path: Path to repository
            branch_name: Git branch name
            requirements: Build requirements/specifications
            language: Programming language
            user_id: User ID
            conversation_id: Conversation ID
            repo_auth_config: Repository authentication config

        Returns:
            Dictionary with task_id, pid, and output_file
        """
        # Step 1: Validate inputs
        _validate_cli_inputs(repository_path, branch_name, language, requirements=requirements)

        # Step 2: Get and validate CLI configuration
        script_path, cli_model = self._get_cli_config()
        _validate_script_path(script_path)
        _validate_cli_provider_config(CLI_PROVIDER, cli_model)

        # Step 3: Create prompt file
        template = await self._load_build_prompt_template(language)
        full_prompt = f"{template}\n\n## User Requirements:\n{requirements}"
        prompt_file = await _create_prompt_file(full_prompt)

        # Step 4: Setup process manager
        from application.agents.shared.process_manager import get_process_manager
        process_manager = get_process_manager()
        if not await process_manager.can_start_process():
            raise RuntimeError("Maximum concurrent CLI processes reached")

        # Step 5: Create and configure output log file
        output_file, output_fd = _create_output_log_file(CLI_PROVIDER, branch_name, "build")
        _write_log_header(output_fd, branch_name, "build")

        # Step 6: Start subprocess (cwd = repository_path for builds)
        process = await _start_subprocess(
            script_path, prompt_file, cli_model,
            repository_path, branch_name, output_fd, repository_path
        )

        # Step 7: Finalize log file
        final_output_file = _finalize_output_file(output_file, process.pid)

        # Step 8: Register process and create task
        try:
            task_id = await _register_process_and_create_task(
                process.pid, get_task_service(),
                user_id, "application_build",
                f"Build {language} app: {branch_name}",
                f"Building app: {requirements[:200]}...",
                branch_name, language, requirements,
                conversation_id, repository_path, repo_auth_config,
                final_output_file
            )
        except RuntimeError as e:
            # Terminate process if registration fails
            process.terminate()
            raise

        # Step 9: Extract repository metadata
        repository_owner, repository_name = _extract_repo_metadata(repo_auth_config)

        # Step 10: Start monitoring task
        monitoring_task = asyncio.create_task(
            self._monitor_cli_process(
                process=process,
                repository_path=repository_path,
                branch_name=branch_name,
                timeout_seconds=DEFAULT_BUILD_TIMEOUT,
                task_id=task_id,
                prompt_file=prompt_file,
                output_file=final_output_file,
                repo_auth_config=repo_auth_config,
                commit_interval=BUILD_COMMIT_INTERVAL,
                conversation_id=conversation_id,
                repository_name=repository_name,
                repository_owner=repository_owner
            )
        )
        self._track_background_task(monitoring_task)

        return {
            "task_id": task_id,
            "pid": process.pid,
            "output_file": final_output_file
        }

    async def _monitor_cli_process(
        self,
        process: Any,
        repository_path: str,
        branch_name: str,
        timeout_seconds: int,
        task_id: str,
        prompt_file: str,
        output_file: str,
        repo_auth_config: Dict[str, Any],
        commit_interval: int = 30,
        conversation_id: Optional[str] = None,
        repository_name: Optional[str] = None,
        repository_owner: Optional[str] = None
    ) -> None:
        """Monitor CLI process with periodic commits and task updates.

        Args:
            process: Process instance
            repository_path: Repository path
            branch_name: Branch name
            timeout_seconds: Process timeout in seconds
            task_id: Task ID
            prompt_file: Prompt file path
            output_file: Output log file path
            repo_auth_config: Repository auth config
            commit_interval: Commit interval in seconds
            conversation_id: Conversation ID (optional)
            repository_name: Repository name (optional)
            repository_owner: Repository owner (optional)
        """
        pid = process.pid
        start_time = asyncio.get_event_loop().time()
        last_push_time = start_time
        elapsed_time = 0
        task_service = get_task_service()

        logger.info(f"🔍 [{branch_name}] Monitoring CLI process {pid}")

        # Step 1: Initial commit
        last_push_time = await _perform_initial_commit(
            self.git_service, repository_path, branch_name, repo_auth_config
        )

        # Step 2: Monitor loop
        while elapsed_time < timeout_seconds:
            try:
                # Check if process is still running
                if not await _check_process_running(process, pid):
                    break

                elapsed_time += PROCESS_CHECK_INTERVAL
                current_time = asyncio.get_event_loop().time()
                time_since_last_push = current_time - last_push_time

                # Periodic commit if interval reached
                if time_since_last_push >= commit_interval:
                    await _perform_periodic_commit(
                        self.git_service, repository_path, branch_name, repo_auth_config,
                        elapsed_time, task_id, task_service, pid
                    )
                    last_push_time = current_time

                # Update progress status
                await _update_progress_status(
                    task_id, elapsed_time, timeout_seconds, task_service, pid
                )

            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}", exc_info=True)

        # Step 3: Cleanup
        await _unregister_process(pid)
        self._cleanup_temp_files(prompt_file)

        # Step 4: Handle completion (success or failure)
        from .cli.monitor import _determine_and_handle_process_result

        await _determine_and_handle_process_result(
            process, task_id, pid, elapsed_time, timeout_seconds,
            self.git_service, repository_path, branch_name, repo_auth_config,
            task_service, conversation_id, repository_name, repository_owner
        )

    async def _handle_success_completion(
        self,
        task_id: str,
        repository_path: str,
        branch_name: str,
        repo_auth_config: Dict[str, Any],
        task_service: Any,
        conversation_id: Optional[str] = None,
        repository_name: Optional[str] = None,
        repository_owner: Optional[str] = None
    ) -> None:
        """Wrapper for _handle_success_completion function (for test compatibility)."""
        return await _handle_success_completion(
            self.git_service, task_id, repository_path, branch_name,
            repo_auth_config, task_service, conversation_id,
            repository_name, repository_owner
        )

    async def _handle_failure_completion(
        self,
        task_id: str,
        return_code: Optional[int],
        elapsed_time: float,
        timeout_seconds: int,
        task_service: Any
    ) -> None:
        """Wrapper for _handle_failure_completion function (for test compatibility)."""
        return await _handle_failure_completion(
            task_id, return_code, elapsed_time, timeout_seconds, task_service
        )

    def _track_background_task(self, task: asyncio.Task) -> None:
        background_tasks: Set[Any] = getattr(asyncio, '_background_tasks', set())
        if not hasattr(asyncio, '_background_tasks'):
            setattr(asyncio, '_background_tasks', background_tasks)
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)


__all__ = [
    # Class
    "GitHubCLIService",
    # Constants
    "DEFAULT_CODEGEN_TIMEOUT",
    "DEFAULT_BUILD_TIMEOUT",
    "CODEGEN_COMMIT_INTERVAL",
    "BUILD_COMMIT_INTERVAL",
    # Re-exported for backward compatibility
    "_validate_cli_inputs",
    "_validate_script_path",
    "_validate_cli_provider_config",
    "_create_prompt_file",
    "_create_output_log_file",
    "_write_log_header",
    "_start_subprocess",
    "_finalize_output_file",
    "_register_process_and_create_task",
    "_extract_repo_metadata",
]
