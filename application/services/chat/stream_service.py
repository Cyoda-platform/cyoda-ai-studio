"""
Chat Stream Service for orchestrating chat streaming logic.

Handles preparation, execution, and persistence of chat streams,
decoupling route handlers from business logic.

NOTE: Currently only Google ADK is actively used. OpenAI SDK support is
available but not currently enabled in production. The _stream_openai()
method is kept for future use but is not called in the current setup.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from application.entity.conversation import Conversation
from application.services.chat.service import ChatService
from application.services.edge_message_persistence_service import (
    EdgeMessagePersistenceService,
)
from application.services.streaming_service import StreamingService
from application.services.sdk_factory import is_using_openai_sdk
from common.config.config import (
    CYODA_ENTITY_TYPE_EDGE_MESSAGE,
    ENTITY_VERSION,
)
from services.services import (
    get_cyoda_assistant,
    get_repository,
)

logger = logging.getLogger(__name__)


class ChatStreamService:
    """Service for orchestrating chat streaming operations."""

    def __init__(
        self,
        chat_service: ChatService,
        persistence_service: EdgeMessagePersistenceService,
    ):
        self.chat_service = chat_service
        self.persistence_service = persistence_service

    async def prepare_stream(
        self,
        technical_id: str,
        user_id: str,
        user_message: str,
        file_blob_ids: Optional[List[str]] = None,
        is_superuser: bool = False,
    ) -> Tuple[Conversation, str, Any]:
        """
        Prepare for streaming: validate, save user message, update conversation.

        Args:
            technical_id: Conversation ID
            user_id: User ID
            user_message: User's message text
            file_blob_ids: List of file blob IDs
            is_superuser: Whether user is superuser

        Returns:
            Tuple of (Updated Conversation, Message text to process, Assistant instance)
        """
        # Get and validate conversation
        conversation = await self.chat_service.get_conversation(technical_id)
        if not conversation:
            raise ValueError("Chat not found")

        try:
            self.chat_service.validate_ownership(conversation, user_id, is_superuser)
        except PermissionError:
            raise PermissionError("Access denied")

        # Save user message as edge message
        msg_id = await self.persistence_service.save_message_as_edge_message(
            message_type="user",
            message_content=user_message,
            conversation_id=technical_id,
            user_id=user_id,
            file_blob_ids=file_blob_ids,
        )

        # Update conversation
        conversation.add_message("user", msg_id, file_blob_ids)
        if file_blob_ids:
            current_files = conversation.file_blob_ids or []
            conversation.file_blob_ids = list(set(current_files + file_blob_ids))

        updated_conversation = await self.chat_service.update_conversation(conversation)

        # Get assistant
        assistant = get_cyoda_assistant()

        # Format message for AI
        message_to_process = user_message
        if file_blob_ids:
            message_to_process = f"{user_message} (with {len(file_blob_ids)} files)"

        return updated_conversation, message_to_process, assistant

    def _select_stream_generator(
        self, assistant: Any, message: str, conversation: Conversation, technical_id: str, user_id: str
    ) -> AsyncGenerator[str, None]:
        """Select appropriate stream generator based on SDK.

        NOTE: Currently only Google ADK is used in production.
        OpenAI SDK support is available but not enabled.

        Args:
            assistant: Assistant instance
            message: Message to process
            conversation: Conversation object
            technical_id: Conversation technical ID
            user_id: User ID

        Returns:
            Stream generator
        """
        if is_using_openai_sdk():
            return self._stream_openai(
                assistant, message, conversation.messages, technical_id, user_id
            )

        return StreamingService.stream_agent_response(
            agent_wrapper=assistant,
            user_message=message,
            conversation_history=conversation.messages,
            conversation_id=technical_id,
            adk_session_id=conversation.adk_session_id,
            user_id=user_id,
        )

    async def _process_stream_event(
        self, event: str
    ) -> tuple[str, str, dict]:
        """Process single stream event and extract data.

        Args:
            event: SSE event string

        Returns:
            Tuple of (event_to_yield, accumulated_chunk, meta_result)
        """
        accumulated_chunk = ""
        meta_result = {}

        if "event: content" in event:
            try:
                data = json.loads(event.split("data: ")[1])
                accumulated_chunk = data.get("chunk", "")
            except Exception:
                pass
            return event, accumulated_chunk, meta_result

        if "event: done" in event:
            try:
                meta_result = json.loads(event.split("data: ")[1])
            except Exception:
                pass
            return event, "", meta_result

        return event, "", {}

    async def stream_and_save(
        self,
        assistant: Any,
        message_to_process: str,
        conversation: Conversation,
        technical_id: str,
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """Execute stream and save results.

        Yields SSE events.
        """
        accumulated_response = ""
        meta_result = {}

        try:
            generator = self._select_stream_generator(
                assistant, message_to_process, conversation, technical_id, user_id
            )

            async for event in generator:
                event_to_yield, chunk, meta = await self._process_stream_event(event)
                accumulated_response += chunk
                meta_result.update(meta)

                if event_to_yield:
                    yield event_to_yield

            if accumulated_response or meta_result:
                await self._save_ai_response(
                    technical_id, user_id, accumulated_response, meta_result
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"

    async def _save_ai_response(
        self,
        technical_id: str,
        user_id: str,
        response_text: str,
        meta: Dict[str, Any],
    ) -> None:
        """Save AI response to persistence and update conversation."""
        try:
            # Save to edge message
            resp_id = await self.persistence_service.save_response_with_history(
                conversation_id=technical_id,
                user_id=user_id,
                response_content=response_text,
                streaming_events=[], # We don't track full history here for now to simplify
                metadata={"hook": meta.get("hook")} if meta.get("hook") else None,
            )

            # Update conversation
            fresh_conv = await self.chat_service.get_conversation(technical_id)
            if fresh_conv:
                if response_text:
                    fresh_conv.add_message(
                        "ai", resp_id, metadata={"hook": meta.get("hook")} if meta.get("hook") else None
                    )
                
                # Update session ID if new
                if not fresh_conv.adk_session_id and meta.get("adk_session_id"):
                    fresh_conv.adk_session_id = meta.get("adk_session_id")
                
                # Update repository info if present
                repo_info = meta.get("repository_info")
                if repo_info:
                    fresh_conv.repository_name = repo_info.get("repository_name")
                    fresh_conv.repository_owner = repo_info.get("repository_owner")
                    fresh_conv.repository_branch = repo_info.get("repository_branch")
                    fresh_conv.repository_url = repo_info.get("repository_url")
                    fresh_conv.installation_id = repo_info.get("installation_id")

                # Update background tasks
                build_task_id = meta.get("build_task_id")
                if build_task_id and build_task_id not in fresh_conv.background_task_ids:
                    fresh_conv.background_task_ids.append(build_task_id)

                await self.chat_service.update_conversation(fresh_conv)
                logger.info(f"✅ Saved AI response for chat {technical_id}")

        except Exception as e:
            logger.error(f"Failed to save AI response: {e}", exc_info=True)

    async def _stream_openai(self, assistant, message, history, conv_id, user_id):
        """Internal helper for OpenAI streaming."""
        yield f"event: start\ndata: {json.dumps({'agent': 'OpenAI'})}\n\n"

        acc = ""
        hooks = []

        async for chunk in assistant.stream_message(message, history, conv_id, user_id):
            if chunk.startswith('{"__hook__":'):
                try:
                    h = json.loads(chunk)["__hook__"]
                    hooks.append(h)
                    yield f"event: hook\ndata: {json.dumps(h)}\n\n"
                except:
                    pass
            elif chunk.startswith("event:"):
                # Don't yield done events from upstream - let stream_and_save handle them
                if "event: done" not in chunk:
                    yield chunk
            else:
                acc += chunk
                yield f"event: content\ndata: {json.dumps({'chunk': chunk})}\n\n"

        yield f"event: done\ndata: {json.dumps({'response': acc, 'hooks': hooks})}\n\n"

    async def handle_file_uploads(self, request_files) -> List[str]:
        """Handle file uploads and return list of blob IDs."""
        blob_ids = []
        if not request_files:
            return blob_ids

        file_list = request_files.getlist('files') if 'files' in request_files else []
        repo = get_repository()
        import base64

        for file in file_list:
            content = base64.b64encode(file.read()).decode("utf-8")
            meta = {
                "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                "entity_model": "flow_edge_message",
                "entity_version": ENTITY_VERSION,
            }
            eid = await repo.save(
                meta=meta, 
                entity={"message": content, "metadata": {"filename": file.filename}}
            )
            if eid:
                blob_ids.append(eid)
        
        return blob_ids
