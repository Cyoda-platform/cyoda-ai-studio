"""
Comprehensive unit tests for retry_failed_generation tool (task restart).

Tests task restart functionality for:
- Application builds (generate_application)
- Code generation (generate_code_with_cli)
- Different error types (retryable vs permanent)
- Circuit breaker integration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.agents.github.tool_definitions.code_generation.tools.retry_generation_tool import (
    retry_failed_generation,
)
from application.entity.background_task import BackgroundTask


@pytest.fixture
def mock_failed_app_build_retryable():
    """Create a mock failed application build task (retryable error)."""
    task = BackgroundTask(
        technical_id="task-app-build-fail-123",
        user_id="user-456",
        task_type="application_build",
        name="Build Customer App",
        description="Failed due to rate limit",
        status="failed",
        progress=25,
        error="Rate limit exceeded. Please retry later.",
        branch_name="feature/customer-mgmt",
        language="python",
        user_request="Build a customer management system with CRUD operations",
        conversation_id="conv-789",
        repository_path="/tmp/repo",
        repository_type="private",
        metadata={
            "error_type": "TRANSIENT",
            "is_retryable": True,
            "error_description": "API rate limit exceeded",
        },
    )
    return task


@pytest.fixture
def mock_failed_app_build_permanent():
    """Create a mock failed application build task (permanent error)."""
    task = BackgroundTask(
        technical_id="task-app-build-perm-123",
        user_id="user-456",
        task_type="application_build",
        name="Build Failed App",
        description="Failed due to syntax error",
        status="failed",
        progress=35,
        error="Syntax error in generated code",
        branch_name="feature/inventory",
        language="python",
        user_request="Build an inventory management system",
        conversation_id="conv-789",
        repository_path="/tmp/repo",
        repository_type="private",
        metadata={
            "error_type": "PERMANENT",
            "is_retryable": False,
            "error_description": "Generated code has syntax errors - prompt needs adjustment",
        },
    )
    return task


@pytest.fixture
def mock_failed_code_gen_retryable():
    """Create a mock failed code generation task (retryable error)."""
    task = BackgroundTask(
        technical_id="task-code-gen-fail-123",
        user_id="user-456",
        task_type="code_generation",
        name="Generate REST API",
        description="Failed due to network timeout",
        status="failed",
        progress=15,
        error="Network timeout while generating code",
        language="javascript",
        user_request="Create a REST API for user management with authentication",
        conversation_id="conv-789",
        repository_path="/tmp/repo",
        branch_name="feature/api",
        metadata={
            "error_type": "TRANSIENT",
            "is_retryable": True,
            "error_description": "Network connection timeout",
        },
    )
    return task


@pytest.fixture
def mock_failed_code_gen_permanent():
    """Create a mock failed code generation task (permanent error)."""
    task = BackgroundTask(
        technical_id="task-code-gen-perm-123",
        user_id="user-456",
        task_type="code_generation",
        name="Generate Invalid Code",
        description="Failed due to authentication error",
        status="failed",
        progress=5,
        error="Invalid API key",
        language="python",
        user_request="Build a data processing pipeline",
        conversation_id="conv-789",
        metadata={
            "error_type": "PERMANENT",
            "is_retryable": False,
            "error_description": "Authentication failed - invalid or expired API key",
        },
    )
    return task


@pytest.fixture
def mock_running_task():
    """Create a mock running task (cannot retry)."""
    task = BackgroundTask(
        technical_id="task-running-123",
        user_id="user-456",
        task_type="application_build",
        name="Build in Progress",
        description="Currently building",
        status="running",
        progress=60,
        language="python",
        user_request="Build a simple app",
        conversation_id="conv-789",
    )
    return task


class TestRetryApplicationBuild:
    """Tests for restarting application build tasks."""

    @pytest.mark.asyncio
    async def test_retry_failed_app_build_success(
        self, mock_failed_app_build_retryable
    ):
        """Test successful retry of failed application build (retryable error)."""
        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.helpers.get_circuit_breaker"
            ) as mock_cb:
                # Mock the import statement inside retry_failed_generation
                with patch(
                    "application.agents.github.tool_definitions.code_generation.tools.generate_application_tool.generate_application",
                    new_callable=AsyncMock,
                ) as mock_generate:
                    # Setup
                    mock_task_service = AsyncMock()
                    mock_service.return_value = mock_task_service
                    mock_task_service.get_task.return_value = (
                        mock_failed_app_build_retryable
                    )

                    mock_circuit_breaker = MagicMock()
                    mock_cb.return_value = mock_circuit_breaker
                    mock_circuit_breaker.can_execute.return_value = (True, None)

                    mock_generate.return_value = "✅ Successfully started application build. Task ID: task-new-123"

                    # Execute
                    result = await retry_failed_generation("task-app-build-fail-123")

                    # Assert
                    assert "✅ Successfully retried" in result
                    assert "task-app-build-fail-123" in result
                    assert "API rate limit exceeded" in result

                    # Verify generate_application was called with correct params
                    mock_generate.assert_called_once()
                    call_kwargs = mock_generate.call_args[1]
                    assert (
                        call_kwargs["requirements"]
                        == "Build a customer management system with CRUD operations"
                    )
                    assert call_kwargs["language"] == "python"
                    assert call_kwargs["branch_name"] == "feature/customer-mgmt"
                    assert call_kwargs["repository_path"] == "/tmp/repo"

    @pytest.mark.asyncio
    async def test_retry_app_build_permanent_error(
        self, mock_failed_app_build_permanent
    ):
        """Test retry blocked for permanent error (syntax error)."""
        with patch("services.services.get_task_service") as mock_service:
            # Setup
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_task.return_value = mock_failed_app_build_permanent

            # Execute
            result = await retry_failed_generation("task-app-build-perm-123")

            # Assert
            assert "❌ Cannot retry" in result
            assert "PERMANENT" in result
            assert "unlikely to succeed on retry" in result
            assert "syntax" in result.lower() or "generated code" in result.lower()
            assert "Review and clarify your requirements" in result

    @pytest.mark.asyncio
    async def test_retry_app_build_circuit_breaker_open(
        self, mock_failed_app_build_retryable
    ):
        """Test retry blocked when circuit breaker is open."""
        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.retry_generation_tool.get_circuit_breaker"
            ) as mock_cb:
                # Setup
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = (
                    mock_failed_app_build_retryable
                )

                mock_circuit_breaker = MagicMock()
                mock_cb.return_value = mock_circuit_breaker
                mock_circuit_breaker.can_execute.return_value = (
                    False,
                    "Circuit breaker is OPEN: Too many recent failures",
                )

                # Execute
                result = await retry_failed_generation("task-app-build-fail-123")

                # Assert - circuit breaker should block before calling generate
                assert "⚠️ Cannot retry" in result
                assert "circuit breaker" in result.lower()
                assert "open" in result.lower()


class TestRetryCodeGeneration:
    """Tests for restarting code generation tasks."""

    @pytest.mark.asyncio
    async def test_retry_failed_code_gen_success(self, mock_failed_code_gen_retryable):
        """Test successful retry of failed code generation (retryable error)."""
        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.helpers.get_circuit_breaker"
            ) as mock_cb:
                # Mock the import statement inside retry_failed_generation
                with patch(
                    "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.generate_code_with_cli",
                    new_callable=AsyncMock,
                ) as mock_generate:
                    # Setup
                    mock_task_service = AsyncMock()
                    mock_service.return_value = mock_task_service
                    mock_task_service.get_task.return_value = (
                        mock_failed_code_gen_retryable
                    )

                    mock_circuit_breaker = MagicMock()
                    mock_cb.return_value = mock_circuit_breaker
                    mock_circuit_breaker.can_execute.return_value = (True, None)

                    mock_generate.return_value = (
                        "✅ Successfully started code generation. Task ID: task-new-456"
                    )

                    # Execute
                    result = await retry_failed_generation("task-code-gen-fail-123")

                    # Assert
                    assert "✅ Successfully retried" in result
                    assert "task-code-gen-fail-123" in result
                    assert "Network connection timeout" in result

                    # Verify generate_code_with_cli was called with correct params
                    mock_generate.assert_called_once()
                    call_kwargs = mock_generate.call_args[1]
                    assert (
                        call_kwargs["user_request"]
                        == "Create a REST API for user management with authentication"
                    )
                    assert call_kwargs["language"] == "javascript"

    @pytest.mark.asyncio
    async def test_retry_code_gen_permanent_error(self, mock_failed_code_gen_permanent):
        """Test retry blocked for permanent error (authentication error)."""
        with patch("services.services.get_task_service") as mock_service:
            # Setup
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_task.return_value = mock_failed_code_gen_permanent

            # Execute
            result = await retry_failed_generation("task-code-gen-perm-123")

            # Assert
            assert "❌ Cannot retry" in result
            assert "PERMANENT" in result
            assert "Authentication or configuration issue" in result
            assert "Verify API keys" in result

    @pytest.mark.asyncio
    async def test_retry_code_gen_retry_also_fails(
        self, mock_failed_code_gen_retryable
    ):
        """Test retry attempt that also fails."""
        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.helpers.get_circuit_breaker"
            ) as mock_cb:
                # Mock the import statement inside retry_failed_generation
                with patch(
                    "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.generate_code_with_cli",
                    new_callable=AsyncMock,
                ) as mock_generate:
                    # Setup
                    mock_task_service = AsyncMock()
                    mock_service.return_value = mock_task_service
                    mock_task_service.get_task.return_value = (
                        mock_failed_code_gen_retryable
                    )

                    mock_circuit_breaker = MagicMock()
                    mock_cb.return_value = mock_circuit_breaker
                    mock_circuit_breaker.can_execute.return_value = (True, None)

                    # Retry fails with same error
                    mock_generate.return_value = (
                        "ERROR: Network timeout while generating code"
                    )

                    # Execute
                    result = await retry_failed_generation("task-code-gen-fail-123")

                    # Assert
                    assert "❌ Retry failed with same error" in result
                    assert "Network timeout" in result


class TestRetryEdgeCases:
    """Tests for edge cases in retry functionality."""

    @pytest.mark.asyncio
    async def test_retry_task_not_found(self):
        """Test retry when task doesn't exist."""
        with patch("services.services.get_task_service") as mock_service:
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_task.return_value = None

            result = await retry_failed_generation("task-nonexistent")

            assert "ERROR: Task task-nonexistent not found" in result

    @pytest.mark.asyncio
    async def test_retry_task_not_failed(self, mock_running_task):
        """Test retry when task is not in failed state."""
        with patch("services.services.get_task_service") as mock_service:
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_task.return_value = mock_running_task

            result = await retry_failed_generation("task-running-123")

            assert "ERROR: Task task-running-123 is not in failed state" in result
            assert "current status: running" in result
            assert "Only failed tasks can be retried" in result

    @pytest.mark.asyncio
    async def test_retry_task_missing_parameters(self):
        """Test retry when task is missing required parameters."""
        task = BackgroundTask(
            technical_id="task-incomplete-123",
            user_id="user-456",
            task_type="application_build",
            name="Incomplete Task",
            status="failed",
            progress=0,
            error="Some error",
            # Missing: repository_path, branch_name, user_request
            metadata={"error_type": "RETRYABLE", "is_retryable": True},
        )

        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.helpers.get_circuit_breaker"
            ) as mock_cb:
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = task

                mock_circuit_breaker = MagicMock()
                mock_cb.return_value = mock_circuit_breaker
                mock_circuit_breaker.can_execute.return_value = (True, None)

                result = await retry_failed_generation("task-incomplete-123")

                assert "ERROR: Cannot retry" in result
                assert "missing required parameters" in result

    @pytest.mark.asyncio
    async def test_retry_unknown_task_type(self):
        """Test retry with unknown task type."""
        task = BackgroundTask(
            technical_id="task-unknown-123",
            user_id="user-456",
            task_type="unknown_type",
            name="Unknown Task",
            status="failed",
            progress=0,
            error="Some error",
            user_request="Do something",
            repository_path="/tmp/repo",
            branch_name="main",
            metadata={"error_type": "RETRYABLE", "is_retryable": True},
        )

        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.helpers.get_circuit_breaker"
            ) as mock_cb:
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = task

                mock_circuit_breaker = MagicMock()
                mock_cb.return_value = mock_circuit_breaker
                mock_circuit_breaker.can_execute.return_value = (True, None)

                result = await retry_failed_generation("task-unknown-123")

                assert "ERROR: Unknown task type 'unknown_type'" in result
                assert (
                    "Only 'application_build' and 'code_generation' tasks can be retried"
                    in result
                )

    @pytest.mark.asyncio
    async def test_retry_exception_handling(self):
        """Test exception handling during retry."""
        with patch("services.services.get_task_service") as mock_service:
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_task.side_effect = Exception(
                "Database connection error"
            )

            result = await retry_failed_generation("task-error-123")

            assert "ERROR: Failed to retry task" in result
            assert "Database connection error" in result


class TestRetryDifferentErrorTypes:
    """Tests for different error type scenarios."""

    @pytest.mark.asyncio
    async def test_retry_rate_limit_error(self):
        """Test retry for rate limit error (retryable)."""
        task = BackgroundTask(
            technical_id="task-ratelimit-123",
            user_id="user-456",
            task_type="code_generation",
            name="Rate Limited",
            status="failed",
            progress=10,
            error="Rate limit exceeded",
            user_request="Generate code",
            language="python",
            repository_path="/tmp/repo",
            branch_name="feature/test",
            metadata={
                "error_type": "TRANSIENT",
                "is_retryable": True,
                "error_description": "API rate limit exceeded - retry after cooldown",
            },
        )

        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.helpers.get_circuit_breaker"
            ) as mock_cb:
                # Mock the import statement inside retry_failed_generation
                with patch(
                    "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.generate_code_with_cli",
                    new_callable=AsyncMock,
                ) as mock_generate:
                    mock_task_service = AsyncMock()
                    mock_service.return_value = mock_task_service
                    mock_task_service.get_task.return_value = task

                    mock_circuit_breaker = MagicMock()
                    mock_cb.return_value = mock_circuit_breaker
                    mock_circuit_breaker.can_execute.return_value = (True, None)

                    mock_generate.return_value = "✅ Success"

                    result = await retry_failed_generation("task-ratelimit-123")

                    assert "✅ Successfully retried" in result

    @pytest.mark.asyncio
    async def test_retry_compilation_error(self):
        """Test retry blocked for compilation error (permanent)."""
        task = BackgroundTask(
            technical_id="task-compile-123",
            user_id="user-456",
            task_type="application_build",
            name="Compilation Error",
            status="failed",
            progress=40,
            error="Compilation failed",
            user_request="Build app",
            repository_path="/tmp/repo",
            branch_name="main",
            language="python",
            metadata={
                "error_type": "PERMANENT",
                "is_retryable": False,
                "error_description": "Generated code has compilation errors",
            },
        )

        with patch("services.services.get_task_service") as mock_service:
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_task.return_value = task

            result = await retry_failed_generation("task-compile-123")

            assert "❌ Cannot retry" in result
            assert "PERMANENT" in result
            assert "compilation" in result.lower() or "syntax" in result.lower()

    @pytest.mark.asyncio
    async def test_retry_network_timeout(self):
        """Test retry for network timeout (retryable)."""
        task = BackgroundTask(
            technical_id="task-timeout-123",
            user_id="user-456",
            task_type="code_generation",
            name="Network Timeout",
            status="failed",
            progress=5,
            error="Connection timeout",
            user_request="Generate REST API",
            language="javascript",
            repository_path="/tmp/repo",
            branch_name="feature/api",
            metadata={
                "error_type": "TRANSIENT",
                "is_retryable": True,
                "error_description": "Network timeout - connection lost",
            },
        )

        with patch("services.services.get_task_service") as mock_service:
            with patch(
                "application.agents.github.tool_definitions.code_generation.helpers.get_circuit_breaker"
            ) as mock_cb:
                # Mock the import statement inside retry_failed_generation
                with patch(
                    "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.generate_code_with_cli",
                    new_callable=AsyncMock,
                ) as mock_generate:
                    mock_task_service = AsyncMock()
                    mock_service.return_value = mock_task_service
                    mock_task_service.get_task.return_value = task

                    mock_circuit_breaker = MagicMock()
                    mock_cb.return_value = mock_circuit_breaker
                    mock_circuit_breaker.can_execute.return_value = (True, None)

                    mock_generate.return_value = "✅ Code generation started"

                    result = await retry_failed_generation("task-timeout-123")

                    assert "✅ Successfully retried" in result
