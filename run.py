#!/usr/bin/env python3
"""
Entry point script to run the Cyoda AI Studio application.

This script should be run from the project root directory:
    python run.py

Or with the virtual environment:
    source .venv/bin/activate && python run.py

Environment variables:
    APP_HOST: Host to bind to (default: 127.0.0.1)
    APP_PORT: Port to bind to (default: 8000)
    APP_DEBUG: Enable debug mode (default: false)
    APP_TIMEOUT: Keep-alive timeout in seconds (default: 600)
"""
import os
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

if __name__ == "__main__":
    from application.app import app

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("APP_DEBUG", "false").lower() == "true"
    timeout = int(os.getenv("APP_TIMEOUT", "600"))  # 10 minutes default

    # Configure Hypercorn with extended timeouts for long-running streams
    config = Config()
    config.bind = [f"{host}:{port}"]

    # Critical timeouts for long-running SSE streams
    config.keep_alive_timeout = timeout  # Keep-alive for SSE connections
    config.shutdown_timeout = timeout    # Allow graceful shutdown of long streams
    config.startup_timeout = timeout     # Allow slow startup
    config.graceful_timeout = 30         # Graceful shutdown timeout

    if debug:
        config.loglevel = "DEBUG"
        config.accesslog = "-"  # Log to stdout
        config.errorlog = "-"

    print(f"Starting Cyoda AI Studio on {host}:{port}")
    print(f"Keep-alive timeout: {timeout} seconds")
    print(f"Debug mode: {debug}")

    # Run with Hypercorn
    asyncio.run(serve(app, config))

