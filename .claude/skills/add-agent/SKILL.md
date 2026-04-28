---
name: add-agent
description: Use this skill when creating a new ADK agent or modifying existing agent structure.
tags: [agent, adk, google-adk, development]
---

# Add Agent Skill

## Purpose
Guide for adding new Google ADK agents to the Cyoda AI Studio project.

## When to Use This Skill
- Creating a new ADK agent
- Adding tools to an existing agent
- Setting up agent evaluations
- Modifying agent prompts

## Prerequisites
- Google ADK installed (`pip install google-adk`)
- Understanding of agent purpose and tools needed
- Prompt template prepared

## Step-by-Step Workflow

### 1. Create Agent Directory Structure

```bash
mkdir -p application/agents/{agent_name}/{scripts,references}
touch application/agents/{agent_name}/__init__.py
touch application/agents/{agent_name}/agent.py
```

### 2. Define Agent in `agent.py`

```python
from google.adk.agents import Agent
from google.adk.tools import tool_name

# Load instruction from prompt file
with open("application/agents/shared/prompts/{agent_name}.txt", "r") as f:
    instruction = f.read()

{agent_name}_agent = Agent(
    name="{agent_name}",
    model="gemini-2.5-flash",  # or "gemini-2.0-pro" for complex reasoning
    instruction=instruction,
    tools=[tool_name],
    # Optional: sub-agents for delegation
    # sub_agents=[other_agent]
)
```

### 3. Create Prompt Template

```bash
# Create prompt file
cat > application/agents/shared/prompts/{agent_name}.txt <<'EOF'
You are a {role} agent responsible for {purpose}.

Your capabilities:
- {capability_1}
- {capability_2}

Guidelines:
1. {guideline_1}
2. {guideline_2}

Always validate inputs and return structured outputs using provided tools.
EOF
```

### 4. Register Agent in Coordinator

```python
# In application/agents/coordinator/agent.py
from application.agents.{agent_name}.agent import {agent_name}_agent

coordinator = Agent(
    name="coordinator",
    model="gemini-2.5-flash",
    instruction=coordinator_instruction,
    sub_agents=[
        existing_agent,
        {agent_name}_agent,  # Add here
    ]
)
```

### 5. Create Evaluation Tests

```bash
mkdir -p application/agents/tests/evals/{agent_name}
cat > application/agents/tests/evals/{agent_name}/test_{agent_name}.py <<'EOF'
import pytest
from google.adk.evals import create_eval

@create_eval("test_{agent_name}_basic")
async def test_basic_functionality():
    """Test basic {agent_name} functionality."""
    from application.agents.{agent_name}.agent import {agent_name}_agent

    response = await {agent_name}_agent.run("Test query")
    assert response is not None
    assert len(response) > 0

@create_eval("test_{agent_name}_tool_usage")
async def test_tool_usage():
    """Test that agent uses tools correctly."""
    from application.agents.{agent_name}.agent import {agent_name}_agent

    response = await {agent_name}_agent.run("Query requiring tool")
    # Add assertions based on expected tool usage
    assert "expected_output" in response.lower()
EOF
```

### 6. Run Evaluations

```bash
# Run specific agent evals
cd application/agents/tests/evals/{agent_name}
python -m google.adk.evals.run test_{agent_name}.py

# Or run all evals
make test-eval
```

### 7. Verify Code Quality

```bash
# Check function sizes and complexity
make complexity

# Run linters
make lint

# Run tests
make test-coverage
```

## Common Patterns

### Multi-Modal Agent (with vision)

```python
multi_modal_agent = Agent(
    name="vision_agent",
    model="gemini-2.5-flash",  # Supports vision
    instruction="Analyze images and extract information.",
    tools=[image_analysis_tool]
)
```

### Agent with Structured Output

```python
from pydantic import BaseModel

class OutputSchema(BaseModel):
    field1: str
    field2: int

structured_agent = Agent(
    name="structured_agent",
    model="gemini-2.5-flash",
    instruction="Return structured data.",
    output_schema=OutputSchema
)
```

### Agent with Sub-Agents (Delegation)

```python
coordinator = Agent(
    name="coordinator",
    model="gemini-2.5-flash",
    instruction="Coordinate tasks between specialists.",
    sub_agents=[specialist1, specialist2]
)
```

## Best Practices

1. **Prompt Separation**
   - ✅ Store prompts in `application/agents/shared/prompts/`
   - ❌ Never hardcode long prompts in Python

2. **Function Size**
   - ✅ Keep functions under 50 lines
   - ✅ Split complex logic into helpers

3. **Type Safety**
   - ✅ Use Pydantic models for structured outputs
   - ✅ Add type hints to all function signatures

4. **Testing**
   - ✅ Write evals for each major capability
   - ✅ Test tool usage, not just responses
   - ✅ Use `@create_eval` decorator

5. **Model Selection**
   - Use `gemini-2.5-flash` for speed (default)
   - Use `gemini-2.0-pro` for complex reasoning
   - Use `gemini-2.5-flash` for vision tasks

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent not responding | Check model quota/limits |
| Tool not being called | Verify tool is registered in agent definition |
| Eval failing | Check mock data in `eval_mocking.py` |
| Import error | Ensure `__init__.py` exists in agent directory |

## Reference Files

- `application/agents/cyoda_assistant/agent.py` - Example agent
- `application/agents/coordinator/agent.py` - Multi-agent coordinator
- `application/agents/shared/prompts/` - Prompt templates
- `application/agents/tests/evals/` - Evaluation examples
- ADK docs: https://github.com/google/adk-python/blob/main/llms-full.txt

## Checklist

- [ ] Agent directory created
- [ ] `agent.py` defined with proper structure
- [ ] Prompt template created in `shared/prompts/`
- [ ] Tools registered (if needed)
- [ ] Agent registered in coordinator (if applicable)
- [ ] Evaluation tests written
- [ ] Evals pass (`make test-eval`)
- [ ] Code quality checks pass (`make check-all`)
- [ ] Documentation updated
