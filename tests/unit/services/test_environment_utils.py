"""Unit tests for environment utility functions."""

import pytest

from application.services.environment.utils import (
    sanitize_keyspace,
    sanitize_namespace,
)


class TestSanitizeNamespace:
    """Test sanitize_namespace function."""

    def test_sanitize_namespace_basic(self):
        """Test basic namespace sanitization."""
        assert sanitize_namespace("test-user") == "test-user"
        assert sanitize_namespace("valid123") == "valid123"

    def test_sanitize_namespace_lowercase(self):
        """Test namespace sanitization converts to lowercase."""
        assert sanitize_namespace("TestUser") == "testuser"
        assert sanitize_namespace("UPPERCASE") == "uppercase"

    def test_sanitize_namespace_special_chars(self):
        """Test namespace sanitization replaces special characters."""
        assert sanitize_namespace("test_user") == "test-user"
        assert sanitize_namespace("user@example.com") == "user-example-com"
        assert sanitize_namespace("My.App") == "my-app"

    def test_sanitize_namespace_trailing_special_chars(self):
        """Test namespace sanitization strips trailing hyphens."""
        assert sanitize_namespace("mcp-cyoda_") == "mcp-cyoda"
        assert sanitize_namespace("test-name_") == "test-name"
        assert sanitize_namespace("app_name_") == "app-name"
        assert sanitize_namespace("trailing___") == "trailing"

    def test_sanitize_namespace_leading_special_chars(self):
        """Test namespace sanitization strips leading hyphens."""
        assert sanitize_namespace("_leading") == "leading"
        assert sanitize_namespace("___test") == "test"
        assert sanitize_namespace("_app-name") == "app-name"

    def test_sanitize_namespace_both_ends(self):
        """Test namespace sanitization strips hyphens from both ends."""
        assert sanitize_namespace("_middle_") == "middle"
        assert sanitize_namespace("___test___") == "test"
        assert sanitize_namespace("_app-name_") == "app-name"

    def test_sanitize_namespace_empty(self):
        """Test namespace sanitization handles empty string."""
        assert sanitize_namespace("") == ""

    def test_sanitize_namespace_only_special_chars(self):
        """Test namespace sanitization handles string with only special chars."""
        assert sanitize_namespace("___") == ""
        assert sanitize_namespace("...") == ""


class TestSanitizeKeyspace:
    """Test sanitize_keyspace function."""

    def test_sanitize_keyspace_basic(self):
        """Test basic keyspace sanitization."""
        assert sanitize_keyspace("test_user") == "test_user"
        assert sanitize_keyspace("valid123") == "valid123"

    def test_sanitize_keyspace_lowercase(self):
        """Test keyspace sanitization converts to lowercase."""
        assert sanitize_keyspace("TestUser") == "testuser"
        assert sanitize_keyspace("UPPERCASE") == "uppercase"

    def test_sanitize_keyspace_special_chars(self):
        """Test keyspace sanitization replaces special characters."""
        assert sanitize_keyspace("test-user") == "test_user"
        assert sanitize_keyspace("user@example.com") == "user_example_com"
        assert sanitize_keyspace("My.App") == "my_app"

    def test_sanitize_keyspace_trailing_special_chars(self):
        """Test keyspace sanitization strips trailing underscores."""
        assert sanitize_keyspace("mcp-cyoda_") == "mcp_cyoda"
        assert sanitize_keyspace("test-name_") == "test_name"
        assert sanitize_keyspace("app-name-") == "app_name"
        assert sanitize_keyspace("trailing---") == "trailing"

    def test_sanitize_keyspace_leading_special_chars(self):
        """Test keyspace sanitization strips leading underscores."""
        assert sanitize_keyspace("-leading") == "leading"
        assert sanitize_keyspace("---test") == "test"
        assert sanitize_keyspace("-app_name") == "app_name"

    def test_sanitize_keyspace_both_ends(self):
        """Test keyspace sanitization strips underscores from both ends."""
        assert sanitize_keyspace("-middle-") == "middle"
        assert sanitize_keyspace("---test---") == "test"
        assert sanitize_keyspace("-app_name-") == "app_name"

    def test_sanitize_keyspace_empty(self):
        """Test keyspace sanitization handles empty string."""
        assert sanitize_keyspace("") == ""

    def test_sanitize_keyspace_only_special_chars(self):
        """Test keyspace sanitization handles string with only special chars."""
        assert sanitize_keyspace("---") == ""
        assert sanitize_keyspace("...") == ""


class TestRealWorldScenarios:
    """Test real-world scenarios that caused issues."""

    def test_mcp_cyoda_with_trailing_underscore(self):
        """Test the specific case from the error: mcp-cyoda_ -> mcp-cyoda."""
        # This was causing: client-1-05e11da2107844fc944ee5b872fcb6b6-dev-mcp-cyoda-
        assert sanitize_namespace("mcp-cyoda_") == "mcp-cyoda"
        assert sanitize_keyspace("mcp-cyoda_") == "mcp_cyoda"

    def test_uuid_with_environment_name(self):
        """Test UUID-based user IDs with environment names."""
        user_id = "05e11da2107844fc944ee5b872fcb6b6"
        env_name = "dev"
        app_name = "mcp-cyoda_"

        user_ns = sanitize_namespace(user_id)
        env_ns = sanitize_namespace(env_name)
        app_ns = sanitize_namespace(app_name)

        # Build the namespace as in _build_app_namespaces
        app_namespace = f"client-1-{user_ns}-{env_ns}-{app_ns}"

        # Should not end with hyphen
        assert not app_namespace.endswith("-")
        assert (
            app_namespace == "client-1-05e11da2107844fc944ee5b872fcb6b6-dev-mcp-cyoda"
        )

    def test_namespace_validation_regex(self):
        """Test that sanitized namespaces pass Kubernetes RFC 1123 validation."""
        import re

        # Kubernetes RFC 1123 validation regex
        k8s_label_regex = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

        test_cases = [
            "mcp-cyoda_",
            "app-name-",
            "_leading",
            "___",
            "test_name",
        ]

        for test_input in test_cases:
            sanitized = sanitize_namespace(test_input)
            # Skip empty results (valid for edge cases)
            if sanitized:
                assert k8s_label_regex.match(
                    sanitized
                ), f"'{sanitized}' (from '{test_input}') failed K8s validation"
