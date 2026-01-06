"""Constants for streaming service."""

# Stream timeout in seconds (5 minutes - prevents infinite loops)
STREAM_TIMEOUT = 300

# Memory limits for streaming
MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB limit for accumulated response
MAX_EVENTS_PER_STREAM = 10000    # Limit number of events per stream

# Heartbeat configuration
HEARTBEAT_INTERVAL = 120  # Send heartbeat every 2 minutes (LLM can take 30-60s)

# Session configuration
APP_NAME = "cyoda-assistant"
CYODA_TECHNICAL_ID_KEY = "__cyoda_technical_id__"

