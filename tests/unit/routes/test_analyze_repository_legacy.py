"""Tests for analyze_repository_legacy endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.routes.repository_endpoints.analyze import analyze_repository_legacy
from application.routes.repository_endpoints.models import AnalyzeRepositoryRequest


class TestAnalyzeRepositoryLegacy:
    """Tests for analyze_repository_legacy function."""

    @pytest.mark.asyncio
    async def test_analyze_repository_with_installation_id(self):
        """Test analyzing repository with installation ID."""
        request = AnalyzeRepositoryRequest(
            owner="test-owner",
            repository_name="test-repo",
            branch="main",
            installation_id=123,
        )

        mock_github_service = AsyncMock()
        mock_parser = AsyncMock()

        # Mock repository structure
        mock_structure = MagicMock()
        mock_structure.repository_name = "test-repo"
        mock_structure.branch = "main"
        mock_structure.app_type = "python"
        mock_structure.entities = []
        mock_structure.workflows = []
        mock_structure.requirements = []

        mock_parser.parse_repository = AsyncMock(return_value=mock_structure)

        with patch(
            "application.routes.repository_endpoints.analyze.get_github_service_for_private_repo",
            return_value=mock_github_service,
        ):
            with patch(
                "application.routes.repository_endpoints.analyze.RepositoryParser",
                return_value=mock_parser,
            ):
                with patch(
                    "application.routes.repository_endpoints.analyze.APIResponse.success",
                    return_value={"success": True},
                ):
                    result = await analyze_repository_legacy(request)

                    assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_repository_without_installation_id(self):
        """Test analyzing public repository without installation ID."""
        request = AnalyzeRepositoryRequest(
            owner="test-owner", repository_name="test-repo", branch="main"
        )

        mock_github_service = AsyncMock()
        mock_parser = AsyncMock()

        # Mock repository structure
        mock_structure = MagicMock()
        mock_structure.repository_name = "test-repo"
        mock_structure.branch = "main"
        mock_structure.app_type = "python"
        mock_structure.entities = []
        mock_structure.workflows = []
        mock_structure.requirements = []

        mock_parser.parse_repository = AsyncMock(return_value=mock_structure)

        with patch(
            "application.routes.repository_endpoints.analyze.get_github_service_for_public_repo",
            return_value=mock_github_service,
        ):
            with patch(
                "application.routes.repository_endpoints.analyze.RepositoryParser",
                return_value=mock_parser,
            ):
                with patch(
                    "application.routes.repository_endpoints.analyze.APIResponse.success",
                    return_value={"success": True},
                ):
                    result = await analyze_repository_legacy(request)

                    assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_repository_with_requirements(self):
        """Test analyzing repository with requirements files."""
        request = AnalyzeRepositoryRequest(
            owner="test-owner", repository_name="test-repo", branch="main"
        )

        mock_github_service = AsyncMock()
        mock_parser = AsyncMock()

        # Mock requirement
        mock_requirement = MagicMock()
        mock_requirement.file_name = "requirements.txt"
        mock_requirement.file_path = "requirements.txt"

        # Mock repository structure
        mock_structure = MagicMock()
        mock_structure.repository_name = "test-repo"
        mock_structure.branch = "main"
        mock_structure.app_type = "python"
        mock_structure.entities = []
        mock_structure.workflows = []
        mock_structure.requirements = [mock_requirement]

        mock_parser.parse_repository = AsyncMock(return_value=mock_structure)
        mock_github_service.contents.get_file_content = AsyncMock(
            return_value="flask==2.0.0"
        )

        with patch(
            "application.routes.repository_endpoints.analyze.get_github_service_for_public_repo",
            return_value=mock_github_service,
        ):
            with patch(
                "application.routes.repository_endpoints.analyze.RepositoryParser",
                return_value=mock_parser,
            ):
                with patch(
                    "application.routes.repository_endpoints.analyze.APIResponse.success",
                    return_value={"success": True},
                ):
                    result = await analyze_repository_legacy(request)

                    assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_repository_requirement_fetch_error(self):
        """Test handling error when fetching requirement content."""
        request = AnalyzeRepositoryRequest(
            owner="test-owner", repository_name="test-repo", branch="main"
        )

        mock_github_service = AsyncMock()
        mock_parser = AsyncMock()

        # Mock requirement
        mock_requirement = MagicMock()
        mock_requirement.file_name = "requirements.txt"
        mock_requirement.file_path = "requirements.txt"

        # Mock repository structure
        mock_structure = MagicMock()
        mock_structure.repository_name = "test-repo"
        mock_structure.branch = "main"
        mock_structure.app_type = "python"
        mock_structure.entities = []
        mock_structure.workflows = []
        mock_structure.requirements = [mock_requirement]

        mock_parser.parse_repository = AsyncMock(return_value=mock_structure)
        mock_github_service.contents.get_file_content = AsyncMock(
            side_effect=Exception("File not found")
        )

        with patch(
            "application.routes.repository_endpoints.analyze.get_github_service_for_public_repo",
            return_value=mock_github_service,
        ):
            with patch(
                "application.routes.repository_endpoints.analyze.RepositoryParser",
                return_value=mock_parser,
            ):
                with patch(
                    "application.routes.repository_endpoints.analyze.APIResponse.success",
                    return_value={"success": True},
                ):
                    result = await analyze_repository_legacy(request)

                    assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_repository_with_entities_and_workflows(self):
        """Test analyzing repository with entities and workflows."""
        request = AnalyzeRepositoryRequest(
            owner="test-owner", repository_name="test-repo", branch="main"
        )

        mock_github_service = AsyncMock()
        mock_parser = AsyncMock()

        # Mock entity
        mock_entity = MagicMock()
        mock_entity.name = "User"
        mock_entity.version = "1.0"
        mock_entity.file_path = "models/user.py"
        mock_entity.class_name = "User"
        mock_entity.fields = [
            {"name": "id", "type": "string"},
            {"name": "name", "type": "string"},
        ]
        mock_entity.has_workflow = True

        # Mock workflow
        mock_workflow = MagicMock()
        mock_workflow.workflow_file = "user_workflow.json"
        mock_workflow.entity_name = "User"
        mock_workflow.file_path = "workflows/user_workflow.json"

        # Mock repository structure
        mock_structure = MagicMock()
        mock_structure.repository_name = "test-repo"
        mock_structure.branch = "main"
        mock_structure.app_type = "python"
        mock_structure.entities = [mock_entity]
        mock_structure.workflows = [mock_workflow]
        mock_structure.requirements = []

        mock_parser.parse_repository = AsyncMock(return_value=mock_structure)

        with patch(
            "application.routes.repository_endpoints.analyze.get_github_service_for_public_repo",
            return_value=mock_github_service,
        ):
            with patch(
                "application.routes.repository_endpoints.analyze.RepositoryParser",
                return_value=mock_parser,
            ):
                with patch(
                    "application.routes.repository_endpoints.analyze.APIResponse.success",
                    return_value={"success": True},
                ):
                    result = await analyze_repository_legacy(request)

                    assert result is not None
