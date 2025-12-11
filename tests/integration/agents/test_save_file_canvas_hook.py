"""Integration test for save_file_to_repository canvas hook functionality."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path
import tempfile
import shutil
import json

from application.agents.github.tools import save_file_to_repository


class TestSaveFileCanvasHookIntegration:
    """Integration tests for save_file_to_repository with canvas hooks."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_tool_context(self, temp_repo):
        """Create a mock tool context."""
        context = MagicMock()
        context.state = {
            "repository_path": temp_repo,
            "conversation_id": "conv-test-123",
        }
        return context

    @pytest.mark.asyncio
    async def test_entity_file_returns_canvas_hook(self, mock_tool_context):
        """Test that saving an entity file returns a canvas hook."""
        entity_content = {
            "name": "Customer",
            "description": "Customer entity",
            "version": 1,
            "fields": [
                {"name": "id", "type": "string", "format": "uuid"},
                {"name": "name", "type": "string"},
                {"name": "email", "type": "string", "format": "email"},
            ]
        }
        
        file_path = "application/resources/entity/customer/version_1/customer.json"
        
        result = await save_file_to_repository(
            file_path=file_path,
            content=json.dumps(entity_content, indent=2),
            tool_context=mock_tool_context,
        )
        
        # Verify file was saved
        full_path = Path(mock_tool_context.state["repository_path"]) / file_path
        assert full_path.exists()
        saved_content = json.loads(full_path.read_text())
        assert saved_content["name"] == "Customer"
        
        # Verify hook was created
        assert "last_tool_hook" in mock_tool_context.state
        hook = mock_tool_context.state["last_tool_hook"]
        assert hook["type"] == "canvas_tab"
        assert hook["action"] == "open_canvas_tab"
        assert hook["data"]["tab_name"] == "entities"
        assert hook["data"]["conversation_id"] == "conv-test-123"
        
        # Verify response message
        assert "File saved" in result
        assert "Entities" in result

    @pytest.mark.asyncio
    async def test_workflow_file_returns_canvas_hook(self, mock_tool_context):
        """Test that saving a workflow file returns a canvas hook."""
        workflow_content = {
            "name": "CustomerWorkflow",
            "entity_name": "Customer",
            "version": 1,
            "initialState": "created",
            "states": [
                {"name": "created", "type": "initial"},
                {"name": "active", "type": "normal"},
            ]
        }
        
        file_path = "application/resources/workflow/customer/version_1/customer.json"
        
        result = await save_file_to_repository(
            file_path=file_path,
            content=json.dumps(workflow_content, indent=2),
            tool_context=mock_tool_context,
        )
        
        # Verify hook was created for workflows
        hook = mock_tool_context.state["last_tool_hook"]
        assert hook["data"]["tab_name"] == "workflows"
        assert "Workflows" in result

    @pytest.mark.asyncio
    async def test_requirement_file_returns_canvas_hook(self, mock_tool_context):
        """Test that saving a requirement file returns a canvas hook."""
        requirement_content = """# Functional Requirements

## Customer Management
- Create new customers
- Update customer information
- Delete customers
"""
        
        file_path = "application/resources/functional_requirements/customer_requirements.md"
        
        result = await save_file_to_repository(
            file_path=file_path,
            content=requirement_content,
            tool_context=mock_tool_context,
        )
        
        # Verify hook was created for requirements
        hook = mock_tool_context.state["last_tool_hook"]
        assert hook["data"]["tab_name"] == "requirements"
        assert "Requirements" in result

    @pytest.mark.asyncio
    async def test_non_canvas_file_no_hook(self, mock_tool_context):
        """Test that non-canvas files don't create hooks."""
        config_content = '{"debug": true, "port": 8000}'
        file_path = "application/config/settings.json"
        
        result = await save_file_to_repository(
            file_path=file_path,
            content=config_content,
            tool_context=mock_tool_context,
        )
        
        # Verify file was saved
        full_path = Path(mock_tool_context.state["repository_path"]) / file_path
        assert full_path.exists()
        
        # Verify no hook was created
        assert "last_tool_hook" not in mock_tool_context.state
        assert "SUCCESS" in result

