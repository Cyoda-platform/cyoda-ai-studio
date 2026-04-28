---
name: cyoda-integration
description: Use this skill when integrating with Cyoda platform APIs (entity management, search, workflows).
tags: [cyoda, api, integration, entity, workflow]
---

# Cyoda Integration Skill

## Purpose
Guide for integrating with Cyoda platform APIs for entity management, search, workflows, and authentication.

## When to Use This Skill
- Creating/reading/updating/deleting entities
- Searching entities with complex conditions
- Managing workflows (export/import)
- Handling authentication tokens
- Debugging Cyoda API errors

## Prerequisites
- Cyoda credentials set in `.env`:
  - `CYODA_CLIENT_ID`
  - `CYODA_CLIENT_SECRET`
  - `CYODA_HOST`
- Understanding of entity models and versions

## Quick Reference Documentation

**ALWAYS consult these files first:**

1. **`llm_docs/outputs/cyoda-api-sitemap-llms.txt`**
   - All 79 API endpoints with navigation
   - Use for: Finding specific endpoints

2. **`llm_docs/outputs/cyoda-api-descriptions-llms.txt`**
   - API section descriptions (OAuth, Entity, Search, etc.)
   - Use for: Understanding API categories

3. **`llm_docs/outputs/cyoda-docs-llms.txt`**
   - Platform concepts (EDBMS, CPL, schemas)
   - Use for: Understanding architecture

## Common Integration Patterns

### 1. Entity CRUD Operations

**Always use `entity_service`, never direct repository access.**

#### Create Entity

```python
from app_init.app_init import entity_service, cyoda_auth_service
from common.config.config import ENTITY_VERSION

entity_id = await entity_service.add_item(
    token=cyoda_auth_service,
    entity_model="MyEntity",  # Entity class name
    entity_version=ENTITY_VERSION,  # Or specific version "1.0"
    entity={
        "field1": "value1",
        "field2": 123,
        "status": "active"
    }
)
# Returns: entity_id (string)
```

#### Read Entity

```python
# Get single entity by ID
entity = await entity_service.get_item(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version=ENTITY_VERSION,
    technical_id=entity_id
)

# Get all entities of a type
entities = await entity_service.get_items(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version=ENTITY_VERSION
)
```

#### Update Entity

```python
await entity_service.update_item(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version=ENTITY_VERSION,
    entity={
        "id": entity_id,  # Technical ID required
        "field1": "updated_value",
        "status": "completed"
    },
    technical_id=entity_id,
    meta={}  # Optional metadata
)
```

#### Delete Entity

```python
await entity_service.delete_item(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version=ENTITY_VERSION,
    technical_id=entity_id,
    meta={}
)
```

### 2. Search Operations

#### Simple Search (Single Condition)

```python
results = await entity_service.get_items_by_condition(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version=ENTITY_VERSION,
    condition={
        "jsonPath": "$.status",
        "operatorType": "EQUALS",
        "value": "active"
    }
)
```

#### Complex Search (Multiple Conditions)

```python
condition = {
    "type": "group",
    "operator": "AND",
    "conditions": [
        {
            "type": "simple",
            "jsonPath": "$.status",
            "operatorType": "EQUALS",
            "value": "active"
        },
        {
            "type": "simple",
            "jsonPath": "$.priority",
            "operatorType": "GREATER_THAN",
            "value": 5
        }
    ]
}

results = await entity_service.get_items_by_condition(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version=ENTITY_VERSION,
    condition=condition
)
```

#### Available Operators

```python
# Comparison
"EQUALS", "NOT_EQUAL"
"GREATER_THAN", "GREATER_OR_EQUAL"
"LESS_THAN", "LESS_OR_EQUAL"

# String Operations
"CONTAINS", "NOT_CONTAINS"
"STARTS_WITH", "NOT_STARTS_WITH"
"ENDS_WITH", "NOT_ENDS_WITH"
"MATCHES_PATTERN"

# Null Checks
"IS_NULL", "NOT_NULL"

# Range
"BETWEEN", "BETWEEN_INCLUSIVE"
```

#### Group Operators

```python
# Logical operators for condition groups
"AND"  # All conditions must be true
"OR"   # At least one condition must be true
"NOT"  # Negates the condition group
```

### 3. Workflow Management

#### Export Workflow

```python
from common.repository.cyoda.cyoda_repository import CyodaRepository

# Via repository (for direct access)
repo = CyodaRepository()
workflow_json = await repo.export_workflow(
    token=cyoda_auth_service,
    entity_name="MyEntity",
    model_version="1.0"
)

# Save to file
import json
with open("workflow_backup.json", "w") as f:
    json.dump(workflow_json, f, indent=2)
```

#### Import Workflow

```python
import json

# Load workflow definition
with open("workflow.json", "r") as f:
    workflow_data = json.load(f)

# Import via repository
await repo.import_workflow(
    token=cyoda_auth_service,
    entity_name="MyEntity",
    model_version="1.0",
    workflow_data=workflow_data
)
```

#### Validate Workflow Before Import

```bash
# Use utility script
python scripts/import_workflows.py \
    --entity MyEntity \
    --version 1 \
    --file path/to/workflow.json \
    --validate-only
```

### 4. Authentication & Token Management

#### Token Expiry Handling

```python
import logging
from common.exception.exception import UnauthorizedException

logger = logging.getLogger(__name__)

try:
    result = await entity_service.get_item(...)
except UnauthorizedException:
    logger.info("Token expired, refreshing...")
    await cyoda_auth_service.refresh()
    # Retry operation
    result = await entity_service.get_item(...)
```

#### Token Best Practices

1. **Cache tokens** - They expire after 1 hour
2. **Implement refresh logic** - Catch 401 errors
3. **Use service singleton** - Don't create multiple auth instances

### 5. Edge Messages (File/Data Storage)

```python
from application.services.edge_message_persistence_service import (
    EdgeMessagePersistenceService
)

edge_service = EdgeMessagePersistenceService()

# Save file as edge message
edge_id = await edge_service.save_message_as_edge_message(
    message_type="file",
    message_content=base64_encoded_content,
    conversation_id=conv_id,
    user_id=user_id,
    metadata={
        "filename": "document.pdf",
        "encoding": "base64",
        "mime_type": "application/pdf"
    }
)

# Retrieve edge message
edge_data = await edge_service.get_edge_message(edge_id)
```

## Error Handling Patterns

### Common API Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| **401** | Unauthorized (token expired) | Refresh token with `cyoda_auth_service.refresh()` |
| **404** | Entity/Model not found | Check entity_name and version spelling |
| **400** | Bad request (invalid condition) | Validate JSON structure and field names |
| **500** | Platform error | Check logs, retry with exponential backoff |

### Robust Error Handling

```python
import logging
from common.exception.exception import (
    UnauthorizedException,
    NotFoundException,
    BadRequestException
)

logger = logging.getLogger(__name__)

async def safe_entity_operation(entity_id: str) -> dict:
    """Example of robust Cyoda operation."""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            return await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="MyEntity",
                entity_version="1.0",
                technical_id=entity_id
            )
        except UnauthorizedException:
            logger.warning("Token expired, refreshing...")
            await cyoda_auth_service.refresh()
            retry_count += 1
        except NotFoundException:
            logger.error(f"Entity {entity_id} not found")
            raise
        except BadRequestException as e:
            logger.error(f"Invalid request: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            retry_count += 1
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff

    raise Exception(f"Failed after {max_retries} retries")
```

## Point-in-Time Queries

```python
from datetime import datetime

# Parse ISO timestamp to datetime
pit_timestamp = datetime.fromisoformat("2024-01-01T00:00:00Z")

entities = await repo.search_entities_at_point_in_time(
    entity_class="MyEntity",
    point_in_time=pit_timestamp,
    condition=search_condition
)
```

## Best Practices

1. **Always Use Service Layer**
   - ✅ Use `entity_service` for all operations
   - ❌ Never call repository directly from business logic

2. **Version Management**
   - ✅ Use `ENTITY_VERSION` constant from config
   - ✅ Document version changes in entity files

3. **Search Optimization**
   - ✅ Use specific conditions (don't fetch all then filter)
   - ✅ Implement pagination for large result sets
   - ✅ Use snapshot search for async large queries

4. **Type Safety**
   - ✅ Entity IDs are strings, not integers
   - ✅ Use Pydantic models for validation

5. **Logging**
   - ✅ Log token refresh events
   - ✅ Log API errors with context
   - ✅ Use structured logging with entity IDs

## Troubleshooting Guide

### Issue: 401 Unauthorized

```python
# Check token expiry
logger.info(f"Token expires at: {cyoda_auth_service.token_expiry}")

# Force refresh
await cyoda_auth_service.refresh()
```

### Issue: Field Not Found in Search

```python
# Verify field exists in entity model
entity = await entity_service.get_item(...)
logger.info(f"Available fields: {entity.keys()}")

# Check jsonPath syntax (must start with $.)
condition = {"jsonPath": "$.my_field", ...}  # Correct
condition = {"jsonPath": "my_field", ...}    # Wrong
```

### Issue: Workflow Import Fails

```bash
# Validate workflow file first
python scripts/import_workflows.py \
    --entity MyEntity --version 1 \
    --file workflow.json --validate-only

# Check existing workflows
python scripts/import_workflows.py --list
```

## Reference Files

- `common/service/entity_service_interface.py` - Service interface
- `common/repository/cyoda/cyoda_repository.py` - Repository implementation
- `llm_docs/outputs/cyoda-api-sitemap-llms.txt` - API endpoints
- `llm_docs/outputs/cyoda-docs-llms.txt` - Platform documentation
- `scripts/import_workflows.py` - Workflow utility

## Checklist

- [ ] Credentials configured in `.env`
- [ ] Using `entity_service`, not repository directly
- [ ] Entity version specified correctly
- [ ] Error handling for 401 (token expiry)
- [ ] Search conditions validated
- [ ] Type hints added (entity_id: str)
- [ ] Logging added for debugging
- [ ] Tests written for integration
