"""CLI invocation tracking to prevent runaway CLI calls."""

from collections import defaultdict

MAX_CLI_CALLS_PER_SESSION = 10


class CLIInvocationTracker:
    """Tracks CLI invocations per agent loop to prevent runaway CLI calls."""

    def __init__(self, max_cli_calls: int = MAX_CLI_CALLS_PER_SESSION):
        self.max_cli_calls = max_cli_calls
        self.cli_call_counts = defaultdict(int)

    def record_cli_call(self, session_id: str) -> tuple[bool, str]:
        """Record a CLI invocation and check if limit exceeded.

        Returns:
            (is_allowed, message) - is_allowed=False if limit exceeded
        """
        self.cli_call_counts[session_id] += 1
        count = self.cli_call_counts[session_id]

        if count > self.max_cli_calls:
            message = (
                f"🚫 CLI LIMIT EXCEEDED: {count} CLI invocations in this agent loop "
                f"(max: {self.max_cli_calls}). Stopping to prevent runaway."
            )
            return False, message

        return True, ""

    def reset_session(self, session_id: str) -> None:
        """Reset CLI call count for a session (called at start of new agent loop)."""
        if session_id in self.cli_call_counts:
            del self.cli_call_counts[session_id]

    def get_count(self, session_id: str) -> int:
        """Get current CLI call count for a session."""
        return self.cli_call_counts.get(session_id, 0)


# Global CLI tracker instance
_cli_tracker = CLIInvocationTracker(max_cli_calls=MAX_CLI_CALLS_PER_SESSION)


def check_cli_invocation_limit(session_id: str) -> tuple[bool, str]:
    """Check if CLI invocation limit has been exceeded for this session.

    Args:
        session_id: The session ID to check

    Returns:
        (is_allowed, message) - is_allowed=False if limit exceeded
    """
    return _cli_tracker.record_cli_call(session_id)


def reset_cli_invocation_count(session_id: str) -> None:
    """Reset CLI invocation count for a new agent loop."""
    _cli_tracker.reset_session(session_id)


def get_cli_invocation_count(session_id: str) -> int:
    """Get current CLI invocation count for a session."""
    return _cli_tracker.get_count(session_id)
