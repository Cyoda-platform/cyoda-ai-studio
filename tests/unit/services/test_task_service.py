"""Comprehensive tests for TaskService.create_task with >=70% coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from application.services.task_service import TaskService
from application.entity.background_task import BackgroundTask


class TestTaskServiceCreateTask:
    """Tests for TaskService.create_task with >=70% coverage."""

    @pytest.fixture
    def mock_entity_service(self):
        """Create mock entity service."""
        return AsyncMock()

    @pytest.fixture
    def task_service(self, mock_entity_service):
        """Create TaskService instance."""
        return TaskService(mock_entity_service)

    @pytest.mark.asyncio
    async def test_create_task_minimal_fields(self, task_service, mock_entity_service):
        """Test with required fields only: user_id, task_type, name."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-001",
            "user_id": "user-1",
            "task_type": "build_app",
            "name": "Build App",
            "description": "",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-1",
            task_type="build_app",
            name="Build App"
        )

        assert result.technical_id == "task-001"
        assert result.user_id == "user-1"
        assert result.task_type == "build_app"
        assert result.status == "pending"
        assert result.progress == 0
        mock_entity_service.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_description(self, task_service, mock_entity_service):
        """Test with description parameter."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-002",
            "user_id": "user-2",
            "task_type": "build",
            "name": "Test",
            "description": "Test description",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-2",
            task_type="build",
            name="Test",
            description="Test description"
        )

        assert result.description == "Test description"
        call_kwargs = mock_entity_service.save.call_args[1]
        assert call_kwargs["entity"]["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_create_task_all_build_fields(self, task_service, mock_entity_service):
        """Test with all optional fields for build task."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-003",
            "user_id": "user-3",
            "task_type": "build_app",
            "name": "Build App",
            "description": "Build description",
            "status": "pending",
            "progress": 0,
            "branch_name": "feature-123",
            "language": "python",
            "user_request": "Build customer system",
            "conversation_id": "conv-123",
            "repository_path": "/tmp/repo",
            "repository_type": "private",
            "repository_url": "https://github.com/test/repo",
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-3",
            task_type="build_app",
            name="Build App",
            description="Build description",
            branch_name="feature-123",
            language="python",
            user_request="Build customer system",
            conversation_id="conv-123",
            repository_path="/tmp/repo",
            repository_type="private",
            repository_url="https://github.com/test/repo"
        )

        assert result.branch_name == "feature-123"
        assert result.language == "python"
        assert result.user_request == "Build customer system"
        assert result.conversation_id == "conv-123"
        assert result.repository_path == "/tmp/repo"
        assert result.repository_type == "private"
        assert result.repository_url == "https://github.com/test/repo"

    @pytest.mark.asyncio
    async def test_create_task_all_deployment_fields(self, task_service, mock_entity_service):
        """Test with all optional fields for deployment task."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-deploy-1",
            "user_id": "user-4",
            "task_type": "environment_deployment",
            "name": "Deploy Env",
            "description": "Deploy to production",
            "status": "pending",
            "progress": 0,
            "conversation_id": "conv-456",
            "build_id": "build-123",
            "namespace": "prod",
            "env_url": "https://app.prod.com",
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-4",
            task_type="environment_deployment",
            name="Deploy Env",
            description="Deploy to production",
            conversation_id="conv-456",
            build_id="build-123",
            namespace="prod",
            env_url="https://app.prod.com"
        )

        assert result.build_id == "build-123"
        assert result.namespace == "prod"
        assert result.env_url == "https://app.prod.com"

    @pytest.mark.asyncio
    async def test_create_task_with_kwargs(self, task_service, mock_entity_service):
        """Test with additional kwargs."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-005",
            "user_id": "user-5",
            "task_type": "custom",
            "name": "Custom Task",
            "description": "",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {"param1": "val1", "param2": "val2"},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-5",
            task_type="custom",
            name="Custom Task",
            param1="val1",
            param2="val2"
        )

        assert result.workflow_cache["param1"] == "val1"
        assert result.workflow_cache["param2"] == "val2"

    @pytest.mark.asyncio
    async def test_create_task_response_with_data_attr(self, task_service, mock_entity_service):
        """Test response with .data attribute."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-006",
            "user_id": "user-6",
            "task_type": "build",
            "name": "Build",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-6",
            task_type="build",
            name="Build"
        )

        assert result.technical_id == "task-006"

    @pytest.mark.asyncio
    async def test_create_task_response_dict(self, task_service, mock_entity_service):
        """Test response as dict (no .data attribute)."""
        mock_response = {
            "technical_id": "task-007",
            "user_id": "user-7",
            "task_type": "build",
            "name": "Build",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-7",
            task_type="build",
            name="Build"
        )

        assert result.technical_id == "task-007"

    @pytest.mark.asyncio
    async def test_create_task_save_params(self, task_service, mock_entity_service):
        """Test entity_service.save parameters."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-008",
            "user_id": "user-8",
            "task_type": "build",
            "name": "Build",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        await task_service.create_task(
            user_id="user-8",
            task_type="build",
            name="Build"
        )

        call_kwargs = mock_entity_service.save.call_args[1]
        assert call_kwargs["entity_class"] == "BackgroundTask"
        assert "entity_version" in call_kwargs

    @pytest.mark.asyncio
    async def test_create_task_logging(self, task_service, mock_entity_service):
        """Test logger is called."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-009",
            "user_id": "user-9",
            "task_type": "build",
            "name": "Build",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        with patch('application.services.task_service.task_operations.logger') as mock_logger:
            await task_service.create_task(
                user_id="user-9",
                task_type="build",
                name="Build"
            )

            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "task-009" in log_msg
            assert "build" in log_msg

    @pytest.mark.asyncio
    async def test_create_task_returns_background_task(self, task_service, mock_entity_service):
        """Test returns BackgroundTask instance."""
        mock_response = MagicMock()
        mock_response.data = {
            "technical_id": "task-010",
            "user_id": "user-10",
            "task_type": "build",
            "name": "Build",
            "status": "pending",
            "progress": 0,
            "workflow_cache": {},
            "progress_messages": []
        }
        mock_entity_service.save.return_value = mock_response

        result = await task_service.create_task(
            user_id="user-10",
            task_type="build",
            name="Build"
        )

        assert isinstance(result, BackgroundTask)

    @pytest.mark.asyncio
    async def test_create_task_exception_propagates(self, task_service, mock_entity_service):
        """Test exceptions propagate."""
        mock_entity_service.save.side_effect = Exception("Service error")

        with pytest.raises(Exception, match="Service error"):
            await task_service.create_task(
                user_id="user-11",
                task_type="build",
                name="Build"
            )

