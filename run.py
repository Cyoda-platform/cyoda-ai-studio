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
"""
import os

if __name__ == "__main__":
    from application.app import app

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("APP_DEBUG", "false").lower() == "true"

    app.run(use_reloader=False, debug=debug, host=host, port=port)

