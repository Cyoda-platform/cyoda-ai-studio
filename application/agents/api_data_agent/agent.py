"""API Data Agent - Provides guidance on REST API interactions.

Note: This agent currently has limited functionality when using OpenAI models,
as Google ADK's built-in tools (GoogleSearchTool, UrlContextTool) only work
with Google models.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response


def _get_instruction() -> str:
    """Get instruction for API Data Agent."""
    return """You are an API Data Agent that helps users with REST API interactions.

## Your Capabilities

You can provide guidance on:
- REST API best practices
- How to structure API requests
- Understanding API documentation
- Troubleshooting API issues

## Limitations

Currently, when using OpenAI models, this agent does not have tools to:
- Search for API documentation online
- Fetch web content from URLs
- Make direct API calls

For these capabilities, please use external tools or switch to Google models.

## How to Help Users

When a user asks about APIs:

1. **Provide Guidance**: Explain how to interact with the API
2. **Suggest Approaches**: Recommend tools and methods for API testing
3. **Documentation**: Help understand API documentation structure
4. **Best Practices**: Share REST API best practices

## Important Guidelines

- Be helpful and informative about API concepts
- Suggest appropriate tools and approaches
- Clarify what you can and cannot do
- Guide users to appropriate resources
"""


root_agent = LlmAgent(
    name="api_data_agent",
    model=get_model_config(),
    description=(
        "Provides guidance on REST API interactions and best practices. "
        "Note: Limited functionality with OpenAI models."
    ),
    instruction=_get_instruction(),
    tools=[],
    after_agent_callback=accumulate_streaming_response,
)

agent = root_agent
