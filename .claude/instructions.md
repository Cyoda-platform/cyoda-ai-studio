# Claude Instructions for Cyoda AI Studio

## Project Overview

This is a Python-based LLM application project using Google's Agent Development Kit (ADK). When working on this codebase, you MUST strictly comply with all guidelines and standards defined below.

## 1. Primary Code Guidelines

**CRITICAL:** You MUST read and follow all standards defined in:
- `llm_code_guidelines.md`

Key principles from these guidelines:
- **Max function size:** 50 lines (refactor/split if exceeded)
- **Max file size:** 350 lines (refactor/split if exceeded)
- **Function ideal size:** 5-20 lines (30+ indicates too much complexity)
- **Line length:** 120 characters maximum
- **Arguments:** 0-2 ideal, 3+ requires dataclass/Pydantic model
- **Type hints:** Mandatory for all function signatures
- **Naming:** snake_case for functions/variables, PascalCase for classes, SCREAMING_SNAKE for constants

### Code Organization Principles
1. **Top-Down Narrative:** High-level logic at the top, details below (caller above callee)
2. **Single Responsibility:** Each function does ONE thing
3. **Fail Fast:** Validate inputs and LLM responses immediately
4. **Pure Functions:** Prefer stateless functions for testability
5. **Command Query Separation:** Functions either do something OR answer something, not both

### LLM-Specific Requirements
- **Prompt Separation:** Never hardcode long prompts in Python logic
  - Store prompts in `application/agents/shared/prompts/` as `.yaml` or `.txt` files
- **Structured Outputs:** Always use Pydantic models for LLM outputs
- **Token Consciousness:** Log token usage and latency for LLM interactions
- **Centralized Config:** Use centralized Config object, never `os.getenv()` in business logic

## 2. Google ADK (Agent Development Kit) Reference

This project uses Google's ADK for Python. Reference documentation:
- **Full Documentation:** https://github.com/google/adk-python/blob/main/llms-full.txt
- **Quick Reference:** https://github.com/google/adk-python/blob/main/llms.txt

### ADK Core Concepts

**Agent Types:**
- **LLM Agents:** Use language models for reasoning and dynamic decision-making
- **Workflow Agents:** Control execution flow in predefined patterns
- **Custom Agents:** Allow unique operational logic and specialized integrations

**Model Integration:**
```python
from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="agent_name",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    tools=[google_search]
)
```

**Supported Models:**
- Direct: Google Gemini models
- Via LiteLLM: Various cloud and proprietary models
- Local: Ollama integration
- Self-hosted endpoints
- Vertex AI deployment

**Installation:**
```bash
# Stable
pip install google-adk

# Development
pip install git+https://github.com/google/adk-python.git@main
```

### ADK Best Practices
1. **Rich Tool Ecosystem:** Utilize pre-built tools, custom functions, OpenAPI specs
2. **Code-First Development:** Define agent logic, tools, and orchestration directly in Python
3. **Modular Multi-Agent Systems:** Design scalable applications by composing specialized agents
4. **Deployment Flexibility:** Deploy to Cloud Run, Vertex AI Agent Engine, or anywhere

## 3. Code Review Checklist

Before completing any task, verify:
1. ✓ **DRY:** No logic duplication
2. ✓ **Size:** Functions < 50 lines, Files < 350 lines
3. ✓ **Typed:** Python type hints present on all signatures
4. ✓ **Narrative:** Code reads top-to-bottom like a story
5. ✓ **Safe:** Error handling for LLM calls
6. ✓ **Abstraction:** Lines in a function at the same level of abstraction
7. ✓ **Pure:** Functions avoid side effects where possible
8. ✓ **Named:** Variables/functions reveal intent without comments

## 4. Project-Specific Patterns

### Module Boundaries
- **Interface vs. Implementation:** Keep LLM provider details in `infrastructure`/`adapter` layer
- **Domain Logic:** Should not care which model is being used

### Import Organization
1. Standard library imports
2. Third-party library imports
3. Local module imports

### Defensive Programming
- Use Google-style docstrings for complex logic
- Replace magic values with named constants
- Use exceptions instead of error codes
- Avoid temporal couplings from side effects

## 5. Cyoda Platform Integration

### Quick Reference Documentation

**ALWAYS consult these files when working with Cyoda APIs or entities:**

1. **`llm_docs/outputs/cyoda-api-sitemap-llms.txt`** - API endpoint reference with navigation
   - Use for: Finding specific API endpoints, navigating to API documentation
   - Contains: All 79 API endpoints organized by category with clickable links to full docs

2. **`llm_docs/outputs/cyoda-api-descriptions-llms.txt`** - API section descriptions
   - Use for: Understanding API categories and their purposes
   - Contains: Detailed descriptions of 13 API sections (Entity Management, Search, OAuth, etc.)

3. **`llm_docs/outputs/cyoda-docs-llms.txt`** - Platform concepts & guides
   - Use for: Understanding EDBMS, Event-Driven Architecture, CPL, schemas
   - Contains: Complete documentation sitemap with 105+ pages including guides, concepts, and schema references

### Cyoda Core Concepts

**Entity Management:**
- Entities are versioned data objects with state machines
- Use `POST /entity/{format}` to create, `GET /entity/{entityId}` to retrieve
- Entity models define schema: `GET /model/` to list all models

**Search & Queries:**
- Synchronous: `POST /search/{entityName}/{modelVersion}`
- Async (large datasets): `POST /search/snapshot/{entityName}/{modelVersion}`
- Always include proper pagination for snapshot results

**Workflows:**
- Export: `GET /model/{entityName}/{modelVersion}/workflow/export`
- Import: `POST /model/{entityName}/{modelVersion}/workflow/import`
- Workflows define entity lifecycle and state transitions

**Authentication:**
- M2M (Machine-to-Machine) clients for service accounts
- OAuth 2.0 Client Credentials flow
- Steps:
  1. Create M2M client: `POST /clients`
  2. Get token: `POST /oauth/token` with client_id/secret
  3. Use Bearer token in `Authorization` header

### Common Integration Patterns

**Repository Pattern:**
```python
# Use existing repositories in common/repository/cyoda/
from common.repository.cyoda.cyoda_repository import CyodaRepository

# Always handle pagination for large result sets
async def search_entities(repo: CyodaRepository, entity_name: str):
    condition = {"field": "status", "operator": "=", "value": "active"}
    entities = await repo.search(
        entity_class=entity_name,
        condition=condition,
        entity_version="1.0"
    )
```

**Edge Message Pattern:**
```python
# Use EdgeMessagePersistenceService for file/message storage
from application.services.edge_message_persistence_service import (
    EdgeMessagePersistenceService
)

edge_id = await edge_service.save_message_as_edge_message(
    message_type="file",
    message_content=base64_content,
    conversation_id=conv_id,
    user_id=user_id,
    metadata={"filename": "data.txt", "encoding": "base64"}
)
```

**Streaming Service Pattern:**
```python
# For AI responses with SSE (Server-Sent Events)
from application.services.streaming_service import StreamingService

# Always accumulate content from 'chunk' field (not 'content')
event_data = json.loads(sse_event)
chunk = event_data.get("chunk") or event_data.get("content")
accumulated_response += chunk
```

### Cyoda-Specific Best Practices

1. **Always Version Entities:** Entity models require version (e.g., "1.0", "2.0")
2. **Use Conditions for Search:** Follow JSON structure: `{"field": "x", "operator": "=", "value": "y"}`
3. **Handle Point-in-Time Queries:** Parse ISO strings to datetime before passing to repository
4. **Validate Workflows:** Export existing workflows before importing to avoid conflicts
5. **Token Management:** Cache M2M tokens (1 hour expiry), implement refresh logic

### Error Handling Guidelines

**Cyoda API Errors:**
- 401: Token expired → Refresh with `POST /oauth/token`
- 404: Entity/Model not found → Check entity_name and version
- 400: Invalid search condition → Validate JSON structure
- 500: Platform error → Check logs, may need retry with backoff

## 6. Working with This Codebase

### Key Directories
- `application/agents/` - Agent implementations
- `application/agents/shared/prompts/` - Prompt templates (YAML/TXT)
- `application/agents/tests/evals/` - Evaluation tests
- `common/` - Shared utilities and repositories
- `common/repository/cyoda/` - Cyoda platform integration
- `llm_docs/outputs/` - **API & platform documentation (READ FIRST)**

### Current Branch Context
- Main branch: `main`
- Always create PRs against `main` unless specified otherwise

## 7. Remember

> "Code is read 10x more often than it is written. Prioritize the next developer's understanding over 'clever' one-liners."

> "A function should be followed by the functions it calls."

> "If you need a comment to explain a variable name, the name is wrong."

---

**When in doubt:**
1. **Code Standards:** Consult `llm_code_guidelines.md`
2. **Cyoda APIs:** Check `llm_docs/outputs/cyoda-api-sitemap-llms.txt` for endpoint documentation
3. **API Categories:** Review `llm_docs/outputs/cyoda-api-descriptions-llms.txt` for section descriptions
4. **Cyoda Concepts:** Review `llm_docs/outputs/cyoda-docs-llms.txt` for platform architecture and guides
5. **ADK Framework:** Reference Google ADK docs at https://github.com/google/adk-python
6. **Integration Patterns:** Look for existing implementations in `common/repository/cyoda/`
7. Ask for clarification before violating any of these standards

**Quick Troubleshooting:**
- **401 errors?** → Token expired, check `llm_docs/outputs/cyoda-api-descriptions-llms.txt` OAuth section
- **Field name mismatches?** → Streaming uses `chunk`, not `content` (see Section 5)
- **Point-in-time queries failing?** → Parse ISO strings to datetime first
- **File attachments not persisting?** → Use EdgeMessagePersistenceService with base64 encoding
