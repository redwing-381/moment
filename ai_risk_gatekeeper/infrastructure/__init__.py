"""
Infrastructure module for the AI Risk Gatekeeper system.
"""

from ai_risk_gatekeeper.infrastructure.kafka_setup import (
    KafkaInfrastructure,
    setup_kafka_infrastructure,
    TOPIC_CONFIGS,
)

__all__ = [
    "KafkaInfrastructure",
    "setup_kafka_infrastructure",
    "TOPIC_CONFIGS",
]
