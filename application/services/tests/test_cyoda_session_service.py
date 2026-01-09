"""Tests for Cyoda Session Service.

This is a compatibility wrapper that re-exports all test functions from the
test_cyoda_session_service package. The actual implementation has been refactored
into focused modules within the test_cyoda_session_service/ subdirectory for
better organization.

For new code, consider importing directly from:
- test_cyoda_session_service.crud_tests: Basic CRUD operations
- test_cyoda_session_service.advanced_tests: Advanced features
"""

from __future__ import annotations

# Re-export all test functions and fixtures for backward compatibility
from .test_cyoda_session_service import (  # Fixtures; CRUD tests; Advanced tests
    mock_entity_service,
    session_service,
    test_append_event,
    test_create_session,
    test_create_session_generates_id,
    test_delete_session,
    test_get_session,
    test_get_session_not_found,
    test_get_session_with_config,
    test_list_sessions,
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
