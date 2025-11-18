"""Build Agent for generating Cyoda applications using Augment CLI."""

import os
from typing import Union

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.exit_loop_tool import exit_loop

from application.agents.environment.tools import deploy_cyoda_environment
from application.agents.prompts import create_instruction_provider

from .tools import (
    check_build_status,
    check_existing_branch_configuration,
    check_user_environment_status,
    clone_repository,
    generate_application,
    generate_branch_uuid,
    retrieve_and_save_conversation_files,
    save_files_to_branch,
    set_repository_config,
    wait_before_next_check,
)

# Import setup agent tools to create a lightweight setup agent for build completion
from application.agents.setup.tools import (
    set_setup_context,
    validate_environment,
    check_project_structure,
    validate_workflow_file,
    get_build_id_from_context,
    get_env_deploy_status,
    get_user_info,
    ui_function_issue_technical_user,
    list_directory_files,
    read_file,
    add_application_resource,
    finish_discussion,
)


def _get_model_config() -> Union[str, LiteLlm]:
    """Get model configuration based on AI_MODEL environment variable.

    Returns:
        Model configuration (string for Gemini, LiteLlm instance for others)
    """
    model_name = os.getenv("AI_MODEL", "openai/gpt-4o-mini")

    # If model starts with "openai/" or "anthropic/", use LiteLLM
    if model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)

    # Otherwise, assume it's a Gemini model
    return model_name



# Build checker agent - checks build status and decides whether to continue
build_checker = LlmAgent(
    name="build_checker",
    model=_get_model_config(),
    description="Checks build job status and decides whether to continue monitoring",
    instruction="""You are a build status checker for Cyoda application builds.

Your job is to:
1. Check the current status of a build job
2. Determine if the build is still in progress or has completed
3. Return a decision to either CONTINUE monitoring or ESCALATE to parent agent

When you receive build job information, use the check_build_status tool to check the status.

Based on the response:
- If status contains "CONTINUE:", the build is still running - report the status and let the loop continue
- If status contains "ESCALATE:", the build has completed - call exit_loop() to exit the monitoring loop

Important:
- ALWAYS call check_build_status() first
- If the response starts with "ESCALATE:", you MUST call exit_loop() to exit the monitoring loop
- If the response starts with "CONTINUE:", just report the status - do NOT call exit_loop()
""",
    tools=[check_build_status, exit_loop],
)

# Build waiter agent - waits between status checks
build_waiter = LlmAgent(
    name="build_waiter",
    model=_get_model_config(),
    description="Waits between build status checks",
    instruction="""You are a build monitoring waiter.

Your job is to wait a specified number of seconds before the next build status check.

Use the wait_before_next_check tool with the number of seconds to wait (default: 30 seconds).

After waiting, confirm that you're ready for the next check.
""",
    tools=[wait_before_next_check],
)

# Build monitor loop agent - orchestrates the monitoring loop
build_monitor = LoopAgent(
    name="build_monitor_loop",
    max_iterations=60,  # 60 iterations * 30 seconds = 30 minutes max
    sub_agents=[build_checker, build_waiter],
)

# Setup agent for post-build configuration
# This is a lightweight version of the main setup_agent, used only by build_agent
# to avoid the "multiple parents" issue with Google ADK
post_build_setup = LlmAgent(
    name="post_build_setup",
    model=_get_model_config(),
    description="Guides users through post-build setup after application generation completes",
    instruction=create_instruction_provider(
        "setup_agent",
        git_branch="<unknown>",
        programming_language="<unknown>",
        repository_name="<unknown>",
    ),
    tools=[
        set_setup_context,
        validate_environment,
        check_project_structure,
        validate_workflow_file,
        get_build_id_from_context,
        get_env_deploy_status,
        get_user_info,
        ui_function_issue_technical_user,
        list_directory_files,
        read_file,
        add_application_resource,
        finish_discussion,
    ],
)

# Step 1: Generate branch UUID
branch_generator = LlmAgent(
    name="branch_generator",
    model=_get_model_config(),
    description="Generates a unique branch UUID for the build",
    instruction="""Generate a unique branch UUID by calling generate_branch_uuid().

Report the generated branch UUID.""",
    tools=[generate_branch_uuid],
)

# Step 2: Clone repository
repository_cloner = LlmAgent(
    name="repository_cloner",
    model=_get_model_config(),
    description="Clones the repository to the generated branch",
    instruction="""Clone the repository using the branch UUID from the previous step.

Call clone_repository() with:
- language: from context (python or java)
- branch_name: from the previous step

Report the repository path.""",
    tools=[clone_repository],
)

# Step 3: Check environment status
environment_checker = LlmAgent(
    name="environment_checker",
    model=_get_model_config(),
    description="Checks if Cyoda environment is deployed",
    instruction="""Check the user's Cyoda environment status by calling check_user_environment_status().

Report the status:
- DEPLOYED: Environment is ready
- NOT_DEPLOYED: Environment needs deployment
- NEEDS_LOGIN: User needs to log in""",
    tools=[check_user_environment_status],
)

# Step 4: Deploy environment (conditionally)
environment_deployer = LlmAgent(
    name="environment_deployer",
    model=_get_model_config(),
    description="Deploys Cyoda environment if needed",
    instruction="""Based on the environment status from the previous step:

If status is NOT_DEPLOYED:
- Call deploy_cyoda_environment() with branch_name and user_id from context
- Extract the Task ID from the response (format: "SUCCESS: ... Task ID: <task_id>)")
- Store it in context for later use
- Report deployment started with the task ID

If status is DEPLOYED:
- Report that environment is already deployed, no deployment needed

If status is NEEDS_LOGIN:
- Report that user needs to log in first""",
    tools=[deploy_cyoda_environment],
)

# Step 5: Generate application
application_generator = LlmAgent(
    name="application_generator",
    model=_get_model_config(),
    description="Generates application code using Augment CLI",
    instruction="""Generate the application code by calling generate_application() with the user's requirements from context.

Report that the build has started successfully.""",
    tools=[generate_application],
)

# Sequential build executor - runs all build steps in order
build_executor = SequentialAgent(
    name="build_executor",
    description="Executes build steps sequentially: branch → clone → check env → deploy env → generate app",
    sub_agents=[
        branch_generator,
        repository_cloner,
        environment_checker,
        environment_deployer,
        application_generator,
    ],
)

# Main build agent - handles user interaction and calls tools in sequence
root_agent = LlmAgent(
    name="build_agent",
    model=_get_model_config(),
    description="Generates new Cyoda applications in Java or Python using Augment CLI. Handles repository setup and build execution.",
    instruction=create_instruction_provider("build_agent"),
    tools=[
        check_existing_branch_configuration,
        set_repository_config,
        generate_branch_uuid,
        clone_repository,
        retrieve_and_save_conversation_files,
        save_files_to_branch,
        check_user_environment_status,
        deploy_cyoda_environment,
        generate_application,
    ],
    sub_agents=[build_monitor, post_build_setup],
)
