"""
Shared tools for all agents.

Includes:
- Web page loading for documentation retrieval
- Local documentation file reading
- Future: Cyoda entity search, code example lookup
"""

import asyncio
import logging
from pathlib import Path

import httpx
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

        # Use async HTTP client
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

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
        # Run BeautifulSoup parsing in thread pool as it's CPU-bound
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(
            None, lambda: BeautifulSoup(response.content, "lxml")
        )
        text = soup.get_text(separator="\n", strip=True)

        lines = [line for line in text.splitlines() if len(line.split()) > 3]
        result = "\n".join(lines)

        logger.info(f"Successfully fetched {len(result)} characters from {url}")
        return result

    except httpx.TimeoutException:
        error_msg = f"Timeout while fetching {url}"
        logger.error(error_msg)
        return error_msg
    except httpx.HTTPError as e:
        error_msg = f"HTTP error fetching {url}: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error loading {url}: {str(e)}"
        logger.exception(error_msg)
        return error_msg


async def read_documentation(tool_context: ToolContext, filename: str) -> str:
    """
    Read local documentation file from llm_docs/outputs/.

    This tool reads pre-generated documentation files that contain
    API references, platform concepts, and guides.

    Args:
        tool_context: The ADK tool context
        filename: The filename to read. Available files:
                  - 'cyoda-api-sitemap-llms.txt' - API endpoint reference
                  - 'cyoda-api-descriptions-llms.txt' - API section descriptions
                  - 'cyoda-docs-llms.txt' - Platform concepts & guides

    Returns:
        File content, or error message if file not found

    Example:
        >>> content = await read_documentation(tool_context, 'cyoda-api-sitemap-llms.txt')
    """
    try:
        logger.info(f"Reading documentation file: {filename}")

        # Resolve path relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        file_path = project_root / "llm_docs" / "outputs" / filename

        if not file_path.exists():
            available_files = [
                "cyoda-api-sitemap-llms.txt",
                "cyoda-api-descriptions-llms.txt",
                "cyoda-docs-llms.txt"
            ]
            error_msg = (
                f"File not found: {filename}\n"
                f"Available files: {', '.join(available_files)}"
            )
            logger.error(error_msg)
            return error_msg

        # Read file content
        content = file_path.read_text(encoding='utf-8')
        logger.info(f"Successfully read {len(content)} characters from {filename}")
        return content

    except Exception as e:
        error_msg = f"Error reading {filename}: {str(e)}"
        logger.exception(error_msg)
        return error_msg
