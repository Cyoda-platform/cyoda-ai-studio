"""Tests for _parse_python_entities method in RepositoryParser."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from application.services.repository_parser import RepositoryParser, EntityInfo


class TestParsePythonEntities:
    """Tests for _parse_python_entities method."""

    @pytest.mark.asyncio
    async def test_parse_python_entities_success(self):
        """Test successful parsing of Python entities."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        # Mock entity directory
        mock_entity_item = MagicMock()
        mock_entity_item.is_directory = True
        mock_entity_item.name = "User"
        mock_entity_item.path = "entities/User"
        
        # Mock version directory
        mock_version_item = MagicMock()
        mock_version_item.is_directory = True
        mock_version_item.name = "version_1"
        mock_version_item.path = "entities/User/version_1"
        
        github_service.contents.list_directory = AsyncMock(side_effect=[
            [mock_entity_item],
            [mock_version_item]
        ])
        
        github_service.contents.file_exists = AsyncMock(return_value=True)
        github_service.contents.get_file_content = AsyncMock(return_value="class User:\n    pass")
        github_service.contents.directory_exists = AsyncMock(return_value=True)
        
        parser._extract_class_name = MagicMock(return_value="User")
        parser._extract_fields = MagicMock(return_value=[{"name": "id", "type": "string"}])
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 1
        assert result[0].name == "User"
        assert result[0].version == 1
        assert result[0].has_workflow is True

    @pytest.mark.asyncio
    async def test_parse_python_entities_no_entities(self):
        """Test parsing when no entities found."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        github_service.contents.list_directory = AsyncMock(return_value=[])
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_parse_python_entities_skip_private_directories(self):
        """Test that private directories (starting with _) are skipped."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        # Mock private entity directory
        mock_private_item = MagicMock()
        mock_private_item.is_directory = True
        mock_private_item.name = "_private"
        
        github_service.contents.list_directory = AsyncMock(return_value=[mock_private_item])
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_parse_python_entities_skip_non_directories(self):
        """Test that non-directory items are skipped."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        # Mock file (not directory)
        mock_file = MagicMock()
        mock_file.is_directory = False
        mock_file.name = "readme.txt"
        
        github_service.contents.list_directory = AsyncMock(return_value=[mock_file])
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_parse_python_entities_skip_invalid_version_format(self):
        """Test that invalid version directory names are skipped."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        # Mock entity directory
        mock_entity_item = MagicMock()
        mock_entity_item.is_directory = True
        mock_entity_item.name = "User"
        mock_entity_item.path = "entities/User"
        
        # Mock invalid version directory
        mock_invalid_version = MagicMock()
        mock_invalid_version.is_directory = True
        mock_invalid_version.name = "invalid_version"
        
        github_service.contents.list_directory = AsyncMock(side_effect=[
            [mock_entity_item],
            [mock_invalid_version]
        ])
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_parse_python_entities_file_not_exists(self):
        """Test when entity file doesn't exist."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        # Mock entity directory
        mock_entity_item = MagicMock()
        mock_entity_item.is_directory = True
        mock_entity_item.name = "User"
        mock_entity_item.path = "entities/User"
        
        # Mock version directory
        mock_version_item = MagicMock()
        mock_version_item.is_directory = True
        mock_version_item.name = "version_1"
        mock_version_item.path = "entities/User/version_1"
        
        github_service.contents.list_directory = AsyncMock(side_effect=[
            [mock_entity_item],
            [mock_version_item]
        ])
        
        github_service.contents.file_exists = AsyncMock(return_value=False)
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_parse_python_entities_multiple_versions(self):
        """Test parsing entity with multiple versions."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        # Mock entity directory
        mock_entity_item = MagicMock()
        mock_entity_item.is_directory = True
        mock_entity_item.name = "User"
        mock_entity_item.path = "entities/User"
        
        # Mock version directories
        mock_version1 = MagicMock()
        mock_version1.is_directory = True
        mock_version1.name = "version_1"
        mock_version1.path = "entities/User/version_1"
        
        mock_version2 = MagicMock()
        mock_version2.is_directory = True
        mock_version2.name = "version_2"
        mock_version2.path = "entities/User/version_2"
        
        github_service.contents.list_directory = AsyncMock(side_effect=[
            [mock_entity_item],
            [mock_version1, mock_version2]
        ])
        
        github_service.contents.file_exists = AsyncMock(return_value=True)
        github_service.contents.get_file_content = AsyncMock(return_value="class User:\n    pass")
        github_service.contents.directory_exists = AsyncMock(return_value=False)
        
        parser._extract_class_name = MagicMock(return_value="User")
        parser._extract_fields = MagicMock(return_value=[])
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 2
        assert result[0].version == 1
        assert result[1].version == 2

    @pytest.mark.asyncio
    async def test_parse_python_entities_exception_handling(self):
        """Test exception handling during parsing."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        github_service.contents.list_directory = AsyncMock(side_effect=Exception("API error"))
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_parse_python_entities_no_workflow(self):
        """Test entity without workflow."""
        github_service = AsyncMock()
        parser = RepositoryParser(github_service)
        
        # Mock entity directory
        mock_entity_item = MagicMock()
        mock_entity_item.is_directory = True
        mock_entity_item.name = "User"
        mock_entity_item.path = "entities/User"
        
        # Mock version directory
        mock_version_item = MagicMock()
        mock_version_item.is_directory = True
        mock_version_item.name = "version_1"
        mock_version_item.path = "entities/User/version_1"
        
        github_service.contents.list_directory = AsyncMock(side_effect=[
            [mock_entity_item],
            [mock_version_item]
        ])
        
        github_service.contents.file_exists = AsyncMock(return_value=True)
        github_service.contents.get_file_content = AsyncMock(return_value="class User:\n    pass")
        github_service.contents.directory_exists = AsyncMock(return_value=False)
        
        parser._extract_class_name = MagicMock(return_value="User")
        parser._extract_fields = MagicMock(return_value=[])
        
        result = await parser._parse_python_entities("test-repo", "main")
        
        assert len(result) == 1
        assert result[0].has_workflow is False

