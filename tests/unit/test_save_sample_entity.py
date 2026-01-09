"""
Test to save a sample entity using the entity service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.entity.cyoda_entity import CyodaEntity
from common.service.service import EntityServiceImpl


class TestSaveSampleEntity:
    """Test suite for saving sample entities."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        repo = AsyncMock()
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def entity_service(self, mock_repository):
        """Create an EntityService with mocked repository."""
        EntityServiceImpl._instance = None
        service = EntityServiceImpl.get_instance(repository=mock_repository)
        return service

    @pytest.fixture
    def sample_entity_data(self):
        """Create sample entity data."""
        return {
            "name": "Test Sample Entity",
            "description": "A sample entity for testing",
            "category": "ELECTRONICS",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "state": "created",
        }

    @pytest.mark.asyncio
    async def test_save_sample_entity(
        self, entity_service, mock_repository, sample_entity_data
    ):
        """Test saving a sample entity."""
        # Mock the repository methods
        mock_repository.get_meta = AsyncMock(return_value={"token": "test-token"})
        mock_repository.save = AsyncMock(return_value="test-entity-123")

        # Save the entity
        result = await entity_service.save(
            entity=sample_entity_data,
            entity_class="ExampleEntity",
            entity_version="1",
        )

        # Assertions
        assert result is not None
        assert result.metadata.id == "test-entity-123"
        assert result.data["name"] == "Test Sample Entity"
        assert result.data["category"] == "ELECTRONICS"
        assert result.data["is_active"] is True

        # Verify repository was called
        mock_repository.save.assert_called_once()

    def test_create_cyoda_entity_from_dict(self, sample_entity_data):
        """Test creating a CyodaEntity from dictionary."""
        entity = CyodaEntity.from_dict(sample_entity_data)

        assert entity is not None
        assert entity.state == "created"
        assert entity.entity_id is not None

    def test_cyoda_entity_to_dict(self, sample_entity_data):
        """Test converting CyodaEntity to dictionary."""
        entity = CyodaEntity.from_dict(sample_entity_data)
        entity_dict = entity.to_dict()

        assert entity_dict is not None
        assert "entity_id" in entity_dict
        assert "state" in entity_dict
