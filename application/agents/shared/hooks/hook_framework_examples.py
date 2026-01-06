"""Hook Framework Examples - Demonstrates usage patterns.

Shows how to use the hook framework in:
- Tools
- Prompts
- Tests
- Documentation generation
"""

from __future__ import annotations

from common.config.config import CLIENT_GIT_BRANCH


# ==================== Example 1: Using Hook Registry ====================

def example_hook_registry() -> None:
    """Example: Query hook registry."""
    from .hook_registry import get_hook_registry

    registry = get_hook_registry()

    # Get specific hook
    hook = registry.get_hook("open_canvas_tab")
    print(f"Hook: {hook.name}, Type: {hook.hook_type}")

    # Get all hooks for a tool
    tool_hooks = registry.get_hooks_by_tool("environment_agent_tools")
    print(f"Hooks created by environment_agent: {[h.name for h in tool_hooks]}")

    # Get all hooks of a type
    option_hooks = registry.get_hooks_by_type("option_selection")
    print(f"Option selection hooks: {[h.name for h in option_hooks]}")

    # List all active hooks
    all_hooks = registry.list_active()
    print(f"Total active hooks: {len(all_hooks)}")


# ==================== Example 2: Using Hook Factory ====================

def example_hook_factory() -> None:
    """Example: Create and validate hooks."""
    from .hook_factory import get_hook_factory

    factory = get_hook_factory()

    # Create a hook with validation
    try:
        hook = factory.create_hook(
            "open_canvas_tab",
            conversation_id="conv-123",
            tab_name="entities",
            message="View Customer Entity",
        )
        print(f"Created hook: {hook}")
    except Exception as e:
        print(f"Hook creation failed: {e}")

    # Validate parameters without creating
    try:
        factory.validate_parameters(
            "open_canvas_tab",
            {"conversation_id": "conv-123", "tab_name": "entities"},
        )
        print("Parameters are valid")
    except Exception as e:
        print(f"Validation failed: {e}")

    # Get hook documentation
    docs = factory.get_hook_documentation("open_canvas_tab")
    print(docs)


# ==================== Example 3: Decorating Tools ====================

def example_tool_decoration() -> None:
    """Example: Mark tools with hooks they create."""
    from .hook_decorator import (
        creates_hook,
        get_tool_hooks,
    )

    @creates_hook("code_changes")
    @creates_hook("background_task")
    async def deploy_user_application(tool_context, app_name: str) -> str:
        """Deploy a user application."""
        # Tool implementation
        return f"Deploying {app_name}"

    # Query hooks created by tool
    hooks = get_tool_hooks(deploy_user_application)
    print(f"Tool creates hooks: {hooks}")


# ==================== Example 4: Using Prompt Helper ====================

def example_prompt_helper() -> None:
    """Example: Generate hook documentation for prompts."""
    from .prompt_hook_helper import (
        get_prompt_hook_helper,
    )

    helper = get_prompt_hook_helper()

    # Get available hooks
    hooks = helper.get_available_hooks()
    print(f"Available hooks: {hooks}")

    # Get instructions for specific hook
    instructions = helper.get_hook_instructions("open_canvas_tab")
    print(instructions)

    # Get hooks for a tool
    tool_hooks = helper.get_hooks_for_tool("environment_agent_tools")
    print(f"Environment agent creates: {tool_hooks}")

    # Generate reference section for prompt
    reference = helper.generate_hook_reference_section()
    print(reference)

    # Generate complete usage guide
    guide = helper.generate_hook_usage_guide()
    print(guide)


# ==================== Example 5: Tool Implementation ====================

def example_tool_with_hooks() -> None:
    """Example: Tool that creates hooks."""
    from .hook_decorator import creates_hook
    from .hook_factory import get_hook_factory
    from .hook_utils import wrap_response_with_hook

    @creates_hook("code_changes")
    @creates_hook("background_task")
    async def deploy_user_application(
        tool_context, app_name: str, env_name: str
    ) -> str:
        """Deploy a user application and create hooks."""
        factory = get_hook_factory()

        # Create code changes hook
        code_hook = factory.create_hook(
            "code_changes",
            conversation_id="conv-123",
            repository_name="my-repo",
            branch_name=CLIENT_GIT_BRANCH,
            changed_files=["app.py"],
            resource_type="application",
        )

        # Create background task hook
        task_hook = factory.create_hook(
            "background_task",
            task_id="task-123",
            task_type="deploy",
            task_name=f"Deploy {app_name}",
            conversation_id="conv-123",
        )

        # Return with hook
        message = f"✅ Deploying {app_name} to {env_name}"
        return wrap_response_with_hook(message, code_hook)


# ==================== Example 6: Prompt Generation ====================

def example_prompt_generation() -> None:
    """Example: Generate prompt with hook documentation."""
    from .prompt_hook_helper import (
        get_prompt_hook_helper,
    )

    helper = get_prompt_hook_helper()

    prompt = """# My Agent Prompt

You are an expert agent.

"""

    # Add hook reference section
    prompt += helper.generate_hook_reference_section()

    # Add tool-hook mapping
    prompt += "\n"
    prompt += helper.generate_tool_hook_mapping()

    print(prompt)


# ==================== Example 7: Testing Hooks ====================

def example_test_hooks() -> None:
    """Example: Test hook creation and validation."""
    from .hook_factory import (
        HookValidationError,
        get_hook_factory,
    )

    factory = get_hook_factory()

    # Test valid hook creation
    try:
        hook = factory.create_hook(
            "open_canvas_tab",
            conversation_id="conv-123",
            tab_name="entities",
        )
        assert hook["type"] == "canvas_tab"
        print("✓ Valid hook created successfully")
    except HookValidationError as e:
        print(f"✗ Hook creation failed: {e}")

    # Test missing required parameter
    try:
        hook = factory.create_hook(
            "open_canvas_tab",
            conversation_id="conv-123",
            # Missing tab_name
        )
        print("✗ Should have failed with missing parameter")
    except HookValidationError as e:
        print(f"✓ Correctly caught missing parameter: {e}")

    # Test unknown hook
    try:
        hook = factory.create_hook("unknown_hook")
        print("✗ Should have failed with unknown hook")
    except HookValidationError as e:
        print(f"✓ Correctly caught unknown hook: {e}")


if __name__ == "__main__":
    print("Hook Framework Examples\n")
    print("=" * 50)

    print("\n1. Hook Registry")
    example_hook_registry()

    print("\n2. Hook Factory")
    example_hook_factory()

    print("\n3. Tool Decoration")
    example_tool_decoration()

    print("\n4. Prompt Helper")
    example_prompt_helper()

    print("\n5. Tool with Hooks")
    example_tool_with_hooks()

    print("\n6. Prompt Generation")
    example_prompt_generation()

    print("\n7. Testing Hooks")
    example_test_hooks()

