"""Formatters for chat service responses."""

import logging
from typing import Dict, List

from .constants import (
    FIELD_CREATED_AT,
    FIELD_DATE,
    FIELD_DESCRIPTION,
    FIELD_NAME,
    FIELD_TECHNICAL_ID,
    RESPONSE_KEY_CACHED,
    RESPONSE_KEY_CHATS,
    RESPONSE_KEY_HAS_MORE,
    RESPONSE_KEY_LIMIT,
    RESPONSE_KEY_NEXT_CURSOR,
)
from .models import PaginationResult

logger = logging.getLogger(__name__)


def calculate_pagination(chats: List[Dict], limit: int) -> PaginationResult:
    """Calculate pagination info from chat list.

    Args:
        chats: List of chats
        limit: Result limit

    Returns:
        PaginationResult with pagination info
    """
    has_more = len(chats) > limit
    next_cursor = chats[limit - 1][FIELD_DATE] if has_more and chats else None

    return PaginationResult(
        has_more=has_more, next_cursor=next_cursor, total_returned=len(chats[:limit])
    )


def format_response(
    chats: List[Dict], pagination: PaginationResult, cached: bool
) -> Dict:
    """Format final response with all metadata.

    Args:
        chats: List of chats
        pagination: Pagination information
        cached: Whether result came from cache

    Returns:
        Formatted response dictionary
    """
    return {
        RESPONSE_KEY_CHATS: chats,
        RESPONSE_KEY_LIMIT: len(chats),
        RESPONSE_KEY_NEXT_CURSOR: pagination.next_cursor,
        RESPONSE_KEY_HAS_MORE: pagination.has_more,
        RESPONSE_KEY_CACHED: cached,
    }


def extract_conversations_from_response(response_list: List) -> List[Dict]:
    """Extract conversation summaries from entity service response.

    Args:
        response_list: Raw response from entity service

    Returns:
        List of conversation dictionaries
    """
    user_chats = []
    for resp in response_list:
        if hasattr(resp, "data") and hasattr(resp, "metadata"):
            cyoda_response = resp.data
            tech_id = resp.metadata.id

            if isinstance(cyoda_response, dict) and "data" in cyoda_response:
                entity_data = cyoda_response["data"]
                name = entity_data.get("name", "")
                description = entity_data.get("description", "")
                date = entity_data.get("date", "") or entity_data.get("created_at", "")
            else:
                name = ""
                description = ""
                date = ""

            user_chats.append(
                {
                    FIELD_TECHNICAL_ID: tech_id,
                    FIELD_NAME: name,
                    FIELD_DESCRIPTION: description,
                    FIELD_DATE: date,
                }
            )
        elif isinstance(resp, dict):
            conv_data = resp.get("data", resp)
            tech_id = resp.get(FIELD_TECHNICAL_ID, "") or conv_data.get(
                FIELD_TECHNICAL_ID, ""
            )

            user_chats.append(
                {
                    FIELD_TECHNICAL_ID: tech_id,
                    FIELD_NAME: conv_data.get("name", ""),
                    FIELD_DESCRIPTION: conv_data.get("description", ""),
                    FIELD_DATE: conv_data.get("date", "")
                    or conv_data.get(FIELD_CREATED_AT, ""),
                }
            )

    return user_chats
