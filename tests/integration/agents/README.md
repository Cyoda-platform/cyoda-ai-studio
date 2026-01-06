# Cyoda Assistant Agent Evaluation Guide

## Overview

This directory contains comprehensive evaluation tests for the Cyoda AI Assistant multi-agent system using Google ADK's evaluation framework.

**Documentation**: https://google.github.io/adk-docs/evaluate/

## Test Structure

### Unit Tests (`.test.json` files)
Located in `evals/` directory:
- `qa_agent.test.json` - Tests QA agent's ability to answer Cyoda platform questions and provide best practices
- `setup_agent.test.json` - Tests Setup agent's project configuration help
- `coordinator.test.json` - Tests coordinator's delegation to correct sub-agents

### Integration Tests (`.evalset.json` files)
- `cyoda_assistant.evalset.json` - Multi-turn conversation scenarios testing agent coordination

### Configuration
- `test_config.json` - Evaluation criteria, thresholds, and quality checks

## Running Evaluations

### Method 1: Pytest (Recommended for CI/CD)

```bash
# Run all evaluations
pytest tests/integration/agents/test_agent_evaluation.py -v

# Run specific agent tests
pytest tests/integration/agents/test_agent_evaluation.py::TestQAAgent -v
pytest tests/integration/agents/test_agent_evaluation.py::TestSetupAgent -v
pytest tests/integration/agents/test_agent_evaluation.py::TestCoordinatorAgent -v

# Run integration tests
pytest tests/integration/agents/test_agent_evaluation.py::TestCyodaAssistantIntegration -v

# Run with detailed output
pytest tests/integration/agents/test_agent_evaluation.py -v -s

# Run with coverage
pytest tests/integration/agents/test_agent_evaluation.py --cov=application.agents
```

### Method 2: ADK CLI

```bash
# Evaluate all test files in evals/ directory
adk eval --eval-dataset tests/integration/agents/evals/

# Evaluate specific agent
adk eval --eval-dataset tests/integration/agents/evals/qa_agent.test.json

# Evaluate integration tests
adk eval --eval-dataset tests/integration/agents/cyoda_assistant.evalset.json

# With custom config
adk eval --eval-dataset tests/integration/agents/evals/ --config tests/integration/agents/test_config.json
```

### Method 3: ADK Web UI

```bash
# Launch interactive web interface
adk web

# Then:
# 1. Navigate to "Evaluation" section
# 2. Upload or select test files from project
# 3. Run evaluations and view detailed results
# 4. Inspect conversation traces and tool calls
# 5. Export results for analysis
```

## Evaluation Criteria

### 1. Tool Trajectory Average Score (Weight: 0.3)
**What it measures**: Exact match of tool usage sequence

**Scoring**:
- 1.0 = Perfect match (all tools called in correct order)
- 0.5 = Partial match (some tools correct)
- 0.0 = No match (wrong tools or order)

**Threshold**: 0.9 (90% accuracy required)

**Example**:
```json
Expected: ["transfer_to_agent(QA)"]
Actual: ["transfer_to_agent(QA)"]
Score: 1.0 ✓
```

### 2. Response Match Score (Weight: 0.4)
**What it measures**: Semantic similarity between expected and actual responses

**Scoring**:
- Uses embedding-based similarity
- Compares meaning, not exact wording
- Handles paraphrasing and variations

**Threshold**: 0.75 (75% similarity required)

**Example**:
```
Expected: "Entity state is workflow-managed and read-only"
Actual: "Workflows control entity state, which cannot be modified directly"
Score: 0.85 ✓ (semantically similar)
```

### 3. Final Response Match V2 (Weight: 0.3)
**What it measures**: LLM-based quality judgment

**Scoring**:
- Uses LLM to judge response quality
- Evaluates accuracy, completeness, helpfulness
- Checks for hallucinations and errors

**Threshold**: 0.8 (80% quality required)

**Criteria**:
- Factual accuracy
- Completeness of answer
- Relevance to question
- Clarity and helpfulness

## Quality Checks

### Hallucination Detection
Ensures agents don't make up information not grounded in Cyoda documentation.

**Enabled**: Yes

**How it works**:
- Compares responses against known Cyoda facts
- Flags unsupported claims
- Checks for invented features or APIs

### Safety Check
Ensures responses don't contain harmful or inappropriate content.

**Enabled**: Yes

**How it works**:
- Scans for unsafe content
- Checks for malicious code suggestions
- Validates security best practices

### Delegation Accuracy
Verifies coordinator delegates to correct sub-agent based on question topic.

**Enabled**: Yes

**How it works**:
- Checks `transfer_to_agent` calls
- Validates agent selection matches question domain
- Ensures proper routing logic

## Test File Format

### Unit Test Format (`.test.json`)

```json
{
  "eval_set_id": "unique_test_id",
  "name": "Test Suite Name",
  "description": "What this test suite covers",
  "eval_cases": [
    {
      "eval_id": "test_case_id",
      "conversation": [
        {
          "invocation_id": "inv-001",
          "user_content": {
            "parts": [{"text": "User question"}],
            "role": "user"
          },
          "final_response": {
            "parts": [{"text": "Expected response"}],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [
              {"name": "transfer_to_agent", "args": {"agent_name": "QA"}}
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "cyoda-assistant",
        "user_id": "test_user",
        "state": {}
      }
    }
  ]
}
```

### Integration Test Format (`.evalset.json`)

Same structure as unit tests, but with multiple conversation turns:

```json
{
  "eval_cases": [
    {
      "conversation": [
        {"invocation_id": "turn-1", ...},
        {"invocation_id": "turn-2", ...},
        {"invocation_id": "turn-3", ...}
      ]
    }
  ]
}
```

## Adding New Tests

### 1. Create Test File

```bash
# For unit tests
touch tests/integration/agents/evals/new_agent.test.json

# For integration tests
touch tests/integration/agents/new_scenario.evalset.json
```

### 2. Define Test Cases

Follow the format above, including:
- Clear `eval_id` for each test case
- Realistic user questions
- Expected responses (can be approximate)
- Expected tool calls (if testing delegation)

### 3. Run Tests

```bash
pytest tests/integration/agents/test_agent_evaluation.py -v
```

### 4. Iterate

- Review evaluation results
- Adjust expected responses if needed
- Update agent instructions if failing
- Re-run until passing

## Interpreting Results

### Success Criteria

**All tests passing**:
- tool_trajectory_avg_score ≥ 0.9
- response_match_score ≥ 0.75
- final_response_match_v2 ≥ 0.8
- No hallucinations detected
- No safety violations

### Common Failures

**Low tool_trajectory_avg_score**:
- Coordinator delegating to wrong agent
- Missing or extra tool calls
- Fix: Update coordinator instructions

**Low response_match_score**:
- Response semantically different from expected
- Missing key information
- Fix: Update agent instructions or expected response

**Low final_response_match_v2**:
- Response quality issues
- Incomplete or inaccurate answers
- Fix: Improve agent knowledge or instructions

**Hallucination detected**:
- Agent making up information
- Unsupported claims
- Fix: Add grounding, improve instructions

## Best Practices

### Writing Good Test Cases

1. **Realistic Questions**: Use actual user questions
2. **Clear Expectations**: Define what "good" looks like
3. **Edge Cases**: Test boundary conditions
4. **Multi-Turn**: Test conversation context
5. **Diverse Topics**: Cover all agent capabilities

### Maintaining Tests

1. **Update Regularly**: As agents evolve, update tests
2. **Version Control**: Track test changes with code
3. **Document Failures**: Note why tests fail and fixes
4. **Regression Testing**: Keep old tests to prevent regressions

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Run Agent Evaluations
  run: |
    pytest tests/integration/agents/test_agent_evaluation.py -v
    
- name: Check Evaluation Thresholds
  run: |
    # Parse results and fail if below thresholds
    python scripts/check_eval_results.py
```

## Troubleshooting

### Tests Timing Out
- Increase `timeout_seconds` in `test_config.json`
- Check network connectivity to Google AI API
- Verify API key is valid

### Inconsistent Results
- LLM responses can vary slightly
- Use semantic matching, not exact matching
- Set appropriate thresholds (not too strict)

### Import Errors
```bash
# Ensure you're in project root
cd ~/mcp-cyoda-quart-app

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### API Key Issues
```bash
# Check environment variables
echo $GOOGLE_API_KEY

# Set if missing
export GOOGLE_API_KEY="your-key-here"
```

## Resources

- [Google ADK Evaluation Docs](https://google.github.io/adk-docs/evaluate/)
- [Multi-Agent Systems Guide](https://google.github.io/adk-docs/agents/multi-agents/)
- [Agent Architecture README](../../application/agents/README.md)
- [Cyoda Development Guidelines](../../../.augment-guidelines)

