"""Environment Management agent for Cyoda deployment operations."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.monitoring.agent import deployment_monitor
from application.agents.environment.prompts import create_instruction_provider
from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import (
    check_environment_exists,
    deploy_cyoda_environment,
    deploy_user_application,
    get_build_logs,
    get_deployment_status,
    issue_technical_user,
    show_deployment_options,
    list_environments,
    describe_environment,
    get_environment_metrics,
    get_environment_pods,
    delete_environment,
    list_user_apps,
    get_user_app_details,
    scale_user_app,
    restart_user_app,
    update_user_app_image,
    get_user_app_status,
    get_user_app_metrics,
    get_user_app_pods,
    delete_user_app,
    search_logs,
)


root_agent = LlmAgent(
    name="environment_agent",
    model=get_model_config(),
    description="Cyoda environment management specialist. Handles environment provisioning, application deployment, build monitoring, troubleshooting, and credential management.",
    instruction=create_instruction_provider("environment_agent"),
    tools=[
        check_environment_exists,
        deploy_cyoda_environment,
        deploy_user_application,
        get_deployment_status,
        get_build_logs,
        issue_technical_user,
        show_deployment_options,
        list_environments,
        describe_environment,
        get_environment_metrics,
        get_environment_pods,
        delete_environment,
        list_user_apps,
        get_user_app_details,
        scale_user_app,
        restart_user_app,
        update_user_app_image,
        get_user_app_status,
        get_user_app_metrics,
        get_user_app_pods,
        delete_user_app,
        search_logs,
    ],
    sub_agents=[deployment_monitor],
    after_agent_callback=accumulate_streaming_response,
)
