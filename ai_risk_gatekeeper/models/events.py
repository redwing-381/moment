"""
Data models for events in the AI Risk Gatekeeper system.

These models define the structure of events flowing through the Kafka pipeline.
"""

from dataclasses import dataclass
from typing import List, Literal
from datetime import datetime
import json


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