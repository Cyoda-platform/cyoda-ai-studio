"""
Stream Monitoring and Debugging Utilities

Provides comprehensive monitoring, debugging, and health checking
for streaming services to prevent and diagnose broken streams.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StreamState(Enum):
    """Stream states for monitoring."""

    STARTING = "starting"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


@dataclass
class StreamMetrics:
    """Metrics for a single stream."""

    stream_id: str
    conversation_id: str
    start_time: float
    end_time: Optional[float] = None
    state: StreamState = StreamState.STARTING
    events_sent: int = 0
    bytes_sent: int = 0
    error_message: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    last_event_id: Optional[str] = None

    @property
    def duration(self) -> float:
        """Get stream duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def is_active(self) -> bool:
        """Check if stream is currently active."""
        return self.state in [StreamState.STARTING, StreamState.ACTIVE]


class StreamMonitor:
    """Monitor and track streaming service health and performance."""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.active_streams: Dict[str, StreamMetrics] = {}
        self.stream_history: deque = deque(maxlen=max_history)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.performance_metrics = {
            "total_streams": 0,
            "successful_streams": 0,
            "failed_streams": 0,
            "average_duration": 0.0,
            "average_events_per_stream": 0.0,
            "average_bytes_per_stream": 0.0,
        }
        self.start_time = time.time()

    def start_stream(
        self,
        stream_id: str,
        conversation_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> StreamMetrics:
        """Start tracking a new stream."""
        metrics = StreamMetrics(
            stream_id=stream_id,
            conversation_id=conversation_id,
            start_time=time.time(),
            client_ip=client_ip,
            user_agent=user_agent,
        )

        self.active_streams[stream_id] = metrics
        self.performance_metrics["total_streams"] += 1

        logger.info(
            f"Started tracking stream {stream_id} for conversation {conversation_id}"
        )
        return metrics

    def update_stream(
        self,
        stream_id: str,
        state: Optional[StreamState] = None,
        events_sent: Optional[int] = None,
        bytes_sent: Optional[int] = None,
        last_event_id: Optional[str] = None,
    ):
        """Update stream metrics."""
        if stream_id not in self.active_streams:
            logger.warning(f"Attempted to update unknown stream {stream_id}")
            return

        metrics = self.active_streams[stream_id]

        if state:
            metrics.state = state
        if events_sent is not None:
            metrics.events_sent = events_sent
        if bytes_sent is not None:
            metrics.bytes_sent = bytes_sent
        if last_event_id:
            metrics.last_event_id = last_event_id

    def end_stream(
        self, stream_id: str, state: StreamState, error_message: Optional[str] = None
    ):
        """End tracking for a stream."""
        if stream_id not in self.active_streams:
            logger.warning(f"Attempted to end unknown stream {stream_id}")
            return

        metrics = self.active_streams[stream_id]
        metrics.end_time = time.time()
        metrics.state = state
        metrics.error_message = error_message

        # Move to history
        self.stream_history.append(metrics)
        del self.active_streams[stream_id]

        # Update performance metrics
        if state == StreamState.COMPLETED:
            self.performance_metrics["successful_streams"] += 1
        else:
            self.performance_metrics["failed_streams"] += 1
            if error_message:
                self.error_counts[error_message] += 1

        self._update_averages()

        logger.info(f"Ended tracking stream {stream_id} with state {state.value}")

    def _update_averages(self):
        """Update average performance metrics."""
        completed_streams = [
            s for s in self.stream_history if s.state == StreamState.COMPLETED
        ]

        if completed_streams:
            total_duration = sum(s.duration for s in completed_streams)
            total_events = sum(s.events_sent for s in completed_streams)
            total_bytes = sum(s.bytes_sent for s in completed_streams)
            count = len(completed_streams)

            self.performance_metrics["average_duration"] = total_duration / count
            self.performance_metrics["average_events_per_stream"] = total_events / count
            self.performance_metrics["average_bytes_per_stream"] = total_bytes / count

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        now = time.time()
        uptime = now - self.start_time

        # Calculate success rate
        total = self.performance_metrics["total_streams"]
        successful = self.performance_metrics["successful_streams"]
        success_rate = (successful / total * 100) if total > 0 else 100

        # Get recent error rate (last 5 minutes)
        recent_cutoff = now - 300  # 5 minutes
        recent_streams = [
            s for s in self.stream_history if s.start_time > recent_cutoff
        ]
        recent_failures = [
            s for s in recent_streams if s.state != StreamState.COMPLETED
        ]
        recent_error_rate = (
            (len(recent_failures) / len(recent_streams) * 100) if recent_streams else 0
        )

        # Identify long-running streams (potential issues)
        long_running_threshold = 300  # 5 minutes
        long_running_streams = [
            s
            for s in self.active_streams.values()
            if s.duration > long_running_threshold
        ]

        return {
            "uptime_seconds": uptime,
            "active_streams": len(self.active_streams),
            "total_streams": total,
            "success_rate_percent": round(success_rate, 2),
            "recent_error_rate_percent": round(recent_error_rate, 2),
            "performance_metrics": self.performance_metrics,
            "top_errors": dict(
                sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ),
            "long_running_streams": len(long_running_streams),
            "long_running_details": [
                {
                    "stream_id": s.stream_id,
                    "conversation_id": s.conversation_id,
                    "duration_seconds": round(s.duration, 2),
                    "events_sent": s.events_sent,
                    "state": s.state.value,
                }
                for s in long_running_streams[:10]  # Top 10
            ],
        }

    def get_stream_details(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific stream."""
        # Check active streams first
        if stream_id in self.active_streams:
            return asdict(self.active_streams[stream_id])

        # Check history
        for metrics in reversed(self.stream_history):
            if metrics.stream_id == stream_id:
                return asdict(metrics)

        return None

    def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old monitoring data."""
        cutoff_time = time.time() - (max_age_hours * 3600)

        # Clean up history
        while self.stream_history and self.stream_history[0].start_time < cutoff_time:
            self.stream_history.popleft()

        # Clean up error counts (reset periodically)
        if len(self.error_counts) > 100:  # Arbitrary limit
            # Keep only top 50 errors
            top_errors = dict(
                sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:50]
            )
            self.error_counts.clear()
            self.error_counts.update(top_errors)

        logger.info(f"Cleaned up monitoring data older than {max_age_hours} hours")

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external monitoring systems."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": self.get_health_status(),
            "active_streams": [asdict(s) for s in self.active_streams.values()],
            "recent_history": [
                asdict(s) for s in list(self.stream_history)[-100:]
            ],  # Last 100
        }


# Global monitor instance
stream_monitor = StreamMonitor()


def monitor_stream(func):
    """Decorator to automatically monitor stream functions."""

    async def wrapper(*args, **kwargs):
        # Extract stream info from arguments
        stream_id = kwargs.get("stream_id") or f"stream_{int(time.time() * 1000)}"
        conversation_id = kwargs.get("conversation_id", "unknown")

        # Start monitoring
        stream_monitor.start_stream(stream_id, conversation_id)

        try:
            # Execute the function
            result = await func(*args, **kwargs)
            stream_monitor.end_stream(stream_id, StreamState.COMPLETED)
            return result
        except Exception as e:
            stream_monitor.end_stream(stream_id, StreamState.FAILED, str(e))
            raise

    return wrapper
