"""Command security validation for Unix commands.

This module provides security validation to ensure only safe,
read-only operations are allowed within the repository directory.
"""

from __future__ import annotations

import re
import shlex
from typing import Any, Dict, Optional

from pydantic import BaseModel

# Security validation constants
MAX_COMMAND_LENGTH = 1000

# Allowed read-only commands
ALLOWED_COMMANDS = {
    # File system exploration
    "find",
    "ls",
    "tree",
    "du",
    "stat",
    "file",
    # Text processing and viewing
    "cat",
    "head",
    "tail",
    "less",
    "more",
    "grep",
    "egrep",
    "fgrep",
    # Text manipulation (read-only)
    "sort",
    "uniq",
    "cut",
    "awk",
    "sed",
    "tr",
    "wc",
    "nl",
    # Path utilities
    "basename",
    "dirname",
    "realpath",
    "readlink",
    # Archive viewing (read-only)
    "tar",
    "gzip",
    "gunzip",
    "zcat",
    # JSON/data processing
    "jq",
}

# Dangerous pattern list with explanations
DANGEROUS_PATTERNS = [
    # File modification/deletion
    (r"\brm\b", "file removal"),
    (r"\bmv\b", "file move"),
    (r"\bcp\b", "file copy"),
    (r"\btouch\b", "file creation"),
    (r"\bmkdir\b", "directory creation"),
    (r"\brmdir\b", "directory removal"),
    # Permission changes
    (r"\bchmod\b", "permission change"),
    (r"\bchown\b", "ownership change"),
    (r"\bchgrp\b", "group change"),
    # System/privilege escalation
    (r"\bsudo\b", "sudo execution"),
    (r"\bsu\b", "user switch"),
    # Output redirection (can overwrite files)
    (r">", "output redirection"),
    (r">>", "output append"),
    (r"\btee\b", "tee command"),
    # Process control
    (r"\bkill\b", "process termination"),
    (r"\bkillall\b", "process group termination"),
    (r"\bpkill\b", "process signal"),
    # Network operations
    (r"\bcurl\b", "network request"),
    (r"\bwget\b", "file download"),
    (r"\bssh\b", "ssh connection"),
    (r"\bscp\b", "secure copy"),
    (r"\brsync\b", "sync operation"),
    # System modification
    (r"\bmount\b", "mount operation"),
    (r"\bumount\b", "unmount operation"),
    (r"\bfdisk\b", "disk partitioning"),
    (r"\bdd\b", "disk writing"),
    # Package management
    (r"\bapt\b", "package management"),
    (r"\byum\b", "package management"),
    (r"\bpip\b", "python package management"),
    (r"\bnpm\b", "node package management"),
    # Dangerous file operations
    (r"\bshred\b", "secure deletion"),
    (r"\bwipe\b", "data wiping"),
    (r"\btruncate\b", "file truncation"),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    (r"\.\./\.\.", "parent directory traversal"),
    (r"/\.\./\.\.", "absolute parent directory traversal"),
    (r"~/", "home directory access"),
    (r"/tmp", "temp directory access"),
    (r"/var", "system var directory access"),
    (r"/etc", "system config access"),
    (r"/usr", "system usr access"),
    (r"/bin", "system bin access"),
    (r"/sbin", "system sbin access"),
    (r"/root", "root directory access"),
]

# Environment variable patterns
ENV_VAR_PATTERNS = [
    (r"\$\{[^}]*\}", "braced environment variable"),
    (r"\$[A-Z_][A-Z0-9_]*", "unbraced environment variable"),
]


class CommandSecurityResult(BaseModel):
    """Result of command security validation."""

    safe: bool
    reason: str


def _parse_command(command: str) -> tuple[bool, Optional[str], Optional[list[str]]]:
    """Parse command safely using shlex.

    Args:
        command: Raw command string to parse

    Returns:
        Tuple of (success, error_message, command_parts)
    """
    try:
        command_parts = shlex.split(command)
    except ValueError as e:
        return False, f"Invalid command syntax: {e}", None

    if not command_parts:
        return False, "Empty command", None

    return True, None, command_parts


def _validate_command_whitelist(base_command: str) -> tuple[bool, Optional[str]]:
    """Validate command is in whitelist of allowed commands.

    Args:
        base_command: First part of the command

    Returns:
        Tuple of (is_valid, error_message)
    """
    if base_command not in ALLOWED_COMMANDS:
        return (
            False,
            f"Command '{base_command}' is not in the allowed list of read-only commands",
        )

    return True, None


def _validate_dangerous_patterns(command: str) -> tuple[bool, Optional[str]]:
    """Check command for dangerous patterns.

    Args:
        command: Full command string to check

    Returns:
        Tuple of (is_safe, reason_if_unsafe)
    """
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Command contains dangerous pattern: {description}"

    return True, None


def _validate_path_safety(command: str) -> tuple[bool, Optional[str]]:
    """Validate command doesn't access paths outside repository.

    Args:
        command: Full command string to check

    Returns:
        Tuple of (is_safe, reason_if_unsafe)
    """
    for pattern, description in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, command):
            return False, f"Command contains path security risk: {description}"

    return True, None


def _validate_command_length(command: str) -> tuple[bool, Optional[str]]:
    """Validate command length to prevent injection attacks.

    Args:
        command: Command string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(command) > MAX_COMMAND_LENGTH:
        return False, f"Command is too long (max {MAX_COMMAND_LENGTH} characters)"

    return True, None


def _validate_environment_variables(command: str) -> tuple[bool, Optional[str]]:
    """Validate command doesn't use environment variables.

    Args:
        command: Full command string to check

    Returns:
        Tuple of (is_safe, reason_if_unsafe)
    """
    for pattern, description in ENV_VAR_PATTERNS:
        if re.search(pattern, command):
            return (
                False,
                f"Environment variable usage is not allowed for security: {description}",
            )

    return True, None


async def validate_command_security(command: str, repo_path: str) -> Dict[str, Any]:
    """Comprehensive security validation for Unix commands.

    This function implements multiple layers of security to ensure only safe,
    read-only operations are allowed within the repository directory.

    Security layers:
    1. Command parsing - ensure valid shell syntax
    2. Command whitelist - only allow read-only operations
    3. Dangerous patterns - block file modification, privilege escalation, etc.
    4. Path safety - prevent directory traversal and system access
    5. Command length - prevent injection attacks
    6. Environment variables - block dynamic variable expansion

    Args:
        command: The command to validate
        repo_path: The repository path (for path validation)

    Returns:
        Dict with 'safe' (bool) and 'reason' (str) keys
    """
    try:
        # Step 1: Parse command safely
        success, error_msg, command_parts = _parse_command(command)
        if not success:
            return {"safe": False, "reason": error_msg}

        base_command = command_parts[0]

        # Step 2: Validate command is in whitelist
        is_valid, error_msg = _validate_command_whitelist(base_command)
        if not is_valid:
            return {"safe": False, "reason": error_msg}

        # Step 3: Check for dangerous patterns
        is_safe, reason = _validate_dangerous_patterns(command)
        if not is_safe:
            return {"safe": False, "reason": reason}

        # Step 4: Validate path safety
        is_safe, reason = _validate_path_safety(command)
        if not is_safe:
            return {"safe": False, "reason": reason}

        # Step 5: Validate command length
        is_valid, error_msg = _validate_command_length(command)
        if not is_valid:
            return {"safe": False, "reason": error_msg}

        # Step 6: Validate environment variables
        is_safe, reason = _validate_environment_variables(command)
        if not is_safe:
            return {"safe": False, "reason": reason}

        # All checks passed
        return {"safe": True, "reason": "Command passed all security checks"}

    except Exception as e:
        return {"safe": False, "reason": f"Security validation error: {str(e)}"}
