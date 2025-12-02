"""Environment MCP agent for Cyoda operations using MCP tools."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from application.agents.shared import get_model_config
from application.agents.shared.prompts import create_instruction_provider


# Create MCP toolset that connects to cyoda_mcp server via HTTP
# The cyoda_mcp server will read user credentials from request headers
# Note: This requires the cyoda_mcp server to be running in HTTP mode
cyoda_mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:8002/mcp",  # Connect to cyoda_mcp server
        timeout=60.0,
    ),
)

root_agent = LlmAgent(
    name="environment_mcp_agent",
    model=get_model_config(),
    description="Cyoda environment management specialist using MCP tools. Handles entity operations, search, edge messages, and workflow management through the Cyoda MCP server.",
    instruction=create_instruction_provider(
        "environment_mcp_agent",
        build_id="<unknown>",
        namespace="<unknown>",
        env_url="<unknown>",
    ),
    tools=[cyoda_mcp_toolset],
)
