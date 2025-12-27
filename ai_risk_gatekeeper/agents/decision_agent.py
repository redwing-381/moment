"""
Decision Agent for the AI Risk Gatekeeper system.

This agent consumes risk signals, queries Vertex AI Gemini for risk decisions,
and publishes structured decisions with confidence scores and reasoning.
"""

import logging
import time
import json
from typing import Dict, Any, Optional

from confluent_kafka import Consumer, Producer, KafkaError
from google import genai
from google.genai import types

from ai_risk_gatekeeper.models.events import RiskSignal, RiskDecision
from ai_risk_gatekeeper.config.settings import config_manager, KafkaConfig, VertexAIConfig


logger = logging.getLogger(__name__)


DECISION_PROMPT_TEMPLATE = """You are a security risk assessment AI. Analyze the following risk signal and provide a decision.

Risk Signal:
- Actor ID: {actor_id}
- Risk Score: {risk_score:.2f}
- Risk Factors: {risk_factors}
- Action: {action}
- Role: {role}
- Frequency (last 60s): {frequency}
- Geographic Change: {geo_change}
- Resource Sensitivity: {sensitivity}

Based on this information, provide a JSON response with:
1. "decision": one of "allow", "throttle", "block", or "escalate"
2. "confidence": a float between 0.0 and 1.0
3. "reason": a brief explanation (max 100 words)

Decision Guidelines:
- allow: Low risk, normal behavior
- throttle: Moderate risk, apply rate limiting
- block: High risk, prevent the action
- escalate: Uncertain or critical, needs human review

Respond ONLY with valid JSON, no other text."""


class DecisionAgent:
    """
    Makes AI-powered risk decisions using Vertex AI Gemini.
    
    Consumes risk signals, queries the AI model, and publishes
    structured decisions with confidence scores and reasoning.
    """
    
    def __init__(
        self,
        kafka_config: Optional[KafkaConfig] = None,
        vertex_config: Optional[VertexAIConfig] = None
    ):
        self._kafka_config = kafka_config
        self._vertex_config = vertex_config
        self._consumer: Optional[Consumer] = None
        self._producer: Optional[Producer] = None
        self._client = None
        self._running = False
        self._decisions_made = 0
        self._ai_failures = 0
    
    @property
    def kafka_config(self) -> KafkaConfig:
        if self._kafka_config is None:
            config = config_manager.load_config()
            self._kafka_config = config.kafka
        return self._kafka_config
    
    @property
    def vertex_config(self) -> VertexAIConfig:
        if self._vertex_config is None:
            config = config_manager.load_config()
            self._vertex_config = config.vertex_ai
        return self._vertex_config
    
    def _get_consumer_config(self) -> Dict[str, Any]:
        return {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": self.kafka_config.security_protocol,
            "sasl.mechanisms": self.kafka_config.sasl_mechanism,
            "sasl.username": self.kafka_config.sasl_username,
            "sasl.password": self.kafka_config.sasl_password,
            "group.id": f"{self.kafka_config.consumer_group_id}-decision-agent",
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
            "client.id": "ai-risk-gatekeeper-decision-agent",
            "linger.ms": 5,
            "acks": "all",
        }

    def connect(self) -> None:
        """Establish connections to Kafka and initialize AI model."""
        try:
            # Connect to Kafka
            self._consumer = Consumer(self._get_consumer_config())
            self._consumer.subscribe([self.kafka_config.risk_signals_topic])
            self._producer = Producer(self._get_producer_config())
            
            # Initialize Gemini client using Vertex AI
            self._client = genai.Client(
                vertexai=True,
                project=self.vertex_config.project_id,
                location=self.vertex_config.location
            )
            
            logger.info("Decision Agent connected to Kafka and Vertex AI")
        except Exception as e:
            logger.error(f"Failed to connect Decision Agent: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Kafka."""
        if self._producer:
            self._producer.flush(timeout=10)
            self._producer = None
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        logger.info("Decision Agent disconnected")
    
    def _build_prompt(self, signal: RiskSignal) -> str:
        """Build the AI prompt from a risk signal."""
        return DECISION_PROMPT_TEMPLATE.format(
            actor_id=signal.actor_id,
            risk_score=signal.risk_score,
            risk_factors=", ".join(signal.risk_factors) or "none",
            action=signal.original_event.action,
            role=signal.original_event.role,
            frequency=signal.original_event.frequency_last_60s,
            geo_change=signal.original_event.geo_change,
            sensitivity=signal.original_event.resource_sensitivity
        )
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response JSON."""
        # Clean up response - remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        
        return json.loads(text)
    
    def _validate_decision(
        self, 
        decision: str, 
        confidence: float
    ) -> tuple:
        """Validate and normalize decision values."""
        valid_decisions = ("allow", "throttle", "block", "escalate")
        
        if decision not in valid_decisions:
            decision = "escalate"
        
        confidence = max(0.0, min(1.0, float(confidence)))
        
        return decision, confidence
    
    def query_ai(self, signal: RiskSignal) -> Dict[str, Any]:
        """
        Query Vertex AI Gemini for a risk decision.
        
        Args:
            signal: The risk signal to evaluate
            
        Returns:
            Dict with decision, confidence, and reason
        """
        prompt = self._build_prompt(signal)
        
        try:
            response = self._client.models.generate_content(
                model=self.vertex_config.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.vertex_config.temperature,
                    max_output_tokens=self.vertex_config.max_tokens,
                )
            )
            
            result = self._parse_ai_response(response.text)
            decision, confidence = self._validate_decision(
                result.get("decision", "escalate"),
                result.get("confidence", 0.5)
            )
            
            return {
                "decision": decision,
                "confidence": confidence,
                "reason": result.get("reason", "AI decision")
            }
            
        except Exception as e:
            logger.error(f"AI query failed: {e}")
            self._ai_failures += 1
            return self._fallback_decision(signal, str(e))
    
    def _fallback_decision(self, signal: RiskSignal, error: str) -> Dict[str, Any]:
        """Generate fallback decision when AI fails."""
        # Use rule-based fallback
        if signal.risk_score >= 0.8:
            decision = "block"
            confidence = 0.7
        elif signal.risk_score >= 0.5:
            decision = "escalate"
            confidence = 0.6
        elif signal.risk_score >= 0.3:
            decision = "throttle"
            confidence = 0.6
        else:
            decision = "allow"
            confidence = 0.7
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reason": f"Fallback decision (AI unavailable: {error[:50]})"
        }
    
    def make_decision(self, signal: RiskSignal) -> RiskDecision:
        """
        Make a risk decision for a signal.
        
        Args:
            signal: The risk signal to evaluate
            
        Returns:
            RiskDecision: The generated decision
        """
        start_time = time.perf_counter()
        
        ai_result = self.query_ai(signal)
        
        decision = RiskDecision(
            actor_id=signal.actor_id,
            decision=ai_result["decision"],
            confidence=ai_result["confidence"],
            reason=ai_result["reason"],
            correlation_id=signal.correlation_id,
            decision_timestamp=int(time.time() * 1000)
        )
        
        processing_time = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Decision made in {processing_time:.2f}ms")
        
        return decision
    
    def publish_decision(self, decision: RiskDecision) -> float:
        """Publish a decision to Kafka."""
        if self._producer is None:
            raise RuntimeError("Decision Agent not connected")
        
        start_time = time.perf_counter()
        
        self._producer.produce(
            topic=self.kafka_config.risk_decisions_topic,
            key=decision.actor_id,
            value=decision.to_json()
        )
        self._producer.poll(0)
        
        return (time.perf_counter() - start_time) * 1000
    
    def process_signal(self, signal: RiskSignal) -> tuple:
        """Process a signal and publish the decision."""
        start_time = time.perf_counter()
        
        decision = self.make_decision(signal)
        self.publish_decision(decision)
        self._decisions_made += 1
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"Decision: actor={decision.actor_id} decision={decision.decision} "
            f"confidence={decision.confidence:.2f} in {total_time:.2f}ms"
        )
        
        return decision, total_time
    
    def run(self, max_signals: Optional[int] = None, timeout: float = 1.0) -> None:
        """Run the decision agent loop."""
        if self._consumer is None:
            raise RuntimeError("Decision Agent not connected")
        
        self._running = True
        signals_count = 0
        
        logger.info("Decision Agent started")
        
        try:
            while self._running:
                if max_signals and signals_count >= max_signals:
                    break
                
                msg = self._consumer.poll(timeout)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    signal = RiskSignal.from_json(msg.value().decode("utf-8"))
                    self.process_signal(signal)
                    signals_count += 1
                except Exception as e:
                    logger.error(f"Failed to process signal: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Decision Agent interrupted")
        finally:
            self._running = False
            if self._producer:
                self._producer.flush(timeout=5)
    
    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
    
    @property
    def stats(self) -> Dict[str, int]:
        return {
            "decisions_made": self._decisions_made,
            "ai_failures": self._ai_failures
        }


def create_decision_agent() -> DecisionAgent:
    """Factory function to create and connect a Decision Agent."""
    agent = DecisionAgent()
    agent.connect()
    return agent
