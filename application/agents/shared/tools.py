"""
Shared tools for all agents.

Includes:
- Web page loading for documentation retrieval
- Future: Cyoda entity search, code example lookup
"""

import asyncio
import logging

import requests
from bs4 import BeautifulSoup
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def load_web_page(tool_context: ToolContext, url: str) -> str:
    """
    Fetch content from a URL and return clean text.

    This tool fetches web pages and extracts readable text content,
    filtering out navigation, scripts, and other non-content elements.

    Note: This tool cannot render JavaScript. If a page requires JavaScript
    to load content, it will return minimal or placeholder text. In such cases,
    try alternative documentation pages or ask the user for specific information.

    Args:
        tool_context: The ADK tool context
        url: The URL to fetch (e.g., 'https://docs.cyoda.net/guides/workflow-config-guide/')

    Returns:
        Clean text content from the page, or error message if fetch fails

    Example:
        >>> content = await load_web_page(tool_context, 'https://docs.cyoda.net/getting-started/introduction/')
        >>> print(content[:100])
    """
    try:
        logger.info(f"Fetching web page: {url}")

        # Run blocking requests.get in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: requests.get(url, timeout=10)
        )

        if response.status_code != 200:
            error_msg = f"Failed to fetch {url}: HTTP {response.status_code}"
            logger.error(error_msg)
            return error_msg

        # Check content type - if JSON, return raw text
        content_type = response.headers.get("content-type", "").lower()
        if "application/json" in content_type or url.endswith(".json"):
            result = response.text
            logger.info(f"Successfully fetched {len(result)} characters of JSON from {url}")
            return result

        # For HTML/text content, parse and extract clean text
        soup = await loop.run_in_executor(
            None, lambda: BeautifulSoup(response.content, "lxml")
        )
        text = soup.get_text(separator="\n", strip=True)

        lines = [line for line in text.splitlines() if len(line.split()) > 3]
        result = "\n".join(lines)

        logger.info(f"Successfully fetched {len(result)} characters from {url}")
        return result

    except requests.exceptions.Timeout:
        error_msg = f"Timeout while fetching {url}"
        logger.error(error_msg)
        return error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching {url}: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error loading {url}: {str(e)}"
        logger.exception(error_msg)
        return error_msg
