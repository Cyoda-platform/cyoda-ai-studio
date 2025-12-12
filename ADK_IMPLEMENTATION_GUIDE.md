# Google ADK Implementation Guide for Cyoda

## 1. Workflow Agents (High Priority)

### Use Case: Sequential Entity Validation Pipeline
```python
from google.adk.agents import SequentialAgent, LlmAgent

# Step 1: Validate entity structure
validator = LlmAgent(
    name="EntityValidator",
    instruction="Validate entity JSON structure",
    output_key="validation_status"
)

# Step 2: Check for required fields
field_checker = LlmAgent(
    name="FieldChecker",
    instruction="Check required fields in {validation_status}",
    output_key="field_check_result"
)

# Step 3: Generate entity
generator = LlmAgent(
    name="EntityGenerator",
    instruction="Generate entity if {field_check_result} is valid",
    output_key="generated_entity"
)

# Orchestrate as sequential pipeline
entity_pipeline = SequentialAgent(
    name="EntityCreationPipeline",
    sub_agents=[validator, field_checker, generator]
)
```

### Use Case: Parallel Data Fetching
```python
from google.adk.agents import ParallelAgent, SequentialAgent

# Fetch from multiple sources concurrently
fetch_api1 = LlmAgent(name="API1Fetcher", output_key="api1_data")
fetch_api2 = LlmAgent(name="API2Fetcher", output_key="api2_data")

parallel_fetch = ParallelAgent(
    name="ConcurrentFetch",
    sub_agents=[fetch_api1, fetch_api2]
)

# Then synthesize results
synthesizer = LlmAgent(
    name="Synthesizer",
    instruction="Combine {api1_data} and {api2_data}"
)

workflow = SequentialAgent(
    name="FetchAndSynthesize",
    sub_agents=[parallel_fetch, synthesizer]
)
```

## 2. Explicit Escalation (High Priority)

### Current (Prompt-based)
```python
# In prompt: "If you can't handle this, transfer to coordinator"
# Problem: Relies on LLM interpretation
```

### Recommended (Event-based)
```python
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions

class QualityChecker(BaseAgent):
    async def _run_async_impl(self, ctx):
        status = ctx.session.state.get("quality_status", "fail")
        should_escalate = (status != "pass")
        
        yield Event(
            author=self.name,
            actions=EventActions(escalate=should_escalate)
        )
```

## 3. Generator-Critic Pattern (High Priority)

```python
from google.adk.agents import SequentialAgent, LlmAgent

# Generate code/entity
generator = LlmAgent(
    name="CodeGenerator",
    instruction="Generate Python code",
    output_key="generated_code"
)

# Review for quality
critic = LlmAgent(
    name="CodeReviewer",
    instruction="Review code in {generated_code}",
    output_key="review_feedback"
)

# Optionally refine based on feedback
refiner = LlmAgent(
    name="CodeRefiner",
    instruction="Refine code based on {review_feedback}",
    output_key="final_code"
)

review_workflow = SequentialAgent(
    name="GenerateAndReview",
    sub_agents=[generator, critic, refiner]
)
```

## 4. Custom BaseAgent Subclass (Medium Priority)

```python
from google.adk.agents import BaseAgent
from google.adk.events import Event

class StateCleanupAgent(BaseAgent):
    """Custom agent for cleanup operations."""
    
    async def _run_async_impl(self, ctx):
        # Custom logic
        ctx.session.state.pop("temp_data", None)
        
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[types.Part(text="Cleanup complete")]
            )
        )
```

## 5. Iterative Refinement with LoopAgent (Medium Priority)

```python
from google.adk.agents import LoopAgent, LlmAgent, BaseAgent

# Refine code iteratively
refiner = LlmAgent(
    name="CodeRefiner",
    instruction="Refine code in {current_code}",
    output_key="current_code"
)

# Check quality
quality_checker = LlmAgent(
    name="QualityChecker",
    instruction="Check {current_code} quality",
    output_key="quality_status"
)

# Stop when quality is good
class StopChecker(BaseAgent):
    async def _run_async_impl(self, ctx):
        status = ctx.session.state.get("quality_status", "fail")
        yield Event(
            author=self.name,
            actions=EventActions(escalate=(status == "pass"))
        )

refinement_loop = LoopAgent(
    name="CodeRefinementLoop",
    max_iterations=5,
    sub_agents=[refiner, quality_checker, StopChecker(name="Checker")]
)
```

## 6. Implementation Roadmap

### Phase 1 (Week 1)
- [ ] Add SequentialAgent for entity validation pipeline
- [ ] Add ParallelAgent for concurrent operations
- [ ] Update coordinator to use workflow agents

### Phase 2 (Week 2)
- [ ] Implement explicit escalation via EventActions
- [ ] Add Generator-Critic pattern for code generation
- [ ] Update GitHub agent to use review workflow

### Phase 3 (Week 3)
- [ ] Create custom BaseAgent subclasses
- [ ] Implement LoopAgent for iterative refinement
- [ ] Add human-in-the-loop for critical operations

## 7. Testing Strategy

- Unit tests for each workflow agent
- Integration tests for multi-agent pipelines
- Evaluation tests for quality metrics
- End-to-end dialogue tests

## 8. Migration Notes

- Existing transfer_to_agent() calls continue to work
- New workflow agents can be added incrementally
- No breaking changes to current implementation
- Both Google ADK and OpenAI SDK can be updated in parallel

