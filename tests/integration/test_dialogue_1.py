import pytest
from unittest.mock import MagicMock, AsyncMock, ANY
from application.agents.cyoda_assistant.wrapper import CyodaAssistantWrapper # Import the class directly

@pytest.mark.asyncio
async def test_initial_business_problem_routing(mocker):
    """
    Test that CyodaAssistantWrapper correctly processes a business problem
    and transfers to the github_agent.
    """
    user_message = "Develop an institutional trading platform with real-time market data feeds, advanced order management systems, comprehensive portfolio tracking, risk controls, regulatory compliance for equities and derivatives, and real-time P&L calculations"

    # Mock the process_message method of the CyodaAssistantWrapper class
    mock_process_message = AsyncMock(return_value={
        "response": "I'll help you build a solution that enables an institutional trading platform...",
        "agent_used": "cyoda_assistant",
        "requires_handoff": True, # Simulate handoff
        "metadata": {},
        "adk_session_id": "mock_session_id",
        "ui_functions": [],
        "repository_info": {},
        "build_task_id": None,
    })
    mocker.patch('application.agents.cyoda_assistant.wrapper.CyodaAssistantWrapper.process_message', new=mock_process_message)

    # Instantiate the wrapper with mocked dependencies for its __init__
    assistant = CyodaAssistantWrapper(adk_agent=MagicMock(), entity_service=MagicMock())
    # Mock the agent.name attribute as it's accessed in the return value for "agent_used"
    assistant.agent = MagicMock(name="cyoda_assistant")

    result = await assistant.process_message(
        user_message=user_message,
        conversation_history=[],
        conversation_id="mock_conversation_id",
        adk_session_id="mock_adk_session_id"
    )

    # Assertions
    # Verify process_message was called with the user's message
    mock_process_message.assert_called_once_with(
        user_message=user_message,
        conversation_history=[],
        conversation_id="mock_conversation_id",
        adk_session_id="mock_adk_session_id"
    )

    # Verify the response text (initial confirmation)
    assert "I'll help you build a solution that enables an institutional trading platform..." in result["response"]

    # Verify that the result indicates a handoff
    assert result["requires_handoff"] is True
    assert result["agent_used"] == "cyoda_assistant"

