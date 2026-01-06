"""Tests for hook_definitions module."""

import pytest
from unittest.mock import MagicMock
from application.agents.shared.hooks.hook_definitions import register_all_hooks
from application.agents.shared.hooks.hook_registry import HookRegistry


class TestRegisterAllHooks:
    """Test register_all_hooks function."""

    def test_register_all_hooks_creates_hooks(self):
        """Test that register_all_hooks registers all hooks."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify hooks were registered
        assert len(registry.list_all()) > 0

    def test_register_all_hooks_canvas_tab_hook(self):
        """Test that open_canvas_tab hook is registered."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify canvas tab hook exists
        assert registry.validate_hook_exists("open_canvas_tab")

    def test_register_all_hooks_code_changes_hook(self):
        """Test that code_changes hook is registered."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify code changes hook exists
        assert registry.validate_hook_exists("code_changes")

    def test_register_all_hooks_cloud_window_hook(self):
        """Test that cloud_window hook is registered."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify cloud window hook exists
        assert registry.validate_hook_exists("cloud_window")

    def test_register_all_hooks_background_task_hook(self):
        """Test that background_task hook is registered."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify background task hook exists
        assert registry.validate_hook_exists("background_task")

    def test_register_all_hooks_issue_technical_user_hook(self):
        """Test that issue_technical_user hook is registered."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify issue technical user hook exists
        assert registry.validate_hook_exists("issue_technical_user")

    def test_register_all_hooks_hook_types(self):
        """Test that hooks have correct types."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify hook types are registered
        hook_types = registry.get_hook_types()
        assert len(hook_types) > 0
        assert "canvas_tab" in hook_types or "code_changes" in hook_types

    def test_register_all_hooks_tool_mapping(self):
        """Test that hooks are mapped to tools."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Verify tools with hooks are registered
        tools_with_hooks = registry.get_tools_with_hooks()
        assert len(tools_with_hooks) > 0

    def test_register_all_hooks_hook_metadata(self):
        """Test that registered hooks have metadata."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Get a hook and verify it has metadata
        all_hooks = registry.list_all()
        assert len(all_hooks) > 0
        
        hook = all_hooks[0]
        assert hook.name is not None
        assert hook.hook_type is not None
        assert hook.description is not None

    def test_register_all_hooks_parameters(self):
        """Test that hooks have parameter specifications."""
        registry = HookRegistry()
        register_all_hooks(registry)
        
        # Get a hook and verify it has parameters
        all_hooks = registry.list_all()
        assert len(all_hooks) > 0
        
        hook = all_hooks[0]
        assert hasattr(hook, 'parameters')

    def test_register_all_hooks_idempotent(self):
        """Test that registering hooks multiple times is safe."""
        registry = HookRegistry()
        
        # Register twice
        register_all_hooks(registry)
        initial_count = len(registry.list_all())
        
        register_all_hooks(registry)
        final_count = len(registry.list_all())
        
        # Count should be same (hooks are overwritten, not duplicated)
        assert initial_count == final_count

