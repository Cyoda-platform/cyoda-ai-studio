"""QA agent for Cyoda platform questions."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.qa.prompts import create_instruction_provider
from application.agents.shared import get_model_config
from application.agents.shared.tools import load_web_page, read_documentation
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import explain_cyoda_pattern, search_cyoda_concepts


root_agent = LlmAgent(
    name="qa_agent",
    model=get_model_config(),
    description=(
        "Cyoda platform expert. Answers questions about architecture, concepts, entity management, "
        "workflows, and troubleshooting."
    ),
    instruction=create_instruction_provider("qa_agent"),
    tools=[
        search_cyoda_concepts,
        explain_cyoda_pattern,
        read_documentation,
        load_web_page,
    ],
    after_agent_callback=accumulate_streaming_response,
)
