"""Circuit breaker pattern for CLI process management.

Prevents cascading failures by temporarily blocking CLI operations
when failure rate exceeds threshold.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 3  # Failures before opening circuit (max 3 attempts)
    success_threshold: int = 2  # Successes in half-open to close circuit
    timeout_seconds: int = 300  # Time to wait before trying half-open (5 min)
    reset_timeout_seconds: int = 3600  # Time to reset failure count (1 hour)


class CliCircuitBreaker:
    """Circuit breaker for CLI process management.

    Tracks failure rate and temporarily blocks operations when threshold exceeded.
    Implements automatic recovery testing via half-open state.
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()
        self.circuit_opened_at: Optional[float] = None

    def can_execute(self) -> tuple[bool, str]:
        """Check if execution is allowed.

        Returns:
            Tuple of (allowed, reason)
        """
        current_time = time.time()

        if self.state == CircuitState.CLOSED:
            # Reset failure count after reset timeout
            if (
                self.last_failure_time
                and current_time - self.last_failure_time
                > self.config.reset_timeout_seconds
            ):
                self._reset_failure_count()
            return True, "Circuit closed - normal operation"

        elif self.state == CircuitState.OPEN:
            # Check if timeout expired
            if (
                self.circuit_opened_at
                and current_time - self.circuit_opened_at > self.config.timeout_seconds
            ):
                self._transition_to_half_open()
                return True, "Circuit half-open - testing recovery"

            time_remaining = int(
                self.config.timeout_seconds - (current_time - self.circuit_opened_at)
            )
            return (
                False,
                f"Circuit open - too many failures. Retry in {time_remaining}s",
            )

        else:  # HALF_OPEN
            return True, "Circuit half-open - testing recovery"

    def record_success(self) -> None:
        """Record successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker: Success in half-open state "
                f"({self.success_count}/{self.config.success_threshold})"
            )

            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.info(
                    f"Circuit breaker: Success after {self.failure_count} failures - resetting counter"
                )
                self._reset_failure_count()

    def record_failure(self) -> None:
        """Record failed execution."""
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker: Failure in half-open state - reopening")
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            logger.warning(
                f"Circuit breaker: Failure recorded "
                f"({self.failure_count}/{self.config.failure_threshold})"
            )

            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.circuit_opened_at = time.time()
        self.last_state_change = time.time()
        self.success_count = 0
        logger.error(
            f"⚠️ Circuit breaker OPENED after {self.failure_count} failures (max 3). "
            f"CLI operations blocked for {self.config.timeout_seconds}s"
        )

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = time.time()
        self.success_count = 0
        logger.info("🔄 Circuit breaker HALF-OPEN - testing recovery")

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        previous_failures = self.failure_count
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self._reset_failure_count()
        logger.info(
            f"✅ Circuit breaker CLOSED - recovery successful after {previous_failures} failures"
        )

    def _reset_failure_count(self) -> None:
        """Reset failure count and related state."""
        self.failure_count = 0
        self.success_count = 0
        self.circuit_opened_at = None

    def get_state(self) -> dict:
        """Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "circuit_opened_at": self.circuit_opened_at,
            "last_state_change": self.last_state_change,
        }


# Global circuit breaker instance
_circuit_breaker: Optional[CliCircuitBreaker] = None


def get_circuit_breaker() -> CliCircuitBreaker:
    """Get global circuit breaker instance.

    Returns:
        Global CliCircuitBreaker instance
    """
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CliCircuitBreaker()
    return _circuit_breaker


def reset_circuit_breaker() -> None:
    """Reset global circuit breaker (for testing)."""
    global _circuit_breaker
    _circuit_breaker = None


__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CliCircuitBreaker",
    "get_circuit_breaker",
    "reset_circuit_breaker",
]
