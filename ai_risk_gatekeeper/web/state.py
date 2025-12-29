"""
Application state management for AI Risk Gatekeeper.

This module contains the AppState class that manages all runtime state
including metrics, connections, and simulation data.
"""

from collections import deque
from typing import Optional, Any
from fastapi import WebSocket

from ai_risk_gatekeeper.models.events import DecisionMode


class AppState:
    """
    Centralized application state for the AI Risk Gatekeeper.
    
    Manages:
    - Agent connections (Kafka producer, signal processor, decision agent)
    - WebSocket clients
    - Metrics and statistics
    - Confluent Cloud integration status
    - Simulation state
    """
    
    def __init__(self):
        # Core agents
        self.producer: Optional[Any] = None
        self.processor: Optional[Any] = None
        self.decision_agent: Optional[Any] = None
        self.hybrid_engine: Optional[Any] = None  # HybridDecisionEngine
        
        # Decision mode (fast, hybrid, full_ai)
        self.decision_mode: DecisionMode = DecisionMode.HYBRID
        
        # WebSocket clients
        self.connected_clients: list[WebSocket] = []
        
        # Event history
        self.recent_events: deque = deque(maxlen=100)
        self.recent_decisions: deque = deque(maxlen=100)
        
        # Metrics
        self.metrics = {
            "events_produced": 0,
            "decisions_made": 0,
            "blocked": 0,
            "allowed": 0,
            "escalated": 0,
            "throttled": 0,
            "avg_latency_ms": 0,
            "latencies": deque(maxlen=100),
        }
        
        # Kafka metrics
        self.kafka_metrics = {
            "messages_sent": 0,
            "messages_per_sec": 0.0,
            "last_send_times": deque(maxlen=100),
            "connection_status": "connecting",
            "topics_used": set(),
        }
        
        # Simulation state
        self.simulation_running = False
        
        # Risk trend data (last 50 data points)
        self.risk_trend: deque = deque(maxlen=50)
        
        # Actor risk profiles
        # actor_id -> {events: int, blocked: int, avg_risk: float, last_action: str}
        self.actor_profiles: dict = {}
        
        # Confluent Advanced Features
        self.schema_registry_client = None
        self.ksqldb_client = None
        self.confluent_metrics_client = None
        self.confluent_status = {
            "schema_registry": {"connected": False, "schema_version": None, "format": "JSON"},
            "ksqldb": {"connected": False, "streams_ready": False},
            "metrics_api": {"connected": False, "cluster_id": None, "region": None},
        }
    
    def reset_metrics(self):
        """Reset all metrics to initial state."""
        self.metrics = {
            "events_produced": 0,
            "decisions_made": 0,
            "blocked": 0,
            "allowed": 0,
            "escalated": 0,
            "throttled": 0,
            "avg_latency_ms": 0,
            "latencies": deque(maxlen=100),
        }
        self.risk_trend.clear()
        self.actor_profiles.clear()
        self.kafka_metrics["messages_sent"] = 0
        self.kafka_metrics["messages_per_sec"] = 0.0
        # Reset hybrid engine stats
        if self.hybrid_engine:
            self.hybrid_engine.reset_stats()
    
    def set_decision_mode(self, mode: DecisionMode):
        """Set the decision mode."""
        self.decision_mode = mode
        if self.hybrid_engine:
            self.hybrid_engine.set_mode(mode)
    
    def get_metrics_dict(self) -> dict:
        """Get metrics as a dictionary for API responses."""
        return {
            "events_produced": self.metrics["events_produced"],
            "decisions_made": self.metrics["decisions_made"],
            "blocked": self.metrics["blocked"],
            "allowed": self.metrics["allowed"],
            "escalated": self.metrics["escalated"],
            "throttled": self.metrics["throttled"],
            "avg_latency_ms": round(self.metrics["avg_latency_ms"], 2),
        }
    
    def get_kafka_metrics_dict(self) -> dict:
        """Get Kafka metrics as a dictionary."""
        return {
            "messages_sent": self.kafka_metrics["messages_sent"],
            "messages_per_sec": round(self.kafka_metrics["messages_per_sec"], 1),
            "connection_status": self.kafka_metrics["connection_status"],
        }
    
    def get_decision_stats_dict(self) -> dict:
        """Get decision engine stats as a dictionary."""
        if self.hybrid_engine:
            stats = self.hybrid_engine.get_stats()
            return stats.to_dict()
        return {
            "mode": self.decision_mode.value,
            "rule_decisions": 0,
            "cache_hits": 0,
            "ai_decisions": 0,
        }


# Global state instance
state = AppState()
