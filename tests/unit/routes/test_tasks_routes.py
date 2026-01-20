"""
Comprehensive unit tests for task routes (cancel, restart).

Tests task cancellation and restart functionality for:
- Application builds (generate_application)
- Code generation (generate_code_with_cli)
- Environment deployments
"""

import json
import os
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from quart import Quart

from application.entity.background_task import BackgroundTask
from application.routes.tasks import tasks_bp


@pytest.fixture
def app():
    """Create test Quart application."""
    app = Quart(__name__)
    app.register_blueprint(tasks_bp, url_prefix="/v1/tasks")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_task_running():
    """Create a mock running task."""
    task = BackgroundTask(
        technical_id="task-running-123",
        user_id="user-456",
        task_type="application_build",
        name="Build Customer App",
        description="Building customer management system",
        status="running",
        progress=45,
        process_pid=12345,
        branch_name="feature/customer-mgmt",
        language="python",
        user_request="Build a customer management system with CRUD operations",
        conversation_id="conv-789",
        repository_path="/tmp/repo",
        repository_type="private",
    )
    return task


@pytest.fixture
def mock_task_pending():
    """Create a mock pending task."""
    task = BackgroundTask(
        technical_id="task-pending-123",
        user_id="user-456",
        task_type="code_generation",
        name="Generate Code",
        description="Generating code with CLI",
        status="pending",
        progress=0,
        language="javascript",
        user_request="Create a REST API for user management",
        conversation_id="conv-789",
    )
    return task


@pytest.fixture
def mock_task_failed():
    """Create a mock failed task."""
    task = BackgroundTask(
        technical_id="task-failed-123",
        user_id="user-456",
        task_type="application_build",
        name="Build Failed App",
        description="Build failed due to syntax error",
        status="failed",
        progress=35,
        error="Syntax error in generated code",
        language="python",
        user_request="Build an inventory system",
        conversation_id="conv-789",
        repository_path="/tmp/repo",
        branch_name="feature/inventory",
        metadata={"error_type": "PERMANENT_ERROR", "is_retryable": False},
    )
    return task


@pytest.fixture
def mock_task_cancelled():
    """Create a mock cancelled task."""
    task = BackgroundTask(
        technical_id="task-cancelled-123",
        user_id="user-456",
        task_type="deploy_env",
        name="Deploy Environment",
        description="Deploying to dev environment",
        status="cancelled",
        progress=20,
        error="Task was cancelled by user request",
        user_request="Deploy customer app to dev environment",
        conversation_id="conv-789",
        namespace="dev-env",
    )
    return task


@pytest.fixture
def mock_task_completed():
    """Create a mock completed task."""
    task = BackgroundTask(
        technical_id="task-completed-123",
        user_id="user-456",
        task_type="application_build",
        name="Build Complete",
        description="Successfully built application",
        status="completed",
        progress=100,
        user_request="Build a simple CRUD app",
        conversation_id="conv-789",
        repository_path="/tmp/repo",
    )
    return task


class TestCancelTask:
    """Tests for DELETE/POST /tasks/<task_id>/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_running_application_build(self, client, mock_task_running):
        """Test cancelling a running application build task."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                with patch("os.kill") as mock_kill:
                    with patch(
                        "application.agents.shared.process_utils._is_process_running"
                    ) as mock_is_running:
                        # Setup
                        mock_auth.return_value = ("user-456", False)
                        mock_task_service = AsyncMock()
                        mock_service.return_value = mock_task_service
                        mock_task_service.get_task.return_value = mock_task_running
                        mock_is_running.return_value = (
                            False  # Process stopped after SIGTERM
                        )

                        cancelled_task = BackgroundTask(**mock_task_running.dict())
                        cancelled_task.status = "cancelled"
                        cancelled_task.error = "Task was cancelled by user request"
                        mock_task_service.get_task.side_effect = [
                            mock_task_running,  # First call: check task
                            cancelled_task,  # Second call: after update
                        ]

                        # Execute
                        response = await client.delete(
                            "/v1/tasks/task-running-123/cancel",
                            headers={"Authorization": "Bearer fake-token"},
                        )

                        # Assert
                        assert response.status_code == 200
                        data = await response.get_json()
                        assert data["message"] == "Task cancelled successfully"
                        assert data["task"]["status"] == "cancelled"
                        assert data["task"]["technical_id"] == "task-running-123"

                        # Verify process was terminated
                        mock_kill.assert_called_with(12345, signal.SIGTERM)

                        # Verify task status was updated
                        mock_task_service.update_task_status.assert_called_once()
                        call_kwargs = mock_task_service.update_task_status.call_args[1]
                        assert call_kwargs["task_id"] == "task-running-123"
                        assert call_kwargs["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_pending_code_generation(self, client, mock_task_pending):
        """Test cancelling a pending code generation task."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                # Setup
                mock_auth.return_value = ("user-456", False)
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = mock_task_pending

                cancelled_task = BackgroundTask(**mock_task_pending.dict())
                cancelled_task.status = "cancelled"
                mock_task_service.get_task.side_effect = [
                    mock_task_pending,
                    cancelled_task,
                ]

                # Execute
                response = await client.delete(
                    "/v1/tasks/task-pending-123/cancel",
                    headers={"Authorization": "Bearer fake-token"},
                )

                # Assert
                assert response.status_code == 200
                data = await response.get_json()
                assert data["task"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_environment_deployment(self, client, mock_task_running):
        """Test cancelling an environment deployment task."""
        # Modify task to be env deployment
        mock_task_running.task_type = "deploy_env"
        mock_task_running.name = "Deploy to Staging"
        mock_task_running.namespace = "staging"

        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                with patch("os.kill"):
                    with patch(
                        "application.agents.shared.process_utils._is_process_running"
                    ) as mock_is_running:
                        mock_auth.return_value = ("user-456", False)
                        mock_task_service = AsyncMock()
                        mock_service.return_value = mock_task_service
                        mock_task_service.get_task.return_value = mock_task_running
                        mock_is_running.return_value = False

                        cancelled_task = BackgroundTask(**mock_task_running.dict())
                        cancelled_task.status = "cancelled"
                        mock_task_service.get_task.side_effect = [
                            mock_task_running,
                            cancelled_task,
                        ]

                        response = await client.delete(
                            "/v1/tasks/task-running-123/cancel",
                            headers={"Authorization": "Bearer fake-token"},
                        )

                        assert response.status_code == 200
                        data = await response.get_json()
                        assert data["task"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_task_sigkill_if_still_running(
        self, client, mock_task_running
    ):
        """Test that SIGKILL is sent if process still running after SIGTERM."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                with patch("os.kill") as mock_kill:
                    with patch(
                        "application.agents.shared.process_utils._is_process_running"
                    ) as mock_is_running:
                        with patch("asyncio.sleep"):
                            mock_auth.return_value = ("user-456", False)
                            mock_task_service = AsyncMock()
                            mock_service.return_value = mock_task_service
                            mock_task_service.get_task.return_value = mock_task_running
                            mock_is_running.return_value = (
                                True  # Still running after SIGTERM
                            )

                            cancelled_task = BackgroundTask(**mock_task_running.dict())
                            cancelled_task.status = "cancelled"
                            mock_task_service.get_task.side_effect = [
                                mock_task_running,
                                cancelled_task,
                            ]

                            response = await client.delete(
                                "/v1/tasks/task-running-123/cancel",
                                headers={"Authorization": "Bearer fake-token"},
                            )

                            assert response.status_code == 200

                            # Verify both signals sent
                            assert mock_kill.call_count == 2
                            calls = mock_kill.call_args_list
                            assert calls[0][0] == (12345, signal.SIGTERM)
                            assert calls[1][0] == (12345, signal.SIGKILL)

    @pytest.mark.asyncio
    async def test_cancel_task_process_already_exited(self, client, mock_task_running):
        """Test cancelling task when process already exited."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                with patch("os.kill") as mock_kill:
                    mock_auth.return_value = ("user-456", False)
                    mock_task_service = AsyncMock()
                    mock_service.return_value = mock_task_service
                    mock_task_service.get_task.return_value = mock_task_running

                    # Simulate ProcessLookupError
                    mock_kill.side_effect = ProcessLookupError()

                    cancelled_task = BackgroundTask(**mock_task_running.dict())
                    cancelled_task.status = "cancelled"
                    mock_task_service.get_task.side_effect = [
                        mock_task_running,
                        cancelled_task,
                    ]

                    response = await client.delete(
                        "/v1/tasks/task-running-123/cancel",
                        headers={"Authorization": "Bearer fake-token"},
                    )

                    # Should still succeed and update status
                    assert response.status_code == 200
                    data = await response.get_json()
                    assert data["task"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, client):
        """Test cancelling non-existent task."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                mock_auth.return_value = ("user-456", False)
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = None

                response = await client.delete(
                    "/v1/tasks/task-nonexistent/cancel",
                    headers={"Authorization": "Bearer fake-token"},
                )

                assert response.status_code == 404
                data = await response.get_json()
                assert "Task not found" in data["error"]

    @pytest.mark.asyncio
    async def test_cancel_task_access_denied(self, client, mock_task_running):
        """Test cancelling another user's task."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                # Different user
                mock_auth.return_value = ("user-999", False)
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = mock_task_running

                response = await client.delete(
                    "/v1/tasks/task-running-123/cancel",
                    headers={"Authorization": "Bearer fake-token"},
                )

                assert response.status_code == 403
                data = await response.get_json()
                assert "Access denied" in data["error"]

    @pytest.mark.asyncio
    async def test_cancel_task_wrong_status_completed(
        self, client, mock_task_completed
    ):
        """Test cancelling already completed task."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                mock_auth.return_value = ("user-456", False)
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = mock_task_completed

                response = await client.delete(
                    "/v1/tasks/task-completed-123/cancel",
                    headers={"Authorization": "Bearer fake-token"},
                )

                assert response.status_code == 400
                data = await response.get_json()
                assert "Cannot cancel task with status 'completed'" in data["error"]

    @pytest.mark.asyncio
    async def test_cancel_task_wrong_status_failed(self, client, mock_task_failed):
        """Test cancelling already failed task."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                mock_auth.return_value = ("user-456", False)
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = mock_task_failed

                response = await client.delete(
                    "/v1/tasks/task-failed-123/cancel",
                    headers={"Authorization": "Bearer fake-token"},
                )

                assert response.status_code == 400
                data = await response.get_json()
                assert "Cannot cancel task with status 'failed'" in data["error"]

    @pytest.mark.asyncio
    async def test_cancel_task_superuser_can_cancel_any_task(
        self, client, mock_task_running
    ):
        """Test superuser can cancel any user's task."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                with patch("os.kill"):
                    with patch(
                        "application.agents.shared.process_utils._is_process_running"
                    ) as mock_is_running:
                        # Superuser (different user ID)
                        mock_auth.return_value = ("admin-user", True)
                        mock_task_service = AsyncMock()
                        mock_service.return_value = mock_task_service
                        mock_task_service.get_task.return_value = mock_task_running
                        mock_is_running.return_value = False

                        cancelled_task = BackgroundTask(**mock_task_running.dict())
                        cancelled_task.status = "cancelled"
                        mock_task_service.get_task.side_effect = [
                            mock_task_running,
                            cancelled_task,
                        ]

                        response = await client.delete(
                            "/v1/tasks/task-running-123/cancel",
                            headers={"Authorization": "Bearer admin-token"},
                        )

                        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_task_no_pid(self, client, mock_task_pending):
        """Test cancelling task with no PID stored."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                mock_auth.return_value = ("user-456", False)
                mock_task_service = AsyncMock()
                mock_service.return_value = mock_task_service
                mock_task_service.get_task.return_value = mock_task_pending

                cancelled_task = BackgroundTask(**mock_task_pending.dict())
                cancelled_task.status = "cancelled"
                mock_task_service.get_task.side_effect = [
                    mock_task_pending,
                    cancelled_task,
                ]

                response = await client.delete(
                    "/v1/tasks/task-pending-123/cancel",
                    headers={"Authorization": "Bearer fake-token"},
                )

                # Should still succeed (no process to kill)
                assert response.status_code == 200
                data = await response.get_json()
                assert data["task"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_via_post_method(self, client, mock_task_running):
        """Test cancelling task using POST instead of DELETE."""
        with patch("application.routes.tasks.get_authenticated_user") as mock_auth:
            with patch("application.routes.tasks.get_task_service") as mock_service:
                with patch("os.kill"):
                    with patch(
                        "application.agents.shared.process_utils._is_process_running"
                    ) as mock_is_running:
                        mock_auth.return_value = ("user-456", False)
                        mock_task_service = AsyncMock()
                        mock_service.return_value = mock_task_service
                        mock_task_service.get_task.return_value = mock_task_running
                        mock_is_running.return_value = False

                        cancelled_task = BackgroundTask(**mock_task_running.dict())
                        cancelled_task.status = "cancelled"
                        mock_task_service.get_task.side_effect = [
                            mock_task_running,
                            cancelled_task,
                        ]

                        # Use POST instead of DELETE
                        response = await client.post(
                            "/v1/tasks/task-running-123/cancel",
                            headers={"Authorization": "Bearer fake-token"},
                        )

                        assert response.status_code == 200
                        data = await response.get_json()
                        assert data["task"]["status"] == "cancelled"
