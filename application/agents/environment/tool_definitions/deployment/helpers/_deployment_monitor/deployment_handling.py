"""Deployment state handling and main monitoring for deployment progress."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from .status_checks import (
    DeploymentStatus,
    StatusCheckContext,
    _parse_status_result,
    _calculate_progress,
    _build_deployment_status,
)
from .task_updates import (
    _update_task_failed,
    _update_task_completed,
    _update_task_progress,
    _get_task_info,
    FAILURE_MESSAGE_TEMPLATE,
    FAILURE_ERROR_TEMPLATE,
    SUCCESS_MESSAGE_TEMPLATE,
    FAILURE_LOG_TEMPLATE,
    SUCCESS_LOG_TEMPLATE,
    PROGRESS_LOG_TEMPLATE,
)

logger = logging.getLogger(__name__)


async def _handle_failure(
    context: StatusCheckContext, dep_status: DeploymentStatus
) -> None:
    """Handle failed deployment status.

    Args:
        context: Status check context
        dep_status: Deployment status
    """
    await _update_task_failed(
        task_id=context.task_id,
        build_id=context.build_id,
        message=FAILURE_MESSAGE_TEMPLATE.format(status=dep_status.status),
        error=FAILURE_ERROR_TEMPLATE.format(status=dep_status.status, state=dep_status.state),
        namespace=context.namespace,
        env_url=context.env_url,
        state=dep_status.state,
    )
    logger.error(FAILURE_LOG_TEMPLATE.format(build_id=context.build_id, error=dep_status.status))


async def _handle_success(
    context: StatusCheckContext, dep_status: DeploymentStatus
) -> None:
    """Handle successful deployment status.

    Args:
        context: Status check context
        dep_status: Deployment status
    """
    await _update_task_completed(
        task_id=context.task_id,
        build_id=context.build_id,
        message=SUCCESS_MESSAGE_TEMPLATE.format(status=dep_status.status),
        namespace=context.namespace,
        env_url=context.env_url,
    )
    logger.info(SUCCESS_LOG_TEMPLATE.format(build_id=context.build_id))


async def _handle_progress(
    context: StatusCheckContext, dep_status: DeploymentStatus, progress: int
) -> None:
    """Handle deployment in progress status.

    Args:
        context: Status check context
        dep_status: Deployment status
        progress: Progress percentage
    """
    await _update_task_progress(
        task_id=context.task_id,
        build_id=context.build_id,
        state=dep_status.state,
        status=dep_status.status,
        progress=progress,
        check_num=context.check_num,
        namespace=context.namespace,
        env_url=context.env_url,
    )
    logger.info(PROGRESS_LOG_TEMPLATE.format(build_id=context.build_id, progress=progress, state=dep_status.state))


async def _handle_status_check(
    task_id: str,
    build_id: str,
    state: str,
    status: str,
    done_flag: str,
    check_num: int,
    max_checks: int,
    namespace: Optional[str],
    env_url: Optional[str],
) -> bool:
    """Handle a single status check result.

    Args:
        task_id: Task ID
        build_id: Build ID
        state: Deployment state
        status: Deployment status
        done_flag: "DONE" or "CONTINUE"
        check_num: Check number
        max_checks: Maximum checks
        namespace: Deployment namespace
        env_url: Environment URL

    Returns:
        True if monitoring should continue, False if done

    Example:
        >>> should_continue = await _handle_status_check(
        ...     task_id="task-123",
        ...     build_id="build-456",
        ...     state="CREATING",
        ...     status="In Progress",
        ...     done_flag="CONTINUE",
        ...     check_num=5,
        ...     max_checks=20,
        ...     namespace="prod",
        ...     env_url="https://cyoda.ai"
        ... )
    """
    # Step 1: Create status check context
    context = StatusCheckContext(
        task_id=task_id,
        build_id=build_id,
        check_num=check_num,
        max_checks=max_checks,
        namespace=namespace,
        env_url=env_url,
    )

    # Step 2: Build deployment status
    dep_status = _build_deployment_status(state, status, done_flag)

    # Step 3: Calculate progress
    progress = _calculate_progress(check_num, max_checks, done_flag)

    # Step 4: Handle failure
    if dep_status.is_failure:
        await _handle_failure(context, dep_status)
        return False

    # Step 5: Handle success
    if dep_status.is_success:
        await _handle_success(context, dep_status)
        return False

    # Step 6: Handle in-progress status
    await _handle_progress(context, dep_status, progress)
    return True


async def _check_deployment_status_once(
    tool_context: ToolContext,
    build_id: str,
    task_id: str,
    check_num: int,
    max_checks: int,
    namespace: str | None,
    env_url: str | None,
) -> bool:
    """Check deployment status once and handle result.

    Args:
        tool_context: Tool context
        build_id: Cloud manager build ID
        task_id: BackgroundTask technical ID
        check_num: Current check number
        max_checks: Maximum checks
        namespace: Kubernetes namespace
        env_url: Environment URL

    Returns:
        True to continue monitoring, False to stop
    """
    from ...tools.get_deployment_status_tool import get_deployment_status

    try:
        status_result = await get_deployment_status(
            tool_context=tool_context,
            build_id=build_id,
            for_monitoring=True,
        )

        parsed = _parse_status_result(status_result)
        if not parsed:
            return True

        state, status, done_flag = parsed

        should_continue = await _handle_status_check(
            task_id=task_id,
            build_id=build_id,
            state=state,
            status=status,
            done_flag=done_flag,
            check_num=check_num,
            max_checks=max_checks,
            namespace=namespace,
            env_url=env_url,
        )

        return should_continue

    except Exception as e:
        logger.warning(f"Failed to check deployment status (attempt {check_num + 1}): {e}")
        return True


async def monitor_deployment_progress(
        build_id: str,
        task_id: str,
        tool_context: ToolContext,
        check_interval: int = 30,
        max_checks: int = 40,
) -> None:
    """Monitor deployment progress and update BackgroundTask.

    Polls deployment status every 30 seconds and updates the task.

    Args:
        build_id: Cloud manager build ID
        task_id: BackgroundTask technical ID
        tool_context: Tool context for accessing deployment status
        check_interval: Seconds between checks (default: 30)
        max_checks: Maximum checks before timeout (default: 40)
    """
    logger.info(f"Starting deployment monitoring: build_id={build_id}, task_id={task_id}")

    try:
        env_url, namespace = await _get_task_info(task_id)

        for check_num in range(max_checks):
            await asyncio.sleep(check_interval)

            should_continue = await _check_deployment_status_once(
                tool_context=tool_context,
                build_id=build_id,
                task_id=task_id,
                check_num=check_num,
                max_checks=max_checks,
                namespace=namespace,
                env_url=env_url,
            )

            if not should_continue:
                return

        await _update_task_failed(
            task_id=task_id,
            build_id=build_id,
            message=f"Deployment monitoring timeout after {max_checks * check_interval}s",
            error="Monitoring timeout - deployment may still be in progress",
            namespace=namespace,
            env_url=env_url,
            state="TIMEOUT",
        )

    except Exception as e:
        logger.error(f"Error in deployment monitoring: {e}", exc_info=True)
