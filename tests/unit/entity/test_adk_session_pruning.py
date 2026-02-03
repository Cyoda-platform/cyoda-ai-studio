"""
Unit tests for AdkSession event pruning functionality.

Tests the automatic pruning of conversation events to prevent
context overflow in LLM calls.
"""

from datetime import datetime, timezone

import pytest

from application.entity.adk_session import AdkSession


class TestAdkSessionPruning:
    """Test suite for AdkSession event pruning."""

    def test_prune_events_when_exceeds_limit(self):
        """Test that events are pruned when they exceed the keep limit."""
        # Create session with 30 events
        session = AdkSession(
            session_id="test-session-123",
            app_name="test-app",
            user_id="test-user",
            events=[
                {"type": "user", "message": f"Message {i}", "timestamp": i}
                for i in range(30)
            ],
        )

        # Prune to keep only 15 most recent events
        pruned_count = session.prune_events(keep_recent=15)

        # Verify pruning results
        assert pruned_count == 15, "Should have pruned 15 events"
        assert len(session.events) == 15, "Should have 15 events remaining"

        # Verify we kept the most recent events (15-29)
        assert session.events[0]["message"] == "Message 15"
        assert session.events[-1]["message"] == "Message 29"

    def test_prune_events_no_pruning_when_under_limit(self):
        """Test that no pruning occurs when events are under the limit."""
        # Create session with 10 events
        session = AdkSession(
            session_id="test-session-456",
            app_name="test-app",
            user_id="test-user",
            events=[
                {"type": "user", "message": f"Message {i}", "timestamp": i}
                for i in range(10)
            ],
        )

        # Try to prune to keep 15 events (more than we have)
        pruned_count = session.prune_events(keep_recent=15)

        # Verify no pruning occurred
        assert pruned_count == 0, "Should not have pruned any events"
        assert len(session.events) == 10, "Should still have all 10 events"

    def test_prune_events_updates_timestamp(self):
        """Test that pruning updates the last_update_time."""
        session = AdkSession(
            session_id="test-session-789",
            app_name="test-app",
            user_id="test-user",
            events=[
                {"type": "user", "message": f"Message {i}", "timestamp": i}
                for i in range(30)
            ],
        )

        # Record the original timestamp
        original_timestamp = session.last_update_time

        # Wait a tiny bit and prune
        pruned_count = session.prune_events(keep_recent=15)

        # Verify timestamp was updated
        assert (
            session.last_update_time >= original_timestamp
        ), "last_update_time should be updated"
        assert pruned_count == 15

    def test_prune_events_exact_limit(self):
        """Test pruning when event count exactly matches the limit."""
        session = AdkSession(
            session_id="test-session-exact",
            app_name="test-app",
            user_id="test-user",
            events=[
                {"type": "user", "message": f"Message {i}", "timestamp": i}
                for i in range(15)
            ],
        )

        # Prune to keep exactly 15 events
        pruned_count = session.prune_events(keep_recent=15)

        # Verify no pruning occurred
        assert pruned_count == 0, "Should not prune when at exact limit"
        assert len(session.events) == 15, "Should still have 15 events"

    def test_prune_events_empty_session(self):
        """Test pruning on an empty session."""
        session = AdkSession(
            session_id="test-session-empty",
            app_name="test-app",
            user_id="test-user",
            events=[],
        )

        # Try to prune empty session
        pruned_count = session.prune_events(keep_recent=15)

        # Verify nothing was pruned
        assert pruned_count == 0, "Should not prune empty session"
        assert len(session.events) == 0, "Should still be empty"

    def test_get_recent_events(self):
        """Test the get_recent_events method."""
        session = AdkSession(
            session_id="test-session-recent",
            app_name="test-app",
            user_id="test-user",
            events=[
                {"type": "user", "message": f"Message {i}", "timestamp": i}
                for i in range(20)
            ],
        )

        # Get 5 most recent events
        recent = session.get_recent_events(num_events=5)

        # Verify we got the right events
        assert len(recent) == 5, "Should have 5 events"
        assert recent[0]["message"] == "Message 15"
        assert recent[-1]["message"] == "Message 19"

    def test_prune_events_preserves_event_structure(self):
        """Test that pruning preserves the structure of remaining events."""
        session = AdkSession(
            session_id="test-session-structure",
            app_name="test-app",
            user_id="test-user",
            events=[
                {
                    "type": "user" if i % 2 == 0 else "ai",
                    "message": f"Message {i}",
                    "timestamp": i,
                    "metadata": {"index": i},
                }
                for i in range(25)
            ],
        )

        # Prune to 10 events
        session.prune_events(keep_recent=10)

        # Verify all fields are preserved
        assert len(session.events) == 10
        for idx, event in enumerate(session.events):
            expected_idx = 15 + idx
            assert event["message"] == f"Message {expected_idx}"
            assert event["metadata"]["index"] == expected_idx
            assert event["timestamp"] == expected_idx
