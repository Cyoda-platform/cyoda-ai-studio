"""Monitoring task management for CLI processes.

This module handles starting background monitoring tasks for CLI processes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .context_extraction import CLIContext

logger = logging.getLogger(__name__)


def _start_monitoring_task(
    process: Any,
    context: CLIContext,
    prompt_file: str,
    output_file: str,
    timeout_seconds: int,
    commit_interval: int,
    progress_update_interval: int,
) -> Any:
    """Start background monitoring task.

    Args:
        process: CLI process
        context: CLI context
        prompt_file: Prompt file path
        output_file: Output file path
        timeout_seconds: Timeout in seconds
        commit_interval: Commit interval
        progress_update_interval: Progress update interval

    Returns:
        Monitoring task
    """
    from application.agents.github.tool_definitions.code_generation.helpers import (
        monitor_cli_process,
    )

    monitoring_task = asyncio.create_task(
        monitor_cli_process(
            process=process,
            repository_path=context.repository_path,
            branch_name=context.branch_name,
            timeout_seconds=timeout_seconds,
            tool_context=context.tool_context,
            prompt_file=prompt_file,
            output_file=output_file,
            commit_interval=commit_interval,
            progress_update_interval=progress_update_interval,
        )
    )

    # Prevent garbage collection
    background_tasks = getattr(asyncio, "_background_tasks", set())
    if not hasattr(asyncio, "_background_tasks"):
        setattr(asyncio, "_background_tasks", background_tasks)
    background_tasks.add(monitoring_task)
    monitoring_task.add_done_callback(background_tasks.discard)

    logger.info("🎯 Monitoring started in background")
    return monitoring_task
