"""
Decision Cache for the AI Risk Gatekeeper system.

Implements an LRU cache with TTL for AI decisions to avoid repeated
API calls for similar risk patterns.
"""

import hashlib
import json
import time
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Dict, Any

from ai_risk_gatekeeper.models.events import DecisionResult, RiskSignal


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached decision with timestamp for TTL checking."""
    result: DecisionResult
    timestamp: float  # Unix timestamp when cached


class DecisionCache:
    """
    LRU cache with TTL for AI decisions.
    
    Caches decisions by risk pattern hash to avoid repeated AI calls
    for similar risk profiles. Uses OrderedDict for O(1) LRU eviction.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Initialize the decision cache.
        
        Args:
            max_size: Maximum number of entries (default 1000)
            ttl_seconds: Time-to-live in seconds (default 5 minutes)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0
    
    def compute_pattern_hash(self, signal: RiskSignal) -> str:
        """
        Compute a hash key for the risk pattern.
        
        Hashes the relevant risk factors (not actor-specific data) so that
        similar risk patterns can share cached decisions.
        
        Args:
            signal: The risk signal to hash
            
        Returns:
            MD5 hash string of the pattern
        """
        pattern = {
            "action": signal.original_event.action,
            "role": signal.original_event.role,
            "risk_bucket": round(signal.risk_score, 1),  # 0.1 granularity
            "factors": sorted(signal.risk_factors),
            "geo_change": signal.original_event.geo_change,
            "sensitivity": signal.original_event.resource_sensitivity
        }
        pattern_str = json.dumps(pattern, sort_keys=True)
        return hashlib.md5(pattern_str.encode()).hexdigest()
    
    def get(self, pattern_hash: str) -> Optional[DecisionResult]:
        """
        Get a cached decision by pattern hash.
        
        Returns None if not found or expired. Moves accessed entry
        to end for LRU ordering.
        
        Args:
            pattern_hash: The hash key to look up
            
        Returns:
            Cached DecisionResult or None
        """
        if pattern_hash not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[pattern_hash]
        
        # Check TTL
        if time.time() - entry.timestamp > self._ttl_seconds:
            del self._cache[pattern_hash]
            self._misses += 1
            return None
        
        # Move to end for LRU
        self._cache.move_to_end(pattern_hash)
        self._hits += 1
        
        # Return a copy with updated source
        result = entry.result
        return DecisionResult(
            decision=result.decision,
            confidence=result.confidence,
            reason=result.reason,
            source="cache",
            latency_ms=0.1,  # Cache lookup is near-instant
            provisional=False,
            correlation_id=result.correlation_id,
            actor_id=result.actor_id
        )
    
    def put(self, pattern_hash: str, result: DecisionResult) -> None:
        """
        Store a decision in the cache.
        
        Evicts oldest entry if cache is full (LRU eviction).
        
        Args:
            pattern_hash: The hash key
            result: The decision result to cache
        """
        # If key exists, remove it first (will be re-added at end)
        if pattern_hash in self._cache:
            del self._cache[pattern_hash]
        
        # Evict oldest if at capacity
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        
        # Add new entry at end
        self._cache[pattern_hash] = CacheEntry(
            result=result,
            timestamp=time.time()
        )
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Decision cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired = [
            key for key, entry in self._cache.items()
            if now - entry.timestamp > self._ttl_seconds
        ]
        for key in expired:
            del self._cache[key]
        return len(expired)
    
    @property
    def size(self) -> int:
        """Current number of cached entries."""
        return len(self._cache)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 1)
        }
