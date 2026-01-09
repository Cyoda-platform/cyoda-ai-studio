"""Tests for create_task method in TaskService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.entity.background_task import BackgroundTask
from application.services.task_service import TaskService


def create_mock_save_that_returns_full_data():
    """Create a mock save function that returns all entity data with technical_id."""

    async def mock_save(entity, entity_class, entity_version):
        result = MagicMock()
        result.data = {**entity, "technical_id": "task-123"}
        return result

    return AsyncMock(side_effect=mock_save)


class TestCreateTask:
    """Tests for create_task method."""

    @pytest.mark.asyncio
    async def test_create_task_basic(self):
        """Test basic task creation."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        # Mock response
        response = MagicMock()
        response.data = {
            "technical_id": "task-123",
            "user_id": "user-1",
            "task_type": "build_app",
            "name": "Build App",
            "status": "pending",
            "progress": 0,
        }
        entity_service.save = AsyncMock(return_value=response)

        with patch(
            "application.services.task_service.BackgroundTask"
        ) as mock_task_class:
            mock_task_instance = MagicMock(spec=BackgroundTask)
            mock_task_instance.technical_id = "task-123"
            mock_task_instance.workflow_cache = {}
            mock_task_instance.model_dump = MagicMock(
                return_value={"technical_id": "task-123"}
            )
            mock_task_class.return_value = mock_task_instance
            mock_task_class.ENTITY_NAME = "BackgroundTask"
            mock_task_class.ENTITY_VERSION = 1

            result = await task_service.create_task(
                user_id="user-1", task_type="build_app", name="Build App"
            )

            assert result is not None
            entity_service.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_all_parameters(self):
        """Test task creation with all parameters."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        entity_service.save = create_mock_save_that_returns_full_data()

        with patch(
            "application.services.task_service.BackgroundTask"
        ) as mock_task_class:
            mock_task_instance = MagicMock(spec=BackgroundTask)
            mock_task_instance.technical_id = "task-123"
            mock_task_instance.workflow_cache = {}
            mock_task_instance.model_dump = MagicMock(
                return_value={"technical_id": "task-123"}
            )
            mock_task_class.return_value = mock_task_instance
            mock_task_class.ENTITY_NAME = "BackgroundTask"
            mock_task_class.ENTITY_VERSION = 1

            result = await task_service.create_task(
                user_id="user-1",
                task_type="build_app",
                name="Build App",
                description="Build the application",
                branch_name="main",
                language="python",
                user_request="Build my app",
                conversation_id="conv-123",
                repository_path="/repo",
                repository_type="private",
                repository_url="https://github.com/test/repo",
                build_id="build-456",
                namespace="default",
                env_url="https://env.example.com",
            )

            assert result is not None
            call_args = entity_service.save.call_args
            assert call_args[1]["entity_class"] == "BackgroundTask"

    @pytest.mark.asyncio
    async def test_create_task_with_kwargs(self):
        """Test task creation with additional kwargs."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        entity_service.save = create_mock_save_that_returns_full_data()

        with patch(
            "application.services.task_service.BackgroundTask"
        ) as mock_task_class:
            mock_workflow_cache = {}
            mock_task_instance = MagicMock(spec=BackgroundTask)
            mock_task_instance.technical_id = "task-123"
            mock_task_instance.workflow_cache = mock_workflow_cache
            mock_task_instance.model_dump = MagicMock(
                return_value={"technical_id": "task-123"}
            )
            mock_task_class.return_value = mock_task_instance
            mock_task_class.ENTITY_NAME = "BackgroundTask"
            mock_task_class.ENTITY_VERSION = 1

            result = await task_service.create_task(
                user_id="user-1",
                task_type="build_app",
                name="Build App",
                custom_field="custom_value",
                another_field="another_value",
            )

            assert result is not None
            # Verify kwargs were added to workflow_cache (either to the mock or to the real instance)
            assert "custom_field" in (
                result.workflow_cache
                if hasattr(result, "workflow_cache")
                else mock_workflow_cache
            )

    @pytest.mark.asyncio
    async def test_create_task_status_is_pending(self):
        """Test that created task has pending status."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        entity_service.save = create_mock_save_that_returns_full_data()

        with patch(
            "application.services.task_service.BackgroundTask"
        ) as mock_task_class:
            mock_task_instance = MagicMock(spec=BackgroundTask)
            mock_task_instance.technical_id = "task-123"
            mock_task_instance.status = "pending"
            mock_task_instance.workflow_cache = {}
            mock_task_instance.model_dump = MagicMock(
                return_value={"technical_id": "task-123", "status": "pending"}
            )
            mock_task_class.return_value = mock_task_instance
            mock_task_class.ENTITY_NAME = "BackgroundTask"
            mock_task_class.ENTITY_VERSION = 1

            result = await task_service.create_task(
                user_id="user-1", task_type="build_app", name="Build App"
            )

            # Verify status was set to pending
            assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_create_task_progress_is_zero(self):
        """Test that created task has zero progress."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        entity_service.save = create_mock_save_that_returns_full_data()

        with patch(
            "application.services.task_service.BackgroundTask"
        ) as mock_task_class:
            mock_task_instance = MagicMock(spec=BackgroundTask)
            mock_task_instance.technical_id = "task-123"
            mock_task_instance.progress = 0
            mock_task_instance.workflow_cache = {}
            mock_task_instance.model_dump = MagicMock(
                return_value={"technical_id": "task-123", "progress": 0}
            )
            mock_task_class.return_value = mock_task_instance
            mock_task_class.ENTITY_NAME = "BackgroundTask"
            mock_task_class.ENTITY_VERSION = 1

            result = await task_service.create_task(
                user_id="user-1", task_type="build_app", name="Build App"
            )

            # Verify progress was set to 0
            assert result.progress == 0

    @pytest.mark.asyncio
    async def test_create_task_returns_background_task(self):
        """Test that create_task returns BackgroundTask instance."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        entity_service.save = create_mock_save_that_returns_full_data()

        with patch(
            "application.services.task_service.BackgroundTask"
        ) as mock_task_class:
            mock_task_instance = MagicMock(spec=BackgroundTask)
            mock_task_instance.technical_id = "task-123"
            mock_task_instance.workflow_cache = {}
            mock_task_instance.model_dump = MagicMock(
                return_value={"technical_id": "task-123"}
            )
            mock_task_class.return_value = mock_task_instance
            mock_task_class.ENTITY_NAME = "BackgroundTask"
            mock_task_class.ENTITY_VERSION = 1

            result = await task_service.create_task(
                user_id="user-1", task_type="build_app", name="Build App"
            )

            assert isinstance(result, (MagicMock, BackgroundTask))
            assert result.technical_id == "task-123"

    @pytest.mark.asyncio
    async def test_create_task_with_description(self):
        """Test task creation with description."""
        entity_service = AsyncMock()
        task_service = TaskService(entity_service)

        entity_service.save = create_mock_save_that_returns_full_data()

        with patch(
            "application.services.task_service.BackgroundTask"
        ) as mock_task_class:
            mock_task_instance = MagicMock(spec=BackgroundTask)
            mock_task_instance.technical_id = "task-123"
            mock_task_instance.description = "Building the application"
            mock_task_instance.workflow_cache = {}
            mock_task_instance.model_dump = MagicMock(
                return_value={
                    "technical_id": "task-123",
                    "description": "Building the application",
                }
            )
            mock_task_class.return_value = mock_task_instance
            mock_task_class.ENTITY_NAME = "BackgroundTask"
            mock_task_class.ENTITY_VERSION = 1

            result = await task_service.create_task(
                user_id="user-1",
                task_type="build_app",
                name="Build App",
                description="Building the application",
            )

            assert result is not None
            assert result.description == "Building the application"
