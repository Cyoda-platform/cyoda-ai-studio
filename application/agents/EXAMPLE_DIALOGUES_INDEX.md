# Cyoda AI Assistant - Example Dialogues Index

This document provides an index of all example dialogue files for the Cyoda AI Assistant multi-agent system.

## Overview

The Cyoda AI Assistant uses a multi-agent architecture where specialized agents handle different aspects of Cyoda development. Each agent has comprehensive example dialogues demonstrating their capabilities.

---

## Agent Example Dialogues

### 1. QA Agent
**Location:** `application/agents/qa/tests/example_dialogues.md`

**Purpose:** Cyoda platform expert that answers questions about architecture, concepts, entity management, workflows, and troubleshooting.

**Example Topics:**
- Understanding technical IDs and business IDs
- Entity concepts and lifecycle
- Workflow mechanics
- EntityService pattern
- Repository structure
- Troubleshooting entity creation
- Loading external documentation

**Key Tools:**
- `search_cyoda_concepts` - Search Cyoda documentation
- `explain_cyoda_pattern` - Explain design patterns
- `load_web_page` - Load web documentation

---

### 2. Guidelines Agent
**Location:** `application/agents/guidelines/tests/example_dialogues.md`

**Purpose:** Cyoda development expert providing guidelines, best practices, and design patterns for Pythonic Cyoda development.

**Example Topics:**
- No reflection principle
- Common module usage
- Thin routes pattern
- Testing best practices
- Pythonic code style
- Error handling
- Code organization
- Processor design

**Key Tools:**
- `get_design_principle` - Retrieve design principles
- `get_testing_guideline` - Get testing guidelines
- `load_web_page` - Load documentation

---

### 3. Setup Agent
**Location:** `application/agents/setup/tests/example_dialogues.md`

**Purpose:** Cyoda setup and configuration specialist for project initialization, environment setup, and getting started.

**Example Topics:**
- Environment variable validation
- Project structure validation
- Workflow file validation
- Getting user information
- Checking deployment status
- Listing and reading files
- Complete setup workflows

**Key Tools:**
- `validate_environment` - Check environment variables
- `check_project_structure` - Validate project structure
- `validate_workflow_file` - Validate workflows
- `get_user_info` - Get user information
- `list_directory_files` - List files
- `read_file` - Read file contents

---

### 4. Environment Agent
**Location:** `application/agents/environment/tests/example_dialogues.md`

**Purpose:** Environment management specialist handling provisioning, deployment, monitoring, and credential management.

**Example Topics:**
- Checking environment existence
- Deploying new environments
- Deploying user applications
- Checking deployment status
- Handling deployment failures
- Retrieving build logs
- Issuing technical credentials
- Multi-turn deployment workflows

**Key Tools:**
- `check_environment_exists` - Check environment status
- `deploy_cyoda_environment` - Deploy environments
- `deploy_user_application` - Deploy applications
- `get_deployment_status` - Get deployment status
- `get_build_logs` - Retrieve logs
- `issue_technical_user` - Issue credentials

---

### 5. GitHub Agent
**Location:** `application/agents/github/tests/example_dialogues.md`

**Purpose:** Repository operations, code generation, file management, and GitHub integration specialist.

**Example Topics:**
- Analyzing repository structure
- Checking repository diffs
- Committing and pushing changes
- Generating code with CLI
- Saving files to repository
- Pulling latest changes
- Getting entity/workflow paths
- Executing Unix commands
- Generating complete applications
- End-to-end feature development

**Key Tools:**
- `analyze_repository_structure` - Analyze repository
- `commit_and_push_changes` - Git operations
- `generate_code_with_cli` - Code generation
- `save_file_to_repository` - File management
- `pull_repository_changes` - Pull updates
- `execute_unix_command` - Run commands
- `generate_application` - Generate full apps

---

### 6. Monitoring Agent
**Location:** `application/agents/monitoring/tests/example_dialogues.md`

**Purpose:** Specialized LoopAgent for continuous deployment monitoring with real-time status updates.

**Example Topics:**
- Successful deployment monitoring
- Failed deployment monitoring
- Long-running deployments
- Deployments with warnings
- Timeout scenarios
- Immediate completion
- Deployment rollbacks
- How the monitoring loop works

**Key Tools:**
- `check_deployment_and_decide` - Check status and decide action
- `wait_before_next_check` - Wait between checks
- `exit_loop` - Exit monitoring loop

**Architecture:**
- Uses LoopAgent pattern with two sub-agents
- Checks status every 30 seconds
- Maximum 60 iterations (30 minutes)
- Automatic escalation on completion/failure

---

## How to Use These Examples

### For Developers
1. **Understanding Agent Capabilities**: Read the example dialogues to understand what each agent can do
2. **Testing Agents**: Use examples as test cases for agent development
3. **Writing Prompts**: Learn how to phrase requests to get the best results
4. **Integration**: Understand how agents work together in multi-turn conversations

### For Users
1. **Learning**: See how to interact with each agent effectively
2. **Reference**: Use examples as templates for your own questions
3. **Troubleshooting**: Find similar scenarios to your issues
4. **Best Practices**: Learn the recommended ways to use each agent

### For QA/Testing
1. **Test Scenarios**: Use dialogues as test cases
2. **Expected Behavior**: Understand what good responses look like
3. **Edge Cases**: See how agents handle various situations
4. **Validation**: Verify agent responses match expected patterns

---

## Agent Interaction Patterns

### Single-Agent Interactions
Most queries are handled by a single specialized agent:
- **QA Agent**: "What is a technical ID?"
- **Guidelines Agent**: "What are testing best practices?"
- **Setup Agent**: "Validate my environment variables"

### Multi-Agent Workflows
Complex tasks involve multiple agents:

**Example: Complete Application Development**
1. **Setup Agent**: Validate environment and project structure
2. **GitHub Agent**: Generate application code
3. **Environment Agent**: Deploy to environment
4. **Monitoring Agent**: Monitor deployment progress

**Example: Troubleshooting Deployment**
1. **Environment Agent**: Check deployment status
2. **Environment Agent**: Retrieve build logs
3. **QA Agent**: Explain error messages
4. **Guidelines Agent**: Suggest fixes based on best practices

### Agent Transfers
Agents can transfer to other agents when needed:
- **Environment Agent** → **Monitoring Agent**: For long-running deployments
- **Coordinator** → **Specialized Agent**: Based on user query

---

## Example Dialogue Format

Each example dialogue follows this structure:

```markdown
## Example Dialogue N: [Title]

**User:** [User's question or request]

**Agent:** [Agent's response]

*[Calls: tool_name(parameters)]*

**Agent:** [Agent's response with tool results]

**User:** [Follow-up question] (if multi-turn)

**Agent:** [Follow-up response]
```

---

## Testing with Example Dialogues

### Unit Testing
Use examples to create unit tests for individual agents:

```python
@pytest.mark.asyncio
async def test_qa_agent_technical_id():
    """Test QA agent explaining technical IDs."""
    # Based on Example Dialogue 1 from qa/tests/example_dialogues.md
    result = await agent.process("What is a technical ID in Cyoda?")
    assert "UUID" in result
    assert "unique" in result.lower()
```

### Integration Testing
Use multi-turn examples for integration tests:

```python
@pytest.mark.asyncio
async def test_complete_deployment_workflow():
    """Test complete deployment workflow across agents."""
    # Based on multi-agent workflow examples
    # 1. Setup validation
    # 2. Code generation
    # 3. Deployment
    # 4. Monitoring
```

---

## Contributing New Examples

When adding new example dialogues:

1. **Follow the Format**: Use the established dialogue format
2. **Be Realistic**: Base examples on real use cases
3. **Show Tool Calls**: Include tool invocations with parameters
4. **Include Variations**: Show success, failure, and edge cases
5. **Multi-turn When Relevant**: Demonstrate conversation flow
6. **Add Context**: Explain what the example demonstrates
7. **Update This Index**: Add new examples to this index file

---

## Related Documentation

- **Agent Evaluation Tests**: `tests/integration/agents/evals/`
- **Agent Implementation**: `application/agents/*/agent.py`
- **Agent Tools**: `application/agents/*/tools.py`
- **Agent Prompts**: `application/agents/*/prompts/`
- **Integration Tests**: `tests/integration/agents/test_agent_evaluation.py`

---

## Quick Reference

| Agent | Primary Use Case | Example File |
|-------|-----------------|--------------|
| QA | Platform questions, concepts, troubleshooting | `qa/tests/example_dialogues.md` |
| Guidelines | Best practices, design patterns, code style | `guidelines/tests/example_dialogues.md` |
| Setup | Project setup, validation, configuration | `setup/tests/example_dialogues.md` |
| Environment | Deployment, credentials, environment management | `environment/tests/example_dialogues.md` |
| GitHub | Repository operations, code generation | `github/tests/example_dialogues.md` |
| Monitoring | Deployment monitoring, status updates | `monitoring/tests/example_dialogues.md` |

---

## Feedback and Improvements

These example dialogues are living documents. If you:
- Find gaps in coverage
- Discover new use cases
- Identify unclear examples
- Have suggestions for improvements

Please update the relevant example dialogue file and this index.

---

**Last Updated:** 2024-01-15
**Version:** 1.0
**Maintainer:** Cyoda AI Assistant Team

