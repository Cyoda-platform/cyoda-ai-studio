"""Setup agent for Cyoda project configuration."""

from __future__ import annotations

import os
from typing import Union

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from application.agents.prompts import create_instruction_provider

from .tools import (
    add_application_resource,
    check_project_structure,
    finish_discussion,
    get_build_context,
    get_build_id_from_context,
    get_env_deploy_status,
    get_user_info,
    list_directory_files,
    read_file,
    set_setup_context,
    ui_function_issue_technical_user,
    validate_environment,
    validate_workflow_file,
)


def _get_model_config() -> Union[str, LiteLlm]:
    """Get model configuration based on AI_MODEL environment variable."""
    model_name = os.getenv("AI_MODEL", "gemini-2.0-flash-exp")
    if model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)
    return model_name


root_agent = LlmAgent(
    name="setup_agent",
    model=_get_model_config(),
    description="Cyoda setup and configuration specialist. Expert in project initialization, environment setup, and getting started with Cyoda development.",
    instruction=create_instruction_provider(
        "setup_agent",
        git_branch="<unknown>",
        programming_language="<unknown>",
        repository_name="<unknown>",
        entity_name="<unknown>",
    ),
    tools=[
        # Setup context management
        set_setup_context,
        get_build_context,
        # Environment validation tools
        validate_environment,
        check_project_structure,
        validate_workflow_file,
        # Deployment and context tools
        get_build_id_from_context,
        get_env_deploy_status,
        get_user_info,
        # Credential management
        ui_function_issue_technical_user,
        # File operation tools
        list_directory_files,
        read_file,
        add_application_resource,
        # Workflow management
        finish_discussion,
    ],
)
