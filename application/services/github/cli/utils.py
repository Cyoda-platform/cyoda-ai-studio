"""Utility functions for CLI service."""

import asyncio
import datetime
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from application.agents.shared.prompt_loader import load_template
from services.services import get_task_service

logger = logging.getLogger(__name__)


async def _create_prompt_file(full_prompt: str) -> str:
    """Create temporary prompt file.

    Args:
        full_prompt: Full prompt text

    Returns:
        Path to created prompt file
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, dir="/tmp"
    ) as f:
        f.write(full_prompt)
        return f.name


def _create_output_log_file(
    provider: str, branch_name: str, log_type: str = "build"
) -> tuple[str, int]:
    """Create output log file for CLI process.

    Args:
        provider: Provider name (claude, gemini, augment)
        branch_name: Branch name
        log_type: Log type (build, codegen)

    Returns:
        Tuple of (file_path, file_descriptor)
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(
        "/tmp", f"{provider}_{log_type}_{branch_name}_TEMP_{timestamp}.log"
    )
    output_fd = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    return output_file, output_fd


def _write_log_header(
    output_fd: int, branch_name: str, log_type: str, model: str = ""
) -> None:
    """Write log file header.

    Args:
        output_fd: File descriptor
        branch_name: Branch name
        log_type: Log type
        model: Model name (optional)
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    header = f"{log_type.title()} Log\nBranch: {branch_name}\n"
    if model:
        header += f"Model: {model}\n"
    header += f"Started: {timestamp}\n\n"
    os.write(output_fd, header.encode())


async def _start_subprocess(
    script_path: Path,
    prompt_file: str,
    model: str,
    repository_path: str,
    branch_name: str,
    output_fd: int,
    cwd: Optional[str] = None,
) -> asyncio.subprocess.Process:
    """Start CLI subprocess.

    Args:
        script_path: Path to CLI script
        prompt_file: Path to prompt file
        model: Model name
        repository_path: Repository path
        branch_name: Branch name
        output_fd: Output file descriptor
        cwd: Working directory (optional)

    Returns:
        Process instance
    """
    cmd = [
        "bash",
        str(script_path.absolute()),
        f"@{prompt_file}",
        model,
        repository_path,
        branch_name,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=output_fd, stderr=output_fd, cwd=cwd or str(script_path.parent)
    )
    os.close(output_fd)
    return process


def _finalize_output_file(output_file: str, process_pid: int) -> str:
    """Rename output log file with process PID.

    Args:
        output_file: Original output file path
        process_pid: Process ID

    Returns:
        Final output file path
    """
    final_output_file = output_file.replace("TEMP", str(process_pid))
    try:
        os.rename(output_file, final_output_file)
    except OSError:
        final_output_file = output_file
    return final_output_file


async def _register_process_and_create_task(
    process_pid: int,
    task_service: Any,
    user_id: str,
    task_type: str,
    task_name: str,
    task_description: str,
    branch_name: str,
    language: str,
    user_request: str,
    conversation_id: str,
    repository_path: str,
    repo_auth_config: Dict[str, Any],
    output_file: str,
) -> str:
    """Register process and create task record.

    Args:
        process_pid: Process ID
        task_service: Task service instance
        user_id: User ID
        task_type: Task type (code_generation, application_build)
        task_name: Task name
        task_description: Task description
        branch_name: Branch name
        language: Language
        user_request: User request/requirements
        conversation_id: Conversation ID
        repository_path: Repository path
        repo_auth_config: Repository auth config
        output_file: Output log file

    Returns:
        Task ID
    """
    from application.agents.shared.process_manager import get_process_manager

    process_manager = get_process_manager()
    if not await process_manager.register_process(process_pid):
        raise RuntimeError("Process limit exceeded during registration")

    task_service = get_task_service()
    repo_url_public = (
        repo_auth_config.get("url")
        if repo_auth_config.get("type") == "public"
        else None
    )

    background_task = await task_service.create_task(
        user_id=user_id,
        task_type=task_type,
        name=task_name,
        description=task_description,
        branch_name=branch_name,
        language=language,
        user_request=user_request,
        conversation_id=conversation_id,
        repository_path=repository_path,
        repository_type=repo_auth_config.get("type"),
        repository_url=repo_url_public,
    )
    task_id = background_task.technical_id

    await task_service.update_task_status(
        task_id=task_id,
        status="running",
        message=f"Process started (PID: {process_pid})",
        progress=5,
        process_pid=process_pid,
        metadata={"output_log": output_file},
    )

    return task_id


def _extract_repo_metadata(
    repo_auth_config: Dict[str, Any],
) -> tuple[Optional[str], Optional[str]]:
    """Extract repository name and owner from config URL.

    Args:
        repo_auth_config: Repository auth config

    Returns:
        Tuple of (repository_owner, repository_name)
    """
    repository_name = None
    repository_owner = None

    if repo_auth_config.get("url"):
        try:
            from application.services.github.repository.url_parser import (
                parse_github_url,
            )

            parsed = parse_github_url(repo_auth_config["url"])
            repository_owner = parsed.get("owner")
            repository_name = parsed.get("repo")
        except Exception as e:
            logger.warning(f"Failed to parse repo URL: {e}")

    return repository_owner, repository_name
