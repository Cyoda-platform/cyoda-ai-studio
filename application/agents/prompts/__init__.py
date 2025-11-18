"""Template loader utilities for ADK agent prompts.

This module provides utilities for loading and processing agent instruction templates
following the official Google ADK pattern demonstrated in the agent_builder_assistant sample.
"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from google.adk.agents.readonly_context import ReadonlyContext


def load_template(template_name: str) -> str:
    """Load a template file from the prompts directory.

    Args:
        template_name: Name of the template file (without .template extension)

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_file = Path(__file__).parent / f"{template_name}.template"
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_file}")
    return template_file.read_text(encoding="utf-8")


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

    content = load_template(template_name)

    # Resolve nested templates first (before variable substitution)
    template_pattern = r"\{template:([^}]+)\}"

    def replace_nested_template(match):
        nested_template_name = match.group(1)
        return load_template(nested_template_name)

    content = re.sub(template_pattern, replace_nested_template, content)

    # Then apply variable substitution if variables provided
    if variables:
        content = content.format(**variables)

    return content


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
    # Load template without variable substitution yet
    # (we'll do that in instruction_provider with runtime context)
    template_content_raw = load_template(template_name)

    def instruction_provider(context: ReadonlyContext) -> str:
        """Provide instruction with runtime variable substitution.

        Args:
            context: ADK readonly context containing session state

        Returns:
            Instruction string with variables substituted
        """
        # Start with default variables
        variables: Dict[str, Any] = {**default_vars}

        # Extract runtime variables from session state if available
        try:
            session_state = context._invocation_context.session.state

            # Add common runtime variables from session state dictionary
            if "git_branch" in session_state:
                variables["git_branch"] = session_state["git_branch"]
            if "programming_language" in session_state:
                variables["programming_language"] = session_state["programming_language"]
            if "repository_name" in session_state:
                variables["repository_name"] = session_state["repository_name"]
            if "environment" in session_state:
                variables["environment"] = session_state["environment"]
            if "cyoda_version" in session_state:
                variables["cyoda_version"] = session_state["cyoda_version"]
            if "project_type" in session_state:
                variables["project_type"] = session_state["project_type"]
            if "entity_name" in session_state:
                variables["entity_name"] = session_state["entity_name"]

        except (AttributeError, KeyError):
            # Session state not available or doesn't have expected structure
            # Use only default variables
            pass

        # Resolve nested templates and substitute variables
        import re

        # First resolve conditional nested templates
        # Syntax: {template_if:variable_name==value:template_name}
        # Example: {template_if:programming_language==PYTHON:setup_python}
        conditional_pattern = r"\{template_if:([^:]+)==([^:]+):([^}]+)\}"

        def replace_conditional_template(match):
            var_name = match.group(1).strip()
            expected_value = match.group(2).strip()
            nested_template_name = match.group(3).strip()

            # Check if variable matches expected value
            actual_value = str(variables.get(var_name, "")).strip()
            if actual_value == expected_value:
                return load_template(nested_template_name)
            return ""  # Don't inject if condition not met

        template_content = re.sub(
            conditional_pattern, replace_conditional_template, template_content_raw
        )

        # Then resolve unconditional nested templates
        template_pattern = r"\{template:([^}]+)\}"

        def replace_nested_template(match):
            nested_template_name = match.group(1)
            return load_template(nested_template_name)

        template_content = re.sub(
            template_pattern, replace_nested_template, template_content
        )

        # Finally substitute variables
        try:
            return template_content.format(**variables)
        except KeyError as e:
            # Missing required variable - return template with error message
            missing_var = str(e).strip("'")
            return f"{template_content}\n\n[ERROR: Missing required variable: {missing_var}]"
        except (IndexError, ValueError) as e:
            # Unescaped curly braces or format string error
            return f"{template_content}\n\n[ERROR: Template formatting error: {str(e)}. Check for unescaped curly braces in template.]"

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
