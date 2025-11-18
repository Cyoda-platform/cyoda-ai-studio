"""
Conversation Entity for AI Assistant Application

Represents a persistent chat conversation stored in Cyoda.
Maintains full chat history, context, and workflow state.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Conversation(CyodaEntity):
    """
    Conversation entity represents a persistent chat session.

    Stores all messages, context, and metadata for AI-powered conversations.
    Compatible with existing UI expectations from ai_assistant_deprecated.
    """

    ENTITY_NAME: ClassVar[str] = "Conversation"
    ENTITY_VERSION: ClassVar[int] = 1

    user_id: str = Field(
        ..., description="User ID who owns this conversation"
    )

    name: Optional[str] = Field(
        default="", description="Display name for the conversation"
    )

    description: Optional[str] = Field(
        default="", description="Optional description of the conversation"
    )

    date: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Creation date of the conversation",
    )

    chat_flow: Dict[str, List[Any]] = Field(
        default_factory=lambda: {"current_flow": [], "finished_flow": []},
        description="Message history - current_flow for active, finished_flow for completed",
    )

    workflow_name: Optional[str] = Field(
        default=None,
        description="Associated workflow name if any",
    )

    current_state: Optional[str] = Field(
        default=None, description="Current workflow state"
    )

    current_transition: Optional[str] = Field(
        default=None,
        description="Current workflow transition",
    )

    workflow_cache: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cache for workflow-related data and AI context",
    )

    file_blob_ids: Optional[List[str]] = Field(
        default=None,
        description="List of file blob IDs attached to this conversation",
    )

    locked: bool = Field(
        default=False, description="Lock flag for concurrent access control"
    )

    child_entities: List[str] = Field(
        default_factory=list,
        description="List of child entity IDs",
    )

    scheduled_entities: List[str] = Field(
        default_factory=list,
        description="List of scheduled entity IDs",
    )

    memory_id: Optional[str] = Field(
        default=None,
        description="Associated memory/context ID for AI",
    )

    adk_session_id: Optional[str] = Field(
        default=None,
        description="Technical ID of the associated AdkSession entity in Cyoda",
    )

    background_task_ids: List[str] = Field(
        default_factory=list,
        description="List of technical IDs of associated BackgroundTask entities (e.g., for app builds, deployments)",
    )

    repository_name: Optional[str] = Field(
        default=None,
        description="GitHub repository name for this conversation's app",
    )

    repository_owner: Optional[str] = Field(
        default=None,
        description="GitHub repository owner/organization",
    )

    repository_branch: Optional[str] = Field(
        default=None,
        description="GitHub branch being worked on",
    )

    repository_url: Optional[str] = Field(
        default=None,
        description="Full GitHub repository URL (e.g., https://github.com/owner/repo)",
    )

    installation_id: Optional[str] = Field(
        default=None,
        description="GitHub App installation ID for accessing this repository",
    )

    def add_message(
        self,
        message_type: str,
        message: str,
        file_blob_ids: Optional[List[str]] = None,
        approve: bool = False,
        consumed: bool = False,
    ) -> None:
        """
        Add a message to the conversation flow.

        Args:
            message_type: Type of message ('question', 'answer', 'notification', 'error')
            message: The message content
            file_blob_ids: Optional file attachments
            approve: Whether this message requires approval
            consumed: Whether this message has been consumed/processed
        """
        import time

        now = datetime.now(timezone.utc)
        timestamp_ms = int(time.time() * 1000)

        message_entry = {
            "type": message_type,
            "message": message,
            "timestamp": now.isoformat(),
            "approve": approve,
            # AI messages (type "question") are consumed, user messages (type "answer") are not
            "consumed": consumed if message_type == "answer" else True,
            "technical_id": str(uuid.uuid4()),
            "user_id": self.user_id or "default",
            "file_blob_ids": file_blob_ids,
            "publish": True,
            "failed": False,
            "error": None,
            "error_code": "None",
            "current_state": None,
            "current_transition": None,
            "workflow_name": None,
            "workflow_cache": {},
            "edge_message_id": None,
            "edge_messages_store": {},
            "metadata": None,
            "last_modified": timestamp_ms,
            "last_modified_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Add type-specific field for backward compatibility
        # Note: "answer" type is user message, "question" type is AI message
        if message_type == "answer":
            message_entry["answer"] = message
        elif message_type == "question":
            message_entry["question"] = message

        self.chat_flow["finished_flow"].append(message_entry)

    @property
    def messages(self) -> List[Dict[str, Any]]:
        """
        Get all messages in the conversation.

        Returns:
            List of message dictionaries
        """
        return self.chat_flow.get("finished_flow", [])

    def get_dialogue(self) -> List[Dict[str, Any]]:
        """
        Get formatted dialogue for UI display.

        Returns:
            List of message dictionaries formatted for UI (returns full message entries)
        """
        # Return the full message entries as they already contain all required fields
        return self.chat_flow.get("finished_flow", [])

    def get_context_for_ai(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """
        Get conversation context formatted for AI model.

        Args:
            max_messages: Maximum number of messages to include

        Returns:
            List of messages in AI-friendly format
        """
        messages = []
        finished_flow = self.chat_flow.get("finished_flow", [])

        # Get last N messages
        recent_messages = (
            finished_flow[-max_messages:]
            if len(finished_flow) > max_messages
            else finished_flow
        )

        for msg in recent_messages:
            msg_type = msg.get("type")
            content = msg.get("message", "")

            # User messages are type "answer", AI messages are type "question"
            if msg_type == "answer":
                messages.append({"role": "user", "content": content})
            elif msg_type == "question":
                messages.append({"role": "assistant", "content": content})

        return messages

    def to_api_response(self) -> Dict[str, Any]:
        """
        Convert to API response format compatible with existing UI.

        Returns:
            Dictionary formatted for API response
        """
        return {
            "technical_id": self.technical_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "date": self.date,
            "chat_flow": self.chat_flow,
            "workflow_name": self.workflow_name,
            "current_state": self.current_state,
            "locked": self.locked,
            "file_blob_ids": self.file_blob_ids,
            "state": self.state,
            "background_task_ids": self.background_task_ids,
            "repository_name": self.repository_name,
            "repository_owner": self.repository_owner,
            "repository_branch": self.repository_branch,
            "repository_url": self.repository_url,
            "installation_id": self.installation_id,
        }

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
