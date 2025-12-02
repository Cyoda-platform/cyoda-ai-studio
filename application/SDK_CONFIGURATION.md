# SDK Configuration Guide

The Cyoda AI Assistant supports two LLM SDKs:
- **Google ADK** (default) - Google's Generative AI Development Kit
- **OpenAI Agents** - OpenAI's Agents SDK

## Selecting an SDK

Set the `AI_SDK` environment variable to choose which SDK to use:

```bash
# Use Google ADK (default)
export AI_SDK=google

# Use OpenAI Agents SDK
export AI_SDK=openai
```

If `AI_SDK` is not set, the application defaults to Google ADK.

## Google ADK Configuration

### Environment Variables

```bash
# Required
export GOOGLE_API_KEY=your_google_api_key

# Optional (defaults shown)
export GOOGLE_MODEL=gemini-2.0-flash-exp
export GOOGLE_TEMPERATURE=0.7
export GOOGLE_MAX_TOKENS=8192
export AI_MODEL=gemini-2.0-flash-exp
```

### Features

- **Coordinator/Dispatcher Pattern**: Uses sub-agents for specialized tasks
- **Session Persistence**: Sessions stored in Cyoda entities
- **Event-based Architecture**: Full event tracking and processing
- **Plugin System**: Response validation and quality plugins
- **Tool Support**: Comprehensive tool ecosystem

### Example

```python
from application.agents.cyoda_assistant import create_cyoda_assistant

# Automatically uses Google ADK when AI_SDK=google
assistant = create_cyoda_assistant(
    google_adk_service=None,
    entity_service=entity_service
)

# Process messages
response = await assistant.process_message(
    user_message="Create a new workflow",
    conversation_history=[],
    conversation_id="conv-123",
    user_id="user-456"
)
```

## OpenAI Agents Configuration

### Environment Variables

```bash
# Required
export OPENAI_API_KEY=your_openai_api_key

# Optional (defaults shown)
export OPENAI_MODEL=gpt-4o
export OPENAI_TEMPERATURE=0.7
export OPENAI_MAX_TOKENS=8192
export AI_MODEL=gpt-4o
```

### Features

- **Agent-based Architecture**: Lightweight agent framework
- **Session Persistence**: Conversations stored in Cyoda entities
- **Streaming Support**: Real-time response streaming
- **Tool Integration**: Function calling and tool support
- **Multi-model Support**: Works with any OpenAI model

### Example

```python
from application.agents.cyoda_assistant import create_cyoda_assistant

# Automatically uses OpenAI Agents when AI_SDK=openai
assistant = create_cyoda_assistant(
    google_adk_service=None,
    entity_service=entity_service
)

# Process messages
response = await assistant.process_message(
    user_message="Create a new workflow",
    conversation_history=[],
    conversation_id="conv-123",
    user_id="user-456"
)
```

## SDK Selection Logic

The `sdk_factory.py` module provides utilities for SDK selection:

```python
from application.services.sdk_factory import (
    get_sdk_service,
    get_sdk_name,
    is_using_openai_sdk,
    is_using_google_sdk,
)

# Get the configured SDK service
service = get_sdk_service()

# Check which SDK is active
if is_using_openai_sdk():
    print("Using OpenAI Agents SDK")
else:
    print("Using Google ADK")

# Get SDK name
sdk_name = get_sdk_name()  # Returns "google" or "openai"
```

## Service Classes

### Google ADK

- **GoogleADKService** (`application/services/google_adk_service.py`)
  - Direct API integration with Google Generative AI
  - Structured output generation
  - Pydantic model support

- **CyodaSessionService** (`application/services/cyoda_session_service.py`)
  - Implements ADK SessionService interface
  - Persistent session storage in Cyoda
  - Event tracking and replay

- **CyodaAssistantWrapper** (`application/agents/cyoda_assistant.py`)
  - Wraps Google ADK LlmAgent
  - Manages session lifecycle
  - Handles event processing

### OpenAI Agents

- **OpenAIAgentsService** (`application/services/openai_agents_service.py`)
  - OpenAI API integration
  - Agent creation and execution
  - Message building and formatting

- **OpenAIAssistantWrapper** (`application/services/openai_assistant_wrapper.py`)
  - Wraps OpenAI Agent
  - Manages conversation state
  - Handles persistence to Cyoda

## Migration Guide

### From Google ADK to OpenAI Agents

1. Set environment variables:
   ```bash
   export AI_SDK=openai
   export OPENAI_API_KEY=your_key
   export OPENAI_MODEL=gpt-4o
   ```

2. No code changes needed - the factory automatically selects the SDK

3. Restart the application

### From OpenAI Agents to Google ADK

1. Set environment variables:
   ```bash
   export AI_SDK=google
   export GOOGLE_API_KEY=your_key
   export GOOGLE_MODEL=gemini-2.0-flash-exp
   ```

2. Restart the application

## Troubleshooting

### "Unsupported AI_SDK value"

Ensure `AI_SDK` is set to either "google" or "openai":
```bash
export AI_SDK=google  # or openai
```

### API Key Not Found

Check that the appropriate API key is set:
- For Google ADK: `GOOGLE_API_KEY`
- For OpenAI: `OPENAI_API_KEY`

### Model Not Available

Verify the model name is correct:
- Google: `gemini-2.0-flash-exp`, `gemini-1.5-pro`, etc.
- OpenAI: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc.

## Performance Considerations

### Google ADK
- Better for complex multi-agent workflows
- Event-based architecture provides detailed tracing
- Session persistence is more robust

### OpenAI Agents
- Lighter weight and faster for simple tasks
- Better streaming support
- Lower latency for single-turn interactions

## Future Enhancements

- [ ] Support for Anthropic Claude via LiteLLM
- [ ] Support for local LLMs via Ollama
- [ ] Dynamic SDK switching without restart
- [ ] SDK-specific performance metrics

