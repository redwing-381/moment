"""
Unit tests for data models and schemas.

Tests the core data structures and JSON serialization/deserialization.
"""

import json
import pytest
from datetime import datetime

from ai_risk_gatekeeper.models.events import (
    EnterpriseActionEvent, 
    RiskSignal, 
    RiskDecision
)
from ai_risk_gatekeeper.models.schemas import SchemaValidator


class TestEnterpriseActionEvent:
    """Test cases for EnterpriseActionEvent model."""
    
    def test_create_event(self):
        """Test creating a valid enterprise action event."""
        event = EnterpriseActionEvent(
            actor_id="user123",
            action="file_access",
            role="developer",
            frequency_last_60s=5,
            geo_change=False,
            timestamp=1640995200,
            session_id="session456",
            resource_sensitivity="medium"
        )
        
        assert event.actor_id == "user123"
        assert event.action == "file_access"
        assert event.role == "developer"
        assert event.frequency_last_60s == 5
        assert event.geo_change is False
        assert event.timestamp == 1640995200
        assert event.session_id == "session456"
        assert event.resource_sensitivity == "medium"
    
    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        original_event = EnterpriseActionEvent(
            actor_id="user123",
            action="file_access",
            role="developer",
            frequency_last_60s=5,
            geo_change=False,
            timestamp=1640995200,
            session_id="session456",
            resource_sensitivity="medium"
        )
        
        # Serialize to JSON
        json_str = original_event.to_json()
        assert isinstance(json_str, str)
        
        # Deserialize from JSON
        restored_event = EnterpriseActionEvent.from_json(json_str)
        
        # Verify all fields match
        assert restored_event.actor_id == original_event.actor_id
        assert restored_event.action == original_event.action
        assert restored_event.role == original_event.role
        assert restored_event.frequency_last_60s == original_event.frequency_last_60s
        assert restored_event.geo_change == original_event.geo_change
        assert restored_event.timestamp == original_event.timestamp
        assert restored_event.session_id == original_event.session_id
        assert restored_event.resource_sensitivity == original_event.resource_sensitivity


class TestRiskSignal:
    """Test cases for RiskSignal model."""
    
    def test_create_risk_signal(self):
        """Test creating a valid risk signal."""
        original_event = EnterpriseActionEvent(
            actor_id="user123",
            action="file_access",
            role="developer",
            frequency_last_60s=5,
            geo_change=False,
            timestamp=1640995200,
            session_id="session456",
            resource_sensitivity="medium"
        )
        
        risk_signal = RiskSignal(
            actor_id="user123",
            risk_score=0.7,
            risk_factors=["high_frequency", "unusual_time"],
            original_event=original_event,
            processing_timestamp=1640995300,
            correlation_id="corr789"
        )
        
        assert risk_signal.actor_id == "user123"
        assert risk_signal.risk_score == 0.7
        assert risk_signal.risk_factors == ["high_frequency", "unusual_time"]
        assert risk_signal.original_event == original_event
        assert risk_signal.processing_timestamp == 1640995300
        assert risk_signal.correlation_id == "corr789"


class TestRiskDecision:
    """Test cases for RiskDecision model."""
    
    def test_create_risk_decision(self):
        """Test creating a valid risk decision."""
        decision = RiskDecision(
            actor_id="user123",
            decision="block",
            confidence=0.9,
            reason="High risk score with multiple suspicious factors",
            correlation_id="corr789",
            decision_timestamp=1640995400
        )
        
        assert decision.actor_id == "user123"
        assert decision.decision == "block"
        assert decision.confidence == 0.9
        assert decision.reason == "High risk score with multiple suspicious factors"
        assert decision.correlation_id == "corr789"
        assert decision.decision_timestamp == 1640995400


class TestSchemaValidator:
    """Test cases for schema validation."""
    
    def test_validate_enterprise_action_event(self):
        """Test validation of enterprise action event schema."""
        valid_data = {
            "actor_id": "user123",
            "action": "file_access",
            "role": "developer",
            "frequency_last_60s": 5,
            "geo_change": False,
            "timestamp": 1640995200,
            "session_id": "session456",
            "resource_sensitivity": "medium"
        }
        
        # Should not raise an exception
        assert SchemaValidator.validate_enterprise_action_event(valid_data) is True
    
    def test_validate_invalid_event_schema(self):
        """Test validation fails for invalid event data."""
        invalid_data = {
            "actor_id": "user123",
            # Missing required fields
            "action": "file_access"
        }
        
        with pytest.raises(Exception):  # ValidationError
            SchemaValidator.validate_enterprise_action_event(invalid_data)