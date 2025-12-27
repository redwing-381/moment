"""
Agents module for the AI Risk Gatekeeper system.

This module contains the four independent agents that process events through the pipeline:
- Event Producer: Generates and publishes enterprise action events
- Signal Processing Agent: Extracts risk indicators from events
- Decision Agent: Makes AI-powered risk decisions
- Action Agent: Executes responses based on decisions
"""

from ai_risk_gatekeeper.agents.event_producer import (
    EventProducer,
    BehaviorPattern,
    EventGeneratorConfig,
    create_event_producer,
)
from ai_risk_gatekeeper.agents.signal_processor import (
    SignalProcessor,
    RiskScoringConfig,
    create_signal_processor,
)
from ai_risk_gatekeeper.agents.decision_agent import (
    DecisionAgent,
    create_decision_agent,
)
from ai_risk_gatekeeper.agents.action_agent import (
    ActionAgent,
    create_action_agent,
)

__all__ = [
    "EventProducer",
    "BehaviorPattern",
    "EventGeneratorConfig",
    "create_event_producer",
    "SignalProcessor",
    "RiskScoringConfig",
    "create_signal_processor",
    "DecisionAgent",
    "create_decision_agent",
    "ActionAgent",
    "create_action_agent",
]
