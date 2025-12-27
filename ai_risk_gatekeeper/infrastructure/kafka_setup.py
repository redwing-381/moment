"""
Kafka infrastructure setup for the AI Risk Gatekeeper system.

This module handles topic creation and configuration for Confluent Cloud.
"""

import logging
from typing import Dict, List, Optional

from confluent_kafka.admin import AdminClient, NewTopic, KafkaException

from ai_risk_gatekeeper.config.settings import config_manager, KafkaConfig


logger = logging.getLogger(__name__)


# Topic configurations
TOPIC_CONFIGS = {
    "enterprise-action-events": {
        "num_partitions": 3,
        "replication_factor": 3,
        "config": {
            "retention.ms": "604800000",  # 7 days
            "cleanup.policy": "delete",
        }
    },
    "risk-signals": {
        "num_partitions": 3,
        "replication_factor": 3,
        "config": {
            "retention.ms": "604800000",
            "cleanup.policy": "delete",
        }
    },
    "risk-decisions": {
        "num_partitions": 3,
        "replication_factor": 3,
        "config": {
            "retention.ms": "2592000000",  # 30 days for audit
            "cleanup.policy": "delete",
        }
    },
}


class KafkaInfrastructure:
    """Manages Kafka infrastructure setup and verification."""
    
    def __init__(self, kafka_config: Optional[KafkaConfig] = None):
        self._kafka_config = kafka_config
        self._admin_client: Optional[AdminClient] = None
    
    @property
    def kafka_config(self) -> KafkaConfig:
        if self._kafka_config is None:
            config = config_manager.load_config()
            self._kafka_config = config.kafka
        return self._kafka_config
    
    def _get_admin_config(self) -> Dict[str, str]:
        return {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": self.kafka_config.security_protocol,
            "sasl.mechanisms": self.kafka_config.sasl_mechanism,
            "sasl.username": self.kafka_config.sasl_username,
            "sasl.password": self.kafka_config.sasl_password,
        }
    
    def connect(self) -> None:
        """Connect to Kafka admin."""
        self._admin_client = AdminClient(self._get_admin_config())
        logger.info("Connected to Kafka admin")
    
    def list_topics(self) -> List[str]:
        """List all existing topics."""
        if self._admin_client is None:
            raise RuntimeError("Not connected")
        
        metadata = self._admin_client.list_topics(timeout=10)
        return list(metadata.topics.keys())
    
    def create_topics(self, topics: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Create required Kafka topics.
        
        Args:
            topics: List of topic names to create (uses defaults if None)
            
        Returns:
            Dict mapping topic names to creation success
        """
        if self._admin_client is None:
            raise RuntimeError("Not connected")
        
        topics_to_create = topics or list(TOPIC_CONFIGS.keys())
        existing = set(self.list_topics())
        results = {}
        
        new_topics = []
        for topic_name in topics_to_create:
            if topic_name in existing:
                logger.info(f"Topic '{topic_name}' already exists")
                results[topic_name] = True
                continue
            
            config = TOPIC_CONFIGS.get(topic_name, {
                "num_partitions": 3,
                "replication_factor": 3,
                "config": {}
            })
            
            new_topics.append(NewTopic(
                topic=topic_name,
                num_partitions=config["num_partitions"],
                replication_factor=config["replication_factor"],
                config=config.get("config", {})
            ))
        
        if not new_topics:
            return results
        
        # Create topics
        futures = self._admin_client.create_topics(new_topics)
        
        for topic, future in futures.items():
            try:
                future.result()
                logger.info(f"Created topic '{topic}'")
                results[topic] = True
            except KafkaException as e:
                logger.error(f"Failed to create topic '{topic}': {e}")
                results[topic] = False
        
        return results
    
    def verify_topics(self) -> Dict[str, bool]:
        """Verify all required topics exist."""
        existing = set(self.list_topics())
        required = [
            self.kafka_config.enterprise_action_events_topic,
            self.kafka_config.risk_signals_topic,
            self.kafka_config.risk_decisions_topic,
        ]
        
        return {topic: topic in existing for topic in required}
    
    def verify_connectivity(self) -> bool:
        """Verify Kafka cluster connectivity."""
        try:
            if self._admin_client is None:
                self.connect()
            
            metadata = self._admin_client.list_topics(timeout=10)
            logger.info(f"Connected to Kafka cluster with {len(metadata.topics)} topics")
            return True
        except Exception as e:
            logger.error(f"Kafka connectivity check failed: {e}")
            return False


def setup_kafka_infrastructure() -> bool:
    """
    Set up Kafka infrastructure for the system.
    
    Returns:
        bool: True if setup successful
    """
    infra = KafkaInfrastructure()
    
    try:
        infra.connect()
        
        # Verify connectivity
        if not infra.verify_connectivity():
            return False
        
        # Create topics
        results = infra.create_topics()
        
        # Verify all topics exist
        verification = infra.verify_topics()
        all_exist = all(verification.values())
        
        if all_exist:
            logger.info("All required Kafka topics are ready")
        else:
            missing = [t for t, exists in verification.items() if not exists]
            logger.warning(f"Missing topics: {missing}")
        
        return all_exist
        
    except Exception as e:
        logger.error(f"Kafka infrastructure setup failed: {e}")
        return False
