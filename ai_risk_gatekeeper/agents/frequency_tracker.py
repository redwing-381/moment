"""
Real-time Frequency Tracker using Windowed Aggregation.

This module demonstrates Confluent Kafka's stream processing capabilities
by maintaining real-time event frequency counts per actor using sliding windows.
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class WindowedCounter:
    """
    Sliding window counter for tracking event frequency.
    
    Uses a time-bucketed approach for efficient memory usage
    while maintaining accurate frequency counts.
    """
    window_size_seconds: int = 60
    bucket_size_seconds: int = 5
    
    # actor_id -> {bucket_timestamp -> count}
    _buckets: Dict[str, Dict[int, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def _get_bucket_key(self, timestamp: Optional[float] = None) -> int:
        """Get the bucket key for a timestamp."""
        ts = timestamp or time.time()
        return int(ts // self.bucket_size_seconds) * self.bucket_size_seconds
    
    def _cleanup_old_buckets(self, actor_id: str, current_time: float) -> None:
        """Remove buckets outside the window."""
        cutoff = current_time - self.window_size_seconds
        buckets = self._buckets[actor_id]
        old_keys = [k for k in buckets.keys() if k < cutoff]
        for key in old_keys:
            del buckets[key]
    
    def record_event(self, actor_id: str, timestamp: Optional[float] = None) -> int:
        """
        Record an event for an actor and return current frequency.
        
        Args:
            actor_id: The actor identifier
            timestamp: Event timestamp (uses current time if not provided)
            
        Returns:
            int: Current frequency (events in last window_size_seconds)
        """
        current_time = timestamp or time.time()
        bucket_key = self._get_bucket_key(current_time)
        
        with self._lock:
            self._buckets[actor_id][bucket_key] += 1
            self._cleanup_old_buckets(actor_id, current_time)
            return self.get_frequency(actor_id, current_time)
    
    def get_frequency(self, actor_id: str, current_time: Optional[float] = None) -> int:
        """
        Get the current frequency for an actor.
        
        Args:
            actor_id: The actor identifier
            current_time: Reference time (uses current time if not provided)
            
        Returns:
            int: Number of events in the last window_size_seconds
        """
        current_time = current_time or time.time()
        cutoff = current_time - self.window_size_seconds
        
        with self._lock:
            buckets = self._buckets.get(actor_id, {})
            return sum(count for ts, count in buckets.items() if ts >= cutoff)
    
    def get_all_frequencies(self) -> Dict[str, int]:
        """Get frequencies for all tracked actors."""
        current_time = time.time()
        result = {}
        
        with self._lock:
            for actor_id in list(self._buckets.keys()):
                self._cleanup_old_buckets(actor_id, current_time)
                freq = self.get_frequency(actor_id, current_time)
                if freq > 0:
                    result[actor_id] = freq
        
        return result
    
    def get_stats(self) -> Dict[str, any]:
        """Get tracker statistics."""
        frequencies = self.get_all_frequencies()
        return {
            "active_actors": len(frequencies),
            "total_events_in_window": sum(frequencies.values()),
            "max_frequency": max(frequencies.values()) if frequencies else 0,
            "frequencies": frequencies
        }


class FrequencyTracker:
    """
    Global frequency tracker for the risk gatekeeper system.
    
    This singleton maintains real-time frequency counts across
    all events processed by the system.
    """
    
    _instance: Optional['FrequencyTracker'] = None
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
        
        self._counter = WindowedCounter(
            window_size_seconds=60,
            bucket_size_seconds=5
        )
        self._total_events = 0
        self._initialized = True
        logger.info("FrequencyTracker initialized with 60s window, 5s buckets")
    
    def record_event(self, actor_id: str, timestamp: Optional[float] = None) -> int:
        """Record an event and return current frequency."""
        self._total_events += 1
        return self._counter.record_event(actor_id, timestamp)
    
    def get_frequency(self, actor_id: str) -> int:
        """Get current frequency for an actor."""
        return self._counter.get_frequency(actor_id)
    
    def get_all_frequencies(self) -> Dict[str, int]:
        """Get all actor frequencies."""
        return self._counter.get_all_frequencies()
    
    def get_stats(self) -> Dict[str, any]:
        """Get tracker statistics."""
        stats = self._counter.get_stats()
        stats["total_events_processed"] = self._total_events
        return stats
    
    def reset(self) -> None:
        """Reset the tracker (for testing)."""
        self._counter = WindowedCounter(
            window_size_seconds=60,
            bucket_size_seconds=5
        )
        self._total_events = 0


# Global instance
frequency_tracker = FrequencyTracker()


def get_frequency_tracker() -> FrequencyTracker:
    """Get the global frequency tracker instance."""
    return frequency_tracker
