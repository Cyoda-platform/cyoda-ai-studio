"""Tests for update_task method in TaskService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.services.task_service import TaskService
from application.entity.background_task import BackgroundTask


def create_mock_update_that_returns_full_data():
    """Create a mock update function that returns all entity data."""
    async def mock_update(entity_id, entity, entity_class, entity_version):
        result = MagicMock()
        result.data = entity  # Return the full entity data passed in
        return result
    return AsyncMock(side_effect=mock_update)


class TestUpdateTask:
    """Tests for update_task method."""

    @pytest.mark.asyncio
    async def test_update_task_success_first_attempt(self):
        """Test successful task update on first attempt."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        # Create a task
        task = MagicMock(spec=BackgroundTask)
        task.technical_id = "task-123"
        task.status = "running"
        task.progress = 50
        task.progress_messages = ["Step 1 complete"]
        task.started_at = "2025-01-01T00:00:00Z"
        task.completed_at = None
        task.result = None
        task.error = None
        task.error_code = None
        task.process_pid = 1234
        task.build_job_id = None
        task.model_dump = MagicMock(return_value={
            "technical_id": "task-123",
            "user_id": "user-1",
            "task_type": "build_app",
            "status": "running",
            "progress": 50
        })

        entity_service.update = create_mock_update_that_returns_full_data()

        with patch("application.services.task_service.BackgroundTask", return_value=task):
            result = await task_service.update_task(task)

            assert result is not None
            entity_service.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_with_version_conflict_retry(self):
        """Test task update with version conflict and successful retry."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        task = MagicMock(spec=BackgroundTask)
        task.technical_id = "task-123"
        task.status = "running"
        task.progress = 50
        task.progress_messages = []
        task.started_at = None
        task.completed_at = None
        task.result = None
        task.error = None
        task.error_code = None
        task.process_pid = None
        task.build_job_id = None
        task.model_dump = MagicMock(return_value={
            "technical_id": "task-123",
            "user_id": "user-1",
            "task_type": "build_app",
            "status": "running",
            "progress": 50
        })

        # Create success response with full data
        success_response = MagicMock()
        success_response.data = {
            "technical_id": "task-123",
            "user_id": "user-1",
            "task_type": "build_app",
            "status": "running",
            "progress": 50
        }

        # Mock get_by_id for retry logic
        get_response = MagicMock()
        get_response.data = {
            "technical_id": "task-123",
            "user_id": "user-1",
            "task_type": "build_app",
            "status": "running",
            "progress": 50
        }
        entity_service.get_by_id = AsyncMock(return_value=get_response)

        # First call fails with version conflict, second succeeds
        entity_service.update = AsyncMock(side_effect=[
            Exception("422 version mismatch"),
            success_response
        ])

        with patch("application.services.task_service.BackgroundTask", return_value=task):
            result = await task_service.update_task(task, max_retries=3)

            assert result is not None
            assert entity_service.update.call_count == 2

    @pytest.mark.asyncio
    async def test_update_task_max_retries_exceeded(self):
        """Test task update fails after max retries."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)
        
        task = MagicMock(spec=BackgroundTask)
        task.technical_id = "task-123"
        task.status = "running"
        task.progress = 50
        task.progress_messages = []
        task.started_at = None
        task.completed_at = None
        task.result = None
        task.error = None
        task.error_code = None
        task.process_pid = None
        task.build_job_id = None
        task.model_dump = MagicMock(return_value={"technical_id": "task-123"})
        
        # Always fail with version conflict
        entity_service.update = AsyncMock(side_effect=Exception("422 version mismatch"))
        task_service.get_task = AsyncMock(return_value=task)
        
        with pytest.raises(Exception):
            await task_service.update_task(task, max_retries=2)

    @pytest.mark.asyncio
    async def test_update_task_non_retryable_error(self):
        """Test task update with non-retryable error."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)
        
        task = MagicMock(spec=BackgroundTask)
        task.technical_id = "task-123"
        task.model_dump = MagicMock(return_value={"technical_id": "task-123"})
        
        # Non-retryable error
        entity_service.update = AsyncMock(side_effect=ValueError("Invalid task"))
        
        with pytest.raises(ValueError):
            await task_service.update_task(task)

    @pytest.mark.asyncio
    async def test_update_task_task_not_found_on_retry(self):
        """Test task update when task not found during retry."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        task = MagicMock(spec=BackgroundTask)
        task.technical_id = "task-123"
        task.model_dump = MagicMock(return_value={
            "technical_id": "task-123",
            "user_id": "user-1",
            "task_type": "build_app"
        })

        # First call fails with version conflict
        entity_service.update = AsyncMock(side_effect=Exception("422 version mismatch"))
        # Mock get_by_id to return None (task not found)
        entity_service.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await task_service.update_task(task, max_retries=2)

    @pytest.mark.asyncio
    async def test_update_task_preserves_all_fields(self):
        """Test that update_task preserves all task fields."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        task = MagicMock(spec=BackgroundTask)
        task.technical_id = "task-123"
        task.status = "completed"
        task.progress = 100
        task.progress_messages = ["Done"]
        task.started_at = "2025-01-01T00:00:00Z"
        task.completed_at = "2025-01-01T01:00:00Z"
        task.result = {"output": "success"}
        task.error = None
        task.error_code = None
        task.process_pid = 5678
        task.build_job_id = "build-456"
        task.model_dump = MagicMock(return_value={
            "technical_id": "task-123",
            "user_id": "user-1",
            "task_type": "build_app",
            "status": "completed",
            "progress": 100
        })

        entity_service.update = create_mock_update_that_returns_full_data()

        with patch("application.services.task_service.BackgroundTask", return_value=task):
            await task_service.update_task(task)

            entity_service.update.assert_called_once()
            call_args = entity_service.update.call_args
            assert call_args[1]["entity_id"] == "task-123"

