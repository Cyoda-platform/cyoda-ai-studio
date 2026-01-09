"""Unit tests for OpenAI Tool Adapter."""

import asyncio
from typing import Optional

import pytest
from agents.tool_context import ToolContext

from application.agents.shared.openai_tool_adapter import (
    adapt_adk_tool_to_openai,
    adapt_adk_tools_list,
)

# Test functions with different signatures


async def async_no_params() -> str:
    """Async function with no parameters."""
    return "no_params_result"


async def async_with_params(name: str, age: int) -> str:
    """Async function with parameters."""
    return f"{name} is {age}"


def sync_no_params() -> str:
    """Sync function with no parameters."""
    return "sync_no_params"


def sync_with_params(name: str) -> str:
    """Sync function with parameters."""
    return f"Hello {name}"


class TestAdaptAsyncToolNoParams:
    """Test adapting async functions with no parameters."""

    def test_adapt_async_no_params(self):
        """Test adapting async function with no parameters."""
        adapted = adapt_adk_tool_to_openai(async_no_params)
        assert adapted.name == "async_no_params"
        assert "no parameters" in adapted.description.lower()

    @pytest.mark.asyncio
    async def test_invoke_async_no_params(self):
        """Test invoking adapted async function with no parameters."""
        adapted = adapt_adk_tool_to_openai(async_no_params)

        # Create a mock ToolContext
        ctx = ToolContext(
            context=None, tool_name="test", tool_call_id="1", tool_arguments=""
        )

        # Invoke the tool
        result = await adapted.on_invoke_tool(ctx, "")
        assert result == "no_params_result"


class TestAdaptAsyncToolWithParams:
    """Test adapting async functions with parameters."""

    def test_adapt_async_with_params(self):
        """Test adapting async function with parameters."""
        adapted = adapt_adk_tool_to_openai(async_with_params)
        assert adapted.name == "async_with_params"
        # The wrapper function uses **kwargs, so parameters are wrapped in kwargs
        assert "kwargs" in adapted.params_json_schema.get("properties", {})


class TestAdaptSyncTools:
    """Test adapting sync functions."""

    def test_adapt_sync_no_params(self):
        """Test adapting sync function with no parameters."""
        adapted = adapt_adk_tool_to_openai(sync_no_params)
        assert adapted.name == "sync_no_params"

    @pytest.mark.asyncio
    async def test_invoke_sync_no_params(self):
        """Test invoking adapted sync function with no parameters."""
        adapted = adapt_adk_tool_to_openai(sync_no_params)

        ctx = ToolContext(
            context=None, tool_name="test", tool_call_id="1", tool_arguments=""
        )

        result = await adapted.on_invoke_tool(ctx, "")
        assert result == "sync_no_params"


class TestAdaptGenerateBranchUuid:
    """Test adapting the generate_branch_uuid function specifically."""

    def test_adapt_generate_branch_uuid(self):
        """Test adapting generate_branch_uuid function."""
        from application.agents.shared.repository_tools import generate_branch_uuid

        adapted = adapt_adk_tool_to_openai(generate_branch_uuid)
        assert adapted.name == "generate_branch_uuid"
        assert "UUID" in adapted.description

    @pytest.mark.asyncio
    async def test_invoke_generate_branch_uuid(self):
        """Test invoking adapted generate_branch_uuid function."""
        from application.agents.shared.repository_tools import generate_branch_uuid

        adapted = adapt_adk_tool_to_openai(generate_branch_uuid)

        ctx = ToolContext(
            context=None, tool_name="test", tool_call_id="1", tool_arguments=""
        )

        result = await adapted.on_invoke_tool(ctx, "")
        # Should return a UUID string
        assert len(result) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert result.count("-") == 4


class TestAdaptToolsList:
    """Test adapting a list of tools."""

    def test_adapt_tools_list(self):
        """Test adapting a list of tools."""
        tools = [async_no_params, async_with_params, sync_no_params]
        adapted = adapt_adk_tools_list(tools)

        assert len(adapted) == 3
        assert adapted[0].name == "async_no_params"
        assert adapted[1].name == "async_with_params"
        assert adapted[2].name == "sync_no_params"
