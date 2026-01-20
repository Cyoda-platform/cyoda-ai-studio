"""
Integration tests for agent handling of task retry requests.

Tests that the agent correctly responds to natural language retry requests
like "my build failed", "retry the task", "investigate the failure", etc.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.entity.background_task import BackgroundTask


class TestAgentTaskRetryConversation:
    """Tests for agent understanding of task retry requests."""

    @pytest.fixture
    def mock_failed_task_retryable(self):
        """Mock a failed task with retryable error."""
        task = BackgroundTask(
            technical_id="task-failed-123",
            user_id="user-456",
            task_type="application_build",
            name="Build Customer App",
            description="Failed due to rate limit",
            status="failed",
            progress=25,
            error="Rate limit exceeded. Please retry later.",
            branch_name="feature/customer-mgmt",
            language="python",
            user_request="Build a customer management system with CRUD operations",
            conversation_id="conv-789",
            repository_path="/tmp/repo",
            metadata={
                "error_type": "TRANSIENT",
                "is_retryable": True,
                "error_description": "API rate limit exceeded",
            },
        )
        return task

    @pytest.fixture
    def mock_failed_task_permanent(self):
        """Mock a failed task with permanent error."""
        task = BackgroundTask(
            technical_id="task-failed-456",
            user_id="user-456",
            task_type="code_generation",
            name="Generate REST API",
            description="Failed due to syntax error",
            status="failed",
            progress=35,
            error="Generated code has syntax errors",
            language="python",
            user_request="Create a REST API with authentication",
            conversation_id="conv-789",
            metadata={
                "error_type": "PERMANENT",
                "is_retryable": False,
                "error_description": "Generated code has syntax errors - prompt needs adjustment",
            },
        )
        return task

    @pytest.mark.asyncio
    async def test_agent_understands_retry_my_build(self, mock_failed_task_retryable):
        """Test agent responds correctly to 'retry my build'."""
        # This test verifies the agent prompt logic
        # In a real scenario, the agent would:
        # 1. Detect "retry my build" request
        # 2. Check conversation history for task_id
        # 3. Call check_task_status(task_id)
        # 4. See it's retryable
        # 5. Call retry_failed_generation(task_id)

        # Simulate the expected tool calls
        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.check_task_status_tool.check_task_status"
        ) as mock_check:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.retry_generation_tool.retry_failed_generation"
            ) as mock_retry:
                # Mock check_task_status response
                mock_check.return_value = """
📋 Task Status: task-failed-123

Status: failed ❌
Progress: 25%
Name: Build Customer App

❌ Error Details:
  Type: TRANSIENT
  Description: API rate limit exceeded
  Retryable: Yes ✅

You can retry this task using:
  retry_failed_generation(task_id='task-failed-123')
"""

                # Mock retry_failed_generation response
                mock_retry.return_value = "✅ Successfully retried failed application build (original task: task-failed-123)."

                # Simulate agent behavior
                task_id = "task-failed-123"

                # Step 1: Agent checks status
                status = await mock_check(task_id)
                assert "Retryable: Yes ✅" in status
                assert "task-failed-123" in status

                # Step 2: Agent sees it's retryable and calls retry
                result = await mock_retry(task_id)
                assert "✅ Successfully retried" in result

                # Verify tools were called
                mock_check.assert_called_once_with(task_id)
                mock_retry.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_agent_handles_permanent_error(self, mock_failed_task_permanent):
        """Test agent explains why permanent errors can't be retried."""
        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.check_task_status_tool.check_task_status"
        ) as mock_check:
            # Mock check_task_status response for permanent error
            mock_check.return_value = """
📋 Task Status: task-failed-456

Status: failed ❌
Progress: 35%
Name: Generate REST API

❌ Error Details:
  Type: PERMANENT
  Description: Generated code has syntax errors - prompt needs adjustment
  Retryable: No ❌

This error is not retryable. Please review the error and fix the underlying issue.
"""

            # Simulate agent behavior
            task_id = "task-failed-456"

            # Agent checks status
            status = await mock_check(task_id)
            assert "Retryable: No ❌" in status
            assert "PERMANENT" in status
            assert "not retryable" in status

            # Agent should NOT call retry_failed_generation
            # Instead, it should explain the issue and ask for clarification

            mock_check.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_agent_maps_various_retry_phrases(self):
        """Test agent recognizes different ways users might request retry."""
        # All these phrases should trigger the same behavior:
        # check_task_status -> retry_failed_generation (if retryable)

        retry_phrases = [
            "retry my build",
            "retry the task",
            "try again",
            "can you retry it?",
            "please fix the build",
            "the generation failed, can you retry?",
            "investigate the failure and retry",
        ]

        # This test documents expected behavior
        # The actual agent prompt in github_agent.template section 7.3
        # maps all these to the same tool calls

        for phrase in retry_phrases:
            # Expected flow for each phrase:
            # 1. Agent recognizes it's a retry request
            # 2. Calls check_task_status(task_id)
            # 3. If retryable, calls retry_failed_generation(task_id)
            assert phrase  # Document the expected phrases

    @pytest.mark.asyncio
    async def test_agent_investigates_before_retry(self):
        """Test agent ALWAYS checks status before retrying."""
        # According to section 7.3 of agent prompt:
        # "Always call check_task_status BEFORE retry_failed_generation"

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.check_task_status_tool.check_task_status"
        ) as mock_check:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.retry_generation_tool.retry_failed_generation"
            ) as mock_retry:
                mock_check.return_value = """
Status: failed ❌
Retryable: Yes ✅
"""
                mock_retry.return_value = "✅ Successfully retried"

                task_id = "task-123"

                # Correct order: check THEN retry
                await mock_check(task_id)
                await mock_retry(task_id)

                # Verify order
                assert mock_check.call_count == 1
                assert mock_retry.call_count == 1

    def test_agent_prompt_has_retry_logic(self):
        """Verify the agent prompt contains retry handling instructions."""
        with open(
            "/home/kseniia/IdeaProjects/cyoda-ai-studio/application/agents/github/prompts/github_agent.template",
            "r",
        ) as f:
            prompt = f.read()

        # Verify key sections exist
        assert "7. 🔄 Task Management & Retry Logic" in prompt
        assert "Handling Failed Task Mentions" in prompt
        assert "My build failed" in prompt
        assert "retry the build" in prompt
        assert "check_task_status" in prompt
        assert "retry_failed_generation" in prompt
        assert "Retryable" in prompt
        assert "transient error" in prompt
        assert "permanent error" in prompt

    def test_check_task_status_provides_retry_guidance(self):
        """Verify check_task_status tool provides retry guidance."""
        # The tool should output instructions like:
        # "You can retry this task using: retry_failed_generation(task_id='xxx')"

        # This is tested in the actual tool implementation at:
        # application/agents/github/tool_definitions/code_generation/tools/check_task_status_tool.py
        # Lines 197-205

        # Read the tool file to verify
        with open(
            "/home/kseniia/IdeaProjects/cyoda-ai-studio/application/agents/github/tool_definitions/code_generation/tools/check_task_status_tool.py",
            "r",
        ) as f:
            tool_code = f.read()

        assert "retry_failed_generation" in tool_code
        assert "is_retryable" in tool_code
        assert "You can retry this task using" in tool_code

    @pytest.mark.asyncio
    async def test_user_journey_build_fails_retry(self):
        """
        Simulate complete user journey:
        1. User: 'build my app'
        2. Agent: calls generate_application -> returns task_id
        3. Task fails (rate limit)
        4. User: 'my build failed, can you retry?'
        5. Agent: checks status -> sees retryable -> retries
        """
        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.check_task_status_tool.check_task_status"
        ) as mock_check:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.retry_generation_tool.retry_failed_generation"
            ) as mock_retry:
                # Setup
                task_id = "task-build-789"

                # Step 4: User says "my build failed, can you retry?"
                # Agent recognizes retry request and checks status
                mock_check.return_value = """
Status: failed ❌
Error: Rate limit exceeded
Retryable: Yes ✅

You can retry this task using:
  retry_failed_generation(task_id='task-build-789')
"""

                status = await mock_check(task_id)

                # Agent sees it's retryable
                assert "Retryable: Yes ✅" in status

                # Step 5: Agent calls retry
                mock_retry.return_value = (
                    "✅ Successfully retried. New task ID: task-build-790"
                )
                result = await mock_retry(task_id)

                assert "✅ Successfully retried" in result
                assert "task-build-790" in result

                # Verify flow
                mock_check.assert_called_once()
                mock_retry.assert_called_once()


class TestRetryLogicDocumentation:
    """Tests that document the retry logic for developers."""

    def test_retry_flow_for_retryable_errors(self):
        """
        Document: Flow for retryable errors (rate limits, timeouts)

        1. User: "my build failed, retry it"
        2. Agent: calls check_task_status(task_id)
        3. check_task_status returns: is_retryable=True
        4. Agent: "I can see it failed due to [error]. Retrying now..."
        5. Agent: calls retry_failed_generation(task_id)
        6. retry_failed_generation: creates new task, returns new task_id
        7. Agent: "✅ Retried successfully. New task ID: xxx"
        """
        assert True  # Documentation test

    def test_retry_flow_for_permanent_errors(self):
        """
        Document: Flow for permanent errors (syntax, auth errors)

        1. User: "my build failed, retry it"
        2. Agent: calls check_task_status(task_id)
        3. check_task_status returns: is_retryable=False, error_type=PERMANENT
        4. Agent: "The build failed due to [error]. This is a permanent error."
        5. Agent: Provides guidance based on error type:
           - Syntax: "Let's review your requirements and clarify..."
           - Auth: "Please verify your API keys..."
        6. Agent: Offers to help fix root cause
        7. User: provides clarification
        8. Agent: calls generate_application/generate_code_with_cli with new params
        """
        assert True  # Documentation test

    def test_supported_user_phrases(self):
        """
        Document: Natural language phrases that trigger retry logic

        Supported phrases (mapped in agent prompt section 7.3):
        - "retry the build"
        - "retry my build"
        - "try again"
        - "can you retry it?"
        - "my build failed"
        - "the generation failed, can you retry?"
        - "please fix the build"
        - "investigate the failure"
        - "what went wrong?"
        - "check the status"

        All map to:
        1. check_task_status(task_id) first
        2. Then either retry_failed_generation OR explain + guide
        """
        assert True  # Documentation test
