"""Canvas Question Service for AI-powered canvas generation."""

import logging
from typing import Any, Dict

from application.services import GoogleADKService

logger = logging.getLogger(__name__)

VALID_RESPONSE_TYPES = [
    "entity_json",
    "workflow_json",
    "app_config_json",
    "environment_json",
    "requirement_json",
    "text",
]


class CanvasQuestionService:
    """Service for handling canvas question generation."""

    def __init__(self, adk_service: GoogleADKService):
        self.adk_service = adk_service

    def validate_response_type(self, response_type: str) -> tuple[bool, str]:
        """Validate response type is supported."""
        if response_type not in VALID_RESPONSE_TYPES:
            message = f"Must be one of: {', '.join(VALID_RESPONSE_TYPES)}"
            return False, message
        return True, ""

    def get_schema(self, response_type: str) -> Dict[str, Any]:
        """Get JSON schema for structured output based on response type."""
        schemas = {
            "entity_json": self._entity_schema(),
            "workflow_json": self._workflow_schema(),
            "app_config_json": self._app_config_schema(),
        }
        return schemas.get(response_type, self._generic_schema())

    def build_prompt(
        self, response_type: str, question: str, context: Dict[str, Any]
    ) -> str:
        """Build detailed prompt for canvas question generation."""
        base_prompt = f"User request: {question}\n\n"

        prompts = {
            "entity_json": (
                "Generate a Cyoda entity configuration with:\n"
                "- A descriptive name (PascalCase)\n"
                "- Fields with name, type (string/number/boolean/date), and required flag\n"
                "- A clear description of the entity's purpose\n"
            ),
            "workflow_json": (
                "Generate a workflow configuration with:\n"
                "- A descriptive name\n"
                "- States (array of state names)\n"
                "- Transitions (from state, to state, transition name)\n"
                "- Initial state\n"
            ),
            "app_config_json": (
                f"Generate an application configuration for '{context.get('app_name', 'MyApp')}' with:\n"
                "- Application name\n"
                "- List of entities\n"
                "- List of workflows\n"
                "- Programming language (python/java/javascript)\n"
            ),
        }

        base_prompt += prompts.get(response_type, "")

        if context:
            base_prompt += f"\n\nAdditional context: {context}"

        return base_prompt

    def generate_mock_response(
        self, response_type: str, question: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate mock structured response for canvas questions (fallback)."""
        mocks = {
            "entity_json": {
                "name": "MockEntity",
                "fields": [
                    {"name": "id", "type": "string", "required": True},
                    {"name": "name", "type": "string", "required": True},
                    {"name": "description", "type": "string", "required": False},
                ],
                "description": f"Mock entity generated from: {question[:50]}",
            },
            "workflow_json": {
                "name": "MockWorkflow",
                "states": ["draft", "active", "completed"],
                "transitions": [
                    {"from": "draft", "to": "active", "name": "activate"},
                    {"from": "active", "to": "completed", "name": "complete"},
                ],
                "initial_state": "draft",
            },
            "app_config_json": {
                "app_name": context.get("app_name", "MockApp"),
                "entities": ["MockEntity"],
                "workflows": ["MockWorkflow"],
                "language": context.get("language", "python"),
            },
        }
        return mocks.get(response_type, {"mock": True, "type": response_type})

    @staticmethod
    def _entity_schema() -> Dict[str, Any]:
        """Entity JSON schema."""
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "required": {"type": "boolean"},
                        },
                    },
                },
                "description": {"type": "string"},
            },
            "required": ["name", "fields"],
        }

    @staticmethod
    def _workflow_schema() -> Dict[str, Any]:
        """Workflow JSON schema."""
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "states": {"type": "array", "items": {"type": "string"}},
                "transitions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "name": {"type": "string"},
                        },
                    },
                },
                "initial_state": {"type": "string"},
            },
            "required": ["name", "states", "transitions", "initial_state"],
        }

    @staticmethod
    def _app_config_schema() -> Dict[str, Any]:
        """App config JSON schema."""
        return {
            "type": "object",
            "properties": {
                "app_name": {"type": "string"},
                "entities": {"type": "array", "items": {"type": "string"}},
                "workflows": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string"},
            },
            "required": ["app_name"],
        }

    @staticmethod
    def _generic_schema() -> Dict[str, Any]:
        """Generic schema for other types."""
        return {
            "type": "object",
            "properties": {"data": {"type": "object"}, "message": {"type": "string"}},
        }
