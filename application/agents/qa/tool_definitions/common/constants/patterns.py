"""Cyoda design patterns and best practices."""

from __future__ import annotations

CYODA_PATTERNS = {
    "no reflection": {
        "principle": "Avoid dynamic imports and reflection",
        "reason": "Improves code clarity and IDE support",
        "instead": "Use common module patterns and explicit imports",
        "example": "from common.entity import CyodaEntity",
    },
    "thin routes": {
        "principle": "Routes are proxies to EntityService",
        "reason": "Separation of concerns, testability",
        "pattern": "Route -> EntityService -> Cyoda",
        "example": "await entity_service.create(entity_data)",
    },
    "manual transitions": {
        "principle": "Use manual transitions for entity updates",
        "reason": "Explicit state management, workflow control",
        "usage": 'entity_service.update(..., transition="approve")',
        "avoid": "Automatic transitions for business logic",
    },
    "technical ids": {
        "principle": "Prefer technical IDs over business IDs",
        "reason": "Guaranteed uniqueness, performance",
        "usage": "entity_service.get_by_id(entity_id=uuid)",
        "avoid": "Searching by business fields when ID is known",
    },
    "workflow-managed state": {
        "principle": "Entity state is read-only",
        "reason": "Workflow controls lifecycle",
        "management": "State changes via transitions only",
        "avoid": "Direct state field modification",
    },
}
