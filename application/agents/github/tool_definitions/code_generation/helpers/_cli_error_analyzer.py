"""Smart CLI error analysis without hardcoded patterns.

Uses heuristics and structural analysis instead of pattern matching.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class CliErrorType(Enum):
    """Classification of CLI errors for retry decisions."""

    TRANSIENT = "transient"  # Retry automatically (network, rate limits)
    RECOVERABLE = "recoverable"  # Retry with caution (timeouts)
    PERMANENT = "permanent"  # Don't retry (bugs, invalid config)


class ErrorSource(Enum):
    """Source of the error."""

    CLI_TOOL = "cli_tool"  # Error in CLI tool itself
    GENERATED_CODE = "generated_code"  # Error in code CLI generated
    NETWORK = "network"  # Network/API error
    CONFIGURATION = "configuration"  # Config/auth error
    UNKNOWN = "unknown"


def _detect_error_source(log_content: str, returncode: int) -> ErrorSource:
    """Detect where the error originated.

    Args:
        log_content: CLI output logs
        returncode: Process exit code

    Returns:
        ErrorSource indicating origin of error
    """
    log_lower = log_content.lower()

    # Network/API errors (always transient)
    network_indicators = [
        "connect",
        "timeout",
        "refused",
        "unreachable",
        "rate limit",
        "quota",
        "429",
        "503",
        "502",
        "504",
        "econnreset",
        "econnrefused",
        "etimedout",
    ]
    if any(indicator in log_lower for indicator in network_indicators):
        return ErrorSource.NETWORK

    # Configuration errors (permanent)
    config_indicators = [
        "api key",
        "authentication",
        "unauthorized",
        "forbidden",
        "permission denied",
        "401",
        "403",
    ]
    if any(indicator in log_lower for indicator in config_indicators):
        return ErrorSource.CONFIGURATION

    # CLI tool internal errors (permanent)
    # These indicate bugs in the CLI tool itself, not user code
    cli_tool_indicators = [
        # Execution framework errors
        "agent execution failed",
        "tool execution failed",
        "tool call failed",
        "internal error",
        # Stack traces from CLI tool (not user code)
        "at object.",  # JavaScript stack trace
        "at process.",  # Node.js internals
        "at module.",  # Module loading errors
        "at async",  # Async execution errors
        # Unhandled exceptions
        "uncaught",
        "unhandled",
        # Generic runtime errors in wrong context
        "is not a function",  # Only if from CLI, not user code
        "is not defined",
        "is null",
        "is undefined",
        "cannot read",
        "cannot set",
    ]

    # Check if error mentions CLI tool paths or internals
    cli_path_indicators = [
        "/node_modules/",
        "/lib/",
        "/dist/",
        "augment",
        "cli.js",
        "tool.js",
        "agent.js",
    ]

    has_cli_indicators = any(
        indicator in log_lower for indicator in cli_tool_indicators
    )
    has_cli_paths = any(indicator in log_lower for indicator in cli_path_indicators)

    if has_cli_indicators or has_cli_paths:
        return ErrorSource.CLI_TOOL

    # Generated code errors (could be either permanent or recoverable)
    # Look for compilation/syntax errors in user's generated code
    code_error_indicators = [
        "syntax error",
        "compilation failed",
        "invalid syntax",
        "indentation error",
        "import error",
        "module not found",
    ]
    if any(indicator in log_lower for indicator in code_error_indicators):
        return ErrorSource.GENERATED_CODE

    return ErrorSource.UNKNOWN


def _is_retryable_by_exit_code(returncode: int) -> bool | None:
    """Determine retryability from exit code alone.

    Args:
        returncode: Process exit code

    Returns:
        True if retryable, False if not, None if inconclusive
    """
    # Success
    if returncode == 0:
        return False  # No need to retry success

    # Timeout/killed (retryable)
    if returncode in [124, 137, 143, 143]:  # SIGTERM, SIGKILL
        return True

    # Permission/not found (not retryable)
    if returncode in [126, 127]:  # Command not executable, not found
        return False

    # Generic error code 1 (inconclusive)
    if returncode == 1:
        return None  # Need to analyze logs

    # Exit code 2 (misuse of shell command)
    if returncode == 2:
        return False

    # Other codes (inconclusive)
    return None


def _contains_stack_trace(log_content: str) -> bool:
    """Check if log contains a stack trace (indicates unhandled exception).

    Args:
        log_content: Log content to analyze

    Returns:
        True if stack trace detected
    """
    stack_trace_patterns = [
        r"at\s+\S+\s+\([^)]+:\d+:\d+\)",  # JavaScript: at function (file:line:col)
        r"File\s+\"[^\"]+\",\s+line\s+\d+",  # Python: File "path", line X
        r"Traceback\s+\(most recent call last\)",  # Python traceback
        r"Stack trace:",  # Generic stack trace header
    ]

    for pattern in stack_trace_patterns:
        if re.search(pattern, log_content, re.IGNORECASE):
            return True

    return False


def classify_cli_error(
    returncode: int, log_content: str, timeout_occurred: bool = False
) -> tuple[CliErrorType, str]:
    """Classify CLI error using structural analysis instead of pattern matching.

    This uses heuristics and error source detection rather than hardcoded patterns.

    Args:
        returncode: Process exit code
        log_content: CLI output/error logs
        timeout_occurred: Whether process was killed due to timeout

    Returns:
        Tuple of (error_type, error_description)
    """
    # Step 1: Check timeout first
    if timeout_occurred:
        return CliErrorType.RECOVERABLE, "Process timeout - may succeed with retry"

    # Step 2: Detect error source
    error_source = _detect_error_source(log_content, returncode)

    # Step 3: Check exit code
    retryable_by_code = _is_retryable_by_exit_code(returncode)
    if retryable_by_code is True:
        return CliErrorType.RECOVERABLE, f"Process terminated (exit {returncode})"
    elif retryable_by_code is False:
        if returncode == 0:
            return CliErrorType.PERMANENT, "Success - no retry needed"
        return CliErrorType.PERMANENT, f"Command error (exit {returncode})"

    # Step 4: Classify based on error source
    if error_source == ErrorSource.NETWORK:
        return (
            CliErrorType.TRANSIENT,
            "Network or API error - likely transient",
        )

    elif error_source == ErrorSource.CONFIGURATION:
        return (
            CliErrorType.PERMANENT,
            "Configuration or authentication error",
        )

    elif error_source == ErrorSource.CLI_TOOL:
        # CLI tool bug - NOT our fault, retry may work
        # CLI could have race conditions, take different paths, or get updated
        has_stack_trace = _contains_stack_trace(log_content)
        if has_stack_trace:
            return (
                CliErrorType.TRANSIENT,
                "CLI tool crashed - may work on retry",
            )
        return (
            CliErrorType.TRANSIENT,
            "CLI tool internal error - retry may work",
        )

    elif error_source == ErrorSource.GENERATED_CODE:
        # Generated code has issues - permanent (need to change prompt)
        return (
            CliErrorType.PERMANENT,
            "Generated code has errors - prompt needs adjustment",
        )

    # Step 5: Exit code 1 with unknown source
    # Default to TRANSIENT for retry (conservative approach)
    # Circuit breaker will catch if this is wrong
    if returncode == 1:
        return (
            CliErrorType.TRANSIENT,
            "Generic error - may be transient, retry recommended",
        )

    # Step 6: Other unknown errors
    return (
        CliErrorType.RECOVERABLE,
        f"Unknown error (exit {returncode}) - retry may help",
    )


__all__ = [
    "CliErrorType",
    "ErrorSource",
    "classify_cli_error",
]
