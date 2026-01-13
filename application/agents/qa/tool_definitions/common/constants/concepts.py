"""Cyoda concepts and terminology."""

from __future__ import annotations

CYODA_CONCEPTS = {
    "technical id": {
        "definition": "Unique UUID identifier for entities in Cyoda",
        "usage": "Prefer technical IDs over business IDs for entity operations",
        "example": 'entity_service.get_by_id(entity_id="uuid-here")',
    },
    "entity": {
        "definition": "Core data object in Cyoda with lifecycle and state management",
        "components": ["technical ID", "business data", "state", "workflow"],
        "operations": ["create", "read", "update", "delete", "transition"],
    },
    "workflow": {
        "definition": "State machine defining entity lifecycle and transitions",
        "components": ["states", "transitions", "processors"],
        "types": ["manual transitions", "automatic transitions"],
    },
    "processor": {
        "definition": "Event handler for entity state changes",
        "types": ["calc", "criteria", "ack", "error", "keep_alive"],
        "execution": "Triggered by gRPC events from Cyoda",
    },
    "grpc": {
        "definition": "Communication protocol between Cyoda client and server",
        "usage": "Event-driven processing via gRPC streams",
        "events": ["calc", "criteria", "ack", "error"],
    },
    "state": {
        "definition": "Current lifecycle stage of an entity",
        "management": "Workflow-managed and read-only",
        "transitions": "Changed via manual transitions only",
    },
}
