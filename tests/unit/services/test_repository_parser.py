"""Tests for RepositoryParser._parse_python_entities with >=70% function coverage."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestParsePythonEntities:
    """Tests for RepositoryParser._parse_python_entities achieving >=70% coverage."""

    @pytest.fixture
    def mock_github_service(self):
        """Create mock GitHub service."""
        service = AsyncMock()
        service.contents = AsyncMock()
        return service

    @pytest.fixture
    def parser(self, mock_github_service):
        """Create RepositoryParser instance."""
        from application.services.repository_parser import RepositoryParser

        return RepositoryParser(mock_github_service)

    @pytest.mark.asyncio
    async def test_parse_python_entities_empty_list(self, parser, mock_github_service):
        """Test when list_directory returns empty list."""
        mock_github_service.contents.list_directory.return_value = []

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []
        mock_github_service.contents.list_directory.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_python_entities_skip_underscore_directory(
        self, parser, mock_github_service
    ):
        """Test that directories starting with underscore are skipped."""
        underscore_dir = MagicMock()
        underscore_dir.is_directory = True
        underscore_dir.name = "_internal"

        mock_github_service.contents.list_directory.return_value = [underscore_dir]

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_skip_files_not_directories(
        self, parser, mock_github_service
    ):
        """Test that files (not directories) are skipped."""
        file_item = MagicMock()
        file_item.is_directory = False
        file_item.name = "config.json"

        mock_github_service.contents.list_directory.return_value = [file_item]

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_empty_versions(
        self, parser, mock_github_service
    ):
        """Test when version directory listing is empty."""
        entity_dir = MagicMock()
        entity_dir.is_directory = True
        entity_dir.name = "customer"
        entity_dir.path = "application/resources/entity/customer"

        # First call returns entity, second call returns empty versions
        mock_github_service.contents.list_directory.side_effect = [[entity_dir], []]

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_skip_non_version_prefix(
        self, parser, mock_github_service
    ):
        """Test that directories not starting with 'version_' are skipped."""
        entity_dir = MagicMock()
        entity_dir.is_directory = True
        entity_dir.name = "product"
        entity_dir.path = "application/resources/entity/product"

        wrong_prefix = MagicMock()
        wrong_prefix.is_directory = True
        wrong_prefix.name = "v1"  # Not "version_"

        mock_github_service.contents.list_directory.side_effect = [
            [entity_dir],
            [wrong_prefix],
        ]

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_skip_version_not_directory(
        self, parser, mock_github_service
    ):
        """Test that version items that are not directories are skipped."""
        entity_dir = MagicMock()
        entity_dir.is_directory = True
        entity_dir.name = "order"
        entity_dir.path = "application/resources/entity/order"

        version_file = MagicMock()
        version_file.is_directory = False
        version_file.name = "version_1"

        mock_github_service.contents.list_directory.side_effect = [
            [entity_dir],
            [version_file],
        ]

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_exception_in_initial_list(
        self, parser, mock_github_service
    ):
        """Test exception handling when listing entity directories fails."""
        mock_github_service.contents.list_directory.side_effect = Exception("API Error")

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_exception_in_version_list(
        self, parser, mock_github_service
    ):
        """Test exception handling when listing version directories fails."""
        entity_dir = MagicMock()
        entity_dir.is_directory = True
        entity_dir.name = "invoice"
        entity_dir.path = "application/resources/entity/invoice"

        # First call succeeds, second raises exception
        mock_github_service.contents.list_directory.side_effect = [
            [entity_dir],
            Exception("Version list error"),
        ]

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_mixed_items(self, parser, mock_github_service):
        """Test with mix of valid directories and invalid items."""
        entity_dir = MagicMock()
        entity_dir.is_directory = True
        entity_dir.name = "customer"
        entity_dir.path = "application/resources/entity/customer"

        underscore_dir = MagicMock()
        underscore_dir.is_directory = True
        underscore_dir.name = "_ignore"

        file_item = MagicMock()
        file_item.is_directory = False
        file_item.name = "readme.txt"

        # Return all items but only customer should be processed
        mock_github_service.contents.list_directory.side_effect = [
            [file_item, underscore_dir, entity_dir],
            [],  # Empty versions for customer
        ]

        result = await parser._parse_python_entities("test-repo", "main")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_python_entities_branch_parameter(
        self, parser, mock_github_service
    ):
        """Test that branch parameter is passed correctly."""
        mock_github_service.contents.list_directory.return_value = []

        await parser._parse_python_entities("test-repo", "develop")

        # Verify branch was passed to list_directory
        call_args = mock_github_service.contents.list_directory.call_args
        assert call_args is not None
        # Branch should be in the call args
        assert "ref" in call_args[1] or len(call_args[0]) > 2

    @pytest.mark.asyncio
    async def test_parse_python_entities_repository_name_parameter(
        self, parser, mock_github_service
    ):
        """Test that repository name is passed correctly."""
        mock_github_service.contents.list_directory.return_value = []

        await parser._parse_python_entities("my-repo", "main")

        # Verify repository name was passed
        call_args = mock_github_service.contents.list_directory.call_args
        assert call_args is not None
        # Repository name should be first argument or in args
        assert "my-repo" in str(call_args)
