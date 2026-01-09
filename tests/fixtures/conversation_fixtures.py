"""
Test fixtures for conversation-related tests.

Provides reusable test data for conversations, messages, and related entities.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from application.entity.conversation import Conversation


def create_test_conversation(
    technical_id: str = "test-conv-123",
    user_id: str = "test-user",
    name: str = "Test Conversation",
    description: str = "Test conversation for unit tests",
    **kwargs,
) -> Conversation:
    """
    Create a test Conversation instance.

    Args:
        technical_id: Conversation ID
        user_id: Owner user ID
        name: Conversation name
        description: Conversation description
        **kwargs: Additional fields to override

    Returns:
        Conversation instance for testing

    Example:
        >>> conv = create_test_conversation()
        >>> assert conv.user_id == "test-user"
    """
    defaults = {
        "technical_id": technical_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "date": datetime.now(timezone.utc).isoformat(),
        "chat_flow": {"finished_flow": [], "current_flow": []},
        "adk_session_id": None,
        "file_blob_ids": [],
        "background_task_ids": [],
    }
    defaults.update(kwargs)
    return Conversation(**defaults)


def create_test_message(
    technical_id: str = "msg-123",
    role: str = "user",
    content: str = "Test message",
    **kwargs,
) -> Dict[str, Any]:
    """
    Create a test message dictionary.

    Args:
        technical_id: Message ID
        role: Message role (user/assistant)
        content: Message content
        **kwargs: Additional message fields

    Returns:
        Message dictionary

    Example:
        >>> msg = create_test_message(role="assistant", content="Hello")
    """
    message = {
        "technical_id": technical_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    message.update(kwargs)
    return message


def create_test_conversation_with_messages(
    num_messages: int = 3, **kwargs
) -> Conversation:
    """
    Create a test conversation with messages.

    Args:
        num_messages: Number of messages to add
        **kwargs: Additional conversation fields

    Returns:
        Conversation with messages

    Example:
        >>> conv = create_test_conversation_with_messages(num_messages=5)
        >>> assert len(conv.chat_flow["finished_flow"]) == 5
    """
    messages = []
    for i in range(num_messages):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append(
            create_test_message(
                technical_id=f"msg-{i}", role=role, content=f"Test message {i}"
            )
        )

    chat_flow = {"finished_flow": messages, "current_flow": []}
    return create_test_conversation(chat_flow=chat_flow, **kwargs)


def create_mock_entity_response(data: Any) -> Any:
    """
    Create a mock entity service response.

    Args:
        data: Response data

    Returns:
        Mock response object with data attribute

    Example:
        >>> response = create_mock_entity_response({"key": "value"})
        >>> assert response.data == {"key": "value"}
    """

    class MockResponse:
        def __init__(self, data):
            self.data = data
            self.metadata = type("obj", (object,), {"id": "test-id"})()

    return MockResponse(data)


def create_conversation_list_response(
    count: int = 3, user_id: str = "test-user"
) -> List[Any]:
    """
    Create a list of mock conversation responses.

    Args:
        count: Number of conversations
        user_id: User ID for conversations

    Returns:
        List of mock responses

    Example:
        >>> responses = create_conversation_list_response(count=5)
        >>> assert len(responses) == 5
    """
    responses = []
    for i in range(count):
        conv = create_test_conversation(
            technical_id=f"conv-{i}", user_id=user_id, name=f"Conversation {i}"
        )
        responses.append(create_mock_entity_response(conv.model_dump()))

    return responses
