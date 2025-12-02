"""
Application routes package.

Contains all API endpoint blueprints for the AI Assistant.
"""

from application.routes.chat import chat_bp
from application.routes.labels_config import labels_config_bp
from application.routes.tasks import tasks_bp
from application.routes.token import token_bp

__all__ = ["chat_bp", "labels_config_bp", "tasks_bp", "token_bp"]
