"""Core code generation logic shared between application build and incremental code generation.

This module provides a unified implementation for both generate_application and
generate_code_with_cli tools, with configurable behavior through CodeGenerationConfig.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import (
    BUILD_PROCESS_TIMEOUT,
    CLI_PROCESS_TIMEOUT,
    COMMIT_INTERVAL_BUILD,
    COMMIT_INTERVAL_DEFAULT,
    PROGRESS_UPDATE_INTERVAL,
)
from application.agents.github.tool_definitions.common.utils import (
    detect_project_type,
    get_cli_config,
)
from common.config.config import CLI_PROVIDER

from ._application_build_helpers import (
    _build_full_prompt,
    _check_functional_requirements_exist,
    _create_missing_requirements_message,
    _load_build_prompt_template,
    _load_pattern_catalog,
)
from ._cli_common import (
    _check_build_already_started,
    _create_background_task,
    _create_output_log_file,
    _extract_cli_context,
    _rename_output_file_with_pid,
    _start_cli_process,
    _start_monitoring_task,
    _validate_branch_not_protected,
    _validate_cli_invocation_limit,
    _write_prompt_to_tempfile,
)
from ._prompt_loader import load_informational_prompt_template

logger = logging.getLogger(__name__)

# Configuration constants
SUPPORTED_LANGUAGES = ["python", "java"]
AUGMENT_CLI_SUPPORTED_MODEL = "haiku4.5"


@dataclass
class CodeGenerationConfig:
    """Configuration for code generation behavior.

    Attributes:
        mode: Type of generation ("application_build" or "code_generation")
        check_functional_requirements: Whether to validate requirements files exist
        auto_detect_language: Whether to auto-detect language from repository
        prompt_type: Type of prompt template ("build" or "informational")
        include_pattern_catalog: Whether to include pattern catalog in prompt
        output_file_prefix: Prefix for output log file ("build" or "codegen")
        task_type: Background task type identifier
        timeout_seconds: Maximum execution time
        commit_interval: Interval for auto-commits during generation
        create_deployment_hook: Whether to create deployment hook
        check_build_already_started: Whether to check if build already started
    """

    mode: Literal["application_build", "code_generation"]
    check_functional_requirements: bool
    auto_detect_language: bool
    prompt_type: Literal["build", "informational"]
    include_pattern_catalog: bool
    output_file_prefix: str
    task_type: str
    timeout_seconds: int
    commit_interval: int
    create_deployment_hook: bool
    check_build_already_started: bool


# Predefined configurations
APPLICATION_BUILD_CONFIG = CodeGenerationConfig(
    mode="application_build",
    check_functional_requirements=True,
    auto_detect_language=False,
    prompt_type="build",
    include_pattern_catalog=True,
    output_file_prefix="build",
    task_type="application_build",
    timeout_seconds=BUILD_PROCESS_TIMEOUT,
    commit_interval=COMMIT_INTERVAL_BUILD,
    create_deployment_hook=True,
    check_build_already_started=True,
)

CODE_GENERATION_CONFIG = CodeGenerationConfig(
    mode="code_generation",
    check_functional_requirements=False,
    auto_detect_language=True,
    prompt_type="informational",
    include_pattern_catalog=False,
    output_file_prefix="codegen",
    task_type="code_generation",
    timeout_seconds=CLI_PROCESS_TIMEOUT,
    commit_interval=COMMIT_INTERVAL_DEFAULT,
    create_deployment_hook=False,
    check_build_already_started=False,
)


async def _validate_context(
    config: CodeGenerationConfig,
    user_input: str,
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
    tool_context: Optional[ToolContext],
) -> tuple[bool, str, object]:
    """Extract and validate CLI context.

    Args:
        config: Generation configuration
        user_input: User requirements or request
        language: Programming language (optional)
        repository_path: Repository path (optional)
        branch_name: Branch name (optional)
        tool_context: Execution context

    Returns:
        Tuple of (success, error_msg, context)
    """
    # Extract CLI context
    success, error_msg, context = _extract_cli_context(
        user_input, language, repository_path, branch_name, tool_context
    )
    if not success:
        return False, error_msg, None

    # Auto-detect language if enabled
    if config.auto_detect_language and not language:
        project_info = detect_project_type(context.repository_path)
        context.language = project_info["type"]
        logger.info(f"Auto-detected project type: {context.language}")

    # Validate language
    if context.language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(f"'{lang}'" for lang in SUPPORTED_LANGUAGES)
        return (
            False,
            f"ERROR: Unsupported language: {context.language}. Must be one of: {supported}",
            None,
        )

    return True, "", context


async def _validate_preconditions(
    config: CodeGenerationConfig, context
) -> tuple[bool, str]:
    """Validate all preconditions before starting generation.

    Args:
        config: Generation configuration
        context: CLI context

    Returns:
        Tuple of (success, error_message)
    """
    # Check if build already started (optional based on config)
    if config.check_build_already_started:
        already_started, error_msg = await _check_build_already_started(
            context.tool_context
        )
        if already_started:
            return False, error_msg

    # Validate branch is not protected
    is_valid, error_msg = await _validate_branch_not_protected(context.branch_name)
    if not is_valid:
        return False, error_msg

    # Check CLI invocation limit
    is_allowed, error_msg, cli_count = _validate_cli_invocation_limit(
        context.session_id
    )
    if not is_allowed:
        return False, error_msg

    # Validate repository exists
    repo_path = Path(context.repository_path)
    if not repo_path.exists():
        return (
            False,
            f"ERROR: Repository directory does not exist: {context.repository_path}",
        )
    if not (repo_path / ".git").exists():
        return (
            False,
            f"ERROR: Directory exists but is not a git repository: {context.repository_path}",
        )

    logger.info(f"✅ Repository verified at: {context.repository_path}")

    # Check functional requirements if required
    if config.check_functional_requirements:
        has_reqs, file_count, error_msg = _check_functional_requirements_exist(
            context.language, context.repository_path
        )

        if error_msg:
            return False, f"ERROR: {error_msg}"

        if not has_reqs:
            from application.agents.github.tool_definitions.code_generation.helpers._application_build_helpers import (
                _get_requirements_path,
            )

            requirements_path = _get_requirements_path(
                context.language, context.repository_path
            )
            return False, _create_missing_requirements_message(requirements_path)

    return True, ""


async def _prepare_prompt(
    config: CodeGenerationConfig, context, user_input: str
) -> tuple[bool, str, str]:
    """Prepare prompt based on configuration.

    Args:
        config: Generation configuration
        context: CLI context
        user_input: User requirements or request

    Returns:
        Tuple of (success, error_message, prompt_content)
    """
    if config.prompt_type == "build":
        # Load build prompt template
        success, template, error_msg = _load_build_prompt_template(context.language)
        if not success:
            return False, error_msg, ""

        # Load pattern catalog if needed
        pattern_catalog = ""
        if config.include_pattern_catalog:
            pattern_catalog = _load_pattern_catalog(context.language)

        # Build full prompt
        full_prompt = _build_full_prompt(template, pattern_catalog, user_input)
        return True, "", full_prompt

    elif config.prompt_type == "informational":
        # Load informational prompt template
        prompt_template = await load_informational_prompt_template(context.language)
        if prompt_template.startswith("ERROR"):
            return False, prompt_template, ""

        full_prompt = f"{prompt_template}\n\n## User Request:\n{user_input}"
        return True, "", full_prompt

    else:
        return False, f"ERROR: Unknown prompt type: {config.prompt_type}", ""


async def _validate_cli_config(
    config: CodeGenerationConfig, context, user_input: str
) -> tuple[bool, str, Path, str]:
    """Validate CLI configuration.

    Args:
        config: Generation configuration
        context: CLI context
        user_input: User input for logging

    Returns:
        Tuple of (success, error_message, script_path, cli_model)
    """
    # Get CLI configuration
    script_path, cli_model = get_cli_config()

    if not script_path.exists():
        logger.error(f"CLI script not found: {script_path}")
        return False, f"ERROR: CLI script not found at {script_path}", Path(), ""

    provider_name = CLI_PROVIDER.capitalize()

    if config.mode == "application_build":
        logger.info(
            f"Generating {context.language} application with {provider_name} CLI "
            f"in {context.repository_path}"
        )
        logger.info(f"Using model: {cli_model}")
    else:
        logger.info(
            f"🤖 Generating code with {provider_name} CLI in {context.repository_path}"
        )
        logger.info(f"📝 User request: {user_input[:100]}...")
        logger.info(f"🎯 Model: {cli_model}")

    # Validate model for Augment CLI
    if CLI_PROVIDER == "augment" and cli_model != AUGMENT_CLI_SUPPORTED_MODEL:
        logger.error(
            f"Invalid model for Augment CLI: {cli_model}. "
            f"Only {AUGMENT_CLI_SUPPORTED_MODEL} is supported."
        )
        return (
            False,
            f"ERROR: Augment CLI only supports {AUGMENT_CLI_SUPPORTED_MODEL} model. "
            f"Current model: {cli_model}",
            Path(),
            "",
        )

    return True, "", script_path, cli_model


async def _start_process(
    config: CodeGenerationConfig,
    context,
    script_path: Path,
    cli_model: str,
    prompt_file: str,
) -> tuple[bool, str, object, str]:
    """Start CLI process and create output log.

    Args:
        config: Generation configuration
        context: CLI context
        script_path: Path to CLI script
        cli_model: CLI model name
        prompt_file: Path to prompt file

    Returns:
        Tuple of (success, error_msg, process, output_file)
    """
    # Create output log file
    success, error_msg, output_file, output_fd = _create_output_log_file(
        context.branch_name, config.output_file_prefix
    )
    if not success:
        if output_fd:
            os.close(output_fd)
        return False, error_msg, None, ""

    # Start CLI process
    process = await _start_cli_process(
        script_path,
        prompt_file,
        cli_model,
        context.repository_path,
        context.branch_name,
        output_fd,
    )

    # Close file descriptor in parent process
    os.close(output_fd)

    # Rename output file with PID
    output_file = _rename_output_file_with_pid(
        output_file, context.branch_name, process.pid, config.output_file_prefix
    )

    logger.info(f"📋 Output log: {output_file}")

    # Store process PID in context
    if config.mode == "application_build":
        context.tool_context.state["build_process_pid"] = process.pid
    else:
        context.tool_context.state["code_gen_process_pid"] = process.pid

    return True, "", process, output_file


async def _setup_monitoring_and_hooks(
    config: CodeGenerationConfig,
    context,
    process,
    prompt_file: str,
    output_file: str,
    user_input: str,
) -> tuple[bool, str, Optional[str], Optional[dict]]:
    """Setup background monitoring and create hooks.

    Args:
        config: Generation configuration
        context: CLI context
        process: Running CLI process
        prompt_file: Path to prompt file
        output_file: Path to output log file
        user_input: User requirements or request

    Returns:
        Tuple of (success, error_msg, task_id, hook)
    """
    # Create background task
    if config.mode == "application_build":
        task_name = f"Build {context.language} application: {context.branch_name}"
        task_description = (
            f"Building complete {context.language} application: {user_input[:200]}..."
        )
        logger.info(f"🔍 Build requirements: {user_input[:100]}...")
    else:
        task_name = f"Generate code: {user_input[:50]}..."
        task_description = f"Generating code with CLI: {user_input[:200]}..."

    task_id = await _create_background_task(
        context=context,
        task_type=config.task_type,
        task_name=task_name,
        task_description=task_description,
        process_pid=process.pid,
        output_file=output_file,
    )

    # Start monitoring in background
    _start_monitoring_task(
        process=process,
        context=context,
        prompt_file=prompt_file,
        output_file=output_file,
        timeout_seconds=config.timeout_seconds,
        commit_interval=config.commit_interval,
        progress_update_interval=PROGRESS_UPDATE_INTERVAL,
    )

    logger.info(f"🎯 Monitoring started in background for task {task_id}")

    # Hooks removed - UI auto-detects build/deployment operations
    return True, "", task_id, None


def _format_response(
    config: CodeGenerationConfig,
    context,
    task_id: Optional[str],
    hook: Optional[dict],
    user_input: str,
    process_pid: int,
) -> str:
    """Format final response based on mode.

    Args:
        config: Generation configuration
        context: CLI context
        task_id: Background task ID
        hook: Hook data (always None now)
        user_input: User requirements or request
        process_pid: CLI process PID

    Returns:
        Formatted response string
    """
    if config.mode == "application_build":
        return (
            f"✅ Application build started on branch `{context.branch_name}` using {context.language}.\n\n"
            f"The build is running in the background (Task ID: {task_id}). "
            f"You can monitor progress in the Tasks panel."
        )
    else:
        if task_id:
            return (
                f"✅ Code generation started on branch `{context.branch_name}`.\n\n"
                f"Processing your request: {user_input}\n\n"
                f"The generation is running in the background (Task ID: {task_id}). "
                f"You can monitor progress in the Tasks panel."
            )
        return (
            f"✅ Code generation started on branch `{context.branch_name}`.\n\n"
            f"Processing your request: {user_input}"
        )


async def _generate_code_core(
    user_input: str,
    config: CodeGenerationConfig,
    tool_context: Optional[ToolContext] = None,
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    branch_name: Optional[str] = None,
) -> str:
    """Core code generation logic shared between application build and incremental generation.

    This function orchestrates the entire code generation flow with configurable behavior.

    Args:
        user_input: User requirements (for build) or request (for codegen)
        config: Configuration controlling generation behavior
        tool_context: Execution context (auto-injected)
        language: Programming language (optional)
        repository_path: Repository path (optional)
        branch_name: Branch name (optional)

    Returns:
        Status message with task ID or error
    """
    try:
        # Step 1: Validate and extract context
        success, error_msg, context = await _validate_context(
            config, user_input, language, repository_path, branch_name, tool_context
        )
        if not success:
            return error_msg

        # Step 2: Validate preconditions
        success, error_msg = await _validate_preconditions(config, context)
        if not success:
            return error_msg

        # Step 3: Prepare prompt
        success, error_msg, full_prompt = await _prepare_prompt(
            config, context, user_input
        )
        if not success:
            return error_msg

        # Step 4: Validate CLI configuration
        success, error_msg, script_path, cli_model = await _validate_cli_config(
            config, context, user_input
        )
        if not success:
            return error_msg

        # Step 5: Write prompt to temp file
        success, error_msg, prompt_file = _write_prompt_to_tempfile(full_prompt)
        if not success:
            return error_msg

        # Step 6: Start CLI process
        success, error_msg, process, output_file = await _start_process(
            config, context, script_path, cli_model, prompt_file
        )
        if not success:
            return error_msg

        # Step 7: Setup monitoring and hooks
        success, error_msg, task_id, hook = await _setup_monitoring_and_hooks(
            config, context, process, prompt_file, output_file, user_input
        )
        if not success:
            return error_msg

        # Step 8: Format and return response
        return _format_response(config, context, task_id, hook, user_input, process.pid)

    except Exception as e:
        logger.error(f"Error in _generate_code_core: {e}", exc_info=True)
        return f"ERROR: {str(e)}"
