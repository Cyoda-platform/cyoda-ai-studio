# Google ADK Code Examples for Cyoda

## 1. SequentialAgent for Entity Validation Pipeline

```python
from google.adk.agents import SequentialAgent, LlmAgent

def create_entity_validation_pipeline():
    """Create sequential pipeline for entity creation."""
    
    # Step 1: Validate JSON structure
    validator = LlmAgent(
        name="EntityValidator",
        instruction="Validate the entity JSON structure. Output 'valid' or 'invalid'.",
        output_key="validation_result"
    )
    
    # Step 2: Check required fields
    field_checker = LlmAgent(
        name="RequiredFieldChecker",
        instruction="Check if {validation_result} entity has all required fields.",
        output_key="field_check_result"
    )
    
    # Step 3: Generate entity if valid
    generator = LlmAgent(
        name="EntityGenerator",
        instruction="If {field_check_result} is valid, generate the entity.",
        output_key="generated_entity"
    )
    
    # Orchestrate as sequential pipeline
    return SequentialAgent(
        name="EntityCreationPipeline",
        sub_agents=[validator, field_checker, generator]
    )
```

## 2. ParallelAgent for Concurrent Operations

```python
from google.adk.agents import ParallelAgent, SequentialAgent, LlmAgent

def create_parallel_data_fetch_workflow():
    """Fetch from multiple sources concurrently, then synthesize."""
    
    # Concurrent fetchers
    fetch_github = LlmAgent(
        name="GitHubFetcher",
        instruction="Fetch repository metadata from GitHub",
        output_key="github_data"
    )
    
    fetch_cyoda = LlmAgent(
        name="CyodaFetcher",
        instruction="Fetch entity definitions from Cyoda",
        output_key="cyoda_data"
    )
    
    # Run both concurrently
    parallel_fetch = ParallelAgent(
        name="ConcurrentDataFetch",
        sub_agents=[fetch_github, fetch_cyoda]
    )
    
    # Synthesize results
    synthesizer = LlmAgent(
        name="DataSynthesizer",
        instruction="Combine {github_data} and {cyoda_data} into unified view",
        output_key="unified_data"
    )
    
    # Sequential: fetch in parallel, then synthesize
    return SequentialAgent(
        name="FetchAndSynthesizeWorkflow",
        sub_agents=[parallel_fetch, synthesizer]
    )
```

## 3. Custom BaseAgent for Quality Checking

```python
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator
from google.genai import types

class QualityCheckAgent(BaseAgent):
    """Custom agent that checks quality and escalates if needed."""
    
    def __init__(self, name: str, quality_threshold: float = 0.8):
        super().__init__(name=name, description="Checks quality metrics")
        self.quality_threshold = quality_threshold
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Check quality and escalate if below threshold."""
        
        # Get quality score from state
        quality_score = ctx.session.state.get("quality_score", 0.0)
        
        # Determine if we should escalate (exit loop/workflow)
        should_escalate = quality_score >= self.quality_threshold
        
        # Create response message
        message = f"Quality score: {quality_score:.2f}. "
        if should_escalate:
            message += "✓ Quality threshold met, proceeding."
        else:
            message += "✗ Quality below threshold, needs refinement."
        
        # Yield event with escalation flag
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text=message)]),
            actions=EventActions(escalate=should_escalate)
        )
```

## 4. LoopAgent for Iterative Refinement

```python
from google.adk.agents import LoopAgent, LlmAgent

def create_code_refinement_loop():
    """Iteratively refine code until quality threshold is met."""
    
    # Refine code based on current version
    refiner = LlmAgent(
        name="CodeRefiner",
        instruction="Improve the code in {current_code}. Save to {current_code}.",
        output_key="current_code"
    )
    
    # Check quality
    quality_checker = LlmAgent(
        name="QualityChecker",
        instruction="Rate code quality in {current_code}. Output score 0-100.",
        output_key="quality_score"
    )
    
    # Use custom agent to check if we should stop
    quality_check = QualityCheckAgent(
        name="StopChecker",
        quality_threshold=80.0
    )
    
    # Loop until quality is good or max iterations reached
    return LoopAgent(
        name="CodeRefinementLoop",
        max_iterations=5,
        sub_agents=[refiner, quality_checker, quality_check]
    )
```

## 5. Generator-Critic Pattern

```python
from google.adk.agents import SequentialAgent, LlmAgent

def create_code_generation_with_review():
    """Generate code, review it, and refine based on feedback."""
    
    # Generate initial code
    generator = LlmAgent(
        name="CodeGenerator",
        instruction="Generate Python code for {task}",
        output_key="generated_code"
    )
    
    # Review for quality, security, style
    critic = LlmAgent(
        name="CodeReviewer",
        instruction="Review code in {generated_code}. List issues found.",
        output_key="review_feedback"
    )
    
    # Refine based on feedback
    refiner = LlmAgent(
        name="CodeRefiner",
        instruction="Fix issues from {review_feedback} in {generated_code}",
        output_key="final_code"
    )
    
    # Sequential: generate → review → refine
    return SequentialAgent(
        name="GenerateAndReviewWorkflow",
        sub_agents=[generator, critic, refiner]
    )
```

## 6. Explicit Escalation Pattern

```python
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions

class ConditionalEscalator(BaseAgent):
    """Escalate to parent if condition is met."""
    
    def __init__(self, name: str, condition_key: str, target_value: str):
        super().__init__(name=name, description="Conditional escalator")
        self.condition_key = condition_key
        self.target_value = target_value
    
    async def _run_async_impl(self, ctx):
        """Check condition and escalate if met."""
        
        current_value = ctx.session.state.get(self.condition_key)
        should_escalate = current_value == self.target_value
        
        yield Event(
            author=self.name,
            actions=EventActions(escalate=should_escalate)
        )

# Usage in workflow
escalator = ConditionalEscalator(
    name="ErrorChecker",
    condition_key="error_status",
    target_value="critical"
)
```

## 7. Integration with Coordinator

```python
# In cyoda_assistant.py, add workflow agents to coordinator

from google.adk.agents import LlmAgent

coordinator = LlmAgent(
    name="cyoda_assistant",
    model=model_config,
    instruction=create_instruction_provider("coordinator"),
    tools=[get_user_info],
    sub_agents=[
        qa_agent,
        guidelines_agent,
        setup_agent,
        environment_agent,
        canvas_agent,
        github_agent,
        cyoda_data_agent,
        # Add workflow agents
        create_entity_validation_pipeline(),
        create_parallel_data_fetch_workflow(),
        create_code_refinement_loop(),
    ],
)
```

## 8. Testing Workflow Agents

```python
import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

@pytest.mark.asyncio
async def test_entity_validation_pipeline():
    """Test sequential entity validation pipeline."""
    
    pipeline = create_entity_validation_pipeline()
    runner = Runner(
        app_name="test",
        agent=pipeline,
        session_service=InMemorySessionService()
    )
    
    # Run pipeline
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=types.Content(
            parts=[types.Part(text="Create entity")]
        )
    ):
        pass
    
    # Verify results in session state
    session = await runner.session_service.get_session(
        app_name="test",
        user_id="test_user",
        session_id="test_session"
    )
    
    assert session.state.get("generated_entity") is not None
```

## Notes

- All examples follow Google ADK patterns from official documentation
- Compatible with existing Cyoda implementation
- Can be added incrementally without breaking changes
- Both Google ADK and OpenAI SDK can be updated in parallel

