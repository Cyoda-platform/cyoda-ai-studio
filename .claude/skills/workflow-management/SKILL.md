---
name: workflow-management
description: Use this skill when managing Cyoda entity workflows (FSM-based state machines).
tags: [workflow, fsm, state-machine, cyoda]
---

# Workflow Management Skill

## Purpose
Guide for creating, exporting, importing, and debugging Cyoda entity workflows (Finite State Machines).

## When to Use This Skill
- Creating new entity workflows
- Modifying existing workflows
- Exporting/importing workflows
- Debugging workflow transitions
- Implementing workflow processors

## Workflow Architecture

Cyoda workflows are **Finite State Machines (FSM)** with:
- **States** - Discrete stages in entity lifecycle
- **Transitions** - Paths between states
- **Processors** - Functions executed during transitions
- **Criterions** - Conditions that determine which transition to take

```
none → state_01 → state_02 → state_terminal
         ↓           ↓
      [processor] [criterion]
```

## Workflow JSON Structure

### Basic Template

```json
{
  "version": "1.0",
  "name": "entity_workflow",
  "desc": "Entity lifecycle workflow",
  "initialState": "none",
  "active": true,
  "states": {
    "none": {
      "transitions": [
        {
          "name": "initialize",
          "next": "created"
        }
      ]
    },
    "created": {
      "transitions": [
        {
          "name": "process",
          "next": "processed",
          "processors": [
            {
              "name": "process_entity",
              "executionMode": "ASYNC_NEW_TX",
              "config": {
                "attachEntity": true,
                "calculationNodesTags": "cyoda_application",
                "responseTimeoutMs": 3000,
                "retryPolicy": "FIXED"
              }
            }
          ]
        }
      ]
    },
    "processed": {
      "transitions": []
    }
  }
}
```

### States

```json
"state_name": {
  "transitions": [
    // Array of possible transitions from this state
  ]
}
```

**Best Practices:**
- Always start from `"initialState": "none"`
- End with terminal states (no transitions)
- Avoid loops (can cause infinite processing)

### Transitions

#### Simple Transition

```json
{
  "name": "transition_name",
  "next": "next_state_name"
}
```

#### Transition with Processor

```json
{
  "name": "process_data",
  "next": "completed",
  "processors": [
    {
      "name": "process_entity_data",  // Maps to Python function
      "executionMode": "ASYNC_NEW_TX",
      "config": {
        "attachEntity": true,
        "calculationNodesTags": "cyoda_application",
        "responseTimeoutMs": 5000,
        "retryPolicy": "FIXED"
      }
    }
  ]
}
```

#### Manual Transition

```json
{
  "name": "manual_approval",
  "next": "approved",
  "manual": true  // Requires explicit trigger
}
```

#### Transition with Simple Criterion

```json
{
  "name": "check_status",
  "next": "active",
  "criterion": {
    "type": "simple",
    "jsonPath": "$.status",
    "operation": "EQUALS",
    "value": "ready"
  }
}
```

#### Transition with Function Criterion

```json
{
  "name": "validate",
  "next": "validated",
  "criterion": {
    "type": "function",
    "function": {
      "name": "is_valid_entity",  // Maps to Python function returning bool
      "config": {
        "attachEntity": true,
        "calculationNodesTags": "cyoda_application",
        "responseTimeoutMs": 5000,
        "retryPolicy": "FIXED"
      }
    }
  }
}
```

#### Transition with Group Criterion

```json
{
  "name": "check_conditions",
  "next": "eligible",
  "criterion": {
    "type": "group",
    "operator": "AND",
    "conditions": [
      {
        "type": "simple",
        "jsonPath": "$.score",
        "operation": "GREATER_OR_EQUAL",
        "value": 80
      },
      {
        "type": "simple",
        "jsonPath": "$.verified",
        "operation": "EQUALS",
        "value": true
      }
    ]
  }
}
```

### Available Operations

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

### Available Operators (for groups)

```python
"AND"  # All conditions must be true
"OR"   # At least one condition must be true
"NOT"  # Negates the condition group
```

## Processor Implementation

Processors are Python functions that execute during transitions.

### File Location

```
application/entity/{entity_name}/workflow.py
```

### Basic Processor

```python
async def process_entity(entity: dict) -> None:
    """
    Process entity during transition.

    Args:
        entity: Entity data (mutable, changes are persisted)
    """
    # Business logic
    result = perform_calculation(entity["input"])

    # Update entity
    entity["result"] = result
    entity["processed"] = True
    entity["processed_at"] = datetime.now().isoformat()
```

### Criterion Function

```python
async def is_valid_entity(entity: dict) -> bool:
    """
    Check if entity meets validation criteria.

    Args:
        entity: Entity data (read-only for criterions)

    Returns:
        True if entity should proceed to next state, False otherwise
    """
    # Validation logic
    return (
        entity.get("status") == "ready" and
        entity.get("score", 0) >= 80
    )
```

### Best Practices for Processors

1. **Single Responsibility**
   ```python
   # ✅ Good: One processor per concern
   async def validate_input(entity: dict):
       entity["validation_status"] = validate(entity["input"])

   async def enrich_data(entity: dict):
       entity["enriched_data"] = fetch_external_data(entity["id"])

   # ❌ Bad: Processor does too much
   async def do_everything(entity: dict):
       # Validates, enriches, transforms, sends notifications...
   ```

2. **Error Handling**
   ```python
   async def safe_processor(entity: dict):
       """Processor with robust error handling."""
       try:
           result = await external_api_call(entity["id"])
           entity["result"] = result
           entity["status"] = "success"
       except Exception as e:
           logger.exception(f"Processor failed: {e}")
           entity["status"] = "failed"
           entity["error"] = str(e)
   ```

3. **Idempotency**
   ```python
   async def idempotent_processor(entity: dict):
       """Safe to run multiple times."""
       # Check if already processed
       if entity.get("processed"):
           logger.info("Already processed, skipping")
           return

       # Process
       entity["result"] = compute_result(entity)
       entity["processed"] = True
   ```

4. **Logging**
   ```python
   import logging

   logger = logging.getLogger(__name__)

   async def logged_processor(entity: dict):
       """Processor with comprehensive logging."""
       entity_id = entity.get("id", "unknown")
       logger.info(f"Processing entity {entity_id}")

       try:
           # Process
           entity["result"] = process_data(entity)
           logger.info(f"Successfully processed {entity_id}")
       except Exception as e:
           logger.exception(f"Failed to process {entity_id}: {e}")
           raise
   ```

## Workflow Operations

### Export Workflow

```python
from common.repository.cyoda.cyoda_repository import CyodaRepository
from app_init.app_init import cyoda_auth_service
import json

repo = CyodaRepository()

# Export workflow
workflow = await repo.export_workflow(
    token=cyoda_auth_service,
    entity_name="MyEntity",
    model_version="1.0"
)

# Save to file
with open("workflow_backup.json", "w") as f:
    json.dump(workflow, f, indent=2)
```

### Import Workflow

```python
import json

# Load workflow
with open("workflow.json", "r") as f:
    workflow_data = json.load(f)

# Import
await repo.import_workflow(
    token=cyoda_auth_service,
    entity_name="MyEntity",
    model_version="1.0",
    workflow_data=workflow_data
)
```

### Using Utility Script

```bash
# List available workflows
python scripts/import_workflows.py --list

# Validate workflow file
python scripts/import_workflows.py \
    --entity MyEntity \
    --version 1 \
    --file path/to/workflow.json \
    --validate-only

# Import workflow
python scripts/import_workflows.py \
    --entity MyEntity \
    --version 1 \
    --file path/to/workflow.json
```

## Debugging Workflows

### Issue: Workflow Not Progressing

**Check current state:**

```python
entity = await entity_service.get_item(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version="1.0",
    technical_id=entity_id
)

print(f"Current state: {entity.get('workflowState')}")
print(f"Workflow name: {entity.get('workflowName')}")
```

**Check for errors:**

```python
# Look for error fields in entity
if "error" in entity:
    print(f"Error: {entity['error']}")
if "workflowError" in entity:
    print(f"Workflow error: {entity['workflowError']}")
```

### Issue: Transition Not Triggering

**Verify criterion:**

```python
# If using simple criterion
criterion = {
    "jsonPath": "$.status",
    "operation": "EQUALS",
    "value": "ready"
}

# Check actual value
actual_value = entity.get("status")
print(f"Expected: 'ready', Actual: '{actual_value}'")
```

**Verify function criterion:**

```python
# Test criterion function directly
from application.entity.my_entity.workflow import is_valid_entity

result = await is_valid_entity(entity)
print(f"Criterion result: {result}")
```

### Issue: Processor Failing

**Check logs:**

```bash
# View application logs
tail -f application/app-log.log

# Look for processor errors
grep "process_entity" application/app-log.log
```

**Add debug logging:**

```python
async def debug_processor(entity: dict):
    """Processor with debug output."""
    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"Processor called with entity: {entity}")

    try:
        result = compute(entity)
        logger.debug(f"Computation result: {result}")

        entity["result"] = result
        logger.info("Processor completed successfully")
    except Exception as e:
        logger.exception(f"Processor failed: {e}")
        raise
```

## Workflow Design Patterns

### 1. Linear Workflow

```
none → created → validated → processed → completed
```

### 2. Branching Workflow

```
none → created → validation
                    ├─(valid)──→ processed
                    └─(invalid)→ rejected
```

### 3. Review Workflow

```
none → draft → submitted → review
                              ├─(approve)──→ approved
                              └─(reject)───→ rejected → resubmitted
```

### 4. Multi-Stage Processing

```
none → stage1 → stage2 → stage3 → final
         ↓         ↓        ↓
     [process1][process2][process3]
```

## Checklist

- [ ] Workflow JSON follows FSM structure
- [ ] All processor names match Python function names
- [ ] All criterion function names match Python functions
- [ ] Initial state is "none"
- [ ] Terminal states have no transitions
- [ ] No loops in workflow (unless intentional)
- [ ] All processors implemented in `workflow.py`
- [ ] All criterion functions return bool
- [ ] Error handling added to processors
- [ ] Workflow validated before import
- [ ] Backup of existing workflow exported
- [ ] Tests written for processors

## Reference Files

- `application/entity/{entity}/workflow.py` - Processor implementations
- `application/resources/workflow/` - Workflow JSON files
- `scripts/import_workflows.py` - Workflow utility script
- `llm_docs/outputs/cyoda-docs-llms.txt` - Workflow concepts

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Processor not found` | Function name mismatch | Check processor name matches Python function |
| `Criterion always false` | Condition logic error | Test criterion function directly |
| `Workflow stuck` | Missing transition | Add transition or make manual |
| `Import failed` | Invalid JSON | Validate with script first |

---

**Quick Reference:**
- Export: `python scripts/import_workflows.py --list`
- Validate: `python scripts/import_workflows.py --validate-only ...`
- Import: `python scripts/import_workflows.py --entity X --version 1 --file Y`
