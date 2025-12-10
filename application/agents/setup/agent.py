"""Setup agent for Cyoda project configuration."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.setup.prompts import create_instruction_provider
from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response

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
    issue_technical_user,
    validate_environment,
    validate_workflow_file,
)


root_agent = LlmAgent(
    name="setup_agent",
    model=get_model_config(),
    description="Cyoda setup and configuration specialist. Expert in project initialization, environment setup, and getting started with Cyoda development.",
    instruction=create_instruction_provider(
        "setup_agent",
        git_branch="<unknown>",
        programming_language="<unknown>",
        repository_name="<unknown>",
        entity_name="<unknown>",
        language="<unknown>",
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
        issue_technical_user,
        # File operation tools
        list_directory_files,
        read_file,
        add_application_resource,
        # Workflow management
        finish_discussion,
    ],
    after_agent_callback=accumulate_streaming_response,
)
