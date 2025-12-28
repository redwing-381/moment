"""
Kafka Metrics Tracker for real-time monitoring.

This module provides real-time Kafka metrics including:
- Messages produced/consumed per second
- Consumer lag
- Partition distribution
- Throughput statistics
"""

import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ThroughputTracker:
    """Tracks messages per second using a sliding window."""
    window_seconds: int = 10
    _timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def record(self) -> None:
        """Record a message timestamp."""
        with self._lock:
            self._timestamps.append(time.time())
    
    def get_rate(self) -> float:
        """Get messages per second over the window."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        with self._lock:
            # Count messages in window
            count = sum(1 for ts in self._timestamps if ts >= cutoff)
            return count / self.window_seconds if self.window_seconds > 0 else 0


class KafkaMetricsTracker:
    """
    Tracks Kafka metrics for dashboard display.
    
    Provides real-time visibility into Kafka operations.
    """
    
    _instance: Optional['KafkaMetricsTracker'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Throughput trackers
        self._produce_tracker = ThroughputTracker(window_seconds=10)
        self._consume_tracker = ThroughputTracker(window_seconds=10)
        
        # Counters
        self._total_produced = 0
        self._total_consumed = 0
        self._total_failed = 0
        
        # Partition tracking
        self._partition_counts: Dict[str, Dict[int, int]] = {}
        
        # Latency tracking
        self._latencies: deque = deque(maxlen=100)
        
        # Connection status
        self._connected = False
        self._last_produce_time: Optional[float] = None
        self._last_consume_time: Optional[float] = None
        
        # Topic stats
        self._topic_message_counts: Dict[str, int] = {}
        
        self._initialized = True
        logger.info("KafkaMetricsTracker initialized")
    
    def record_produce(self, topic: str, partition: int = 0, latency_ms: float = 0) -> None:
        """Record a produced message."""
        self._produce_tracker.record()
        self._total_produced += 1
        self._last_produce_time = time.time()
        self._connected = True
        
        # Track partition distribution
        if topic not in self._partition_counts:
            self._partition_counts[topic] = {}
        self._partition_counts[topic][partition] = self._partition_counts[topic].get(partition, 0) + 1
        
        # Track topic counts
        self._topic_message_counts[topic] = self._topic_message_counts.get(topic, 0) + 1
        
        # Track latency
        if latency_ms > 0:
            self._latencies.append(latency_ms)
    
    def record_consume(self, topic: str, partition: int = 0) -> None:
        """Record a consumed message."""
        self._consume_tracker.record()
        self._total_consumed += 1
        self._last_consume_time = time.time()
        self._connected = True
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self._total_failed += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current Kafka metrics."""
        now = time.time()
        
        # Calculate average latency
        avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0
        
        # Determine connection status
        connection_status = "disconnected"
        if self._connected:
            last_activity = max(
                self._last_produce_time or 0,
                self._last_consume_time or 0
            )
            if now - last_activity < 30:
                connection_status = "active"
            else:
                connection_status = "idle"
        
        # Get partition distribution for display
        partition_info = {}
        for topic, partitions in self._partition_counts.items():
            partition_info[topic] = {
                "partition_count": len(partitions),
                "distribution": dict(partitions)
            }
        
        return {
            "connection_status": connection_status,
            "produce_rate": round(self._produce_tracker.get_rate(), 1),
            "consume_rate": round(self._consume_tracker.get_rate(), 1),
            "total_produced": self._total_produced,
            "total_consumed": self._total_consumed,
            "total_failed": self._total_failed,
            "avg_latency_ms": round(avg_latency, 2),
            "topics": self._topic_message_counts,
            "partitions": partition_info,
            "last_produce_ago": round(now - self._last_produce_time, 1) if self._last_produce_time else None,
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._produce_tracker = ThroughputTracker(window_seconds=10)
        self._consume_tracker = ThroughputTracker(window_seconds=10)
        self._total_produced = 0
        self._total_consumed = 0
        self._total_failed = 0
        self._partition_counts = {}
        self._latencies = deque(maxlen=100)
        self._topic_message_counts = {}
        self._last_produce_time = None
        self._last_consume_time = None


# Global instance
kafka_metrics = KafkaMetricsTracker()


def get_kafka_metrics() -> KafkaMetricsTracker:
    """Get the global Kafka metrics tracker."""
    return kafka_metrics
