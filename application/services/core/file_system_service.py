"""Service for file system operations."""

import asyncio
import logging
import re
import shlex
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Command execution constants
COMMAND_EXECUTION_ERROR = "Error executing command '{command}': {error}"
DEFAULT_ENCODING = "utf-8"
ENCODING_ERROR_HANDLER = "replace"
MAX_COMMAND_LENGTH = 1000
COMMAND_TOO_LONG_ERROR = f"Command is too long (max {MAX_COMMAND_LENGTH} characters)"
COMMAND_EMPTY_ERROR = "Empty command"
INVALID_COMMAND_SYNTAX_ERROR = "Invalid command syntax: {error}"

# Allowed commands list
ALLOWED_COMMANDS = {
    'find', 'ls', 'tree', 'du', 'stat', 'file',
    'cat', 'head', 'tail', 'less', 'more', 'grep', 'egrep', 'fgrep',
    'sort', 'uniq', 'cut', 'awk', 'sed', 'tr', 'wc', 'nl',
    'basename', 'dirname', 'realpath', 'readlink',
    'tar', 'gzip', 'gunzip', 'zcat', 'jq'
}

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    r'\brm\b', r'\bmv\b', r'\bcp\b', r'\btouch\b', r'\bmkdir\b',
    r'\bchmod\b', r'\bchown\b', r'\bchgrp\b',
    r'\bsudo\b', r'\bsu\b', r'>', r'>>', r'\btee\b',
    r'\bkill\b', r'\bkillall\b', r'\bpkill\b',
    r'\bcurl\b', r'\bwget\b', r'\bssh\b', r'\bscp\b', r'\brsync\b',
    r'\bmount\b', r'\bumount\b', r'\bfdisk\b', r'\bdd\b',
    r'\bapt\b', r'\byum\b', r'\bpip\b', r'\bnpm\b',
    r'\bshred\b', r'\bwipe\b', r'\btruncate\b'
]

# Path traversal patterns to block
PATH_TRAVERSAL_PATTERNS = [
    r'\.\./\.\.', r'/\.\./\.\.', r'~/', r'/tmp', r'/var',
    r'/etc', r'/usr', r'/bin', r'/sbin', r'/root'
]

# Environment variable patterns to block
ENV_VAR_PATTERNS = [r'\$\{[^}]*\}', r'\$[A-Z_][A-Z0-9_]*']

COMMAND_NOT_ALLOWED_ERROR = "Command '{command}' is not in the allowed list"
DANGEROUS_PATTERN_ERROR = "Command contains dangerous pattern: {pattern}"
PATH_TRAVERSAL_ERROR = "Command contains path traversal or system directory access"
ENV_VAR_ERROR = "Environment variable usage is not allowed"


class CommandResult(BaseModel):
    """Command execution result."""

    command: str
    repository_path: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    summary: Dict[str, Any]


class SecurityValidationResult(BaseModel):
    """Security validation result."""

    safe: bool
    reason: str
    allowed_commands: Optional[list] = None
    security_note: Optional[str] = None


class FileSystemService:
    """Service for safe file system operations."""

    def __init__(self):
        pass

    def _decode_bytes(self, data: bytes) -> str:
        """Decode bytes to string with error handling.

        Args:
            data: Bytes to decode

        Returns:
            Decoded string
        """
        return data.decode(DEFAULT_ENCODING, errors=ENCODING_ERROR_HANDLER) if data else ""

    def _build_success_summary(self, stdout: str) -> Dict[str, Any]:
        """Build summary for successful command execution.

        Args:
            stdout: Standard output

        Returns:
            Summary dictionary
        """
        stdout_lines = stdout.strip().split('\n') if stdout.strip() else []
        return {
            "output_lines": len(stdout_lines),
            "has_output": bool(stdout.strip())
        }

    def _build_failure_summary(self, stderr: str) -> Dict[str, Any]:
        """Build summary for failed command execution.

        Args:
            stderr: Standard error

        Returns:
            Summary dictionary
        """
        return {
            "error": True,
            "stderr_lines": len(stderr.strip().split('\n')) if stderr.strip() else 0
        }

    async def execute_unix_command(self, command: str, repo_path: Path) -> Dict[str, Any]:
        """Execute a Unix command safely within the repository path.

        Args:
            command: Command to execute
            repo_path: Repository path to execute within

        Returns:
            Execution result with stdout, stderr, and exit code

        Example:
            >>> result = await service.execute_unix_command("ls -la", Path("/repo"))
            >>> print(result["success"])
        """
        # Step 1: Validate command security
        security_result = self.validate_command_security(command)
        if not security_result["safe"]:
            return {
                "success": False,
                "error": security_result["reason"],
                "allowed_commands": security_result.get("allowed_commands"),
                "security_note": security_result.get("security_note")
            }

        try:
            # Step 2: Create and execute subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(repo_path)
            )

            # Step 3: Communicate with process
            stdout, stderr = await process.communicate()

            # Step 4: Decode output
            stdout_str = self._decode_bytes(stdout)
            stderr_str = self._decode_bytes(stderr)

            # Step 5: Build result
            result = {
                "command": command,
                "repository_path": str(repo_path),
                "exit_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "success": process.returncode == 0
            }

            # Step 6: Add summary based on success/failure
            if result["success"]:
                result["summary"] = self._build_success_summary(stdout_str)
            else:
                result["summary"] = self._build_failure_summary(stderr_str)

            return result

        except Exception as e:
            logger.error(COMMAND_EXECUTION_ERROR.format(command=command, error=e), exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

    def _check_command_allowed(self, base_command: str) -> Tuple[bool, str]:
        """Check if command is in allowed list.

        Args:
            base_command: Base command name

        Returns:
            Tuple of (is_allowed, error_message)
        """
        if base_command in ALLOWED_COMMANDS:
            return True, ""

        return False, COMMAND_NOT_ALLOWED_ERROR.format(command=base_command)

    def _check_dangerous_patterns(self, command: str) -> Tuple[bool, str]:
        """Check for dangerous command patterns.

        Args:
            command: Command string

        Returns:
            Tuple of (is_safe, error_message)
        """
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, DANGEROUS_PATTERN_ERROR.format(pattern=pattern)

        return True, ""

    def _check_path_traversal(self, command: str) -> Tuple[bool, str]:
        """Check for path traversal attempts.

        Args:
            command: Command string

        Returns:
            Tuple of (is_safe, error_message)
        """
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, command):
                return False, PATH_TRAVERSAL_ERROR

        return True, ""

    def _check_env_variables(self, command: str) -> Tuple[bool, str]:
        """Check for environment variable usage.

        Args:
            command: Command string

        Returns:
            Tuple of (is_safe, error_message)
        """
        for pattern in ENV_VAR_PATTERNS:
            if re.search(pattern, command):
                return False, ENV_VAR_ERROR

        return True, ""

    def validate_command_security(self, command: str) -> Dict[str, Any]:
        """Comprehensive security validation for Unix commands.

        Args:
            command: Command to validate

        Returns:
            Dictionary with safe flag and reason
        """
        # Step 1: Parse command syntax
        try:
            command_parts = shlex.split(command)
        except ValueError as e:
            return {"safe": False, "reason": INVALID_COMMAND_SYNTAX_ERROR.format(error=e)}

        # Step 2: Check for empty command
        if not command_parts:
            return {"safe": False, "reason": COMMAND_EMPTY_ERROR}

        # Step 3: Check command length
        if len(command) > MAX_COMMAND_LENGTH:
            return {"safe": False, "reason": COMMAND_TOO_LONG_ERROR}

        # Step 4: Check command is allowed
        base_command = command_parts[0]
        is_allowed, error_msg = self._check_command_allowed(base_command)
        if not is_allowed:
            return {"safe": False, "reason": error_msg}

        # Step 5: Check for dangerous patterns
        is_safe, error_msg = self._check_dangerous_patterns(command)
        if not is_safe:
            return {"safe": False, "reason": error_msg}

        # Step 6: Check for path traversal
        is_safe, error_msg = self._check_path_traversal(command)
        if not is_safe:
            return {"safe": False, "reason": error_msg}

        # Step 7: Check for environment variables
        is_safe, error_msg = self._check_env_variables(command)
        if not is_safe:
            return {"safe": False, "reason": error_msg}

        # Step 8: Return safe result
        return {"safe": True, "reason": "Command passed all security checks"}

    async def save_file(self, file_path: Path, content: str) -> None:
        """Save content to a file, creating directories as needed."""
        def _write():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write)
