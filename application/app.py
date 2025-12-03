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
import os
from typing import Callable, Dict, Optional

from quart import Quart, Response, jsonify, request
from quart_rate_limiter import RateLimiter
from quart_schema import QuartSchema, ResponseSchemaValidationError, hide

from common.exception.exception_handler import (
    register_error_handlers as _register_error_handlers,
)
from services.services import get_grpc_client, initialize_services

# Import blueprints for different route groups
from application.routes import chat_bp, labels_config_bp, logs_bp, metrics_bp, tasks_bp, token_bp
from application.routes.repository_routes import repository_bp

# Configure root logging to both stdout and a file for debugging/triage.
# Default file is app-log.log in the current working directory; override with APP_LOG_FILE.
log_file = os.getenv("APP_LOG_FILE", "app-log.log")
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode="a"),
    ],
)

# Enable LiteLLM debug mode if DEBUG_LITELLM is set
if os.getenv("DEBUG_LITELLM", "false").lower() == "true":
    import litellm
    litellm._turn_on_debug()
    logger = logging.getLogger(__name__)
    logger.info("🔍 LiteLLM debug mode enabled")

# Enable detailed debug logging for Google ADK internals so we see
# any streaming timeouts/shutdowns or silent failures.
adk_logger = logging.getLogger("google_adk")
adk_logger.setLevel(logging.DEBUG)

# Enable debug logging for OpenAI SDK if DEBUG_OPENAI is set
if os.getenv("DEBUG_OPENAI", "false").lower() == "true":
    try:
        from agents import enable_verbose_stdout_logging
        enable_verbose_stdout_logging()
        logger = logging.getLogger(__name__)
        logger.info("🔍 OpenAI SDK debug mode enabled")

        # Also enable tracing logger
        tracing_logger = logging.getLogger("openai.agents.tracing")
        tracing_logger.setLevel(logging.DEBUG)
        tracing_logger.addHandler(logging.StreamHandler(sys.stdout))
    except ImportError:
        logger = logging.getLogger(__name__)
        logger.warning("DEBUG_OPENAI is set but OpenAI agents SDK is not installed")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)

# Extend Quart timeouts for long-lived SSE responses
# RESPONSE_TIMEOUT controls how long Quart will wait to finish sending a response
# before cancelling the handler task.
# BODY_TIMEOUT controls how long to wait for the request body; kept for completeness.
response_timeout = os.getenv("QUART_RESPONSE_TIMEOUT")
body_timeout = os.getenv("QUART_BODY_TIMEOUT")

if response_timeout is not None:
    app.config["RESPONSE_TIMEOUT"] = int(response_timeout)
else:
    app.config["RESPONSE_TIMEOUT"] = 600  # 10 minutes

if body_timeout is not None:
    app.config["BODY_TIMEOUT"] = int(body_timeout)
else:
    app.config["BODY_TIMEOUT"] = 600

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
app.register_blueprint(logs_bp)  # URL prefix already set in blueprint
app.register_blueprint(metrics_bp)  # URL prefix already set in blueprint
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
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    import sys

    host = os.getenv("APP_HOST", "127.0.0.1")  # Default to localhost for security
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("APP_DEBUG", "false").lower() == "true"
    timeout = int(os.getenv("APP_TIMEOUT", "600"))  # 10 minutes default for long-running streams

    # Configure Hypercorn with extended timeouts for SSE streaming
    config = Config()
    config.bind = [f"{host}:{port}"]

    # Critical timeouts for long-running SSE streams
    config.keep_alive_timeout = timeout  # Keep-alive for SSE connections
    config.shutdown_timeout = timeout    # Allow graceful shutdown of long streams
    config.startup_timeout = timeout     # Allow slow startup
    config.graceful_timeout = 30         # Graceful shutdown timeout

    # CRITICAL: Set websocket_ping_interval to prevent connection drops
    # Even though we're using SSE, not WebSocket, this affects keep-alive behavior
    config.websocket_ping_interval = None  # Disable WebSocket ping (we use SSE heartbeat)

    # Set h11 max incomplete event size (prevents early connection close)
    # This is an internal h11 setting that Hypercorn uses
    config.h11_max_incomplete_event_size = 16 * 1024 * 1024  # 16MB

    # Optional: read_timeout (None = no timeout, which is fine for SSE)
    # config.read_timeout = None  # Already None by default

    if debug:
        config.loglevel = "DEBUG"
        config.accesslog = "-"  # Log to stdout
        config.errorlog = "-"

    logger.info(f"Starting Cyoda AI Studio on {host}:{port}")
    logger.info(f"Timeouts configured:")
    logger.info(f"  - keep_alive_timeout: {config.keep_alive_timeout}s")
    logger.info(f"  - shutdown_timeout: {config.shutdown_timeout}s")
    logger.info(f"  - startup_timeout: {config.startup_timeout}s")
    logger.info(f"  - graceful_timeout: {config.graceful_timeout}s")
    logger.info(f"  - read_timeout: {config.read_timeout}")
    logger.info(f"  - websocket_ping_interval: {config.websocket_ping_interval}")
    logger.info(f"  - h11_max_incomplete_event_size: {config.h11_max_incomplete_event_size}")
    logger.info(f"Debug mode: {debug}")

    # Verify config is actually applied
    logger.info(f"Config object: {config}")

    # Run with Hypercorn (supports async and has proper timeout configuration)
    asyncio.run(serve(app, config))
