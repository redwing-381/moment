"""
Integration tests for the AI Risk Gatekeeper system.

Tests the complete event processing pipeline end-to-end.
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from ai_risk_gatekeeper.agents import (
    EventProducer,
    SignalProcessor,
    DecisionAgent,
    ActionAgent,
    BehaviorPattern,
)
from ai_risk_gatekeeper.models.events import (
    EnterpriseActionEvent,
    RiskSignal,
    RiskDecision,
)


class TestEventProducer:
    """Tests for Event Producer agent."""
    
    def test_generate_normal_event(self):
        """Test generating a normal behavior event."""
        producer = EventProducer()
        event = producer.generate_event(BehaviorPattern.NORMAL)
        
        assert event.actor_id is not None
        assert event.action is not None
        assert event.frequency_last_60s <= 5
        assert event.timestamp > 0
    
    def test_generate_suspicious_event(self):
        """Test generating a suspicious behavior event."""
        producer = EventProducer()
        event = producer.generate_event(BehaviorPattern.SUSPICIOUS)
        
        assert event.actor_id.startswith("user_suspicious")
        assert event.frequency_last_60s >= 10
    
    def test_generate_high_frequency_event(self):
        """Test generating a high frequency event."""
        producer = EventProducer()
        event = producer.generate_event(BehaviorPattern.HIGH_FREQUENCY)
        
        assert event.frequency_last_60s >= 15
    
    def test_generate_geo_anomaly_event(self):
        """Test generating a geo anomaly event."""
        producer = EventProducer()
        event = producer.generate_event(BehaviorPattern.GEO_ANOMALY)
        
        assert event.geo_change is True
    
    def test_generate_privilege_escalation_event(self):
        """Test generating a privilege escalation event."""
        producer = EventProducer()
        event = producer.generate_event(BehaviorPattern.PRIVILEGE_ESCALATION)
        
        assert event.role in ("admin", "superuser", "root")


class TestSignalProcessor:
    """Tests for Signal Processing agent."""
    
    def test_calculate_low_risk_score(self):
        """Test risk score calculation for low-risk event."""
        processor = SignalProcessor()
        event = EnterpriseActionEvent(
            actor_id="user_001",
            action="file_read",
            role="developer",
            frequency_last_60s=2,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id="session_1",
            resource_sensitivity="low"
        )
        
        score = processor.calculate_risk_score(event)
        assert score < 0.3
    
    def test_calculate_high_risk_score(self):
        """Test risk score calculation for high-risk event."""
        processor = SignalProcessor()
        event = EnterpriseActionEvent(
            actor_id="user_suspicious",
            action="bulk_export",
            role="developer",
            frequency_last_60s=50,
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id="session_2",
            resource_sensitivity="critical"
        )
        
        score = processor.calculate_risk_score(event)
        assert score >= 0.7
    
    def test_identify_risk_factors_high_frequency(self):
        """Test risk factor identification for high frequency."""
        processor = SignalProcessor()
        event = EnterpriseActionEvent(
            actor_id="user_001",
            action="file_read",
            role="developer",
            frequency_last_60s=25,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id="session_1",
            resource_sensitivity="low"
        )
        
        factors = processor.identify_risk_factors(event)
        assert "high_frequency_activity" in factors
    
    def test_identify_risk_factors_geo_change(self):
        """Test risk factor identification for geo change."""
        processor = SignalProcessor()
        event = EnterpriseActionEvent(
            actor_id="user_001",
            action="file_read",
            role="developer",
            frequency_last_60s=2,
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id="session_1",
            resource_sensitivity="low"
        )
        
        factors = processor.identify_risk_factors(event)
        assert "geographic_anomaly" in factors
    
    def test_process_event_creates_signal(self):
        """Test that processing an event creates a valid signal."""
        processor = SignalProcessor()
        event = EnterpriseActionEvent(
            actor_id="user_001",
            action="file_read",
            role="developer",
            frequency_last_60s=2,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id="session_1",
            resource_sensitivity="low"
        )
        
        signal = processor.process_event(event)
        
        assert signal.actor_id == event.actor_id
        assert 0.0 <= signal.risk_score <= 1.0
        assert isinstance(signal.risk_factors, list)
        assert signal.correlation_id is not None


class TestDecisionAgent:
    """Tests for Decision Agent."""
    
    def test_fallback_decision_low_risk(self):
        """Test fallback decision for low risk signal."""
        agent = DecisionAgent()
        signal = RiskSignal(
            actor_id="user_001",
            risk_score=0.1,
            risk_factors=[],
            original_event=EnterpriseActionEvent(
                actor_id="user_001", action="file_read", role="developer",
                frequency_last_60s=2, geo_change=False,
                timestamp=int(time.time() * 1000),
                session_id="s1", resource_sensitivity="low"
            ),
            processing_timestamp=int(time.time() * 1000),
            correlation_id="corr_1"
        )
        
        result = agent._fallback_decision(signal, "test")
        assert result["decision"] == "allow"
    
    def test_fallback_decision_high_risk(self):
        """Test fallback decision for high risk signal."""
        agent = DecisionAgent()
        signal = RiskSignal(
            actor_id="user_001",
            risk_score=0.9,
            risk_factors=["high_frequency_activity"],
            original_event=EnterpriseActionEvent(
                actor_id="user_001", action="bulk_export", role="developer",
                frequency_last_60s=50, geo_change=True,
                timestamp=int(time.time() * 1000),
                session_id="s1", resource_sensitivity="critical"
            ),
            processing_timestamp=int(time.time() * 1000),
            correlation_id="corr_1"
        )
        
        result = agent._fallback_decision(signal, "test")
        assert result["decision"] == "block"
    
    def test_validate_decision_normalizes_values(self):
        """Test that decision validation normalizes values."""
        agent = DecisionAgent()
        
        decision, confidence = agent._validate_decision("invalid", 1.5)
        assert decision == "escalate"
        assert confidence == 1.0
        
        decision, confidence = agent._validate_decision("allow", -0.5)
        assert decision == "allow"
        assert confidence == 0.0


class TestActionAgent:
    """Tests for Action Agent."""
    
    def test_execute_allow_action(self):
        """Test executing an allow action."""
        agent = ActionAgent()
        decision = RiskDecision(
            actor_id="user_001",
            decision="allow",
            confidence=0.9,
            reason="Normal behavior",
            correlation_id="corr_1",
            decision_timestamp=int(time.time() * 1000)
        )
        
        exec_time = agent.execute_action(decision)
        
        assert exec_time < 100  # Should be under 100ms
        assert agent.stats["allows"] == 1
    
    def test_execute_block_action(self):
        """Test executing a block action."""
        agent = ActionAgent()
        decision = RiskDecision(
            actor_id="user_001",
            decision="block",
            confidence=0.95,
            reason="Security violation",
            correlation_id="corr_1",
            decision_timestamp=int(time.time() * 1000)
        )
        
        exec_time = agent.execute_action(decision)
        
        assert exec_time < 100
        assert agent.stats["blocks"] == 1
    
    def test_execute_all_action_types(self):
        """Test executing all action types."""
        agent = ActionAgent()
        
        for action_type in ["allow", "throttle", "block", "escalate"]:
            decision = RiskDecision(
                actor_id=f"user_{action_type}",
                decision=action_type,
                confidence=0.8,
                reason=f"Test {action_type}",
                correlation_id=f"corr_{action_type}",
                decision_timestamp=int(time.time() * 1000)
            )
            agent.execute_action(decision)
        
        assert agent.stats["actions_executed"] == 4
        assert agent.stats["allows"] == 1
        assert agent.stats["throttles"] == 1
        assert agent.stats["blocks"] == 1
        assert agent.stats["escalations"] == 1


class TestEndToEndPipeline:
    """End-to-end pipeline tests."""
    
    def test_event_to_signal_pipeline(self):
        """Test event generation through signal processing."""
        producer = EventProducer()
        processor = SignalProcessor()
        
        # Generate event
        event = producer.generate_event(BehaviorPattern.NORMAL)
        
        # Process to signal
        signal = processor.process_event(event)
        
        assert signal.actor_id == event.actor_id
        assert signal.original_event.action == event.action
    
    def test_signal_to_decision_pipeline(self):
        """Test signal processing through decision making."""
        processor = SignalProcessor()
        agent = DecisionAgent()
        
        # Create event
        event = EnterpriseActionEvent(
            actor_id="user_test",
            action="file_read",
            role="developer",
            frequency_last_60s=3,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id="session_test",
            resource_sensitivity="low"
        )
        
        # Process to signal
        signal = processor.process_event(event)
        
        # Make decision (using fallback)
        result = agent._fallback_decision(signal, "test")
        
        assert result["decision"] in ["allow", "throttle", "block", "escalate"]
        assert 0.0 <= result["confidence"] <= 1.0
    
    def test_complete_pipeline_timing(self):
        """Test that complete pipeline meets timing requirements."""
        producer = EventProducer()
        processor = SignalProcessor()
        decision_agent = DecisionAgent()
        action_agent = ActionAgent()
        
        start_time = time.perf_counter()
        
        # Generate event
        event = producer.generate_event(BehaviorPattern.NORMAL)
        
        # Process to signal
        signal = processor.process_event(event)
        
        # Make decision (using fallback for speed)
        result = decision_agent._fallback_decision(signal, "test")
        
        # Create decision object
        decision = RiskDecision(
            actor_id=signal.actor_id,
            decision=result["decision"],
            confidence=result["confidence"],
            reason=result["reason"],
            correlation_id=signal.correlation_id,
            decision_timestamp=int(time.time() * 1000)
        )
        
        # Execute action
        action_agent.execute_action(decision)
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Should complete in under 350ms (requirement)
        assert total_time < 350, f"Pipeline took {total_time:.2f}ms, expected <350ms"
