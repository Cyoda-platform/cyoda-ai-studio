"""Tools for the Guidelines agent."""

from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]


async def get_design_principle(tool_context: ToolContext, principle: str) -> dict[str, Any]:
    """Get detailed information about a Cyoda design principle.

    Args:
      tool_context: The ADK tool context
      principle: The principle name to look up.

    Returns:
      Dictionary with principle details and examples.
    """
    principles = {
        "no reflection": {
            "description": "Avoid dynamic imports and reflection in Cyoda applications",
            "rationale": "Improves code clarity, IDE support, and maintainability",
            "instead_use": "Common module patterns with explicit imports",
            "example": """# Bad: Dynamic import
module = __import__(f'application.{entity_name}')

# Good: Explicit import
from common.entity import CyodaEntity""",
        },
        "use common module": {
            "description": "Shared code goes in common/, not application-specific modules",
            "rationale": "Promotes code reuse and prevents circular dependencies",
            "structure": "common/ contains reusable components, application/ contains app-specific code",
            "example": """# Common module structure
common/
  entity/
    cyoda_entity.py
  services/
    entity_service.py""",
        },
        "thin routes": {
            "description": "Routes are thin proxies to EntityService, no business logic",
            "rationale": "Separation of concerns, testability, maintainability",
            "pattern": "Route -> EntityService -> Cyoda",
            "example": """@app.route('/entities', methods=['POST'])
async def create_entity():
    data = await request.get_json()
    result = await entity_service.create(data)
    return jsonify(result)""",
        },
        "prefer technical ids": {
            "description": "Use entity technical IDs (UUIDs) over business identifiers",
            "rationale": "Guaranteed uniqueness, better performance, simpler queries",
            "usage": "Always use technical ID when available",
            "example": """# Good: Use technical ID
entity = await entity_service.get_by_id(entity_id=uuid)

# Avoid: Search by business field when ID is known
entities = await entity_service.search({'business_id': value})""",
        },
        "manual transitions only": {
            "description": "Use manual transitions for entity state updates",
            "rationale": "Explicit state management, workflow control, auditability",
            "usage": "Always specify transition parameter in updates",
            "example": """# Good: Manual transition
await entity_service.update(
    entity_id=uuid,
    entity=data,
    transition='approve'
)

# Avoid: Automatic transitions for business logic""",
        },
        "workflow-managed state": {
            "description": "Entity state is read-only, managed by workflows",
            "rationale": "Workflow controls lifecycle, prevents invalid states",
            "rule": "Never modify state field directly",
            "example": """# Good: Change state via transition
await entity_service.update(..., transition='approve')

# Bad: Direct state modification
entity.state = 'APPROVED'  # Don't do this!""",
        },
    }

    principle_lower = principle.lower()

    for key, value in principles.items():
        if principle_lower in key or key in principle_lower:
            return {
                "found": True,
                "principle": key,
                "details": value,
            }

    return {
        "found": False,
        "principle": principle,
        "available_principles": list(principles.keys()),
    }


async def get_testing_guideline(tool_context: ToolContext, topic: str) -> dict[str, Any]:
    """Get testing guidelines for Cyoda applications.

    Args:
      tool_context: The ADK tool context
      topic: The testing topic to look up.

    Returns:
      Dictionary with testing guidelines and examples.
    """
    guidelines = {
        "unit tests": {
            "description": "Test individual functions and methods in isolation",
            "coverage": "Aim for >80% code coverage",
            "structure": "One test file per module (test_module.py)",
            "example": """def test_validate_environment(monkeypatch):
    monkeypatch.setenv('CYODA_HOST', 'localhost')
    result = validate_environment(['CYODA_HOST'])
    assert result['CYODA_HOST'] is True""",
        },
        "integration tests": {
            "description": "Test agent behavior and tool usage",
            "approach": "Use real ADK components, mock only external dependencies",
            "example": """@pytest.mark.asyncio
async def test_agent_uses_tool():
    runner = Runner(agent=root_agent)
    response = await runner.run_async('Check environment')
    assert response.text is not None""",
        },
        "mocking": {
            "description": "Mock external dependencies, not ADK components",
            "principle": "Test behavior, not implementation",
            "example": """def test_with_mock(mocker):
    mock_service = mocker.patch('module.external_service')
    mock_service.return_value = {'status': 'ok'}
    result = function_under_test()
    assert result is not None""",
        },
        "fixtures": {
            "description": "Use pytest fixtures for common setup",
            "benefits": "Reduces duplication, improves readability",
            "example": """@pytest.fixture
def sample_entity():
    return {'id': 'uuid', 'name': 'test'}

def test_with_fixture(sample_entity):
    assert sample_entity['name'] == 'test' """,
        },
    }

    topic_lower = topic.lower()

    for key, value in guidelines.items():
        if topic_lower in key or key in topic_lower:
            return {
                "found": True,
                "topic": key,
                "details": value,
            }

    return {
        "found": False,
        "topic": topic,
        "available_topics": list(guidelines.keys()),
    }
