import sys
from pathlib import Path

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv
load_dotenv()

# Add project root to path (for IDE compatibility when running directly)
# This ensures imports work whether running as module or directly
project_root = Path(__file__).parent.parent.resolve()
project_root_str = str(project_root)

# Remove application directory from path if it's there and add project root
if sys.path and Path(sys.path[0]).name == 'application':
    sys.path[0] = project_root_str
elif project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

import asyncio
import logging
from typing import Callable, Dict, Optional

from quart import Quart, Response, jsonify, request
from quart_rate_limiter import RateLimiter
from quart_schema import QuartSchema, ResponseSchemaValidationError, hide

from common.exception.exception_handler import (
    register_error_handlers as _register_error_handlers,
)
from services.services import get_grpc_client, initialize_services

# Import blueprints for different route groups
from application.routes import chat_bp, labels_config_bp, tasks_bp, token_bp
from application.routes.repository_routes import repository_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)

# Initialize rate limiter
RateLimiter(app)

QuartSchema(
    app,
    info={"title": "AI Assistant Application", "version": "1.0.0"},
    tags=[
        {
            "name": "Chat",
            "description": "Chat conversation management endpoints",
        },
        {"name": "Token", "description": "Token generation endpoints"},
        {"name": "Tasks", "description": "Background task tracking endpoints"},
        {"name": "System", "description": "System and health endpoints"},
    ],
    security=[{"bearerAuth": []}],
    security_schemes={
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
        }
    },
)

# Global holder for the background task to satisfy mypy
# (avoid setting arbitrary attrs on app)
_background_task: Optional[asyncio.Task[None]] = None


# Register error handlers for custom and generic exceptions
@app.errorhandler(ResponseSchemaValidationError)
async def handle_response_validation_error(
    error: ResponseSchemaValidationError,
) -> tuple[Dict[str, str], int]:
    # You can log/inspect `error` if needed
    return {"error": "VALIDATION"}, 500


# Give mypy a typed view of the external function (if it lacks type hints)
_register_error_handlers_typed: Callable[[Quart], None] = (  # type: ignore[assignment]
    _register_error_handlers
)
_register_error_handlers_typed(app)

# Register blueprints
app.register_blueprint(chat_bp, url_prefix="/api/v1/chats")
app.register_blueprint(token_bp, url_prefix="/api/v1")
app.register_blueprint(labels_config_bp, url_prefix="/api/v1/labels_config")
app.register_blueprint(tasks_bp, url_prefix="/api/v1/tasks")
app.register_blueprint(repository_bp)  # URL prefix already set in blueprint


@app.route("/favicon.ico")
@hide
def favicon() -> tuple[str, int]:
    return "", 200


# Startup tasks: initialize services and start the GRPC stream in the background
@app.before_serving
async def startup() -> None:
    from services.config import get_service_config, validate_configuration

    # Validate configuration and log any issues
    validation = validate_configuration()
    if not validation["valid"]:
        logger.error("Service configuration validation failed!")
        raise RuntimeError("Invalid service configuration")

    # Initialize services with validated configuration
    config = get_service_config()
    logger.info("Initializing services at application startup...")
    initialize_services(config)
    logger.info("All services initialized successfully at startup")

    # Get the gRPC client and start the stream
    grpc_client = get_grpc_client()

    # The stream method is expected to be an async coroutine returning None
    stream_coro = grpc_client.grpc_stream()
    global _background_task
    _background_task = asyncio.create_task(stream_coro)  # type: ignore[arg-type]


# Shutdown tasks: cancel the background tasks when shutting down
@app.after_serving
async def shutdown() -> None:
    """Cleanup tasks on shutdown."""
    logger.info("Shutting down application...")

    global _background_task
    # Cancel the background gRPC stream task
    if _background_task is not None:
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass
        finally:
            _background_task = None

    logger.info("Application shutdown complete")


# Middleware to add CORS headers to every response
@app.before_serving
async def add_cors_headers() -> None:
    @app.after_request
    async def apply_cors(response: Response) -> Response:
        # Allow all origins (using JWT auth, not cookies, so credentials not needed)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


# Handle OPTIONS preflight requests for CORS
@app.route("/<path:path>", methods=["OPTIONS"])
async def handle_options(path: str) -> tuple[Response, int]:
    """Handle CORS preflight OPTIONS requests."""
    response = jsonify({"status": "ok"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response, 200


if __name__ == "__main__":
    import os

    host = os.getenv("APP_HOST", "127.0.0.1")  # Default to localhost for security
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("APP_DEBUG", "false").lower() == "true"
    app.run(use_reloader=False, debug=debug, host=host, port=port)
