"""Tests for workflow validation tool."""

import json

import pytest

from application.agents.github.tools import validate_workflow_against_schema


class TestValidateWorkflow:
    """Test workflow validation against schema."""

    @pytest.mark.asyncio
    async def test_valid_workflow_passes_validation(self):
        """Test that a valid workflow passes validation."""
        valid_workflow = {
            "version": "1",
            "name": "Customer",
            "initialState": "initial_state",
            "states": {
                "initial_state": {
                    "transitions": [
                        {
                            "name": "activate",
                            "next": "active",
                            "manual": True,
                        }
                    ]
                },
                "active": {"transitions": []},
            },
        }

        result = await validate_workflow_against_schema(json.dumps(valid_workflow))
        assert "✅" in result
        assert "validation passed" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_required_field_fails(self):
        """Test that missing required fields fail validation."""
        invalid_workflow = {
            "name": "Customer",
            "initialState": "initial_state",
            # Missing "version" and "states"
        }

        result = await validate_workflow_against_schema(json.dumps(invalid_workflow))
        assert "❌" in result
        assert "validation failed" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_json_fails(self):
        """Test that invalid JSON fails validation."""
        invalid_json = "{ invalid json }"

        result = await validate_workflow_against_schema(invalid_json)
        assert "❌" in result
        assert "Invalid JSON" in result
