"""
Signal Processing Agent for the AI Risk Gatekeeper system.

This agent consumes enterprise action events, extracts risk indicators,
calculates risk scores using deterministic logic, and publishes risk signals.

Key Confluent Feature: Real-time windowed frequency aggregation
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from confluent_kafka import Consumer, Producer, KafkaError

from ai_risk_gatekeeper.models.events import EnterpriseActionEvent, RiskSignal
from ai_risk_gatekeeper.config.settings import config_manager, KafkaConfig
from ai_risk_gatekeeper.agents.frequency_tracker import get_frequency_tracker


logger = logging.getLogger(__name__)


@dataclass
class RiskScoringConfig:
    """Configuration for risk score calculation."""
    # Frequency thresholds
    normal_frequency_max: int = 5
    elevated_frequency_threshold: int = 10
    high_frequency_threshold: int = 20
    
    # Score weights
    frequency_weight: float = 0.3
    geo_change_weight: float = 0.25
    sensitivity_weight: float = 0.25
    role_action_weight: float = 0.2
    
    # Sensitivity scores
    sensitivity_scores: Dict[str, float] = None
    
    # Suspicious action-role combinations
    suspicious_combinations: List[tuple] = None
    
    def __post_init__(self):
        if self.sensitivity_scores is None:
            self.sensitivity_scores = {
                "low": 0.1,
                "medium": 0.3,
                "high": 0.6,
                "critical": 1.0
            }
        if self.suspicious_combinations is None:
            self.suspicious_combinations = [
                ("developer", "admin_access"),
                ("analyst", "config_change"),
                ("support", "data_delete"),
                ("developer", "bulk_export"),
            ]


class SignalProcessor:
    """
    Processes enterprise action events and generates risk signals.
    
    This agent uses deterministic logic to calculate risk scores
    and identify risk factors from incoming events.
    """
    
    def __init__(
        self,
        kafka_config: Optional[KafkaConfig] = None,
        scoring_config: Optional[RiskScoringConfig] = None,
        use_real_frequency: bool = True
    ):
        self._kafka_config = kafka_config
        self._scoring_config = scoring_config or RiskScoringConfig()
        self._use_real_frequency = use_real_frequency
        self._frequency_tracker = get_frequency_tracker() if use_real_frequency else None
        self._consumer: Optional[Consumer] = None
        self._producer: Optional[Producer] = None
        self._running = False
        self._events_processed = 0
        self._events_failed = 0
    
    @property
    def kafka_config(self) -> KafkaConfig:
        if self._kafka_config is None:
            config = config_manager.load_config()
            self._kafka_config = config.kafka
        return self._kafka_config
    
    def _get_consumer_config(self) -> Dict[str, Any]:
        return {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": self.kafka_config.security_protocol,
            "sasl.mechanisms": self.kafka_config.sasl_mechanism,
            "sasl.username": self.kafka_config.sasl_username,
            "sasl.password": self.kafka_config.sasl_password,
            "group.id": f"{self.kafka_config.consumer_group_id}-signal-processor",
            "auto.offset.reset": self.kafka_config.auto_offset_reset,
            "enable.auto.commit": True,
        }
    
    def _get_producer_config(self) -> Dict[str, Any]:
        return {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": self.kafka_config.security_protocol,
            "sasl.mechanisms": self.kafka_config.sasl_mechanism,
            "sasl.username": self.kafka_config.sasl_username,
            "sasl.password": self.kafka_config.sasl_password,
            "client.id": "ai-risk-gatekeeper-signal-processor",
            "linger.ms": 5,
            "acks": "all",
        }

    def connect(self) -> None:
        """Establish connections to Kafka."""
        try:
            self._consumer = Consumer(self._get_consumer_config())
            self._consumer.subscribe([self.kafka_config.enterprise_action_events_topic])
            
            self._producer = Producer(self._get_producer_config())
            
            logger.info("Signal Processor connected to Kafka")
        except Exception as e:
            logger.error(f"Failed to connect Signal Processor: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Kafka."""
        if self._producer:
            self._producer.flush(timeout=10)
            self._producer = None
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        logger.info("Signal Processor disconnected")
    
    def calculate_risk_score(self, event: EnterpriseActionEvent, real_frequency: Optional[int] = None) -> float:
        """
        Calculate risk score using deterministic logic.
        
        Args:
            event: The enterprise action event
            real_frequency: Real-time frequency from windowed aggregation (overrides event.frequency_last_60s)
            
        Returns:
            float: Risk score between 0.0 and 1.0
        """
        cfg = self._scoring_config
        score = 0.0
        
        # Use real frequency if available, otherwise fall back to event's frequency
        frequency = real_frequency if real_frequency is not None else event.frequency_last_60s
        
        # Frequency score
        if frequency > cfg.high_frequency_threshold:
            freq_score = 1.0
        elif frequency > cfg.elevated_frequency_threshold:
            freq_score = 0.6
        elif frequency > cfg.normal_frequency_max:
            freq_score = 0.3
        else:
            freq_score = 0.0
        score += freq_score * cfg.frequency_weight
        
        # Geo change score
        if event.geo_change:
            score += 1.0 * cfg.geo_change_weight
        
        # Sensitivity score
        sensitivity_score = cfg.sensitivity_scores.get(event.resource_sensitivity, 0.3)
        score += sensitivity_score * cfg.sensitivity_weight
        
        # Role-action combination score
        if (event.role, event.action) in cfg.suspicious_combinations:
            score += 1.0 * cfg.role_action_weight
        elif event.role in ("admin", "superuser", "root"):
            score += 0.3 * cfg.role_action_weight
        
        return min(score, 1.0)
    
    def identify_risk_factors(self, event: EnterpriseActionEvent, real_frequency: Optional[int] = None) -> List[str]:
        """
        Identify specific risk factors from the event.
        
        Args:
            event: The enterprise action event
            real_frequency: Real-time frequency from windowed aggregation
            
        Returns:
            List[str]: List of identified risk factors
        """
        cfg = self._scoring_config
        factors = []
        
        # Use real frequency if available
        frequency = real_frequency if real_frequency is not None else event.frequency_last_60s
        
        # Check frequency
        if frequency > cfg.high_frequency_threshold:
            factors.append(f"high_frequency_activity ({frequency}/min)")
        elif frequency > cfg.elevated_frequency_threshold:
            factors.append(f"elevated_frequency ({frequency}/min)")
        
        # Check geo change
        if event.geo_change:
            factors.append("geographic_anomaly")
        
        # Check sensitivity
        if event.resource_sensitivity in ("high", "critical"):
            factors.append(f"sensitive_resource_{event.resource_sensitivity}")
        
        # Check role-action combination
        if (event.role, event.action) in cfg.suspicious_combinations:
            factors.append("suspicious_role_action_combination")
        
        # Check elevated privileges
        if event.role in ("admin", "superuser", "root"):
            factors.append("elevated_privileges")
        
        # Check sensitive actions
        if event.action in ("bulk_export", "data_delete", "config_change"):
            factors.append(f"sensitive_action_{event.action}")
        
        return factors
    
    def process_event(self, event: EnterpriseActionEvent) -> RiskSignal:
        """
        Process an event and generate a risk signal.
        
        Uses real-time windowed frequency aggregation when available.
        
        Args:
            event: The enterprise action event
            
        Returns:
            RiskSignal: The generated risk signal
        """
        start_time = time.perf_counter()
        
        # Get real-time frequency from windowed aggregation
        real_frequency = None
        if self._use_real_frequency and self._frequency_tracker:
            real_frequency = self._frequency_tracker.record_event(
                event.actor_id, 
                event.timestamp / 1000.0  # Convert ms to seconds
            )
        
        risk_score = self.calculate_risk_score(event, real_frequency)
        risk_factors = self.identify_risk_factors(event, real_frequency)
        
        signal = RiskSignal(
            actor_id=event.actor_id,
            risk_score=risk_score,
            risk_factors=risk_factors,
            original_event=event,
            processing_timestamp=int(time.time() * 1000),
            correlation_id=str(uuid.uuid4())
        )
        
        processing_time = (time.perf_counter() - start_time) * 1000
        freq_info = f"real_freq={real_frequency}" if real_frequency else f"simulated_freq={event.frequency_last_60s}"
        logger.debug(f"Processed event in {processing_time:.2f}ms, score={risk_score:.2f}, {freq_info}")
        
        return signal
    
    def publish_signal(self, signal: RiskSignal) -> float:
        """
        Publish a risk signal to Kafka.
        
        Args:
            signal: The risk signal to publish
            
        Returns:
            float: Time taken in milliseconds
        """
        if self._producer is None:
            raise RuntimeError("Signal Processor not connected")
        
        start_time = time.perf_counter()
        
        self._producer.produce(
            topic=self.kafka_config.risk_signals_topic,
            key=signal.actor_id,
            value=signal.to_json()
        )
        self._producer.poll(0)
        
        return (time.perf_counter() - start_time) * 1000
    
    def process_and_publish(self, event: EnterpriseActionEvent) -> tuple:
        """
        Process an event and publish the resulting signal.
        
        Args:
            event: The enterprise action event
            
        Returns:
            tuple: (signal, total_time_ms)
        """
        start_time = time.perf_counter()
        
        signal = self.process_event(event)
        self.publish_signal(signal)
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"Processed actor={signal.actor_id} score={signal.risk_score:.2f} "
            f"factors={len(signal.risk_factors)} in {total_time:.2f}ms"
        )
        
        return signal, total_time
    
    def run(self, max_events: Optional[int] = None, timeout: float = 1.0) -> None:
        """
        Run the signal processor loop.
        
        Args:
            max_events: Maximum events to process (None for infinite)
            timeout: Poll timeout in seconds
        """
        if self._consumer is None:
            raise RuntimeError("Signal Processor not connected")
        
        self._running = True
        events_count = 0
        
        logger.info("Signal Processor started")
        
        try:
            while self._running:
                if max_events and events_count >= max_events:
                    break
                
                msg = self._consumer.poll(timeout)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    event = EnterpriseActionEvent.from_json(msg.value().decode("utf-8"))
                    self.process_and_publish(event)
                    self._events_processed += 1
                    events_count += 1
                except Exception as e:
                    self._events_failed += 1
                    logger.error(f"Failed to process event: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Signal Processor interrupted")
        finally:
            self._running = False
            if self._producer:
                self._producer.flush(timeout=5)
    
    def stop(self) -> None:
        """Stop the processor loop."""
        self._running = False
    
    @property
    def stats(self) -> Dict[str, int]:
        return {
            "events_processed": self._events_processed,
            "events_failed": self._events_failed
        }


def create_signal_processor() -> SignalProcessor:
    """Factory function to create and connect a Signal Processor."""
    processor = SignalProcessor()
    processor.connect()
    return processor
