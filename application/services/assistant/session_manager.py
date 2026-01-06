"""Session manager for Cyoda Assistant state persistence."""

import asyncio
import logging
from typing import Any, Dict, Optional

from application.entity.conversation import Conversation
from common.service.service import EntityServiceError

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session state loading and saving to Cyoda entities."""

    def __init__(self, entity_service: Any):
        self.entity_service = entity_service

    async def load_session_state(self, conversation_id: str) -> Dict[str, Any]:
        """Load session state from conversation entity."""
        try:
            response = await self.entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not response:
                return {}

            data = response.data if hasattr(response, "data") else response
            conversation = Conversation(**data)
            return conversation.workflow_cache.get("adk_session_state", {})

        except Exception as e:
            logger.warning(f"Failed to load session state: {e}")
            return {}

    async def save_session_state(self, conversation_id: str, session_state: Dict[str, Any]) -> None:
        """Save session state with retry logic."""
        max_retries = 5
        base_delay = 0.1

        for attempt in range(max_retries):
            try:
                response = await self.entity_service.get_by_id(
                    entity_id=conversation_id,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                if not response:
                    logger.warning(f"Conversation {conversation_id} not found for save")
                    return

                data = response.data if hasattr(response, "data") else response
                conversation = Conversation(**data)
                
                conversation.workflow_cache["adk_session_state"] = session_state
                entity_data = conversation.model_dump(by_alias=False)

                await self.entity_service.update(
                    entity_id=conversation_id,
                    entity=entity_data,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
                return

            except EntityServiceError as e:
                if self._is_retryable_error(str(e)) and attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2**attempt))
                    continue
                logger.error(f"Failed to save session state: {e}")
                return
            except Exception as e:
                logger.error(f"Unexpected error saving session state: {e}")
                return

    def _is_retryable_error(self, error_str: str) -> bool:
        """Check if error is retryable (version conflict)."""
        error_str = error_str.lower()
        return (
            "422" in error_str or 
            "500" in error_str or 
            "version mismatch" in error_str or 
            "earliestupdateaccept" in error_str or
            "changed by another transaction" in error_str
        )
