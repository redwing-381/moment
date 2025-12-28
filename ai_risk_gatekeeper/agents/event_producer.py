"""
Event Producer Agent for the AI Risk Gatekeeper system.

This agent generates and publishes enterprise action events to Kafka.
It simulates realistic enterprise scenarios including normal operations
and suspicious behavior patterns.
"""

import logging
import random
import time
import uuid
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from confluent_kafka import Producer, KafkaError, KafkaException

from ai_risk_gatekeeper.models.events import EnterpriseActionEvent
from ai_risk_gatekeeper.config.settings import config_manager, KafkaConfig

# Optional import for Avro serialization
try:
    from ai_risk_gatekeeper.agents.schema_registry import AvroSerializer
except ImportError:
    AvroSerializer = None


logger = logging.getLogger(__name__)


class BehaviorPattern(Enum):
    """Types of behavior patterns for event generation."""
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    HIGH_FREQUENCY = "high_frequency"
    GEO_ANOMALY = "geo_anomaly"
    PRIVILEGE_ESCALATION = "privilege_escalation"


@dataclass
class EventGeneratorConfig:
    """Configuration for event generation patterns."""
    normal_frequency_range: tuple = (1, 5)
    suspicious_frequency_range: tuple = (15, 50)
    geo_change_probability_normal: float = 0.05
    geo_change_probability_suspicious: float = 0.8
    
    # Actor pools
    normal_actors: tuple = ("user_001", "user_002", "user_003", "user_004", "user_005")
    suspicious_actors: tuple = ("user_suspicious_001", "user_suspicious_002")
    
    # Action types
    normal_actions: tuple = ("file_read", "email_send", "report_view", "dashboard_access")
    sensitive_actions: tuple = ("file_download", "bulk_export", "admin_access", "config_change", "data_delete")
    
    # Roles
    normal_roles: tuple = ("developer", "analyst", "manager", "support")
    elevated_roles: tuple = ("admin", "superuser", "root")
    
    # Resource sensitivity levels
    sensitivity_levels: tuple = ("low", "medium", "high", "critical")


class EventProducer:
    """
    Produces enterprise action events to Kafka.
    
    This agent generates realistic enterprise scenarios and publishes
    them to the enterprise-action-events topic with proper error handling
    and timing instrumentation.
    """
    
    def __init__(
        self,
        kafka_config: Optional[KafkaConfig] = None,
        generator_config: Optional[EventGeneratorConfig] = None,
        avro_serializer: Optional['AvroSerializer'] = None
    ):
        """
        Initialize the Event Producer.
        
        Args:
            kafka_config: Kafka configuration (uses global config if not provided)
            generator_config: Event generation configuration
            avro_serializer: Optional Avro serializer for Schema Registry integration
        """
        self._kafka_config = kafka_config
        self._generator_config = generator_config or EventGeneratorConfig()
        self._avro_serializer = avro_serializer
        self._producer: Optional[Producer] = None
        self._delivery_callbacks: list = []
        self._events_produced = 0
        self._events_failed = 0
        self._using_avro = avro_serializer is not None
    
    @property
    def kafka_config(self) -> KafkaConfig:
        """Get Kafka configuration, loading from global config if needed."""
        if self._kafka_config is None:
            config = config_manager.load_config()
            self._kafka_config = config.kafka
        return self._kafka_config
    
    def _get_producer_config(self) -> Dict[str, Any]:
        """Build Kafka producer configuration dictionary."""
        return {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": self.kafka_config.security_protocol,
            "sasl.mechanisms": self.kafka_config.sasl_mechanism,
            "sasl.username": self.kafka_config.sasl_username,
            "sasl.password": self.kafka_config.sasl_password,
            "client.id": "ai-risk-gatekeeper-event-producer",
            # Performance settings for low latency
            "linger.ms": 5,
            "batch.size": 16384,
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 100,
        }
    
    def connect(self) -> None:
        """
        Establish connection to Kafka cluster.
        
        Raises:
            KafkaException: If connection fails
        """
        if self._producer is not None:
            return
        
        try:
            config = self._get_producer_config()
            self._producer = Producer(config)
            logger.info(f"Event Producer connected to {self.kafka_config.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect Event Producer: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Kafka cluster and flush pending messages."""
        if self._producer is not None:
            # Flush with longer timeout for network latency
            remaining = self._producer.flush(timeout=15)
            if remaining > 0:
                logger.warning(f"{remaining} messages still pending after flush")
            self._producer = None
            logger.info("Event Producer disconnected")
    
    def _delivery_callback(self, err: Optional[KafkaError], msg) -> None:
        """
        Callback for message delivery confirmation.
        
        Args:
            err: Error if delivery failed, None if successful
            msg: The message that was delivered
        """
        if err is not None:
            self._events_failed += 1
            logger.error(f"Message delivery failed: {err}")
        else:
            self._events_produced += 1
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")

    def generate_event(
        self,
        pattern: BehaviorPattern = BehaviorPattern.NORMAL,
        actor_id: Optional[str] = None
    ) -> EnterpriseActionEvent:
        """
        Generate an enterprise action event based on the specified pattern.
        
        Args:
            pattern: The behavior pattern to simulate
            actor_id: Optional specific actor ID (random if not provided)
            
        Returns:
            EnterpriseActionEvent: Generated event
        """
        cfg = self._generator_config
        
        # Select actor based on pattern
        if actor_id is None:
            if pattern in (BehaviorPattern.SUSPICIOUS, BehaviorPattern.HIGH_FREQUENCY, 
                          BehaviorPattern.GEO_ANOMALY, BehaviorPattern.PRIVILEGE_ESCALATION):
                actor_id = random.choice(cfg.suspicious_actors)
            else:
                actor_id = random.choice(cfg.normal_actors)
        
        # Generate frequency based on pattern
        if pattern == BehaviorPattern.HIGH_FREQUENCY:
            frequency = random.randint(*cfg.suspicious_frequency_range)
        elif pattern == BehaviorPattern.SUSPICIOUS:
            frequency = random.randint(10, 30)
        else:
            frequency = random.randint(*cfg.normal_frequency_range)
        
        # Determine geo change based on pattern
        if pattern == BehaviorPattern.GEO_ANOMALY:
            geo_change = True
        elif pattern == BehaviorPattern.SUSPICIOUS:
            geo_change = random.random() < cfg.geo_change_probability_suspicious
        else:
            geo_change = random.random() < cfg.geo_change_probability_normal
        
        # Select action based on pattern
        if pattern in (BehaviorPattern.SUSPICIOUS, BehaviorPattern.PRIVILEGE_ESCALATION):
            action = random.choice(cfg.sensitive_actions)
        else:
            action = random.choice(cfg.normal_actions)
        
        # Select role based on pattern
        if pattern == BehaviorPattern.PRIVILEGE_ESCALATION:
            role = random.choice(cfg.elevated_roles)
        else:
            role = random.choice(cfg.normal_roles)
        
        # Determine resource sensitivity
        if pattern in (BehaviorPattern.SUSPICIOUS, BehaviorPattern.PRIVILEGE_ESCALATION):
            sensitivity = random.choice(["high", "critical"])
        else:
            sensitivity = random.choice(cfg.sensitivity_levels)
        
        return EnterpriseActionEvent(
            actor_id=actor_id,
            action=action,
            role=role,
            frequency_last_60s=frequency,
            geo_change=geo_change,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity=sensitivity
        )
    
    def publish_event(
        self,
        event: EnterpriseActionEvent,
        topic: Optional[str] = None
    ) -> float:
        """
        Publish an enterprise action event to Kafka.
        
        Args:
            event: The event to publish
            topic: Target topic (uses default if not provided)
            
        Returns:
            float: Time taken to publish in milliseconds
            
        Raises:
            RuntimeError: If producer is not connected
            KafkaException: If publishing fails
        """
        if self._producer is None:
            raise RuntimeError("Event Producer not connected. Call connect() first.")
        
        target_topic = topic or self.kafka_config.enterprise_action_events_topic
        
        start_time = time.perf_counter()
        
        try:
            # Serialize event - use Avro if available, otherwise JSON
            if self._avro_serializer is not None:
                try:
                    event_data = self._avro_serializer.serialize(event.to_dict())
                except Exception as avro_err:
                    logger.warning(f"Avro serialization failed, falling back to JSON: {avro_err}")
                    event_data = event.to_json()
            else:
                event_data = event.to_json()
            
            # Produce message with actor_id as key for partitioning
            self._producer.produce(
                topic=target_topic,
                key=event.actor_id,
                value=event_data,
                callback=self._delivery_callback
            )
            
            # Poll to trigger delivery callbacks
            self._producer.poll(0)
            
            end_time = time.perf_counter()
            publish_time_ms = (end_time - start_time) * 1000
            
            logger.info(
                f"Published event for actor {event.actor_id} "
                f"action={event.action} in {publish_time_ms:.2f}ms"
            )
            
            return publish_time_ms
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise
    
    def flush(self, timeout: float = 10.0) -> int:
        """
        Flush all pending messages to Kafka.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            int: Number of messages still in queue (0 if all flushed)
        """
        if self._producer is None:
            return 0
        
        remaining = self._producer.flush(timeout=timeout)
        # Poll to process any remaining callbacks
        self._producer.poll(0)
        return remaining
    
    def generate_and_publish(
        self,
        pattern: BehaviorPattern = BehaviorPattern.NORMAL,
        actor_id: Optional[str] = None
    ) -> tuple:
        """
        Generate and publish an event in one call.
        
        Args:
            pattern: The behavior pattern to simulate
            actor_id: Optional specific actor ID
            
        Returns:
            tuple: (event, publish_time_ms)
        """
        event = self.generate_event(pattern=pattern, actor_id=actor_id)
        publish_time_ms = self.publish_event(event)
        return event, publish_time_ms
    
    def generate_demo_scenario(self, scenario: str = "mixed") -> list:
        """
        Generate a sequence of events for demonstration.
        
        Args:
            scenario: Type of scenario ("normal", "suspicious", "mixed")
            
        Returns:
            list: List of (event, publish_time_ms) tuples
        """
        results = []
        
        if scenario == "normal":
            # Generate 5 normal events
            for _ in range(5):
                results.append(self.generate_and_publish(BehaviorPattern.NORMAL))
                
        elif scenario == "suspicious":
            # Generate suspicious behavior sequence
            results.append(self.generate_and_publish(BehaviorPattern.HIGH_FREQUENCY))
            results.append(self.generate_and_publish(BehaviorPattern.GEO_ANOMALY))
            results.append(self.generate_and_publish(BehaviorPattern.PRIVILEGE_ESCALATION))
            
        else:  # mixed
            # Generate a mix of normal and suspicious events
            results.append(self.generate_and_publish(BehaviorPattern.NORMAL))
            results.append(self.generate_and_publish(BehaviorPattern.NORMAL))
            results.append(self.generate_and_publish(BehaviorPattern.HIGH_FREQUENCY))
            results.append(self.generate_and_publish(BehaviorPattern.NORMAL))
            results.append(self.generate_and_publish(BehaviorPattern.GEO_ANOMALY))
        
        # Flush to ensure all messages are sent
        self.flush()
        
        return results
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get producer statistics."""
        return {
            "events_produced": self._events_produced,
            "events_failed": self._events_failed,
            "using_avro": self._using_avro
        }
    
    @property
    def using_avro(self) -> bool:
        """Check if Avro serialization is enabled."""
        return self._using_avro


def create_event_producer() -> EventProducer:
    """
    Factory function to create and connect an Event Producer.
    
    Returns:
        EventProducer: Connected event producer instance
    """
    producer = EventProducer()
    producer.connect()
    return producer
