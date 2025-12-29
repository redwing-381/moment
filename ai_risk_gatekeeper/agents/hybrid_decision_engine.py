"""
Hybrid Decision Engine for the AI Risk Gatekeeper system.

Combines fast rule-based decisions with selective AI evaluation to handle
high throughput while maintaining intelligent decision-making for ambiguous cases.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, Callable

from ai_risk_gatekeeper.models.events import (
    RiskSignal, DecisionResult, DecisionMode, DecisionStats
)
from ai_risk_gatekeeper.agents.decision_cache import DecisionCache


logger = logging.getLogger(__name__)


class HybridDecisionEngine:
    """
    Hybrid decision engine that routes decisions based on risk score and mode.
    
    - FAST mode: Rule-based only, 10k+ decisions/sec
    - HYBRID mode: Rules for clear cases, AI for ambiguous (0.3-0.8)
    - FULL_AI mode: AI for everything (demo only)
    """
    
    def __init__(
        self,
        low_threshold: float = 0.3,
        high_threshold: float = 0.8,
        max_concurrent_ai: int = 10,
        max_queue_size: int = 100,
        cache_ttl_seconds: int = 300,
        cache_max_size: int = 1000
    ):
        """
        Initialize the hybrid decision engine.
        
        Args:
            low_threshold: Risk score below this = auto-allow (default 0.3)
            high_threshold: Risk score above this = auto-block (default 0.8)
            max_concurrent_ai: Max concurrent AI requests (default 10)
            max_queue_size: Max queued AI requests before fallback (default 100)
            cache_ttl_seconds: Cache TTL in seconds (default 300)
            cache_max_size: Max cache entries (default 1000)
        """
        self._low_threshold = low_threshold
        self._high_threshold = high_threshold
        self._max_concurrent_ai = max_concurrent_ai
        self._max_queue_size = max_queue_size
        
        # Decision mode
        self._mode = DecisionMode.HYBRID
        
        # Cache for AI decisions
        self._cache = DecisionCache(
            max_size=cache_max_size,
            ttl_seconds=cache_ttl_seconds
        )
        
        # AI client (initialized lazily)
        self._ai_client = None
        self._model_name = None
        
        # Concurrency control
        self._ai_semaphore = asyncio.Semaphore(max_concurrent_ai)
        self._ai_queue_size = 0
        
        # Statistics
        self._stats = DecisionStats(mode=self._mode.value)
        self._rule_latencies: list = []
        self._cache_latencies: list = []
        self._ai_latencies: list = []
    
    def _init_ai_client(self) -> bool:
        """Initialize the AI client if not already done."""
        if self._ai_client is not None:
            return True
        
        try:
            api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                from google import genai
                self._ai_client = genai.Client(api_key=api_key)
                self._model_name = os.getenv("VERTEX_AI_MODEL_NAME", "gemini-2.0-flash-lite")
                logger.info(f"AI client initialized with model {self._model_name}")
                return True
            else:
                logger.warning("No AI API key found, AI decisions will use fallback")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            return False
    
    def set_mode(self, mode: DecisionMode) -> None:
        """Set the decision mode."""
        self._mode = mode
        self._stats.mode = mode.value
        logger.info(f"Decision mode set to {mode.value}")
    
    def get_mode(self) -> DecisionMode:
        """Get the current decision mode."""
        return self._mode
    
    async def decide(self, signal: RiskSignal) -> DecisionResult:
        """
        Make a decision for a risk signal.
        
        Routes to rule-based or AI based on mode and risk score.
        
        Args:
            signal: The risk signal to evaluate
            
        Returns:
            DecisionResult with decision and metadata
        """
        start_time = time.perf_counter()
        
        # FAST mode: always use rules
        if self._mode == DecisionMode.FAST:
            return self._rule_decision(signal, start_time)
        
        # Check if clear-cut case (rules apply regardless of mode)
        if signal.risk_score < self._low_threshold:
            return self._rule_decision(signal, start_time, decision="allow")
        
        if signal.risk_score > self._high_threshold:
            return self._rule_decision(signal, start_time, decision="block")
        
        # Ambiguous case (0.3 - 0.8) - check cache first
        pattern_hash = self._cache.compute_pattern_hash(signal)
        cached = self._cache.get(pattern_hash)
        if cached:
            latency = (time.perf_counter() - start_time) * 1000
            cached.latency_ms = latency
            cached.correlation_id = signal.correlation_id
            cached.actor_id = signal.actor_id
            self._record_latency("cache", latency)
            return cached
        
        # HYBRID mode with cache miss - go to AI
        if self._mode == DecisionMode.HYBRID:
            return await self._ai_decision(signal, pattern_hash, start_time)
        
        # FULL_AI mode - always go to AI
        if self._mode == DecisionMode.FULL_AI:
            return await self._ai_decision(signal, pattern_hash, start_time)
        
        # Fallback
        return self._rule_decision(signal, start_time)
    
    def _rule_decision(
        self, 
        signal: RiskSignal, 
        start_time: float,
        decision: Optional[str] = None
    ) -> DecisionResult:
        """Make a fast rule-based decision."""
        if decision is None:
            # Determine decision from risk score
            if signal.risk_score < self._low_threshold:
                decision = "allow"
                confidence = 0.9
            elif signal.risk_score > self._high_threshold:
                decision = "block"
                confidence = 0.9
            elif signal.risk_score >= 0.5:
                decision = "throttle"
                confidence = 0.7
            else:
                decision = "allow"
                confidence = 0.7
        else:
            confidence = 0.9 if decision in ("allow", "block") else 0.7
        
        latency = (time.perf_counter() - start_time) * 1000
        
        # Generate reason
        if decision == "allow":
            reason = f"Low risk ({signal.risk_score:.0%}) - auto-approved by rules"
        elif decision == "block":
            reason = f"High risk ({signal.risk_score:.0%}) - auto-blocked by rules"
        elif decision == "throttle":
            reason = f"Medium risk ({signal.risk_score:.0%}) - rate limited by rules"
        else:
            reason = f"Risk score {signal.risk_score:.0%} - rule-based decision"
        
        self._stats.rule_decisions += 1
        self._stats.total_decisions += 1
        self._record_latency("rule", latency)
        
        return DecisionResult(
            decision=decision,
            confidence=confidence,
            reason=reason,
            source="rule",
            latency_ms=latency,
            provisional=False,
            correlation_id=signal.correlation_id,
            actor_id=signal.actor_id
        )
    
    async def _ai_decision(
        self, 
        signal: RiskSignal, 
        pattern_hash: str,
        start_time: float
    ) -> DecisionResult:
        """Make an AI-powered decision with concurrency control."""
        # Check queue overflow
        if self._ai_queue_size >= self._max_queue_size:
            logger.warning("AI queue overflow, falling back to rules")
            return self._rule_decision(signal, start_time)
        
        self._ai_queue_size += 1
        self._stats.ai_queue_size = self._ai_queue_size
        
        try:
            async with self._ai_semaphore:
                self._stats.ai_pending = self._max_concurrent_ai - self._ai_semaphore._value
                result = await self._query_ai(signal, start_time)
                
                # Cache the result
                self._cache.put(pattern_hash, result)
                
                return result
        finally:
            self._ai_queue_size -= 1
            self._stats.ai_queue_size = self._ai_queue_size
    
    async def _query_ai(self, signal: RiskSignal, start_time: float) -> DecisionResult:
        """Query the AI model for a decision."""
        if not self._init_ai_client():
            return self._rule_decision(signal, start_time)
        
        prompt = self._build_prompt(signal)
        
        try:
            from google.genai import types
            
            # Run in executor to not block event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._ai_client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=500,
                    )
                )
            )
            
            result = self._parse_ai_response(response.text, signal)
            latency = (time.perf_counter() - start_time) * 1000
            
            self._stats.ai_decisions += 1
            self._stats.total_decisions += 1
            self._record_latency("ai", latency)
            
            return DecisionResult(
                decision=result["decision"],
                confidence=result["confidence"],
                reason=result["reason"],
                source="ai",
                latency_ms=latency,
                provisional=False,
                correlation_id=signal.correlation_id,
                actor_id=signal.actor_id
            )
            
        except Exception as e:
            logger.error(f"AI query failed: {e}")
            return self._rule_decision(signal, start_time)
    
    def _build_prompt(self, signal: RiskSignal) -> str:
        """Build the AI prompt."""
        return f"""You are a security risk assessment AI. Analyze this risk signal and provide a decision.

Risk Signal:
- Actor ID: {signal.actor_id}
- Risk Score: {signal.risk_score:.2f}
- Risk Factors: {", ".join(signal.risk_factors) or "none"}
- Action: {signal.original_event.action}
- Role: {signal.original_event.role}
- Frequency (last 60s): {signal.original_event.frequency_last_60s}
- Geographic Change: {signal.original_event.geo_change}
- Resource Sensitivity: {signal.original_event.resource_sensitivity}

Respond with JSON only:
{{"decision": "allow|throttle|block|escalate", "confidence": 0.0-1.0, "reason": "brief explanation"}}"""
    
    def _parse_ai_response(self, response_text: str, signal: RiskSignal) -> Dict[str, Any]:
        """Parse AI response JSON."""
        import json
        
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        
        try:
            result = json.loads(text)
            decision = result.get("decision", "escalate")
            if decision not in ("allow", "throttle", "block", "escalate"):
                decision = "escalate"
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            reason = result.get("reason", "AI decision")
            return {"decision": decision, "confidence": confidence, "reason": reason}
        except:
            # Fallback if parsing fails
            if signal.risk_score >= 0.6:
                return {"decision": "throttle", "confidence": 0.6, "reason": "AI response parsing failed, using fallback"}
            return {"decision": "allow", "confidence": 0.6, "reason": "AI response parsing failed, using fallback"}
    
    def _record_latency(self, source: str, latency: float) -> None:
        """Record latency for statistics."""
        if source == "rule":
            self._rule_latencies.append(latency)
            if len(self._rule_latencies) > 100:
                self._rule_latencies = self._rule_latencies[-100:]
            self._stats.avg_rule_latency_ms = sum(self._rule_latencies) / len(self._rule_latencies)
        elif source == "cache":
            self._cache_latencies.append(latency)
            if len(self._cache_latencies) > 100:
                self._cache_latencies = self._cache_latencies[-100:]
            self._stats.avg_cache_latency_ms = sum(self._cache_latencies) / len(self._cache_latencies)
        elif source == "ai":
            self._ai_latencies.append(latency)
            if len(self._ai_latencies) > 100:
                self._ai_latencies = self._ai_latencies[-100:]
            self._stats.avg_ai_latency_ms = sum(self._ai_latencies) / len(self._ai_latencies)
    
    def get_stats(self) -> DecisionStats:
        """Get current statistics."""
        self._stats.ai_pending = self._max_concurrent_ai - self._ai_semaphore._value
        return self._stats
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = DecisionStats(mode=self._mode.value)
        self._rule_latencies.clear()
        self._cache_latencies.clear()
        self._ai_latencies.clear()
        self._cache.clear()
    
    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.stats
