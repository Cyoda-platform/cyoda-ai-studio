---
name: debug-streaming
description: Use this skill when debugging SSE (Server-Sent Events) streaming issues or implementing streaming responses.
tags: [streaming, sse, debug, real-time]
---

# Debug Streaming Skill

## Purpose
Guide for debugging and implementing SSE (Server-Sent Events) streaming in Cyoda AI Studio.

## When to Use This Skill
- Streaming responses not appearing
- Partial content received
- Connection drops
- Field name mismatches (`content` vs `chunk`)
- Implementing new streaming endpoints

## Common Issues & Solutions

### Issue 1: Field Name Mismatch

**Problem:** Accumulating from wrong field

```python
# ❌ WRONG - Using 'content' field
event_data = json.loads(sse_event)
chunk = event_data.get("content")  # This might be None!
accumulated_response += chunk
```

```python
# ✅ CORRECT - Check both 'chunk' and 'content'
event_data = json.loads(sse_event)
chunk = event_data.get("chunk") or event_data.get("content")
accumulated_response += chunk
```

**Root Cause:** Streaming service uses `chunk` field, not `content`

**File:** `application/services/streaming_service.py`

### Issue 2: Missing Event Handling

**Problem:** Not handling all SSE event types

```python
# ✅ Complete event handling
async for event in stream:
    if event.type == "message":
        data = json.loads(event.data)
        chunk = data.get("chunk") or data.get("content")
        if chunk:
            accumulated_response += chunk
    elif event.type == "error":
        logger.error(f"Stream error: {event.data}")
        break
    elif event.type == "done":
        logger.info("Stream completed")
        break
```

### Issue 3: Connection Timeout

**Problem:** Stream drops after N seconds

```python
# ✅ Set appropriate timeouts
import httpx

async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes
    async with client.stream("POST", url, json=payload) as response:
        async for line in response.aiter_lines():
            # Process SSE events
            pass
```

### Issue 4: Buffer Not Flushing

**Problem:** Events arrive late or in batches

```python
# ✅ Explicitly flush after each event
async def stream_response():
    for chunk in generate_chunks():
        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        # Force flush (in Quart)
        await asyncio.sleep(0)  # Yield control to event loop
```

## Streaming Service Architecture

### Core Components

```
Client Request
    ↓
Quart Route (/chat endpoint)
    ↓
StreamingService.stream_response()
    ↓
Google ADK Agent.run_stream()
    ↓
SSE Events → Client
```

### StreamingService Usage

```python
from application.services.streaming_service import StreamingService

streaming_service = StreamingService()

# Stream agent response
async for event in streaming_service.stream_response(
    agent=my_agent,
    query="User question",
    context={"user_id": "123"}
):
    # event format: {"chunk": "...", "metadata": {...}}
    yield f"data: {json.dumps(event)}\n\n"
```

### Creating Streaming Endpoint

```python
from quart import Response, request
import json

@app.route("/api/chat/stream", methods=["POST"])
async def chat_stream():
    """Streaming chat endpoint."""
    data = await request.get_json()
    query = data.get("query")

    async def generate():
        accumulated = ""
        async for event in streaming_service.stream_response(
            agent=chat_agent,
            query=query
        ):
            chunk = event.get("chunk", "")
            accumulated += chunk

            # Send SSE event
            yield f"data: {json.dumps(event)}\n\n"

        # Final event with complete response
        yield f"data: {json.dumps({'done': True, 'full_response': accumulated})}\n\n"

    return Response(generate(), mimetype="text/event-stream")
```

## Debugging Techniques

### 1. Stream Monitor

Use the built-in stream monitor:

```python
from application.utils.stream_monitor import StreamMonitor

monitor = StreamMonitor()

async for event in stream:
    monitor.track_event(event)  # Track all events
    chunk = event.get("chunk", "")
    accumulated += chunk

# Print statistics
monitor.print_stats()
```

### 2. Logging SSE Events

```python
import logging

logger = logging.getLogger(__name__)

async def debug_stream(stream):
    """Debug wrapper for SSE streams."""
    event_count = 0
    total_bytes = 0

    async for event in stream:
        event_count += 1
        chunk = event.get("chunk", "")
        total_bytes += len(chunk.encode('utf-8'))

        logger.debug(f"Event #{event_count}: {len(chunk)} chars")
        logger.debug(f"Content preview: {chunk[:50]}...")

        yield event

    logger.info(f"Stream complete: {event_count} events, {total_bytes} bytes")
```

### 3. Client-Side Debugging

```javascript
// Browser console debugging
const eventSource = new EventSource('/api/chat/stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Chunk:', data.chunk);
    console.log('Metadata:', data.metadata);
};

eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
    eventSource.close();
};
```

## Best Practices

### 1. Always Check Both Fields

```python
# Support both 'chunk' and 'content' for compatibility
chunk = event_data.get("chunk") or event_data.get("content") or ""
```

### 2. Handle Empty Chunks

```python
# Don't append empty strings
chunk = event_data.get("chunk", "")
if chunk:  # Only append non-empty chunks
    accumulated_response += chunk
```

### 3. Set Proper Content-Type

```python
# For SSE streams
return Response(
    generate(),
    mimetype="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"  # Disable nginx buffering
    }
)
```

### 4. Implement Timeout Protection

```python
import asyncio

async def stream_with_timeout(stream, timeout=300):
    """Wrap stream with timeout protection."""
    try:
        async with asyncio.timeout(timeout):
            async for event in stream:
                yield event
    except asyncio.TimeoutError:
        logger.error(f"Stream timeout after {timeout}s")
        yield {"error": "Stream timeout", "done": True}
```

### 5. Graceful Error Handling

```python
async def safe_stream(stream):
    """Stream with error recovery."""
    try:
        async for event in stream:
            yield event
    except Exception as e:
        logger.exception(f"Stream error: {e}")
        yield {
            "error": str(e),
            "done": True,
            "chunk": "\n[Stream interrupted due to error]"
        }
```

## Testing Streaming

### Unit Test Example

```python
import pytest
from application.services.streaming_service import StreamingService

@pytest.mark.asyncio
async def test_streaming_accumulation():
    """Test that chunks accumulate correctly."""
    streaming_service = StreamingService()

    accumulated = ""
    chunks_received = 0

    async for event in streaming_service.stream_response(
        agent=test_agent,
        query="Test query"
    ):
        chunk = event.get("chunk") or event.get("content") or ""
        accumulated += chunk
        chunks_received += 1

    assert len(accumulated) > 0, "Should accumulate content"
    assert chunks_received > 0, "Should receive chunks"
    print(f"Received {chunks_received} chunks, {len(accumulated)} total chars")
```

### Manual Testing with curl

```bash
# Test streaming endpoint
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello, world!"}' \
  --no-buffer
```

## Troubleshooting Checklist

- [ ] Using `chunk` field (not `content`)
- [ ] Handling empty chunks
- [ ] Timeout set appropriately (>= 300s for long responses)
- [ ] Content-Type is `text/event-stream`
- [ ] No nginx buffering (`X-Accel-Buffering: no`)
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Client properly handles SSE events
- [ ] Connection close handled gracefully

## Reference Files

- `application/services/streaming_service.py` - Main streaming service
- `application/utils/stream_monitor.py` - Debugging utility
- `application/routes/chat.py` - Streaming endpoint examples
- `application/config/streaming_config.py` - Configuration

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `'NoneType' object has no attribute '__add__'` | Appending None chunk | Check field name, use `or ""` |
| `Connection reset by peer` | Timeout or buffer issue | Increase timeout, disable buffering |
| `Stream closes immediately` | Missing await/async | Use `async for`, not `for` |
| `Chunks arrive in batches` | Buffering enabled | Set `X-Accel-Buffering: no` |

---

**Quick Fix:** If streaming is broken, always check field name first:
```python
chunk = event.get("chunk") or event.get("content") or ""
```
