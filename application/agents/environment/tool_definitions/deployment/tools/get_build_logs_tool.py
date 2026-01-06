"""Tool for retrieving build logs."""

from __future__ import annotations

import httpx
import logging
import os

logger = logging.getLogger(__name__)


async def get_build_logs(build_id: str, max_lines: int = 100) -> str:
    """Retrieve build logs for debugging deployment issues.

    Fetches the build logs from the cloud manager to help diagnose
    deployment failures or issues.

    Args:
      build_id: The build identifier to get logs for
      max_lines: Maximum number of log lines to retrieve (default: 100)

    Returns:
      Build logs as formatted text, or error message
    """
    try:

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return "Error: CLOUD_MANAGER_HOST environment variable not configured."

        # Construct logs URL
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        logs_url = os.getenv(
            "BUILD_LOGS_URL", f"{protocol}://{cloud_manager_host}/build/logs"
        )

        logger.info(f"Retrieving build logs for build_id: {build_id}")

        # Make logs request
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{logs_url}?build_id={build_id}&max_lines={max_lines}"
            )
            response.raise_for_status()

            data = response.json()
            logs = data.get("logs", "")

            if not logs:
                return f"No logs available for build {build_id}. The build may not have started yet."

            # Format logs for display
            result = f"""📋 **Build Logs for {build_id}**

```
{logs}
```

Showing last {max_lines} lines. For complete logs, check the cloud manager dashboard."""

            logger.info(f"Retrieved {len(logs)} characters of logs for {build_id}")
            return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: Build ID '{build_id}' not found or logs not available yet."
        error_msg = f"Logs request failed with status {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return f"Error: {error_msg}"
    except httpx.HTTPError as e:
        error_msg = f"Network error retrieving build logs: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error retrieving build logs: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}"
