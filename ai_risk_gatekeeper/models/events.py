"""
Data models for events in the AI Risk Gatekeeper system.

These models define the structure of events flowing through the Kafka pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional
from datetime import datetime
from enum import Enum
import json


class DecisionMode(Enum):
    """Decision engine operating modes."""
    FAST = "fast"           # Rule-based only - fastest, 10k+ decisions/sec
    HYBRID = "hybrid"       # Rules + AI for ambiguous cases (0.3-0.8 risk)
    FULL_AI = "full_ai"     # AI for everything - slowest, demo only


@dataclass
class DecisionResult:
    """
    Extended decision result with routing and performance information.
    
    Used by the hybrid decision engine to track how decisions were made.
    """
    decision: Literal["allow", "throttle", "block", "escalate"]
    confidence: float           # 0.0 - 1.0
    reason: str
    source: Literal["rule", "cache", "ai"]  # How the decision was made
    latency_ms: float           # Processing time
    provisional: bool = False   # True if AI evaluation is pending
    correlation_id: str = ""
    actor_id: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reason": self.reason,
            "source": self.source,
            "latency_ms": self.latency_ms,
            "provisional": self.provisional,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DecisionResult':
        """Create from dictionary."""
        return cls(
            decision=data["decision"],
            confidence=data["confidence"],
            reason=data["reason"],
            source=data["source"],
            latency_ms=data["latency_ms"],
            provisional=data.get("provisional", False),
            correlation_id=data.get("correlation_id", ""),
            actor_id=data.get("actor_id", "")
        )


@dataclass
class DecisionStats:
    """Statistics for decision engine performance tracking."""
    mode: str = "hybrid"
    rule_decisions: int = 0
    cache_hits: int = 0
    ai_decisions: int = 0
    ai_pending: int = 0
    ai_queue_size: int = 0
    total_decisions: int = 0
    avg_rule_latency_ms: float = 0.0
    avg_cache_latency_ms: float = 0.0
    avg_ai_latency_ms: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "mode": self.mode,
            "rule_decisions": self.rule_decisions,
            "cache_hits": self.cache_hits,
            "ai_decisions": self.ai_decisions,
            "ai_pending": self.ai_pending,
            "ai_queue_size": self.ai_queue_size,
            "total_decisions": self.total_decisions,
            "avg_rule_latency_ms": round(self.avg_rule_latency_ms, 2),
            "avg_cache_latency_ms": round(self.avg_cache_latency_ms, 2),
            "avg_ai_latency_ms": round(self.avg_ai_latency_ms, 2)
        }


@dataclass
class EnterpriseActionEvent:
    """
    Represents a sensitive enterprise action that needs risk assessment.
    
    This is the input event that flows through the enterprise-action-events topic.
    """
    actor_id: str
    action: str
    role: str
    frequency_last_60s: int
    geo_change: bool
    timestamp: int
    session_id: str
    resource_sensitivity: str

    def to_json(self) -> str:
        """Convert the event to JSON string for Kafka publishing."""
        return json.dumps({
            "actor_id": self.actor_id,
            "action": self.action,
            "role": self.role,
            "frequency_last_60s": self.frequency_last_60s,
            "geo_change": self.geo_change,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "resource_sensitivity": self.resource_sensitivity
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'EnterpriseActionEvent':
        """Create an EnterpriseActionEvent from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class RiskSignal:
    """
    Represents processed risk indicators extracted from enterprise action events.
    
    This flows through the risk-signals topic after signal processing.
    """
    actor_id: str
    risk_score: float
    risk_factors: List[str]
    original_event: EnterpriseActionEvent
    processing_timestamp: int
    correlation_id: str

    def to_json(self) -> str:
        """Convert the risk signal to JSON string for Kafka publishing."""
        return json.dumps({
            "actor_id": self.actor_id,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "original_event": {
                "actor_id": self.original_event.actor_id,
                "action": self.original_event.action,
                "role": self.original_event.role,
                "frequency_last_60s": self.original_event.frequency_last_60s,
                "geo_change": self.original_event.geo_change,
                "timestamp": self.original_event.timestamp,
                "session_id": self.original_event.session_id,
                "resource_sensitivity": self.original_event.resource_sensitivity
            },
            "processing_timestamp": self.processing_timestamp,
            "correlation_id": self.correlation_id
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'RiskSignal':
        """Create a RiskSignal from JSON string."""
        data = json.loads(json_str)
        original_event = EnterpriseActionEvent(**data["original_event"])
        return cls(
            actor_id=data["actor_id"],
            risk_score=data["risk_score"],
            risk_factors=data["risk_factors"],
            original_event=original_event,
            processing_timestamp=data["processing_timestamp"],
            correlation_id=data["correlation_id"]
        )


@dataclass
class RiskDecision:
    """
    Represents an AI-generated risk decision for an enterprise action.
    
    This flows through the risk-decisions topic after AI processing.
    """
    actor_id: str
    decision: Literal["allow", "throttle", "block", "escalate"]
    confidence: float
    reason: str
    correlation_id: str
    decision_timestamp: int

    def to_json(self) -> str:
        """Convert the risk decision to JSON string for Kafka publishing."""
        return json.dumps({
            "actor_id": self.actor_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "reason": self.reason,
            "correlation_id": self.correlation_id,
            "decision_timestamp": self.decision_timestamp
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'RiskDecision':
        """Create a RiskDecision from JSON string."""
        data = json.loads(json_str)
        return cls(**data)