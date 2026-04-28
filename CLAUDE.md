# Cyoda AI Studio - Project Brain

> **Last Updated:** 2026-04-28
> **AI-Native Documentation:** This project is optimized for Claude Code and modern AI agents.

## Project Persona

**Cyoda AI Studio** is a Python-based MCP (Model Context Protocol) server that bridges AI assistants with the Cyoda platform's entity management, search, workflow, and deployment capabilities.

### Tech Stack & Philosophy

- **Language:** Python 3.10+ (async-first with asyncio/await)
- **AI Framework:** Google ADK (Agent Development Kit) 1.21.0
- **Web Framework:** Quart 0.20.0 (async Flask alternative)
- **Protocol:** MCP (Model Context Protocol) via fastmcp 2.12.3
- **Communication:** gRPC + REST for Cyoda platform integration
- **Validation:** Pydantic 2.12.3 for data models
- **Testing:** pytest + ADK evals
- **Code Style:** Black (88 chars) + isort + flake8 + bandit

### Architectural Principles

1. **Async-First:** All I/O operations use `async/await`
2. **Function Size:** Max 50 lines, ideal 5-20 lines
3. **File Size:** Max 350 lines (split if exceeded)
4. **Type Safety:** Mandatory type hints on all function signatures
5. **Separation of Concerns:** Prompts live in YAML/TXT files, not code
6. **Top-Down Narrative:** High-level logic at top, details below (caller above callee)
7. **Fail Fast:** Validate inputs and LLM responses immediately

## Command Cheat Sheet

```bash
# Development Setup
python -m venv .venv && source .venv/bin/activate
make install                    # Install all dependencies

# Testing & Quality
make test-coverage              # Run tests with coverage report
make test-eval                  # Run ADK agent evaluations
make lint                       # Run all linters (Black, isort, flake8, bandit)
make complexity                 # Run lizard complexity analysis
make check-all                  # Run all checks + generate reports
make open-reports               # Open all HTML reports in browser

# Running the Application
python run.py                   # Run Quart web app (http://127.0.0.1:8000)
python -m cyoda_mcp            # Run MCP server for AI assistants
mcp-cyoda                       # Run installed MCP package

# Code Formatting (auto-fix)
black . && isort .              # Format code + sort imports

# Environment Variables (required)
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-123.eu.cyoda.net"

# Utility Scripts
python scripts/import_workflows.py --list                    # List workflows
python scripts/import_workflows.py --entity X --version 1    # Import workflow

# Build & Package
python -m build                                              # Build package
pipx install dist/mcp_cyoda-0.1.7-py3-none-any.whl         # Install locally
```

## Directory Map

```
cyoda-ai-studio/
├── application/           # Business logic & agents
│   ├── agents/           # ADK agents (coordinator, cyoda_assistant, github, qa)
│   │   └── shared/prompts/  # Prompt templates (YAML/TXT)
│   ├── entity/           # Entity definitions (conversation, task, etc.)
│   ├── routes/           # Quart API endpoints
│   └── services/         # Business services
├── common/               # Shared utilities & Cyoda integration
│   ├── proto/           # gRPC proto definitions
│   ├── repository/      # Data access layer (Cyoda REST/gRPC)
│   ├── service/         # Entity service interface
│   └── config/          # Configuration & constants
├── cyoda_mcp/           # MCP server implementation
├── services/            # Top-level service layer
├── tests/               # Unit & integration tests
├── scripts/             # Utility scripts
├── llm_docs/            # LLM-optimized documentation
├── .claude/             # Claude Code configuration
│   ├── instructions.md  # Detailed coding guidelines
│   └── skills/          # Specialized workflows (see below)
├── CLAUDE.md            # This file (project brain)
├── llms.txt             # AI documentation sitemap
└── Makefile             # Build automation
```

## Decision Log

### Architectural Decisions

1. **Why Google ADK?**
   - Code-first agent development (no YAML configs)
   - Multi-modal support (Gemini integration)
   - Built-in evaluation framework
   - Flexible tool ecosystem

2. **Why Quart over Flask?**
   - Native async/await support (required for ADK)
   - Compatible with Flask ecosystem
   - Better performance for I/O-bound operations

3. **Why Pydantic?**
   - Mandatory for ADK structured outputs
   - Runtime validation + type safety
   - Auto-generated JSON schemas

4. **Why MCP Protocol?**
   - Universal AI assistant integration (Claude, Cursor, etc.)
   - Standardized tool/resource discovery
   - Streaming support for real-time updates

5. **Prompt Separation Decision**
   - Prompts stored in `application/agents/shared/prompts/` as YAML/TXT
   - Rationale: Version control, A/B testing, non-engineer editing
   - Never hardcode multi-line prompts in Python

### Code Organization Decisions

1. **Max Function Size: 50 Lines**
   - Enforced by complexity analysis
   - Ideal: 5-20 lines
   - Split into helpers if exceeded

2. **Top-Down Narrative**
   - Caller functions appear above callee functions
   - Read like a newspaper: headline → details
   - Public API at top of file, private helpers below

3. **Fail Fast Pattern**
   ```python
   # DO: Validate immediately
   if not entity_id:
       raise ValueError("entity_id required")

   # DON'T: Check later in logic
   result = process_entity(entity_id)
   if not entity_id:  # Too late!
       return None
   ```

## Quick Start for New Contributors

1. **Read These First (in order):**
   - This file (`CLAUDE.md`)
   - `.claude/instructions.md` - Detailed coding standards
   - `llm_code_guidelines.md` - Function size/naming rules
   - `llm_docs/outputs/cyoda-api-sitemap-llms.txt` - Cyoda API reference

2. **Set Up Environment:**
   ```bash
   git clone <repo> && cd cyoda-ai-studio
   python -m venv .venv && source .venv/bin/activate
   make install
   cp .env.template .env  # Add your Cyoda credentials
   ```

3. **Verify Setup:**
   ```bash
   make test-coverage     # Should pass
   make lint              # Should pass
   python run.py          # Should start web app
   ```

4. **Make Changes:**
   - Always create a feature branch from `develop`
   - Run `make check-all` before committing
   - PRs target `main` branch (see git status above)

## Common Tasks & Patterns

### Adding a New Agent

```python
# File: application/agents/my_agent/agent.py
from google.adk.agents import Agent

my_agent = Agent(
    name="my_agent",
    model="gemini-2.5-flash",
    instruction="Load from application/agents/shared/prompts/my_agent.txt",
    tools=[tool1, tool2]
)
```

### Cyoda Entity Operations

```python
# Use entity_service, never direct repository access
from app_init.app_init import entity_service, cyoda_auth_service

# Create
entity_id = await entity_service.add_item(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version="1.0",
    entity={"field": "value"}
)

# Read
entity = await entity_service.get_item(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version="1.0",
    technical_id=entity_id
)

# Search
results = await entity_service.get_items_by_condition(
    token=cyoda_auth_service,
    entity_model="MyEntity",
    entity_version="1.0",
    condition={
        "jsonPath": "$.status",
        "operatorType": "EQUALS",
        "value": "active"
    }
)
```

### Streaming Responses (SSE)

```python
# IMPORTANT: Accumulate from 'chunk' field, not 'content'
event_data = json.loads(sse_event)
chunk = event_data.get("chunk") or event_data.get("content")
accumulated_response += chunk
```

## Critical Files Reference

| File Path | Purpose | When to Consult |
|-----------|---------|-----------------|
| `.claude/instructions.md` | Detailed coding guidelines | Before writing any code |
| `llm_code_guidelines.md` | Function size/naming rules | When refactoring |
| `llm_docs/outputs/cyoda-api-sitemap-llms.txt` | Cyoda API endpoints | When calling Cyoda APIs |
| `llm_docs/outputs/cyoda-docs-llms.txt` | Cyoda platform concepts | When designing features |
| `pyproject.toml` | Dependencies & config | When adding packages |
| `Makefile` | Build commands | When running tests |

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| **401 Unauthorized** | Token expired → check `cyoda_auth_service.refresh()` |
| **Field name mismatch** | Streaming uses `chunk`, not `content` |
| **Point-in-time query fails** | Parse ISO string to datetime first |
| **File upload fails** | Use `EdgeMessagePersistenceService` with base64 |
| **Import circular dependency** | Use lazy imports in function scope |
| **Tests fail on CI** | Check `.env` variables are set in CI |
| **Test suite timeout** | Full suite takes ~5-10 min; run individual tests: `pytest tests/unit/test_file.py` |
| **GitHub MCP warnings** | Non-blocking; custom tools work fine; optional GitHub token in `.env` |

## Documentation Navigation

- **For API Integration:** See `llm_docs/outputs/cyoda-api-sitemap-llms.txt`
- **For Platform Concepts:** See `llm_docs/outputs/cyoda-docs-llms.txt`
- **For Coding Standards:** See `.claude/instructions.md`
- **For Skills (Specialized Workflows):** See `.claude/skills/` directory
- **For AI Universal Docs:** See `llms.txt` (root)

## Git Workflow

- **Main Branch:** `main` (PRs target this)
- **Current Branch:** `develop`
- **Feature Branches:** `feature/my-feature` (branch from `develop`)
- **Commit Convention:** Use descriptive messages, reference issues

---

## For AI Assistants

**When you (Claude Code or other AI) work on this codebase:**

1. **Always check CLAUDE.md first** (this file)
2. **Follow guidelines in `.claude/instructions.md`** (detailed standards)
3. **Use skills in `.claude/skills/`** when available (specialized workflows)
4. **Consult `llm_docs/` for Cyoda platform specifics**
5. **Run `make check-all` before marking work complete**
6. **Never hardcode prompts** - use `application/agents/shared/prompts/`
7. **Never exceed 50 lines per function** - split if needed
8. **Never use `os.getenv()` in business logic** - use centralized Config

**Key Principles:**
- Top-down narrative (caller above callee)
- Fail fast (validate inputs immediately)
- Pure functions (avoid side effects)
- Type hints mandatory
- Async-first (always use async/await for I/O)

**Common Mistakes to Avoid:**
- ❌ Hardcoding prompts in Python code
- ❌ Functions > 50 lines
- ❌ Missing type hints
- ❌ Calling repository directly (use entity_service)
- ❌ Forgetting to handle token expiry (401 errors)
- ❌ Using `content` instead of `chunk` for streaming

---

**Project Status:** Active Development
**License:** MIT
**Support:** https://github.com/Cyoda-platform/quart-client-template/issues
