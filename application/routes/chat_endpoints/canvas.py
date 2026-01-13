"""Canvas questions endpoint."""

import logging
from datetime import timedelta
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_rate_limiter import rate_limit

from application.routes.chat_endpoints.helpers import get_canvas_question_service
from application.routes.common.rate_limiting import default_rate_limit_key
from application.services import GoogleADKService
from application.services.openai.canvas_question_service import CanvasQuestionService

logger = logging.getLogger(__name__)

canvas_bp = Blueprint("chat_canvas", __name__)

# Initialize Google ADK service
google_adk_service = GoogleADKService()


async def _parse_canvas_question_request() -> (
    tuple[str | None, str | None, Dict[str, Any]]
):
    """Parse canvas question request data."""
    data = await request.get_json()
    return data.get("question"), data.get("response_type"), data.get("context", {})


def _validate_canvas_question_input(
    question: str | None, response_type: str | None
) -> tuple[Any, int] | None:
    """Validate canvas question input. Returns error response if invalid."""
    if not question:
        return jsonify({"error": "Missing required field: question"}), 400
    if not response_type:
        return jsonify({"error": "Missing required field: response_type"}), 400
    return None


def _validate_response_type(
    service: CanvasQuestionService, response_type: str
) -> tuple[Any, int] | None:
    """Validate response type. Returns error response if invalid."""
    is_valid, error_msg = service.validate_response_type(response_type)
    if not is_valid:
        return (
            jsonify(
                {
                    "error": "Invalid request",
                    "details": {"field": "response_type", "message": error_msg},
                }
            ),
            400,
        )
    return None


async def _generate_structured_response(
    service: CanvasQuestionService,
    response_type: str,
    question: str,
    context: Dict[str, Any],
) -> tuple[Dict[str, Any], str]:
    """Generate structured response using Google ADK."""
    schema = service.get_schema(response_type)
    prompt = service.build_prompt(response_type, question, context)
    generated_data = await google_adk_service.generate_structured_output(
        prompt=prompt,
        schema=schema,
        system_instruction=(
            "You are an expert in Cyoda platform configuration. "
            "Generate valid, production-ready configurations."
        ),
    )
    message = (
        f"I've created a {response_type.replace('_', ' ')} based on your requirements."
    )
    return generated_data, message


async def _generate_text_response(question: str) -> tuple[Dict[str, Any], str]:
    """Generate text response using Google ADK or mock."""
    if google_adk_service.is_configured():
        text_response = await google_adk_service.generate_response(
            prompt=question,
            system_instruction="You are a helpful AI assistant for the Cyoda platform.",
        )
        return {"text": text_response}, text_response

    mock_text = f"[MOCK] Response to: {question}"
    return {"text": mock_text}, mock_text


async def _generate_canvas_response(
    service: CanvasQuestionService,
    response_type: str,
    question: str,
    context: Dict[str, Any],
) -> tuple[Dict[str, Any], str]:
    """Generate canvas response using service or fallback to mock."""
    try:
        if google_adk_service.is_configured() and response_type != "text":
            return await _generate_structured_response(
                service, response_type, question, context
            )

        if response_type == "text":
            return await _generate_text_response(question)

        logger.warning("Google ADK not configured - using mock response")
        generated_data = service.generate_mock_response(
            response_type, question, context
        )
        response_name = response_type.replace("_", " ")
        message = (
            f"[MOCK] I've created a {response_name} based on your requirements. "
            f"Please configure GOOGLE_API_KEY for real AI generation."
        )
        return generated_data, message

    except Exception as ai_error:
        logger.exception(f"Error generating canvas response: {ai_error}")
        mock_data = service.generate_mock_response(response_type, question, context)
        message = f"Error generating response: {str(ai_error)}. Using fallback data."
        return mock_data, message


@canvas_bp.route("/canvas-questions", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def submit_canvas_question() -> tuple[Any, int]:
    """Submit a canvas question for stateless AI generation."""
    try:
        question, response_type, context = await _parse_canvas_question_request()

        error_response = _validate_canvas_question_input(question, response_type)
        if error_response:
            return error_response

        service = get_canvas_question_service(google_adk_service)
        error_response = _validate_response_type(service, response_type)
        if error_response:
            return error_response

        generated_data, message = await _generate_canvas_response(
            service, response_type, question, context
        )

        return (
            jsonify(
                {
                    "message": message,
                    "hook": {
                        "type": response_type.replace("_json", "_config"),
                        "action": "preview",
                        "data": generated_data,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.exception(f"Error in canvas question: {e}")
        return jsonify({"error": str(e)}), 400
