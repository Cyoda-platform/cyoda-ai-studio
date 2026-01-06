"""Tests for Cyoda Session Service.

This test suite is organized into focused modules:
- crud_tests: Basic CRUD operations (create, get, list, delete)
- advanced_tests: Advanced features (events, persistence, config)
"""

from __future__ import annotations

# Re-export all test functions and fixtures
from .crud_tests import (
    mock_entity_service,
    session_service,
    test_create_session,
    test_create_session_generates_id,
    test_get_session,
    test_get_session_not_found,
    test_list_sessions,
    test_delete_session,
)

from .advanced_tests import (
    test_get_session_with_config,
    test_append_event,
    test_session_persistence_simulation,
)

__all__ = [
    # Fixtures
    "mock_entity_service",
    "session_service",
    # CRUD tests
    "test_create_session",
    "test_create_session_generates_id",
    "test_get_session",
    "test_get_session_not_found",
    "test_list_sessions",
    "test_delete_session",
    # Advanced tests
    "test_get_session_with_config",
    "test_append_event",
    "test_session_persistence_simulation",
]
