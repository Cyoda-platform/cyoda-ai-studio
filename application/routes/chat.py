"""
Chat Routes for AI Assistant Application

Manages all chat-related API endpoints including CRUD operations,
question/answer flow, and canvas questions.

This module acts as a thin orchestration layer that imports and registers
endpoint blueprints from dedicated endpoint modules.
"""

import logging

from quart import Blueprint

# Import endpoint blueprints
from application.routes.chat_endpoints.canvas import canvas_bp
from application.routes.chat_endpoints.crud import crud_bp
from application.routes.chat_endpoints.list_and_create import list_create_bp
from application.routes.chat_endpoints.stream import stream_bp
from application.routes.chat_endpoints.workflow import workflow_bp

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


# Register endpoint blueprints
chat_bp.register_blueprint(list_create_bp)
chat_bp.register_blueprint(crud_bp)
chat_bp.register_blueprint(stream_bp)
chat_bp.register_blueprint(canvas_bp)
chat_bp.register_blueprint(workflow_bp)
