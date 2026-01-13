"""API Data Fetcher Subagent for Cyoda Data Agent.

This subagent handles fetching data from external REST APIs like Petstore Swagger.
It can search for API documentation and fetch data from specified endpoints.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import fetch_api_data, search_api_documentation


def _get_instruction() -> str:
    """Load instruction template from subagent's prompts directory."""
    from pathlib import Path

    current_file = Path(__file__).resolve()
    prompts_dir = current_file.parent / "prompts"
    template_file = prompts_dir / "agent.template"

    if template_file.exists():
        return template_file.read_text(encoding="utf-8")
    else:
        # Fallback instruction if template not found
        return """You are an API Data Fetcher agent that helps users fetch data from external REST APIs.

Your capabilities:
1. Fetch data from REST API endpoints (GET, POST, PUT, DELETE, etc.)
2. Search for API documentation using Google Search
3. Handle query parameters, headers, and request bodies
4. Parse and return API responses

When a user asks to fetch data from an API:
1. First, clarify the API endpoint URL if not provided
2. Determine the HTTP method needed
3. Ask for any required parameters, headers, or authentication
4. Fetch the data and return the results

Always validate URLs and handle errors gracefully."""


api_data_fetcher_agent = LlmAgent(
    name="api_data_fetcher_agent",
    model=get_model_config(),
    description=(
        "Fetches data from external REST APIs like Petstore Swagger. Can search "
        "API documentation and retrieve data from specified endpoints."
    ),
    instruction=_get_instruction(),
    tools=[
        fetch_api_data,
        search_api_documentation,
    ],
    after_agent_callback=accumulate_streaming_response,
)
