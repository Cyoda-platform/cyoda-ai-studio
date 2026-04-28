---
name: ai-assistant-sdlc
description: Use this skill when maintaining AI assistants, implementing guardrails, or preventing tangential dialogues.
tags: [ai-maintenance, testing, guardrails, sdlc, quality-assurance]
---

# AI Assistant SDLC & Guardrails Skill

## Purpose
Guide for maintaining AI assistants in production, implementing guardrails to prevent off-topic responses, and establishing a proper SDLC for AI agent development.

## When to Use This Skill
- Setting up testing for AI assistant behavior
- Implementing guardrails to prevent tangential dialogues
- Establishing SDLC processes for AI agents
- Debugging unexpected AI responses
- Quality assurance for production AI assistants

---

## The Problem: Tangential Dialogues

### Real Example

**User asks:** "Give me a news story about the Sieve of Eratosthenes"

**AI responds:** *[Generates a fictional news story]*
- Offers follow-ups: "Show a code example", "Explain the algorithm"
- User clicks "show a code example"
- **Result:** AI went from "news story" → "tutorial" (off-topic)

### Why This Happens

1. **Vague Intent:** "News story" is ambiguous (real news? educational story? historical?)
2. **No Constraints:** AI has no boundary on what constitutes valid response
3. **Follow-up Suggestions:** AI generates its own prompts, leading user astray
4. **Context Drift:** Each turn moves further from original intent

---

## Solution 1: Prompt Engineering with Constraints

### Before (Weak)

```python
instruction = """
You are a helpful AI assistant that answers questions.
"""
```

**Problem:** No boundaries, no scope definition

### After (Strong)

```python
instruction = """
You are a Cyoda platform AI assistant specialized in:
- Entity management operations
- Workflow configuration
- Search and query construction
- Deployment and integration

STRICT BOUNDARIES:
- Only answer questions related to Cyoda platform
- If user asks off-topic questions, politely redirect:
  "I'm specialized in Cyoda platform assistance. For general
   questions, please use a general-purpose AI. How can I help
   with Cyoda today?"
- Never generate fictional content or stories
- Never provide code examples outside Cyoda context

RESPONSE FORMAT:
- Be direct and technical
- Provide working code snippets with Cyoda APIs
- Reference official documentation when applicable
- Suggest next steps related to Cyoda tasks only
"""
```

**Result:** Clear scope, explicit rejection of off-topic queries

---

## Solution 2: Intent Classification Layer

### Architecture Pattern

```
User Input
    ↓
Intent Classifier (Pre-processing)
    ↓
┌─────────────┐
│ Is question │
│ on-topic?   │
└─────┬───────┘
      │
   ┌──┴──┐
   ↓     ↓
  Yes   No
   ↓     ↓
 Main   Rejection
 Agent  Message
```

### Implementation

```python
from pydantic import BaseModel

class IntentClassification(BaseModel):
    is_on_topic: bool
    topic_category: str  # "entity", "workflow", "search", "off-topic"
    confidence: float
    reasoning: str

async def classify_intent(query: str) -> IntentClassification:
    """Pre-screen user query before sending to main agent."""

    classifier_prompt = f"""
    Classify this user query for a Cyoda platform AI assistant.

    Valid topics: entity management, workflows, search, deployment

    User query: "{query}"

    Is this question on-topic for Cyoda platform?
    Return classification with reasoning.
    """

    classification = await classifier_agent.run(
        classifier_prompt,
        output_schema=IntentClassification
    )

    return classification

async def handle_user_query(query: str) -> str:
    """Main handler with intent gate."""

    # Step 1: Classify intent
    intent = await classify_intent(query)

    if not intent.is_on_topic:
        return f"""
        I'm specialized in Cyoda platform assistance. Your question
        appears to be about {intent.topic_category}.

        For general questions, please use a general-purpose AI assistant.

        How can I help you with Cyoda platform today?
        """

    # Step 2: Route to appropriate handler
    if intent.topic_category == "entity":
        return await entity_agent.run(query)
    elif intent.topic_category == "workflow":
        return await workflow_agent.run(query)
    # ... etc
```

### Benefits

✅ **Explicit Filtering:** Off-topic queries rejected early
✅ **No Context Drift:** Main agent never sees irrelevant queries
✅ **Measurable:** Can track rejection rate and accuracy
✅ **Fast:** Classification is quick (< 500ms)

---

## Solution 3: Response Validation Layer

### Architecture Pattern

```
Main Agent generates response
    ↓
Response Validator (Post-processing)
    ↓
┌─────────────┐
│ Is response │
│ appropriate?│
└─────┬───────┘
      │
   ┌──┴──┐
   ↓     ↓
  Yes   No
   ↓     ↓
Return  Regenerate
to     with more
user   constraints
```

### Implementation

```python
from pydantic import BaseModel

class ResponseValidation(BaseModel):
    is_appropriate: bool
    contains_off_topic: bool
    contains_fictional_content: bool
    contains_code_outside_scope: bool
    reasoning: str
    suggested_fix: str | None

async def validate_response(
    original_query: str,
    agent_response: str
) -> ResponseValidation:
    """Validate agent response stays on-topic."""

    validator_prompt = f"""
    Validate this AI response for a Cyoda platform assistant.

    User asked: "{original_query}"
    Agent responded: "{agent_response}"

    Check if response:
    1. Stays on-topic (Cyoda platform only)
    2. Contains no fictional content
    3. Contains no code examples outside Cyoda APIs
    4. Doesn't offer tangential follow-ups

    Return validation with reasoning.
    """

    validation = await validator_agent.run(
        validator_prompt,
        output_schema=ResponseValidation
    )

    return validation

async def safe_agent_response(query: str) -> str:
    """Generate and validate response."""

    # Generate response
    response = await main_agent.run(query)

    # Validate response
    validation = await validate_response(query, response)

    if not validation.is_appropriate:
        # Regenerate with stricter constraints
        constrained_prompt = f"""
        {query}

        CONSTRAINT: {validation.suggested_fix}
        Stay strictly on Cyoda platform topics.
        """
        response = await main_agent.run(constrained_prompt)

    return response
```

### Benefits

✅ **Quality Gate:** Bad responses never reach user
✅ **Self-Correcting:** Agent learns from validation feedback
✅ **Auditable:** Log validation failures for analysis

---

## Solution 4: Evaluation-Based Testing

### Test for Tangential Responses

```python
import pytest
from google.adk.evals import create_eval

@create_eval("test_rejects_off_topic_queries")
async def test_off_topic_rejection():
    """Test that assistant rejects off-topic questions."""

    off_topic_queries = [
        "Give me a news story about the Sieve of Eratosthenes",
        "Write me a poem about spring",
        "What's the weather in Paris?",
        "How do I bake a chocolate cake?",
    ]

    for query in off_topic_queries:
        response = await assistant.run(query)

        # Response should contain rejection keywords
        assert any(keyword in response.lower() for keyword in [
            "specialized in cyoda",
            "cyoda platform",
            "off-topic",
            "not within my scope",
            "general-purpose ai"
        ]), f"Failed to reject: {query}\nGot: {response}"

@create_eval("test_stays_on_topic")
async def test_stays_on_topic():
    """Test that responses stay focused on Cyoda."""

    query = "How do I create an entity?"
    response = await assistant.run(query)

    # Response should NOT contain
    forbidden_content = [
        "once upon a time",  # No stories
        "here's a joke",     # No humor
        "fun fact",          # No tangents
        "by the way",        # No side topics
    ]

    for forbidden in forbidden_content:
        assert forbidden not in response.lower(), \
            f"Response contains forbidden tangent: {forbidden}"

    # Response SHOULD contain
    required_content = [
        "entity",
        "cyoda",
        "create" or "add",
    ]

    assert any(req in response.lower() for req in required_content), \
        "Response doesn't address the Cyoda entity question"

@create_eval("test_no_follow_up_tangents")
async def test_no_tangential_follow_ups():
    """Test that follow-up suggestions stay on-topic."""

    query = "Explain Cyoda workflows"
    response = await assistant.run(query)

    # If response suggests follow-ups, they must be on-topic
    if "would you like to" in response.lower():
        # Extract suggested follow-ups
        # Validate each is Cyoda-related

        forbidden_follow_ups = [
            "show a code example",  # Too vague
            "learn more",           # Too generic
            "see a tutorial",       # Might go off-topic
        ]

        for forbidden in forbidden_follow_ups:
            assert forbidden not in response.lower(), \
                f"Response suggests tangential follow-up: {forbidden}"
```

### Run Evaluation Tests

```bash
# Run guardrail tests
cd application/agents/tests/evals/guardrails
python -m google.adk.evals.run test_guardrails.py

# Expected output:
# ✓ test_rejects_off_topic_queries (4/4 passed)
# ✓ test_stays_on_topic (passed)
# ✓ test_no_follow_up_tangents (passed)
```

---

## Solution 5: Conversation Context Limits

### Prevent Context Drift Over Multiple Turns

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ConversationTurn:
    query: str
    response: str
    topic: str
    timestamp: float

class ContextDriftDetector:
    """Detect when conversation drifts off-topic."""

    def __init__(self, max_turns: int = 10, drift_threshold: float = 0.5):
        self.conversation_history: List[ConversationTurn] = []
        self.max_turns = max_turns
        self.drift_threshold = drift_threshold

    async def check_drift(self, new_query: str) -> bool:
        """Check if new query represents topic drift."""

        if not self.conversation_history:
            return False  # First turn, no drift possible

        # Get recent topics
        recent_topics = [
            turn.topic
            for turn in self.conversation_history[-3:]
        ]

        # Classify new query topic
        new_topic = await classify_topic(new_query)

        # Calculate topic consistency
        consistency = sum(
            1 for topic in recent_topics if topic == new_topic
        ) / len(recent_topics)

        if consistency < self.drift_threshold:
            return True  # Drift detected

        return False

    async def handle_query(self, query: str) -> str:
        """Handle query with drift detection."""

        # Check for drift
        if await self.check_drift(query):
            return """
            I notice we've moved away from our original topic.

            We started discussing Cyoda workflows, but your latest
            question is about general programming concepts.

            Let's refocus: What would you like to know about
            Cyoda workflows specifically?
            """

        # Process normally
        topic = await classify_topic(query)
        response = await main_agent.run(query)

        # Record turn
        self.conversation_history.append(
            ConversationTurn(
                query=query,
                response=response,
                topic=topic,
                timestamp=time.time()
            )
        )

        # Trim history
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history = \
                self.conversation_history[-self.max_turns:]

        return response
```

---

## SDLC Process for AI Assistants

### Phase 1: Requirements & Design

```markdown
## Agent Requirements Document

### Scope
- Domain: Cyoda platform assistance
- Tasks: Entity management, workflows, search, deployment
- Exclusions: General knowledge, entertainment, creative writing

### Guardrails
1. Intent Classification: Reject off-topic queries
2. Response Validation: Filter inappropriate responses
3. Context Monitoring: Prevent conversation drift
4. Rate Limiting: Prevent abuse

### Quality Metrics
- On-topic accuracy: >95%
- Off-topic rejection rate: >90%
- Response time: <2 seconds
- User satisfaction: >4.0/5.0
```

### Phase 2: Development

```bash
# 1. Create agent with constraints
vim application/agents/cyoda_assistant/agent.py

# 2. Add prompt with explicit boundaries
vim application/agents/shared/prompts/cyoda_assistant_strict.txt

# 3. Implement intent classifier
vim application/services/intent_classifier.py

# 4. Implement response validator
vim application/services/response_validator.py

# 5. Add conversation context manager
vim application/services/conversation_manager.py
```

### Phase 3: Testing

**Unit Tests (Mock AI responses):**
```bash
pytest tests/unit/test_intent_classifier.py
pytest tests/unit/test_response_validator.py
pytest tests/unit/test_conversation_manager.py
```

**Integration Tests (Real AI calls):**
```bash
pytest tests/integration/test_guardrails_e2e.py
```

**Evaluation Tests (Quality assurance):**
```bash
cd application/agents/tests/evals/guardrails
bash run_guardrail_evals.sh
```

### Phase 4: Staging

```bash
# Deploy to staging environment
APP_ENV=staging python run.py

# Run smoke tests
curl -X POST http://staging:8000/api/chat \
  -d '{"query": "Give me a news story about math"}'
# Expected: Rejection message

curl -X POST http://staging:8000/api/chat \
  -d '{"query": "How do I create an entity?"}'
# Expected: On-topic Cyoda response
```

### Phase 5: Monitoring (Production)

```python
# application/services/monitoring/guardrail_metrics.py

from prometheus_client import Counter, Histogram

# Metrics
off_topic_queries = Counter(
    'off_topic_queries_total',
    'Number of off-topic queries rejected'
)

response_validation_failures = Counter(
    'response_validation_failures_total',
    'Number of responses that failed validation'
)

context_drift_detections = Counter(
    'context_drift_detections_total',
    'Number of times conversation drift was detected'
)

response_generation_time = Histogram(
    'response_generation_seconds',
    'Time to generate and validate response'
)

# Usage
async def monitored_response(query: str) -> str:
    with response_generation_time.time():
        # Classify intent
        intent = await classify_intent(query)

        if not intent.is_on_topic:
            off_topic_queries.inc()
            return rejection_message()

        # Generate response
        response = await main_agent.run(query)

        # Validate response
        validation = await validate_response(query, response)

        if not validation.is_appropriate:
            response_validation_failures.inc()
            response = await regenerate_with_constraints(query)

        return response
```

**Dashboard Queries:**
```promql
# Off-topic query rate (should be <10% of total)
rate(off_topic_queries_total[5m]) / rate(total_queries[5m])

# Response validation failure rate (should be <5%)
rate(response_validation_failures_total[5m]) / rate(total_queries[5m])

# P95 response time (should be <2s)
histogram_quantile(0.95, response_generation_seconds)
```

---

## Best Practices

### 1. Layered Defense (Defense in Depth)

```
┌─────────────────────────────────────┐
│ Layer 1: Intent Classification     │  ← Reject off-topic early
├─────────────────────────────────────┤
│ Layer 2: Agent with Constraints     │  ← Explicit scope in prompt
├─────────────────────────────────────┤
│ Layer 3: Response Validation        │  ← Quality gate before user
├─────────────────────────────────────┤
│ Layer 4: Context Drift Detection    │  ← Monitor conversation flow
├─────────────────────────────────────┤
│ Layer 5: User Feedback Loop         │  ← Learn from user reports
└─────────────────────────────────────┘
```

**Why:** Single layer can fail; multiple layers provide resilience

### 2. Explicit > Implicit

```python
# ❌ BAD: Implicit scope
instruction = "You are a helpful assistant."

# ✅ GOOD: Explicit scope
instruction = """
You are a Cyoda platform AI assistant.

ONLY answer questions about:
- Entity operations (create, read, update, delete)
- Workflow configuration (FSM, processors, criterions)
- Search and queries (conditions, operators)
- Deployment and integration

NEVER:
- Generate fictional content or stories
- Provide code examples outside Cyoda APIs
- Answer general knowledge questions
- Engage in creative writing
- Suggest off-topic follow-ups

If user asks off-topic question, respond:
"I specialize in Cyoda platform. For [topic], use a general AI."
"""
```

### 3. Test Negative Cases Extensively

```python
# Test that agent REJECTS these
negative_test_cases = [
    "Tell me a story",
    "Write a poem",
    "What's the weather?",
    "How do I bake cookies?",
    "Explain quantum physics",
    "Give me a news article about [anything]",
]

for query in negative_test_cases:
    response = await assistant.run(query)
    assert "specialize in cyoda" in response.lower()
```

### 4. Log and Analyze Edge Cases

```python
import logging

logger = logging.getLogger(__name__)

async def handle_with_logging(query: str) -> str:
    # Log all queries
    logger.info(f"User query: {query}")

    intent = await classify_intent(query)
    logger.info(f"Intent classification: {intent}")

    if not intent.is_on_topic:
        logger.warning(f"Rejected off-topic query: {query}")
        return rejection_message()

    response = await main_agent.run(query)
    logger.info(f"Agent response length: {len(response)}")

    validation = await validate_response(query, response)
    if not validation.is_appropriate:
        logger.error(f"Response validation failed: {validation.reasoning}")

    return response
```

**Analysis:**
```bash
# Find common off-topic patterns
grep "Rejected off-topic" logs/app.log | \
  awk -F': ' '{print $NF}' | \
  sort | uniq -c | sort -rn | head -10

# Output:
#   15 "Tell me a story about..."
#    8 "What's the weather..."
#    5 "Write a poem..."
#    3 "Give me a news article..."
```

### 5. User Feedback Integration

```python
@app.route("/api/feedback", methods=["POST"])
async def submit_feedback():
    """Collect user feedback on responses."""

    data = await request.get_json()

    feedback = {
        "query": data["query"],
        "response": data["response"],
        "rating": data["rating"],  # 1-5
        "issue": data.get("issue"),  # "off-topic", "unhelpful", etc.
        "timestamp": time.time()
    }

    # Store for analysis
    await store_feedback(feedback)

    # If off-topic report, retrain classifier
    if feedback["issue"] == "off-topic":
        await retrain_intent_classifier(
            negative_example=feedback["query"]
        )

    return {"status": "success"}
```

---

## Troubleshooting

### Issue: Agent Still Goes Off-Topic

**Diagnosis:**
```python
# Check prompt clarity
print(agent.instruction)

# Check classification accuracy
for query in test_queries:
    intent = await classify_intent(query)
    print(f"{query} → {intent.is_on_topic}")
```

**Solutions:**
1. Make prompt constraints more explicit
2. Add more negative examples to classifier
3. Increase validation strictness
4. Add topic consistency check

### Issue: Agent Rejects Valid Queries

**Diagnosis:**
```python
# Check false positive rate
true_positives = 0
false_positives = 0

for query in on_topic_queries:
    intent = await classify_intent(query)
    if intent.is_on_topic:
        true_positives += 1
    else:
        false_positives += 1
        print(f"FALSE POSITIVE: {query}")

print(f"Precision: {true_positives / (true_positives + false_positives)}")
```

**Solutions:**
1. Add edge case examples to classifier training
2. Reduce classification confidence threshold
3. Add fallback: "I'm not sure if this is Cyoda-related. Could you clarify?"

---

## Checklist: Implementing Guardrails

- [ ] Define explicit scope in agent instruction
- [ ] List forbidden topics/content explicitly
- [ ] Implement intent classification layer
- [ ] Implement response validation layer
- [ ] Add conversation context monitoring
- [ ] Write evaluation tests for off-topic rejection
- [ ] Write evaluation tests for on-topic accuracy
- [ ] Set up monitoring metrics (Prometheus/Grafana)
- [ ] Create alerts for high off-topic rate
- [ ] Implement user feedback collection
- [ ] Document edge cases and resolutions
- [ ] Regular review of logs for new patterns

---

## Reference Files

- `application/agents/cyoda_assistant/agent.py` - Main agent
- `application/services/intent_classifier.py` - Intent classification
- `application/services/response_validator.py` - Response validation
- `application/services/conversation_manager.py` - Context management
- `tests/evals/guardrails/` - Guardrail evaluation tests

---

## Further Reading

- Google ADK Evaluation Framework: https://github.com/google/adk-python
- Prompt Engineering Guide: https://www.promptingguide.ai/
- LangSmith Evaluation: https://docs.smith.langchain.com/evaluation

---

**Last Updated:** 2026-04-28
**Status:** Production-Ready Pattern
**Next Review:** When new tangential patterns emerge
