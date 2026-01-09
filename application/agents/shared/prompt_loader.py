"""Template loader utilities for ADK agent prompts.

This module provides utilities for loading and processing agent instruction templates
with support for both per-agent and shared prompts.

Design Philosophy:
- Prompts are colocated with their agents for better cohesion
- Shared prompts live in shared/prompts/ directory
- Loader checks agent-local prompts first, then falls back to shared
"""

import inspect
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from google.adk.agents.readonly_context import ReadonlyContext


def load_template(template_name: str, caller_file: Optional[str] = None) -> str:
    """Load a template file with support for per-agent and shared prompts.

    Search order:
    1. Agent-local prompts directory (e.g., application/agents/github/prompts/)
    2. Shared prompts directory (application/agents/shared/prompts/)
    3. Legacy centralized directory (application/agents/prompts/) - for backward compatibility

    Args:
        template_name: Name of the template file (without .template extension)
        caller_file: Path to the calling file (auto-detected if not provided)

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template file doesn't exist in any location

    Example:
        # From github/agent.py - will check github/prompts/ first
        load_template("github_agent")

        # From shared/repository_tools.py - will check shared/prompts/
        load_template("build_python_instructions")
    """
    # Auto-detect caller's directory if not provided
    if caller_file is None:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_file = frame.f_back.f_code.co_filename

    search_paths = []

    # 1. Check agent-local prompts directory
    if caller_file:
        caller_path = Path(caller_file).resolve()
        # Find the agent directory (e.g., application/agents/github/)
        for parent in caller_path.parents:
            if parent.name == "agents":
                # Caller is in agents/some_agent/ directory
                agent_dir = caller_path.parent
                if agent_dir.parent == parent:
                    local_prompts_dir = agent_dir / "prompts"
                    search_paths.append(local_prompts_dir)
                break

    # 2. Check shared prompts directory
    shared_prompts_dir = Path(__file__).parent / "prompts"
    search_paths.append(shared_prompts_dir)

    # 3. Check legacy centralized directory (backward compatibility)
    legacy_prompts_dir = Path(__file__).parent.parent / "prompts"
    search_paths.append(legacy_prompts_dir)

    # Try each search path
    for prompts_dir in search_paths:
        template_file = prompts_dir / f"{template_name}.template"
        if template_file.exists():
            return template_file.read_text(encoding="utf-8")

    # Template not found in any location
    searched_locations = "\n  - ".join(str(p) for p in search_paths)
    raise FileNotFoundError(
        f"Template '{template_name}.template' not found in any of these locations:\n  - {searched_locations}"
    )


def load_nested_template(template_name: str, **variables: Any) -> str:
    """Load a template and resolve nested template references.

    Supports {template:template_name} syntax for nested template injection.
    Example: {template:setup_java} will inject the setup_java.template content.

    Args:
        template_name: Name of the template file (without .template extension)
        **variables: Variables to substitute in the template

    Returns:
        Template content with nested templates resolved and variables substituted
    """
    import re

    # Get caller's file for proper template resolution
    frame = inspect.currentframe()
    caller_file = None
    if frame and frame.f_back:
        caller_file = frame.f_back.f_code.co_filename

    content = load_template(template_name, caller_file=caller_file)

    # Resolve nested templates first (before variable substitution)
    template_pattern = r"\{template:([^}]+)\}"

    def replace_nested_template(match):
        nested_template_name = match.group(1)
        return load_template(nested_template_name, caller_file=caller_file)

    content = re.sub(template_pattern, replace_nested_template, content)

    # Then apply variable substitution if variables provided
    if variables:
        content = content.format(**variables)

    return content


def _extract_session_variables(context: ReadonlyContext) -> Dict[str, Any]:
    """Extract runtime variables from session state.

    Args:
        context: ADK readonly context

    Returns:
        Dictionary of runtime variables
    """
    variables: Dict[str, Any] = {}

    try:
        session_state = context._invocation_context.session.state

        # Common variable names to extract
        variable_names = [
            "git_branch",
            "programming_language",
            "repository_name",
            "environment",
            "cyoda_version",
            "project_type",
            "entity_name",
            "language",
        ]

        for var_name in variable_names:
            if var_name in session_state:
                variables[var_name] = session_state[var_name]

    except (AttributeError, KeyError):
        pass

    return variables


def _replace_conditional_templates(
    template_content: str,
    variables: Dict[str, Any],
    caller_file: Optional[str],
) -> str:
    """Replace conditional nested templates.

    Args:
        template_content: Template content
        variables: Variable dictionary
        caller_file: Caller file path

    Returns:
        Template with conditional templates replaced
    """
    import re

    conditional_pattern = r"\{template_if:([^:]+)==([^:]+):([^}]+)\}"

    def replace_conditional(match):
        var_name = match.group(1).strip()
        expected_value = match.group(2).strip()
        nested_template_name = match.group(3).strip()

        actual_value = str(variables.get(var_name, "")).strip()
        if actual_value == expected_value:
            return load_template(nested_template_name, caller_file=caller_file)
        return ""

    return re.sub(conditional_pattern, replace_conditional, template_content)


def _replace_nested_templates(
    template_content: str,
    caller_file: Optional[str],
) -> str:
    """Replace unconditional nested templates.

    Args:
        template_content: Template content
        caller_file: Caller file path

    Returns:
        Template with nested templates replaced
    """
    import re

    template_pattern = r"\{template:([^}]+)\}"

    def replace_nested(match):
        nested_template_name = match.group(1)
        return load_template(nested_template_name, caller_file=caller_file)

    return re.sub(template_pattern, replace_nested, template_content)


def _substitute_variables(
    template_content: str,
    variables: Dict[str, Any],
) -> str:
    """Substitute variables in template with error handling.

    Args:
        template_content: Template content
        variables: Variable dictionary

    Returns:
        Template with variables substituted (or error message)
    """
    try:
        return template_content.format(**variables)
    except KeyError as e:
        missing_var = str(e).strip("'")
        return (
            f"{template_content}\n\n[ERROR: Missing required variable: {missing_var}]"
        )
    except (IndexError, ValueError) as e:
        error_msg = (
            f"{template_content}\n\n[ERROR: Template formatting error: {str(e)}. "
            "Check for unescaped curly braces in template.]"
        )
        return error_msg


def create_instruction_provider(
    template_name: str, **default_vars: Any
) -> Callable[[ReadonlyContext], str]:
    """Create a dynamic instruction provider function for ADK agents.

    This follows the official ADK pattern from agent_builder_assistant sample.
    The returned function accepts ReadonlyContext and returns the instruction string
    with variables substituted from both default_vars and runtime context.

    Args:
        template_name: Name of the template file (without .template extension)
        **default_vars: Default variable values to use in template substitution

    Returns:
        Function that accepts ReadonlyContext and returns instruction string

    Example:
        >>> instruction_fn = create_instruction_provider(
        ...     "setup_agent",
        ...     repository_name="mcp-cyoda-quart-app"
        ... )
        >>> # Use in LlmAgent:
        >>> agent = LlmAgent(
        ...     name="setup_agent",
        ...     instruction=instruction_fn,
        ...     ...
        ... )
    """
    # Get caller's file for proper template resolution
    frame = inspect.currentframe()
    caller_file = None
    if frame and frame.f_back:
        caller_file = frame.f_back.f_code.co_filename

    # Load template without variable substitution yet
    template_content_raw = load_template(template_name, caller_file=caller_file)

    def instruction_provider(context: ReadonlyContext) -> str:
        """Provide instruction with runtime variable substitution.

        Args:
            context: ADK readonly context containing session state

        Returns:
            Instruction string with variables substituted
        """
        # Merge default and runtime variables
        variables = {**default_vars}
        runtime_vars = _extract_session_variables(context)
        variables.update(runtime_vars)

        # Replace conditional templates
        template_content = _replace_conditional_templates(
            template_content_raw, variables, caller_file
        )

        # Replace unconditional nested templates
        template_content = _replace_nested_templates(template_content, caller_file)

        # Substitute variables with error handling
        return _substitute_variables(template_content, variables)

    return instruction_provider


def extract_session_variable(
    context: ReadonlyContext, variable_name: str, default: Optional[Any] = None
) -> Any:
    """Extract a variable from session state.

    Args:
        context: ADK readonly context
        variable_name: Name of the variable to extract
        default: Default value if variable not found

    Returns:
        Variable value or default
    """
    try:
        session_state = context._invocation_context.session.state
        return getattr(session_state, variable_name, default)
    except (AttributeError, KeyError):
        return default
