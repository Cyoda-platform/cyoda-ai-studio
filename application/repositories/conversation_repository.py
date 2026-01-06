"""
Conversation Repository for data access operations.

Provides clean abstraction over entity service with conversation-specific logic.
"""

import asyncio
import copy
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.entity.conversation import Conversation
from common.exception import is_not_found
from common.service.entity_service import EntityService, SearchConditionRequest

logger = logging.getLogger(__name__)

# Constants
MAX_CONVERSATION_UPDATE_RETRIES = 5
RETRY_BASE_DELAY_SECONDS = 0.1

# Retryable error indicators
RETRYABLE_ERROR_INDICATORS = (
    "422",
    "500",
    "version mismatch",
    "earliestupdateaccept",
    "changed by another transaction",
    "update operation returned no entity id",
)


class ConversationRepository:
    """Repository for conversation entity operations."""

    def __init__(self, entity_service: EntityService):
        """
        Initialize conversation repository.

        Args:
            entity_service: Entity service for data persistence operations.
        """
        self.entity_service = entity_service

    async def get_by_id(self, technical_id: str) -> Optional[Conversation]:
        """
        Get conversation by technical ID.

        Args:
            technical_id: Technical UUID of the conversation.

        Returns:
            Conversation object if found, None otherwise.

        Raises:
            Exception: If retrieval fails for reasons other than not found.
        """
        try:
            response = await self.entity_service.get_by_id(
                entity_id=technical_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if response and hasattr(response, "data"):
                return Conversation(**response.data)
            elif response:
                return Conversation(**response)
            return None
        except Exception as e:
            if is_not_found(e):
                return None
            raise

    async def search(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        point_in_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search conversations with optional filters.

        Args:
            user_id: Filter by user ID. If None, returns all conversations.
            limit: Maximum number of results to return. Defaults to 100.
            point_in_time: Optional timestamp for temporal queries.

        Returns:
            List of conversation dictionaries matching the search criteria.
        """
        if user_id:
            search_condition = (
                SearchConditionRequest.builder()
                .equals("user_id", user_id)
                .limit(limit)
                .build()
            )

            if point_in_time:
                # Parse ISO format string to datetime object
                point_in_time_dt = datetime.fromisoformat(point_in_time.replace("Z", "+00:00"))
                response_list = await self.entity_service.search_at_time(
                    entity_class=Conversation.ENTITY_NAME,
                    condition=search_condition,
                    point_in_time=point_in_time_dt,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
            else:
                response_list = await self.entity_service.search(
                    entity_class=Conversation.ENTITY_NAME,
                    condition=search_condition,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
        else:
            response_list = await self.entity_service.find_all(
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

        return response_list if isinstance(response_list, list) else []

    async def create(self, conversation: Conversation) -> Conversation:
        """
        Create a new conversation.

        Args:
            conversation: Conversation object to create.

        Returns:
            Created conversation with populated technical ID and metadata.
        """
        entity_data = conversation.model_dump(by_alias=False)
        response = await self.entity_service.save(
            entity=entity_data,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        saved_data = response.data if hasattr(response, "data") else response
        return Conversation(**saved_data)

    async def update_with_retry(self, conversation: Conversation) -> Conversation:
        """
        Update conversation with automatic retry on version conflicts.

        Implements optimistic locking with intelligent merge strategy. On conflict,
        fetches fresh version and merges changes before retrying.

        Args:
            conversation: Conversation object to update with desired state.

        Returns:
            Updated conversation object with latest state.

        Raises:
            RuntimeError: If update fails after all retry attempts.
            Exception: For non-retryable errors.
        """
        # Snapshot target state
        target_state = {
            "chat_flow": copy.deepcopy(conversation.chat_flow) if conversation.chat_flow else {},
            "adk_session_id": conversation.adk_session_id,
            "name": conversation.name,
            "description": conversation.description,
            "background_task_ids": conversation.background_task_ids or []
        }

        for attempt in range(MAX_CONVERSATION_UPDATE_RETRIES):
            try:
                # On retry, fetch fresh version and merge
                if attempt > 0 and conversation.technical_id:
                    fresh_conversation = await self.get_by_id(conversation.technical_id)
                    if fresh_conversation:
                        self._merge_conversation_state(fresh_conversation, target_state)
                        conversation = fresh_conversation

                # Attempt update
                entity_data = conversation.model_dump(by_alias=False)
                response = await self.entity_service.update(
                    entity_id=conversation.technical_id,
                    entity=entity_data,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                saved_data = response.data if hasattr(response, "data") else response
                return Conversation(**saved_data)

            except Exception as e:
                if not self._is_retryable_error(str(e)) or attempt >= MAX_CONVERSATION_UPDATE_RETRIES - 1:
                    logger.error(f"Failed to update conversation after {attempt + 1} attempts: {e}")
                    raise

                delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                logger.warning(
                    f"Version conflict updating conversation {conversation.technical_id} "
                    f"(attempt {attempt + 1}). Retrying in {delay:.3f}s..."
                )
                await asyncio.sleep(delay)

        raise RuntimeError("Update conversation failed after all retries")

    async def delete(self, technical_id: str) -> None:
        """
        Delete conversation by technical ID.

        Args:
            technical_id: Technical UUID of the conversation to delete.
        """
        await self.entity_service.delete_by_id(
            entity_id=technical_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

    def _merge_conversation_state(self, fresh: Conversation, target: Dict[str, Any]) -> None:
        """
        Merge target state into fresh conversation object.

        Combines messages and tasks from both versions, preferring fresh data
        but adding any new items from target state.

        Args:
            fresh: Fresh conversation object fetched from database (modified in place).
            target: Dictionary containing desired state changes.
        """
        # Merge messages
        fresh_messages = fresh.chat_flow.get("finished_flow", [])
        target_messages = target["chat_flow"].get("finished_flow", [])
        
        existing_ids = {m.get("technical_id") for m in fresh_messages if m.get("technical_id")}
        
        for msg in target_messages:
            msg_id = msg.get("technical_id")
            if msg_id and msg_id not in existing_ids:
                fresh_messages.append(msg)
                existing_ids.add(msg_id)

        # Update fields
        fresh.chat_flow["finished_flow"] = fresh_messages
        fresh.chat_flow["current_flow"] = target["chat_flow"].get("current_flow", [])
        fresh.adk_session_id = target["adk_session_id"]
        fresh.name = target["name"]
        fresh.description = target["description"]

        # Merge tasks
        fresh_task_ids = set(fresh.background_task_ids or [])
        target_task_ids = set(target["background_task_ids"])
        fresh.background_task_ids = list(fresh_task_ids | target_task_ids)

    def _is_retryable_error(self, error_str: str) -> bool:
        """
        Check if error indicates a retryable condition (e.g., version conflict).

        Args:
            error_str: Error message to check.

        Returns:
            True if the error is retryable, False otherwise.
        """
        error_lower = error_str.lower()
        return any(indicator in error_lower for indicator in RETRYABLE_ERROR_INDICATORS)