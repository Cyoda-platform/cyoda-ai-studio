"""Deployment Monitoring Agent using LoopAgent pattern."""

from __future__ import annotations

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools.exit_loop_tool import exit_loop

from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import check_deployment_and_decide, wait_before_next_check


# Monitoring agent that checks status and decides whether to continue
monitoring_checker = LlmAgent(
    name="deployment_status_checker",
    model=get_model_config(),
    description="Checks deployment status and decides whether to continue monitoring",
    instruction="""You are monitoring a Cyoda environment deployment.

Your job is to:
1. Call check_deployment_and_decide() with the build_id to check the deployment status
2. Parse the response:
   - If it starts with "ESCALATE:", the deployment is done (success or failure) - call escalate() to exit the monitoring loop
   - If it starts with "CONTINUE:", the deployment is still in progress - report the status and let the loop continue
3. Be concise and informative in your status updates

Important:
- ALWAYS call check_deployment_and_decide() first
- If the response starts with "ESCALATE:", you MUST call exit_loop() to exit the monitoring loop
- If the response starts with "CONTINUE:", just report the status - do NOT call exit_loop()
- The build_id will be provided in the conversation context

Example flow:
User: "Monitor build abc123"
You: [Call check_deployment_and_decide(build_id="abc123")]
Response: "CONTINUE:Deployment in progress. State: RUNNING, Status: Building. Will check again in 30 seconds."
You: "Deployment is currently running. Status: Building. I'll check again shortly."

[Loop continues...]

Response: "ESCALATE:Deployment completed successfully! State: COMPLETE, Status: SUCCESS"
You: [Call exit_loop()] "Great news! Your deployment has completed successfully!"
""",
    tools=[check_deployment_and_decide, exit_loop],
    after_agent_callback=accumulate_streaming_response,
)

# Waiter agent that adds delay between checks
monitoring_waiter = LlmAgent(
    name="deployment_status_waiter",
    model=get_model_config(),
    description="Waits between deployment status checks",
    instruction="""You wait between deployment status checks to avoid overwhelming the API.

Your job is simple:
1. Call wait_before_next_check() to wait 30 seconds
2. Confirm that you're ready for the next check

Be brief and friendly.
""",
    tools=[wait_before_next_check],
    after_agent_callback=accumulate_streaming_response,
)

# Loop agent that orchestrates the monitoring process
deployment_monitor = LoopAgent(
    name="deployment_monitor_loop",
    max_iterations=60,  # Max 60 checks = 60 * 30s = 30 minutes
    sub_agents=[
        monitoring_checker,  # Check status and decide
        monitoring_waiter,  # Wait before next check
    ],
)

