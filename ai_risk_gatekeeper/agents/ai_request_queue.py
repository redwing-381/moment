"""
AI Request Queue for the AI Risk Gatekeeper system.

Manages batching and rate limiting of AI requests with concurrency control
and overflow fallback.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, List, Dict, Any

from ai_risk_gatekeeper.models.events import RiskSignal, DecisionResult


logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """A queued AI request with its future for result delivery."""
    signal: RiskSignal
    future: asyncio.Future
    queued_at: float


class AIRequestQueue:
    """
    Manages AI requests with concurrency control and overflow handling.
    
    Features:
    - Semaphore-based concurrency limiting
    - Queue overflow detection with fallback
    - Exponential backoff on rate limit errors
    - Statistics tracking
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        max_queue: int = 100,
        initial_backoff_ms: int = 1000,
        max_backoff_ms: int = 30000
    ):
        """
        Initialize the AI request queue.
        
        Args:
            max_concurrent: Maximum concurrent AI requests (default 10)
            max_queue: Maximum queued requests before fallback (default 100)
            initial_backoff_ms: Initial backoff on rate limit (default 1s)
            max_backoff_ms: Maximum backoff time (default 30s)
        """
        self._max_concurrent = max_concurrent
        self._max_queue = max_queue
        self._initial_backoff_ms = initial_backoff_ms
        self._max_backoff_ms = max_backoff_ms
        
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: List[QueuedRequest] = []
        self._current_backoff_ms = 0
        
        # Statistics
        self._submitted = 0
        self._completed = 0
        self._overflowed = 0
        self._rate_limited = 0
    
    @property
    def queue_size(self) -> int:
        """Current queue size."""
        return len(self._queue)
    
    @property
    def in_flight(self) -> int:
        """Number of requests currently being processed."""
        return self._max_concurrent - self._semaphore._value
    
    def is_overloaded(self) -> bool:
        """Check if queue is overloaded."""
        return len(self._queue) >= self._max_queue
    
    async def submit(
        self,
        signal: RiskSignal,
        ai_func: Callable[[RiskSignal], Awaitable[DecisionResult]],
        fallback_func: Callable[[RiskSignal], DecisionResult]
    ) -> DecisionResult:
        """
        Submit a request to the queue.
        
        If queue is overloaded, returns fallback immediately.
        Otherwise, waits for semaphore and executes AI function.
        
        Args:
            signal: The risk signal to process
            ai_func: Async function to call AI
            fallback_func: Sync function for fallback decision
            
        Returns:
            DecisionResult from AI or fallback
        """
        self._submitted += 1
        
        # Check overflow
        if self.is_overloaded():
            self._overflowed += 1
            logger.warning(f"Queue overflow ({len(self._queue)}/{self._max_queue}), using fallback")
            return fallback_func(signal)
        
        # Apply backoff if rate limited
        if self._current_backoff_ms > 0:
            await asyncio.sleep(self._current_backoff_ms / 1000)
        
        # Wait for semaphore
        async with self._semaphore:
            try:
                result = await ai_func(signal)
                self._completed += 1
                # Reset backoff on success
                self._current_backoff_ms = 0
                return result
            except Exception as e:
                error_str = str(e).lower()
                if "rate" in error_str or "429" in error_str or "quota" in error_str:
                    self._rate_limited += 1
                    self._apply_backoff()
                    logger.warning(f"Rate limited, backoff now {self._current_backoff_ms}ms")
                return fallback_func(signal)
    
    def _apply_backoff(self) -> None:
        """Apply exponential backoff."""
        if self._current_backoff_ms == 0:
            self._current_backoff_ms = self._initial_backoff_ms
        else:
            self._current_backoff_ms = min(
                self._current_backoff_ms * 2,
                self._max_backoff_ms
            )
    
    def reset_backoff(self) -> None:
        """Reset backoff to zero."""
        self._current_backoff_ms = 0
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "max_concurrent": self._max_concurrent,
            "max_queue": self._max_queue,
            "queue_size": len(self._queue),
            "in_flight": self.in_flight,
            "submitted": self._submitted,
            "completed": self._completed,
            "overflowed": self._overflowed,
            "rate_limited": self._rate_limited,
            "current_backoff_ms": self._current_backoff_ms
        }
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self._submitted = 0
        self._completed = 0
        self._overflowed = 0
        self._rate_limited = 0
        self._current_backoff_ms = 0
