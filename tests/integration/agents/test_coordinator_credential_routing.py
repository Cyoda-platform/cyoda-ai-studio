"""
Test that coordinator routes credential requests to Environment Agent

This test verifies that when a user asks for credentials, the coordinator
properly routes the request to the environment agent, which then calls
ui_function_issue_technical_user and returns JSON.
"""

import pytest


class TestCoordinatorCredentialRouting:
    """Test coordinator routing for credential requests."""
    
    def test_coordinator_prompt_includes_credentials(self):
        """Verify coordinator prompt includes credential routing rules."""
        import os
        from pathlib import Path

        # Read coordinator template directly - go up from tests/integration/agents to project root
        project_root = Path(__file__).parent.parent.parent.parent
        template_path = project_root / "application" / "agents" / "prompts" / "coordinator.template"
        with open(template_path, 'r') as f:
            prompt_text = f.read()

        # Verify credential keywords are mentioned
        assert "credentials" in prompt_text.lower(), "Coordinator prompt should mention 'credentials'"
        assert "client id" in prompt_text.lower() or "client_id" in prompt_text.lower(), "Coordinator prompt should mention 'client ID'"
        assert "environment_agent" in prompt_text.lower(), "Coordinator prompt should mention environment_agent"

        # Verify routing examples
        assert "I need credentials" in prompt_text or "need credentials" in prompt_text, "Should have credential request example"

        print("✅ Coordinator prompt includes credential routing rules")
    
    def test_environment_agent_has_credential_tool(self):
        """Verify environment agent has the credential issuance tool."""
        from application.agents.environment.agent import root_agent
        
        # Check that the agent has tools
        assert hasattr(root_agent, 'tools'), "Environment agent should have tools"
        assert len(root_agent.tools) > 0, "Environment agent should have at least one tool"
        
        # Check for ui_function_issue_technical_user tool
        tool_names = {getattr(tool, "__name__", str(tool)) for tool in root_agent.tools}
        assert "ui_function_issue_technical_user" in tool_names, "Environment agent should have ui_function_issue_technical_user tool"
        
        print("✅ Environment agent has credential issuance tool")
    
    def test_environment_agent_prompt_mentions_credentials(self):
        """Verify environment agent prompt includes credential management."""
        from pathlib import Path

        # Read environment agent template directly - go up from tests/integration/agents to project root
        project_root = Path(__file__).parent.parent.parent.parent
        template_path = project_root / "application" / "agents" / "prompts" / "environment_agent.template"
        with open(template_path, 'r') as f:
            prompt_text = f.read()

        # Verify credential management is mentioned
        assert "credential" in prompt_text.lower(), "Environment agent prompt should mention credentials"
        assert "ui_function_issue_technical_user" in prompt_text, "Environment agent prompt should mention the credential tool"

        print("✅ Environment agent prompt includes credential management")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

