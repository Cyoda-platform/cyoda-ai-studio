"""
Conversation Repository for data access operations.

Provides clean abstraction over entity service with conversation-specific logic.
"""

import asyncio
import copy
import logging
from typing import List, Optional

from application.entity.conversation import Conversation
from application.routes.common.constants import (
    MAX_CONVERSATION_UPDATE_RETRIES,
    RETRY_BASE_DELAY_SECONDS,
)
from common.exception import is_not_found
from common.service.entity_service import SearchConditionRequest

logger = logging.getLogger(__name__)


class ConversationRepository:
    """
    Repository for conversation entity operations.

    Encapsulates data access logic and provides domain-specific methods.
    """

    def __init__(self, entity_service):
        """
        Initialize conversation repository.

        Args:
            entity_service: Entity service for data persistence
        """
        self.entity_service = entity_service

    async def get_by_id(self, technical_id: str) -> Optional[Conversation]:
        """
        Get conversation by technical ID.

        Args:
            technical_id: Conversation technical ID

        Returns:
            Conversation object or None if not found

        Example:
            >>> repo = ConversationRepository(entity_service)
            >>> conv = await repo.get_by_id("123-456")
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
    ) -> List[dict]:
        """
        Search conversations with optional filters.

        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum number of results
            point_in_time: Cursor for pagination (optional)

        Returns:
            List of conversation dictionaries

        Example:
            >>> repo = ConversationRepository(entity_service)
            >>> convs = await repo.search(user_id="alice", limit=50)
        """
        if user_id:
            search_condition = (
                SearchConditionRequest.builder()
                .equals("user_id", user_id)
                .limit(limit)
                .build()
            )

            if point_in_time:
                response_list = await self.entity_service.search_at_time(
                    entity_class=Conversation.ENTITY_NAME,
                    condition=search_condition,
                    point_in_time=point_in_time,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
            else:
                response_list = await self.entity_service.search(
                    entity_class=Conversation.ENTITY_NAME,
                    condition=search_condition,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
        else:
            # Get all conversations (superuser mode)
            response_list = await self.entity_service.find_all(
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

        return response_list if isinstance(response_list, list) else []

    async def create(self, conversation: Conversation) -> Conversation:
        """
        Create a new conversation.

        Args:
            conversation: Conversation object to create

        Returns:
            Created conversation with technical_id populated

        Example:
            >>> conv = Conversation(user_id="alice", name="My Chat")
            >>> created = await repo.create(conv)
            >>> print(created.technical_id)
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

        Implements optimistic locking with exponential backoff retry.
        On conflict, fetches fresh version and merges changes intelligently:
        - Messages are merged (no duplicates)
        - Background task IDs are merged (no duplicates)
        - Other fields are overwritten with target values

        Args:
            conversation: Conversation with updates to persist

        Returns:
            Updated conversation

        Raises:
            Exception: If all retries fail or non-retryable error occurs

        Example:
            >>> conv.name = "Updated Name"
            >>> updated = await repo.update_with_retry(conv)
        """
        # Store target state for re-application on retry
        target_chat_flow = (
            copy.deepcopy(conversation.chat_flow) if conversation.chat_flow else {}
        )
        target_adk_session_id = conversation.adk_session_id
        target_name = conversation.name
        target_description = conversation.description
        target_background_task_ids = conversation.background_task_ids or []

        for attempt in range(MAX_CONVERSATION_UPDATE_RETRIES):
            try:
                # On retry, fetch fresh version
                if attempt > 0 and conversation.technical_id:
                    fresh_conversation = await self.get_by_id(conversation.technical_id)
                    if fresh_conversation:
                        # Merge messages to avoid data loss
                        fresh_messages = fresh_conversation.chat_flow.get(
                            "finished_flow", []
                        )
                        target_messages = target_chat_flow.get("finished_flow", [])

                        # Build set of existing message IDs
                        existing_ids = {
                            msg.get("technical_id")
                            for msg in fresh_messages
                            if msg.get("technical_id")
                        }

                        # Add only new messages
                        for msg in target_messages:
                            msg_id = msg.get("technical_id")
                            if msg_id and msg_id not in existing_ids:
                                fresh_messages.append(msg)
                                existing_ids.add(msg_id)

                        # Update merged state
                        fresh_conversation.chat_flow["finished_flow"] = fresh_messages
                        fresh_conversation.chat_flow["current_flow"] = (
                            target_chat_flow.get("current_flow", [])
                        )
                        fresh_conversation.adk_session_id = target_adk_session_id
                        fresh_conversation.name = target_name
                        fresh_conversation.description = target_description

                        # Merge background task IDs
                        fresh_task_ids = set(
                            fresh_conversation.background_task_ids or []
                        )
                        target_task_ids = set(target_background_task_ids)
                        fresh_conversation.background_task_ids = list(
                            fresh_task_ids | target_task_ids
                        )

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
                error_str = str(e).lower()
                is_version_conflict = (
                    "422" in error_str
                    or "500" in error_str
                    or "version mismatch" in error_str
                    or "earliestupdateaccept" in error_str
                    or "was changed by another transaction" in error_str
                )

                if is_version_conflict and attempt < MAX_CONVERSATION_UPDATE_RETRIES - 1:
                    # Exponential backoff
                    delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        f"Version conflict updating conversation {conversation.technical_id} "
                        f"(attempt {attempt + 1}/{MAX_CONVERSATION_UPDATE_RETRIES}). "
                        f"Retrying in {delay:.3f}s... Error: {str(e)[:100]}"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    if attempt == MAX_CONVERSATION_UPDATE_RETRIES - 1:
                        logger.error(
                            f"Failed to update conversation after {MAX_CONVERSATION_UPDATE_RETRIES} attempts: {e}"
                        )
                    raise

        raise RuntimeError("Update conversation failed after all retries")

    async def delete(self, technical_id: str) -> None:
        """
        Delete conversation by technical ID.

        Args:
            technical_id: Conversation technical ID

        Example:
            >>> await repo.delete("123-456")
        """
        await self.entity_service.delete_by_id(
            entity_id=technical_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )
