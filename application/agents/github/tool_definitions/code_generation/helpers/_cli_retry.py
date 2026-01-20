"""Retry logic for CLI process failures.

Handles automatic retry of failed CLI processes with error classification
and exponential backoff.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Use smart error analyzer instead of pattern matching
from ._cli_error_analyzer import CliErrorType, classify_cli_error

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""

    max_retries: int = 3  # Maximum retry attempts
    base_delay: float = 5.0  # Initial delay in seconds
    max_delay: float = 60.0  # Maximum delay between retries
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier
    retryable_exit_codes: set = field(
        default_factory=lambda: {1, 124, 137, 143}
    )  # Exit codes that may be retryable


def _read_log_tail(log_file: str, max_chars: int = 2000) -> str:
    """Read tail of log file for error analysis.

    Args:
        log_file: Path to log file
        max_chars: Maximum characters to read from end

    Returns:
        Log content (last max_chars characters)
    """
    try:
        if not os.path.exists(log_file):
            return ""

        with open(log_file, "r") as f:
            f.seek(0, 2)  # Go to end
            size = f.tell()
            f.seek(max(0, size - max_chars))
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to read log file {log_file}: {e}")
        return ""


# classify_cli_error is now imported from _cli_error_analyzer
# Uses smart heuristics instead of hardcoded patterns


def is_retryable_error(error_type: CliErrorType, retry_config: RetryConfig) -> bool:
    """Determine if error should be retried.

    Args:
        error_type: Classified error type
        retry_config: Retry configuration

    Returns:
        True if error should be retried
    """
    return error_type in [CliErrorType.TRANSIENT, CliErrorType.RECOVERABLE]


def calculate_retry_delay(
    attempt: int, retry_config: RetryConfig, error_type: CliErrorType
) -> float:
    """Calculate delay before next retry with exponential backoff.

    Args:
        attempt: Current retry attempt (0-indexed)
        retry_config: Retry configuration
        error_type: Type of error for delay adjustment

    Returns:
        Delay in seconds
    """
    # Calculate base exponential backoff
    delay = retry_config.base_delay * (retry_config.backoff_multiplier**attempt)

    # Adjust delay based on error type
    if error_type == CliErrorType.TRANSIENT:
        # Longer delay for rate limits
        delay = min(delay * 2, retry_config.max_delay)
    elif error_type == CliErrorType.RECOVERABLE:
        # Standard delay
        delay = min(delay, retry_config.max_delay)

    return delay


def format_retry_message(
    attempt: int,
    max_retries: int,
    error_type: CliErrorType,
    error_description: str,
    delay: float,
) -> str:
    """Format retry status message.

    Args:
        attempt: Current attempt number (1-indexed)
        max_retries: Maximum retry attempts
        error_type: Type of error
        error_description: Error description
        delay: Delay before next retry

    Returns:
        Formatted message
    """
    return (
        f"CLI process failed (attempt {attempt}/{max_retries}): {error_description}. "
        f"Error type: {error_type.value}. Retrying in {delay:.1f}s..."
    )


def should_retry(
    returncode: int,
    log_file: Optional[str],
    attempt: int,
    retry_config: RetryConfig,
    timeout_occurred: bool = False,
) -> tuple[bool, CliErrorType, str, float]:
    """Determine if CLI process should be retried.

    Args:
        returncode: Process exit code
        log_file: Path to log file
        attempt: Current attempt number (0-indexed)
        retry_config: Retry configuration
        timeout_occurred: Whether process timed out

    Returns:
        Tuple of (should_retry, error_type, error_description, retry_delay)
    """
    # Read log content for analysis
    log_content = _read_log_tail(log_file) if log_file else ""

    # Classify error
    error_type, error_description = classify_cli_error(
        returncode, log_content, timeout_occurred
    )

    # Check if we've exhausted retries
    if attempt >= retry_config.max_retries:
        logger.error(
            f"Maximum retries ({retry_config.max_retries}) exhausted. "
            f"Final error: {error_description}"
        )
        return False, error_type, error_description, 0.0

    # Check if error is retryable
    if not is_retryable_error(error_type, retry_config):
        logger.error(f"Non-retryable error: {error_description}")
        return False, error_type, error_description, 0.0

    # Calculate retry delay
    retry_delay = calculate_retry_delay(attempt, retry_config, error_type)

    logger.warning(
        format_retry_message(
            attempt + 1,
            retry_config.max_retries,
            error_type,
            error_description,
            retry_delay,
        )
    )

    return True, error_type, error_description, retry_delay


async def execute_with_retry(
    func,
    retry_config: RetryConfig,
    *args,
    **kwargs,
) -> tuple[bool, str, any]:
    """Execute async function with retry logic.

    Args:
        func: Async function to execute
        retry_config: Retry configuration
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Tuple of (success, error_message, result)
    """
    for attempt in range(retry_config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            return True, "", result
        except Exception as e:
            if attempt >= retry_config.max_retries:
                return False, f"Failed after {attempt + 1} attempts: {str(e)}", None

            delay = calculate_retry_delay(
                attempt, retry_config, CliErrorType.RECOVERABLE
            )
            logger.warning(
                f"Execution failed (attempt {attempt + 1}/{retry_config.max_retries + 1}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    return False, "Failed after all retries", None


__all__ = [
    "CliErrorType",  # Re-exported from _cli_error_analyzer
    "RetryConfig",
    "classify_cli_error",  # Re-exported from _cli_error_analyzer
    "is_retryable_error",
    "calculate_retry_delay",
    "format_retry_message",
    "should_retry",
    "execute_with_retry",
]
