"""
Streaming Configuration for Enhanced Reliability

This module contains configuration settings optimized for reliable streaming
with proper timeouts, buffering, and error handling.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class StreamingConfig:
    """Configuration for streaming services with reliability enhancements."""

    # Timeout settings (in seconds)
    STREAM_TIMEOUT: int = 600  # 10 minutes - server-side timeout
    CLIENT_TIMEOUT: int = (
        600  # 10 minutes - client-side timeout (match server timeout for long tool executions)
    )
    HEARTBEAT_INTERVAL: int = 10  # 30 seconds - heartbeat frequency

    # Agent execution settings
    MAX_AGENT_TURNS: int = (
        25  # Maximum turns/iterations for agent execution to prevent infinite loops
    )

    # Retry and circuit breaker settings
    MAX_RETRY_ATTEMPTS: int = 5
    RETRY_BASE_DELAY: float = 1.0  # Base delay in seconds
    RETRY_MAX_DELAY: float = 30.0  # Maximum delay in seconds
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 300  # 5 minute

    # Buffer and chunk settings
    STREAM_BUFFER_SIZE: int = 8192  # 8KB buffer
    CHUNK_SIZE: int = 1024  # 1KB chunks
    MAX_ACCUMULATED_CONTENT: int = 1024 * 1024  # 1MB max content

    # Persistence settings
    STREAM_STATE_TTL: int = 300  # 5 minutes - how long to keep stream state
    CLEANUP_INTERVAL: int = 90  # 1.5 minute - how often to cleanup old states

    # Health monitoring
    HEALTH_CHECK_INTERVAL: int = 30  # 30 seconds
    METRICS_RETENTION_PERIOD: int = 3600  # 1 hour

    # Network optimization
    TCP_KEEPALIVE: bool = True
    TCP_KEEPALIVE_IDLE: int = 50  # Start keepalive after 50s of inactivity
    TCP_KEEPALIVE_INTERVAL: int = 10  # Send keepalive every 10s
    TCP_KEEPALIVE_COUNT: int = 6  # Drop connection after 6 failed keepalives

    # SSE specific settings
    SSE_RETRY_INTERVAL: int = 3000  # 3 seconds - client retry interval
    SSE_MAX_EVENT_SIZE: int = 65536  # 64KB - maximum event size

    @classmethod
    def from_env(cls) -> "StreamingConfig":
        """Create configuration from environment variables."""
        return cls(
            STREAM_TIMEOUT=int(os.getenv("STREAM_TIMEOUT", 600)),
            CLIENT_TIMEOUT=int(os.getenv("CLIENT_TIMEOUT", 600)),
            HEARTBEAT_INTERVAL=int(os.getenv("HEARTBEAT_INTERVAL", 30)),
            MAX_AGENT_TURNS=int(os.getenv("MAX_AGENT_TURNS", 25)),
            MAX_RETRY_ATTEMPTS=int(os.getenv("MAX_RETRY_ATTEMPTS", 5)),
            RETRY_BASE_DELAY=float(os.getenv("RETRY_BASE_DELAY", 1.0)),
            RETRY_MAX_DELAY=float(os.getenv("RETRY_MAX_DELAY", 30.0)),
            CIRCUIT_BREAKER_FAILURE_THRESHOLD=int(
                os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", 5)
            ),
            CIRCUIT_BREAKER_RECOVERY_TIMEOUT=int(
                os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", 180)
            ),
            STREAM_BUFFER_SIZE=int(os.getenv("STREAM_BUFFER_SIZE", 8192)),
            CHUNK_SIZE=int(os.getenv("CHUNK_SIZE", 1024)),
            MAX_ACCUMULATED_CONTENT=int(
                os.getenv("MAX_ACCUMULATED_CONTENT", 1024 * 1024)
            ),
            STREAM_STATE_TTL=int(os.getenv("STREAM_STATE_TTL", 300)),
            CLEANUP_INTERVAL=int(os.getenv("CLEANUP_INTERVAL", 90)),
            HEALTH_CHECK_INTERVAL=int(os.getenv("HEALTH_CHECK_INTERVAL", 30)),
            METRICS_RETENTION_PERIOD=int(os.getenv("METRICS_RETENTION_PERIOD", 3600)),
            TCP_KEEPALIVE=os.getenv("TCP_KEEPALIVE", "true").lower() == "true",
            TCP_KEEPALIVE_IDLE=int(os.getenv("TCP_KEEPALIVE_IDLE", 60)),
            TCP_KEEPALIVE_INTERVAL=int(os.getenv("TCP_KEEPALIVE_INTERVAL", 10)),
            TCP_KEEPALIVE_COUNT=int(os.getenv("TCP_KEEPALIVE_COUNT", 6)),
            SSE_RETRY_INTERVAL=int(os.getenv("SSE_RETRY_INTERVAL", 3000)),
            SSE_MAX_EVENT_SIZE=int(os.getenv("SSE_MAX_EVENT_SIZE", 65536)),
        )


# Global configuration instance
streaming_config = StreamingConfig.from_env()


# Nginx/Proxy configuration recommendations
NGINX_CONFIG_RECOMMENDATIONS = """
# Add these to your nginx.conf for optimal SSE streaming:

location /v1/chats/*/stream {
    proxy_pass http://backend;

    # Disable buffering for real-time streaming
    proxy_buffering off;
    proxy_cache off;

    # Set appropriate timeouts
    proxy_connect_timeout 180s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;

    # Enable keepalive
    proxy_http_version 1.1;
    proxy_set_header Connection "";

    # Forward necessary headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Last-Event-ID $http_last_event_id;

    # SSE specific headers
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header X-Accel-Buffering "no";
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Headers "Last-Event-ID";
    add_header Access-Control-Expose-Headers "Last-Event-ID";
}
"""

# Gunicorn configuration recommendations
GUNICORN_CONFIG_RECOMMENDATIONS = """
# Add these to your gunicorn.conf.py:

# Worker settings for streaming
worker_class = "uvicorn.workers.UvicornWorker"
workers = 4
worker_connections = 1000
max_requests = 0  # Disable worker recycling for long-running streams
max_requests_jitter = 0

# Timeout settings
timeout = 600  # 10 minutes - match STREAM_TIMEOUT
keepalive = 600  # Keep connections alive
graceful_timeout = 30

# Buffer settings
worker_tmp_dir = "/dev/shm"  # Use memory for temporary files
"""
