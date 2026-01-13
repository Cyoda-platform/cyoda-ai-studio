#!/usr/bin/env python3
"""
Start the Cyoda MCP server in HTTP mode for the environment_mcp agent.

This script starts the cyoda_mcp server in HTTP mode so that the environment_mcp agent
can connect to it via HTTP instead of spawning subprocesses.
"""

import logging
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Start the Cyoda MCP server in HTTP mode."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Set environment variables for HTTP transport
        os.environ["MCP_TRANSPORT"] = "http"
        os.environ["MCP_HOST"] = "127.0.0.1"
        os.environ["MCP_PORT"] = "8002"

        logger.info("Starting Cyoda MCP server in HTTP mode...")
        logger.info("Server will be available at: http://127.0.0.1:8002/mcp")
        logger.info("The server will accept user credentials via HTTP headers:")
        logger.info("  - X-Cyoda-Client-Id")
        logger.info("  - X-Cyoda-Client-Secret")
        logger.info("  - X-Cyoda-Host")
        logger.info("")
        logger.info("Press Ctrl+C to stop the server")

        # Import and start the server
        from cyoda_mcp.server import start

        start(transport="http", host="127.0.0.1", port=8002)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start Cyoda MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
