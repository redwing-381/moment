"""
Action Agent for the AI Risk Gatekeeper system.

This agent consumes risk decisions and executes appropriate responses
including blocking, throttling, allowing, and escalating actions.
"""

import logging
import time
from typing import Dict, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from confluent_kafka import Consumer, KafkaError

from ai_risk_gatekeeper.models.events import RiskDecision
from ai_risk_gatekeeper.config.settings import config_manager, KafkaConfig


logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Simple rate limiter for throttling."""
    window_seconds: int = 60
    max_requests: int = 5
    _requests: Dict[str, list] = field(default_factory=lambda: defaultdict(list))
    
    def is_allowed(self, actor_id: str) -> bool:
        """Check if actor is within rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean old requests
        self._requests[actor_id] = [
            t for t in self._requests[actor_id] if t > cutoff
        ]
        
        if len(self._requests[actor_id]) >= self.max_requests:
            return False
        
        self._requests[actor_id].append(now)
        return True


class ActionAgent:
    """
    Executes responses based on risk decisions.
    
    Handles blocking, throttling, allowing, and escalating
    actions with proper logging and audit trails.
    """
    
    def __init__(self, kafka_config: Optional[KafkaConfig] = None):
        self._kafka_config = kafka_config
        self._consumer: Optional[Consumer] = None
        self._rate_limiter = RateLimiter()
        self._running = False
        
        # Statistics
        self._actions_executed = 0
        self._blocks = 0
        self._throttles = 0
        self._allows = 0
        self._escalations = 0
    
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
            "group.id": f"{self.kafka_config.consumer_group_id}-action-agent",
            "auto.offset.reset": self.kafka_config.auto_offset_reset,
            "enable.auto.commit": True,
        }
    
    def connect(self) -> None:
        """Connect to Kafka."""
        try:
            self._consumer = Consumer(self._get_consumer_config())
            self._consumer.subscribe([self.kafka_config.risk_decisions_topic])
            logger.info("Action Agent connected to Kafka")
        except Exception as e:
            logger.error(f"Failed to connect Action Agent: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Kafka."""
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        logger.info("Action Agent disconnected")
    
    def execute_block(self, decision: RiskDecision) -> None:
        """Execute a block action."""
        self._blocks += 1
        logger.warning(
            f"🚫 BLOCKED: actor={decision.actor_id} "
            f"reason='{decision.reason}' confidence={decision.confidence:.2f}"
        )
        # In production: integrate with access control system
    
    def execute_throttle(self, decision: RiskDecision) -> None:
        """Execute a throttle action."""
        self._throttles += 1
        allowed = self._rate_limiter.is_allowed(decision.actor_id)
        status = "allowed (within limit)" if allowed else "rate limited"
        logger.info(
            f"⏱️ THROTTLE: actor={decision.actor_id} status={status} "
            f"reason='{decision.reason}'"
        )
    
    def execute_allow(self, decision: RiskDecision) -> None:
        """Execute an allow action."""
        self._allows += 1
        logger.info(
            f"✅ ALLOWED: actor={decision.actor_id} "
            f"confidence={decision.confidence:.2f}"
        )
    
    def execute_escalate(self, decision: RiskDecision) -> None:
        """Execute an escalate action."""
        self._escalations += 1
        logger.warning(
            f"⚠️ ESCALATED: actor={decision.actor_id} "
            f"reason='{decision.reason}' - Requires human review"
        )
        # In production: send to security team queue
    
    def execute_action(self, decision: RiskDecision) -> float:
        """
        Execute the appropriate action for a decision.
        
        Args:
            decision: The risk decision to execute
            
        Returns:
            float: Execution time in milliseconds
        """
        start_time = time.perf_counter()
        
        action_handlers = {
            "block": self.execute_block,
            "throttle": self.execute_throttle,
            "allow": self.execute_allow,
            "escalate": self.execute_escalate,
        }
        
        handler = action_handlers.get(decision.decision, self.execute_escalate)
        handler(decision)
        
        self._actions_executed += 1
        
        return (time.perf_counter() - start_time) * 1000
    
    def run(self, max_decisions: Optional[int] = None, timeout: float = 1.0) -> None:
        """Run the action agent loop."""
        if self._consumer is None:
            raise RuntimeError("Action Agent not connected")
        
        self._running = True
        decisions_count = 0
        
        logger.info("Action Agent started")
        
        try:
            while self._running:
                if max_decisions and decisions_count >= max_decisions:
                    break
                
                msg = self._consumer.poll(timeout)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    decision = RiskDecision.from_json(msg.value().decode("utf-8"))
                    exec_time = self.execute_action(decision)
                    decisions_count += 1
                    logger.debug(f"Action executed in {exec_time:.2f}ms")
                except Exception as e:
                    logger.error(f"Failed to execute action: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Action Agent interrupted")
        finally:
            self._running = False
    
    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
    
    @property
    def stats(self) -> Dict[str, int]:
        return {
            "actions_executed": self._actions_executed,
            "blocks": self._blocks,
            "throttles": self._throttles,
            "allows": self._allows,
            "escalations": self._escalations,
        }


def create_action_agent() -> ActionAgent:
    """Factory function to create and connect an Action Agent."""
    agent = ActionAgent()
    agent.connect()
    return agent
