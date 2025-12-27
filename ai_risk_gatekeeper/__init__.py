"""
AI Risk Gatekeeper - Real-time enterprise action risk assessment system.

This package provides event-driven risk assessment for enterprise actions
using Confluent Kafka and Google Cloud Vertex AI.
"""

__version__ = "1.0.0"

from ai_risk_gatekeeper.agents import (
    EventProducer,
    SignalProcessor,
    DecisionAgent,
    ActionAgent,
    BehaviorPattern,
    create_event_producer,
    create_signal_processor,
    create_decision_agent,
    create_action_agent,
)
from ai_risk_gatekeeper.models import (
    EnterpriseActionEvent,
    RiskSignal,
    RiskDecision,
)

__all__ = [
    "__version__",
    "EventProducer",
    "SignalProcessor",
    "DecisionAgent",
    "ActionAgent",
    "BehaviorPattern",
    "create_event_producer",
    "create_signal_processor",
    "create_decision_agent",
    "create_action_agent",
    "EnterpriseActionEvent",
    "RiskSignal",
    "RiskDecision",
]