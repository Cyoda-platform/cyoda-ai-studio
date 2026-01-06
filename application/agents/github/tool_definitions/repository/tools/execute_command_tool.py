"""Tool for executing Unix commands in the repository.

This module handles safe execution of Unix/Linux commands for repository exploration
and analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.security.command_validator import (
    validate_command_security,
)

logger = logging.getLogger(__name__)


def _validate_tool_context(tool_context: ToolContext) -> tuple[Optional[str], Optional[str]]:
    """Validate tool context and extract repository path.

    Args:
        tool_context: Tool execution context.

    Returns:
        Tuple of (repository_path, error_message). Path is None if validation fails.
    """
    if not tool_context:
        return None, "Tool context not available"

    repository_path = tool_context.state.get("repository_path")
    if not repository_path:
        return None, "Repository path not found in context"

    return repository_path, None


def _verify_repository_path(repository_path: str) -> tuple[bool, Optional[str]]:
    """Verify repository path exists.

    Args:
        repository_path: Path to verify.

    Returns:
        Tuple of (valid, error_message). Error is None if valid.
    """
    repo_path = Path(repository_path)
    if not repo_path.exists():
        return False, f"Repository path does not exist: {repository_path}"
    return True, None


def _parse_command(command: str) -> list[str]:
    """Parse command string into parts.

    Args:
        command: Command string.

    Returns:
        List of command parts, empty list if parsing fails.
    """
    try:
        return shlex.split(command)
    except ValueError:
        return []


async def _validate_command_security(command: str, repo_path: str) -> tuple[bool, Optional[str]]:
    """Validate command security.

    Args:
        command: Command to validate.
        repo_path: Repository path for context.

    Returns:
        Tuple of (safe, error_reason). Error is None if safe.
    """
    security_result = await validate_command_security(command, repo_path)
    if not security_result["safe"]:
        return False, security_result["reason"]
    return True, None


async def _execute_command_subprocess(command: str, repo_path: str) -> tuple[int, str, str]:
    """Execute command in subprocess.

    Args:
        command: Command to execute.
        repo_path: Working directory.

    Returns:
        Tuple of (return_code, stdout, stderr).
    """
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repo_path
    )
    stdout, stderr = await process.communicate()
    decoded_stdout = stdout.decode('utf-8', errors='replace') or ""
    decoded_stderr = stderr.decode('utf-8', errors='replace') or ""
    return process.returncode, decoded_stdout, decoded_stderr


def _build_success_result(
    command: str, repository_path: str, return_code: int, stdout: str,
    stderr: str, command_parts: list[str]
) -> dict:
    """Build successful command result.

    Args:
        command: Executed command.
        repository_path: Repository path.
        return_code: Process return code.
        stdout: Standard output.
        stderr: Standard error.
        command_parts: Parsed command parts.

    Returns:
        Result dictionary.
    """
    result = {
        "command": command,
        "repository_path": repository_path,
        "exit_code": return_code,
        "stdout": stdout,
        "stderr": stderr,
        "success": return_code == 0
    }

    if result["success"]:
        stdout_lines = stdout.strip().split('\n') if stdout.strip() else []
        result["summary"] = {
            "output_lines": len(stdout_lines),
            "has_output": bool(stdout.strip()),
            "command_type": command_parts[0] if command_parts else "unknown"
        }
        logger.info(f"✅ Command executed successfully: {len(stdout_lines)} lines of output")
    else:
        result["summary"] = {
            "error": True,
            "stderr_lines": len(stderr.strip().split('\n')) if stderr.strip() else 0
        }
        logger.warning(f"⚠️ Command failed with exit code {return_code}")

    return result


def _format_security_error(command: str) -> str:
    """Format security validation error response.

    Args:
        command: Command that failed validation.

    Returns:
        JSON string with error details.
    """
    return json.dumps({
        "error": "Command failed security validation",
        "command": command,
        "allowed_commands": [
            "find", "grep", "ls", "cat", "head", "tail", "wc", "sort", "uniq",
            "cut", "awk", "sed", "file", "tree", "du", "stat", "basename", "dirname"
        ],
        "security_note": "Only read-only operations within repository directory are allowed"
    })


def _format_error_response(message: str, command: str = "") -> str:
    """Format error response as JSON.

    Args:
        message: Error message.
        command: Command that caused error.

    Returns:
        JSON string with error details.
    """
    result = {"error": message}
    if command:
        result["command"] = command
    return json.dumps(result)


async def execute_unix_command(
    command: str,
    tool_context: ToolContext = None
) -> str:
    """Execute any Unix command in the repository directory.

    Validates tool context, repository path, and command security before execution.
    Returns command output with metadata including exit code and summary information.

    Args:
        command: Unix command to execute (e.g., "find . -name '*.json' | head -10")
        tool_context: Execution context

    Returns:
        JSON string with command output and metadata

    Examples:
        # Find all JSON files
        execute_unix_command("find . -name '*.json'")

        # Search for specific content
        execute_unix_command("grep -r 'OrderProcessing' --include='*.json' .")

        # Count entity versions
        execute_unix_command("find . -path '*/entity/*/version_*' -type d | wc -l")
    """
    try:
        # Validate tool context
        repository_path, context_error = _validate_tool_context(tool_context)
        if context_error:
            return _format_error_response(context_error, command)

        # Verify repository path
        repo_exists, path_error = _verify_repository_path(repository_path)
        if path_error:
            return _format_error_response(path_error, command)

        # Parse command
        command_parts = _parse_command(command)

        # Validate command security
        safe, security_error = await _validate_command_security(command, repository_path)
        if security_error:
            return _format_security_error(command)

        logger.info(f"🔧 Executing Unix command: {command}")

        # Execute command
        return_code, stdout, stderr = await _execute_command_subprocess(command, repository_path)

        # Build result
        result = _build_success_result(command, repository_path, return_code, stdout, stderr, command_parts)
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error executing Unix command '{command}': {e}", exc_info=True)
        return _format_error_response(str(e), command)
