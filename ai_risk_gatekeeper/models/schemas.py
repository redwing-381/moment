"""
JSON schema definitions and validation for AI Risk Gatekeeper events.

Provides schema validation to ensure data integrity throughout the pipeline.
"""

import json
from typing import Dict, Any, List
from jsonschema import validate, ValidationError


# JSON Schema for Enterprise Action Events
ENTERPRISE_ACTION_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "actor_id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the actor performing the action"
        },
        "action": {
            "type": "string",
            "minLength": 1,
            "description": "Type of enterprise action being performed"
        },
        "role": {
            "type": "string",
            "minLength": 1,
            "description": "Role of the actor in the organization"
        },
        "frequency_last_60s": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of similar actions in the last 60 seconds"
        },
        "geo_change": {
            "type": "boolean",
            "description": "Whether there was a geographical location change"
        },
        "timestamp": {
            "type": "integer",
            "minimum": 0,
            "description": "Unix timestamp of the action"
        },
        "session_id": {
            "type": "string",
            "minLength": 1,
            "description": "Session identifier for the action"
        },
        "resource_sensitivity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Sensitivity level of the resource being accessed"
        }
    },
    "required": [
        "actor_id", "action", "role", "frequency_last_60s", 
        "geo_change", "timestamp", "session_id", "resource_sensitivity"
    ],
    "additionalProperties": False
}

# JSON Schema for Risk Signals
RISK_SIGNAL_SCHEMA = {
    "type": "object",
    "properties": {
        "actor_id": {
            "type": "string",
            "minLength": 1
        },
        "risk_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Risk score between 0.0 (low risk) and 1.0 (high risk)"
        },
        "risk_factors": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1
            },
            "description": "List of identified risk factors"
        },
        "original_event": ENTERPRISE_ACTION_EVENT_SCHEMA,
        "processing_timestamp": {
            "type": "integer",
            "minimum": 0,
            "description": "Unix timestamp when signal was processed"
        },
        "correlation_id": {
            "type": "string",
            "minLength": 1,
            "description": "Correlation ID for tracking events through pipeline"
        }
    },
    "required": [
        "actor_id", "risk_score", "risk_factors", 
        "original_event", "processing_timestamp", "correlation_id"
    ],
    "additionalProperties": False
}

# JSON Schema for Risk Decisions
RISK_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "actor_id": {
            "type": "string",
            "minLength": 1
        },
        "decision": {
            "type": "string",
            "enum": ["allow", "throttle", "block", "escalate"],
            "description": "Risk decision made by AI"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence score for the decision"
        },
        "reason": {
            "type": "string",
            "minLength": 1,
            "description": "Human-readable reasoning for the decision"
        },
        "correlation_id": {
            "type": "string",
            "minLength": 1,
            "description": "Correlation ID for tracking events through pipeline"
        },
        "decision_timestamp": {
            "type": "integer",
            "minimum": 0,
            "description": "Unix timestamp when decision was made"
        }
    },
    "required": [
        "actor_id", "decision", "confidence", 
        "reason", "correlation_id", "decision_timestamp"
    ],
    "additionalProperties": False
}


class SchemaValidator:
    """Validates JSON data against defined schemas."""
    
    @staticmethod
    def validate_enterprise_action_event(data: Dict[str, Any]) -> bool:
        """
        Validate enterprise action event data against schema.
        
        Args:
            data: Dictionary containing event data
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If data doesn't match schema
        """
        validate(instance=data, schema=ENTERPRISE_ACTION_EVENT_SCHEMA)
        return True
    
    @staticmethod
    def validate_risk_signal(data: Dict[str, Any]) -> bool:
        """
        Validate risk signal data against schema.
        
        Args:
            data: Dictionary containing risk signal data
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If data doesn't match schema
        """
        validate(instance=data, schema=RISK_SIGNAL_SCHEMA)
        return True
    
    @staticmethod
    def validate_risk_decision(data: Dict[str, Any]) -> bool:
        """
        Validate risk decision data against schema.
        
        Args:
            data: Dictionary containing risk decision data
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If data doesn't match schema
        """
        validate(instance=data, schema=RISK_DECISION_SCHEMA)
        return True
    
    @staticmethod
    def validate_json_string(json_str: str, schema_type: str) -> bool:
        """
        Validate JSON string against specified schema type.
        
        Args:
            json_str: JSON string to validate
            schema_type: Type of schema ('event', 'signal', 'decision')
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If data doesn't match schema
            ValueError: If schema_type is invalid
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
        
        if schema_type == "event":
            return SchemaValidator.validate_enterprise_action_event(data)
        elif schema_type == "signal":
            return SchemaValidator.validate_risk_signal(data)
        elif schema_type == "decision":
            return SchemaValidator.validate_risk_decision(data)
        else:
            raise ValueError(f"Unknown schema type: {schema_type}")


# Export schemas for external use
__all__ = [
    "ENTERPRISE_ACTION_EVENT_SCHEMA",
    "RISK_SIGNAL_SCHEMA", 
    "RISK_DECISION_SCHEMA",
    "SchemaValidator"
]