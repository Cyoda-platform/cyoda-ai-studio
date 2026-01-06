"""
SDK Factory for selecting between Google ADK and OpenAI Agents SDK.

Provides a factory function that selects the appropriate SDK based on
the AI_SDK environment variable.
"""

import logging
import os
from typing import Any, Union

logger = logging.getLogger(__name__)


def get_sdk_service() -> Union[Any, Any]:
    """
    Get the appropriate SDK service based on AI_SDK environment variable.

    Environment variables:
        AI_SDK: "google" for Google ADK (default), "openai" for OpenAI SDK

    Returns:
        Initialized service instance (GoogleADKService or OpenAISDKService)

    Raises:
        ValueError: If AI_SDK is set to an unsupported value
    """
    sdk_choice = os.getenv("AI_SDK", "google").lower().strip()

    if sdk_choice == "google":
        logger.info("Using Google ADK SDK")
        from application.services.google_adk_service import GoogleADKService
        return GoogleADKService()

    elif sdk_choice == "openai":
        logger.info("Using OpenAI SDK")
        from application.services.openai.sdk_service import OpenAISDKService
        return OpenAISDKService()

    else:
        raise ValueError(
            f"Unsupported AI_SDK value: {sdk_choice}. "
            f"Must be 'google' or 'openai'"
        )


def get_sdk_name() -> str:
    """
    Get the name of the currently selected SDK.

    Returns:
        "google" or "openai"
    """
    sdk_choice = os.getenv("AI_SDK", "google").lower().strip()
    if sdk_choice not in ("google", "openai"):
        raise ValueError(
            f"Unsupported AI_SDK value: {sdk_choice}. "
            f"Must be 'google' or 'openai'"
        )
    return sdk_choice


def is_using_openai_sdk() -> bool:
    """
    Check if OpenAI SDK is currently selected.

    Returns:
        True if AI_SDK is set to "openai", False otherwise
    """
    return get_sdk_name() == "openai"


def is_using_google_sdk() -> bool:
    """
    Check if Google ADK SDK is currently selected.

    Returns:
        True if AI_SDK is set to "google" or not set (default), False otherwise
    """
    return get_sdk_name() == "google"

