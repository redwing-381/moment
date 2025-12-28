"""
AI Risk Gatekeeper - Web Application

FastAPI app with WebSocket for real-time updates.
Designed for Cloud Run deployment.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from ai_risk_gatekeeper.agents import (
    EventProducer,
    BehaviorPattern,
    SignalProcessor,
    DecisionAgent,
)
from ai_risk_gatekeeper.models.events import EnterpriseActionEvent
from ai_risk_gatekeeper.config.settings import config_manager

# Optional Confluent advanced features
try:
    from ai_risk_gatekeeper.agents.schema_registry import SchemaRegistryClient, create_avro_serializer
    from ai_risk_gatekeeper.agents.ksqldb_client import KsqlDBClient, create_ksqldb_client
    from ai_risk_gatekeeper.agents.confluent_metrics import ConfluentMetricsClient, create_confluent_metrics_client
    CONFLUENT_FEATURES_AVAILABLE = True
except ImportError:
    CONFLUENT_FEATURES_AVAILABLE = False


# Store for real-time metrics and events
class AppState:
    def __init__(self):
        self.producer: Optional[EventProducer] = None
        self.processor: Optional[SignalProcessor] = None
        self.decision_agent: Optional[DecisionAgent] = None
        self.connected_clients: list[WebSocket] = []
        self.recent_events: deque = deque(maxlen=100)
        self.recent_decisions: deque = deque(maxlen=100)
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
        self.kafka_metrics = {
            "messages_sent": 0,
            "messages_per_sec": 0.0,
            "last_send_times": deque(maxlen=100),
            "connection_status": "connecting",
            "topics_used": set(),
        }
        self.simulation_running = False
        # New: Risk trend data (last 50 data points)
        self.risk_trend: deque = deque(maxlen=50)
        # New: Actor risk profiles
        self.actor_profiles: dict = {}  # actor_id -> {events: int, blocked: int, avg_risk: float, last_action: str}
        
        # Confluent Advanced Features
        self.schema_registry_client = None
        self.ksqldb_client = None
        self.confluent_metrics_client = None
        self.confluent_status = {
            "schema_registry": {"connected": False, "schema_version": None, "format": "JSON"},
            "ksqldb": {"connected": False, "streams_ready": False},
            "metrics_api": {"connected": False, "cluster_id": None, "region": None},
        }


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connections on startup."""
    try:
        state.producer = EventProducer()
        state.producer.connect()
        state.kafka_metrics["connection_status"] = "connected"
        state.kafka_metrics["topics_used"].add("enterprise-action-events")
        # Disable real frequency tracking to avoid threading issues
        state.processor = SignalProcessor(use_real_frequency=False)
        state.decision_agent = DecisionAgent()
        state.decision_agent.connect()
        print("✓ Core agents connected")
    except Exception as e:
        state.kafka_metrics["connection_status"] = "error"
        print(f"Warning: Could not connect agents: {e}")
    
    # Initialize Confluent Advanced Features (graceful degradation)
    if CONFLUENT_FEATURES_AVAILABLE:
        try:
            config = config_manager.load_config()
            
            # Schema Registry
            if config.schema_registry:
                try:
                    client = SchemaRegistryClient(
                        config.schema_registry.url,
                        config.schema_registry.api_key,
                        config.schema_registry.api_secret
                    )
                    if client.check_connection():
                        state.schema_registry_client = client
                        state.confluent_status["schema_registry"]["connected"] = True
                        state.confluent_status["schema_registry"]["format"] = "Avro"
                        print("✓ Schema Registry connected")
                except Exception as e:
                    print(f"Schema Registry unavailable: {e}")
            
            # ksqlDB
            if config.ksqldb:
                try:
                    client = await create_ksqldb_client(
                        config.ksqldb.endpoint,
                        config.ksqldb.api_key,
                        config.ksqldb.api_secret
                    )
                    if client:
                        state.ksqldb_client = client
                        state.confluent_status["ksqldb"]["connected"] = True
                        # Try to set up streams
                        if await client.setup_streams():
                            state.confluent_status["ksqldb"]["streams_ready"] = True
                        print("✓ ksqlDB connected")
                except Exception as e:
                    print(f"ksqlDB unavailable: {e}")
            
            # Confluent Cloud Metrics
            if config.confluent_cloud:
                try:
                    client = await create_confluent_metrics_client(
                        config.confluent_cloud.api_key,
                        config.confluent_cloud.api_secret,
                        config.confluent_cloud.cluster_id,
                        config.confluent_cloud.environment_id
                    )
                    if client:
                        state.confluent_metrics_client = client
                        state.confluent_status["metrics_api"]["connected"] = True
                        state.confluent_status["metrics_api"]["cluster_id"] = config.confluent_cloud.cluster_id
                        print("✓ Confluent Metrics API connected")
                except Exception as e:
                    print(f"Confluent Metrics API unavailable: {e}")
                    
        except Exception as e:
            print(f"Confluent features initialization error: {e}")
    
    yield
    
    # Cleanup
    if state.producer:
        state.producer.disconnect()
    if state.decision_agent:
        state.decision_agent.disconnect()
    if state.ksqldb_client:
        await state.ksqldb_client.close()
    if state.confluent_metrics_client:
        await state.confluent_metrics_client.close()


app = FastAPI(
    title="AI Risk Gatekeeper",
    description="Real-time AI-powered Enterprise Security",
    lifespan=lifespan
)


class SimulationRequest(BaseModel):
    event_count: int = 50
    attack_percentage: int = 20
    duration_seconds: int = 10
    use_ai: bool = False  # Use rule-based by default for speed


async def broadcast(message: dict):
    """Send message to all connected WebSocket clients."""
    dead_clients = []
    for client in state.connected_clients:
        try:
            await client.send_json(message)
        except:
            dead_clients.append(client)
    for client in dead_clients:
        state.connected_clients.remove(client)


def generate_explanation(event: EnterpriseActionEvent, signal, decision_result: dict) -> str:
    """Generate human-readable explanation for the decision."""
    decision = decision_result["decision"]
    risk_score = signal.risk_score
    factors = signal.risk_factors
    
    explanations = []
    
    # Risk level context
    if risk_score >= 0.8:
        explanations.append(f"🔴 Critical risk level ({risk_score*100:.0f}%)")
    elif risk_score >= 0.6:
        explanations.append(f"🟠 High risk level ({risk_score*100:.0f}%)")
    elif risk_score >= 0.4:
        explanations.append(f"🟡 Moderate risk level ({risk_score*100:.0f}%)")
    else:
        explanations.append(f"🟢 Low risk level ({risk_score*100:.0f}%)")
    
    # Factor explanations
    factor_texts = {
        "high_frequency": f"User made {event.frequency_last_60s} requests in 60s (unusual activity)",
        "geo_anomaly": "Location changed unexpectedly (possible account compromise)",
        "sensitive_resource": f"Accessing {event.resource_sensitivity}-sensitivity resource",
        "off_hours": "Activity outside normal business hours",
        "privilege_escalation": "Attempting elevated privilege operation",
        "bulk_operation": "Bulk data operation detected",
    }
    
    for factor in factors[:3]:  # Top 3 factors
        if factor in factor_texts:
            explanations.append(f"• {factor_texts[factor]}")
        else:
            explanations.append(f"• {factor.replace('_', ' ').title()}")
    
    # Decision rationale
    decision_texts = {
        "block": "Action blocked to prevent potential security breach",
        "throttle": "Rate limited to slow down suspicious activity",
        "escalate": "Flagged for security team review",
        "allow": "Permitted - within normal behavior patterns",
    }
    explanations.append(f"\n→ {decision_texts.get(decision, 'Decision made based on risk analysis')}")
    
    return "\n".join(explanations)


def get_top_risky_actors(limit: int = 5) -> list:
    """Get top risky actors sorted by average risk score."""
    actors = []
    for actor_id, profile in state.actor_profiles.items():
        actors.append({
            "actor_id": actor_id,
            "events": profile["events"],
            "blocked": profile["blocked"],
            "avg_risk": round(profile["avg_risk"], 2),
            "last_action": profile["last_action"],
            "last_decision": profile["last_decision"],
        })
    # Sort by avg_risk descending, then by blocked count
    actors.sort(key=lambda x: (x["avg_risk"], x["blocked"]), reverse=True)
    return actors[:limit]


async def process_single_event(event: EnterpriseActionEvent, use_ai: bool = False) -> dict:
    """Process a single event through the pipeline."""
    start_time = time.perf_counter()
    
    # Publish to Kafka (fire and forget - don't wait)
    try:
        state.producer.publish_event(event)
        # Track Kafka metrics
        state.kafka_metrics["messages_sent"] += 1
        state.kafka_metrics["last_send_times"].append(time.time())
        # Calculate messages per second (last 10 seconds)
        now = time.time()
        recent = [t for t in state.kafka_metrics["last_send_times"] if now - t < 10]
        state.kafka_metrics["messages_per_sec"] = len(recent) / 10.0
    except Exception:
        pass  # Don't block on Kafka errors
    state.metrics["events_produced"] += 1
    
    # Process signal
    signal = state.processor.process_event(event)
    
    # Make decision
    if use_ai and state.decision_agent:
        decision_result = state.decision_agent.query_ai(signal)
    else:
        decision_result = state.decision_agent._fallback_decision(signal, "speed-mode")
    
    # Calculate latency
    latency_ms = (time.perf_counter() - start_time) * 1000
    state.metrics["latencies"].append(latency_ms)
    state.metrics["avg_latency_ms"] = sum(state.metrics["latencies"]) / len(state.metrics["latencies"])
    
    # Update counters
    state.metrics["decisions_made"] += 1
    decision_type = decision_result["decision"]
    if decision_type == "block":
        state.metrics["blocked"] += 1
    elif decision_type == "allow":
        state.metrics["allowed"] += 1
    elif decision_type == "escalate":
        state.metrics["escalated"] += 1
    elif decision_type == "throttle":
        state.metrics["throttled"] += 1
    
    # Update risk trend
    state.risk_trend.append({
        "timestamp": datetime.now().isoformat(),
        "risk_score": signal.risk_score,
        "decision": decision_type,
    })
    
    # Update actor profiles
    actor_id = event.actor_id
    if actor_id not in state.actor_profiles:
        state.actor_profiles[actor_id] = {
            "events": 0,
            "blocked": 0,
            "total_risk": 0.0,
            "last_action": "",
            "last_decision": "",
        }
    profile = state.actor_profiles[actor_id]
    profile["events"] += 1
    profile["total_risk"] += signal.risk_score
    profile["avg_risk"] = profile["total_risk"] / profile["events"]
    profile["last_action"] = event.action
    profile["last_decision"] = decision_type
    if decision_type == "block":
        profile["blocked"] += 1
    
    # Build result
    result = {
        "type": "event_processed",
        "timestamp": datetime.now().isoformat(),
        "event": {
            "actor_id": event.actor_id,
            "action": event.action,
            "role": event.role,
            "frequency": event.frequency_last_60s,
            "geo_change": event.geo_change,
            "sensitivity": event.resource_sensitivity,
        },
        "signal": {
            "risk_score": signal.risk_score,
            "risk_factors": signal.risk_factors,
        },
        "decision": decision_result,
        "latency_ms": round(latency_ms, 2),
        "explanation": generate_explanation(event, signal, decision_result),
    }
    
    state.recent_events.append(result)
    return result


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main dashboard."""
    return get_dashboard_html()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    state.connected_clients.append(websocket)
    
    # Send current metrics
    await websocket.send_json({
        "type": "metrics",
        "data": {
            "events_produced": state.metrics["events_produced"],
            "decisions_made": state.metrics["decisions_made"],
            "blocked": state.metrics["blocked"],
            "allowed": state.metrics["allowed"],
            "escalated": state.metrics["escalated"],
            "throttled": state.metrics["throttled"],
            "avg_latency_ms": round(state.metrics["avg_latency_ms"], 2),
        }
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("action") == "start_simulation":
                asyncio.create_task(run_simulation(
                    event_count=msg.get("event_count", 50),
                    attack_percentage=msg.get("attack_percentage", 20),
                    duration_seconds=msg.get("duration_seconds", 10),
                    use_ai=msg.get("use_ai", False),
                ))
            elif msg.get("action") == "stop_simulation":
                state.simulation_running = False
            elif msg.get("action") == "reset_metrics":
                state.metrics = {
                    "events_produced": 0,
                    "decisions_made": 0,
                    "blocked": 0,
                    "allowed": 0,
                    "escalated": 0,
                    "throttled": 0,
                    "avg_latency_ms": 0,
                    "latencies": deque(maxlen=100),
                }
                state.risk_trend.clear()
                state.actor_profiles.clear()
                state.kafka_metrics["messages_sent"] = 0
                state.kafka_metrics["messages_per_sec"] = 0.0
                await broadcast({"type": "metrics_reset"})
                
    except WebSocketDisconnect:
        state.connected_clients.remove(websocket)


async def run_simulation(event_count: int, attack_percentage: int, duration_seconds: int, use_ai: bool):
    """Run a simulation with the given parameters."""
    if state.simulation_running:
        return
    
    state.simulation_running = True
    await broadcast({"type": "simulation_started", "total_events": event_count})
    
    delay = duration_seconds / event_count if event_count > 0 else 0.1
    attack_count = int(event_count * attack_percentage / 100)
    normal_count = event_count - attack_count
    
    # Create event queue with mixed patterns
    patterns = []
    patterns.extend([BehaviorPattern.NORMAL] * normal_count)
    patterns.extend([BehaviorPattern.SUSPICIOUS] * (attack_count // 3))
    patterns.extend([BehaviorPattern.HIGH_FREQUENCY] * (attack_count // 3))
    patterns.extend([BehaviorPattern.GEO_ANOMALY] * (attack_count - 2 * (attack_count // 3)))
    
    import random
    random.shuffle(patterns)
    
    for i, pattern in enumerate(patterns):
        if not state.simulation_running:
            break
        
        try:
            event = state.producer.generate_event(pattern=pattern)
            result = await process_single_event(event, use_ai=use_ai)
            
            # Broadcast event result
            await broadcast(result)
            
            # Broadcast updated metrics
            confluent_metrics_data = None
            if state.confluent_metrics_client:
                try:
                    cm = await state.confluent_metrics_client.get_cluster_metrics()
                    confluent_metrics_data = cm.to_dict()
                except Exception:
                    pass
            
            ksqldb_summaries = []
            if state.ksqldb_client and i % 5 == 0:  # Query every 5 events to reduce load
                try:
                    summaries = await state.ksqldb_client.get_user_risk_summaries(limit=5)
                    ksqldb_summaries = [s.to_dict() for s in summaries]
                except Exception:
                    pass
            
            await broadcast({
                "type": "metrics",
                "data": {
                    "events_produced": state.metrics["events_produced"],
                    "decisions_made": state.metrics["decisions_made"],
                    "blocked": state.metrics["blocked"],
                    "allowed": state.metrics["allowed"],
                    "escalated": state.metrics["escalated"],
                    "throttled": state.metrics["throttled"],
                    "avg_latency_ms": round(state.metrics["avg_latency_ms"], 2),
                },
                "kafka": {
                    "messages_sent": state.kafka_metrics["messages_sent"],
                    "messages_per_sec": round(state.kafka_metrics["messages_per_sec"], 1),
                    "connection_status": state.kafka_metrics["connection_status"],
                },
                "risk_trend": list(state.risk_trend),
                "top_actors": get_top_risky_actors(5),
                "progress": round((i + 1) / event_count * 100, 1),
                "confluent_status": state.confluent_status,
                "confluent_metrics": confluent_metrics_data,
                "ksqldb_summaries": ksqldb_summaries,
            })
            
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"Error processing event {i}: {e}")
    
    state.simulation_running = False
    try:
        state.producer.flush(timeout=5)
    except Exception:
        pass
    await broadcast({"type": "simulation_complete"})


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics."""
    return {
        "events_produced": state.metrics["events_produced"],
        "decisions_made": state.metrics["decisions_made"],
        "blocked": state.metrics["blocked"],
        "allowed": state.metrics["allowed"],
        "escalated": state.metrics["escalated"],
        "throttled": state.metrics["throttled"],
        "avg_latency_ms": round(state.metrics["avg_latency_ms"], 2),
    }


@app.get("/api/confluent-status")
async def get_confluent_status():
    """Get Confluent advanced features status."""
    return {
        "schema_registry": state.confluent_status["schema_registry"],
        "ksqldb": state.confluent_status["ksqldb"],
        "metrics_api": state.confluent_status["metrics_api"],
        "all_connected": all([
            state.confluent_status["schema_registry"]["connected"],
            state.confluent_status["ksqldb"]["connected"],
            state.confluent_status["metrics_api"]["connected"],
        ])
    }


@app.get("/api/confluent-metrics")
async def get_confluent_metrics():
    """Get Confluent Cloud cluster metrics."""
    if state.confluent_metrics_client:
        metrics = await state.confluent_metrics_client.get_cluster_metrics()
        return metrics.to_dict()
    return {"status": "unavailable"}


@app.get("/api/ksqldb/user-risk-summaries")
async def get_ksqldb_summaries():
    """Get user risk summaries from ksqlDB."""
    if state.ksqldb_client:
        summaries = await state.ksqldb_client.get_user_risk_summaries(limit=10)
        return [s.to_dict() for s in summaries]
    return []


def get_dashboard_html() -> str:
    """Return the dashboard HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Risk Gatekeeper</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .event-card { animation: slideIn 0.3s ease-out; }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .block-flash { animation: blockFlash 0.5s ease-out; }
        @keyframes blockFlash {
            0% { background-color: rgba(239, 68, 68, 0.5); }
            100% { background-color: transparent; }
        }
        .risk-high { color: #ef4444; }
        .risk-medium { color: #f59e0b; }
        .risk-low { color: #22c55e; }
    </style>
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold mb-2">🛡️ AI Risk Gatekeeper</h1>
            <p class="text-gray-400">Real-time AI-powered Enterprise Security | Confluent Kafka + Google Vertex AI</p>
        </div>

        <!-- Metrics Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
            <div class="bg-gray-800 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-blue-400" id="metric-events">0</div>
                <div class="text-xs text-gray-400">Events</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-purple-400" id="metric-decisions">0</div>
                <div class="text-xs text-gray-400">Decisions</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-green-400" id="metric-allowed">0</div>
                <div class="text-xs text-gray-400">Allowed</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-yellow-400" id="metric-throttled">0</div>
                <div class="text-xs text-gray-400">Throttled</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-orange-400" id="metric-escalated">0</div>
                <div class="text-xs text-gray-400">Escalated</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 text-center" id="blocked-card">
                <div class="text-2xl font-bold text-red-400" id="metric-blocked">0</div>
                <div class="text-xs text-gray-400">Blocked</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 text-center">
                <div class="text-2xl font-bold text-cyan-400" id="metric-latency">0</div>
                <div class="text-xs text-gray-400">Avg ms</div>
            </div>
        </div>

        <!-- Control Panel -->
        <div class="bg-gray-800 rounded-lg p-6 mb-8">
            <h2 class="text-xl font-semibold mb-4">Simulation Control</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div>
                    <label class="block text-sm text-gray-400 mb-2">Event Count: <span id="event-count-val">50</span></label>
                    <input type="range" id="event-count" min="10" max="500" value="50" class="w-full">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-2">Attack %: <span id="attack-pct-val">20</span>%</label>
                    <input type="range" id="attack-pct" min="0" max="100" value="20" class="w-full">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-2">Duration: <span id="duration-val">10</span>s</label>
                    <input type="range" id="duration" min="5" max="60" value="10" class="w-full">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-2">Use Vertex AI</label>
                    <label class="flex items-center cursor-pointer">
                        <input type="checkbox" id="use-ai" class="sr-only peer">
                        <div class="relative w-11 h-6 bg-gray-600 rounded-full peer peer-checked:bg-blue-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                        <span class="ml-2 text-sm text-gray-400">Slower but smarter</span>
                    </label>
                </div>
            </div>
            <div class="mt-6 flex gap-4">
                <button id="btn-start" class="bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg font-semibold transition">
                    ▶ Start Simulation
                </button>
                <button id="btn-stop" class="bg-red-600 hover:bg-red-700 px-6 py-2 rounded-lg font-semibold transition hidden">
                    ⏹ Stop
                </button>
                <button id="btn-reset" class="bg-gray-600 hover:bg-gray-700 px-6 py-2 rounded-lg font-semibold transition">
                    ↺ Reset Metrics
                </button>
            </div>
            <div class="mt-4">
                <div class="bg-gray-700 rounded-full h-2 overflow-hidden">
                    <div id="progress-bar" class="bg-blue-500 h-full transition-all duration-300" style="width: 0%"></div>
                </div>
                <p id="status-text" class="text-sm text-gray-400 mt-2">Ready to simulate</p>
            </div>
        </div>

        <!-- Risk Trend Chart + Top Risky Actors -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
            <!-- Risk Trend Chart -->
            <div class="lg:col-span-2 bg-gray-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4">📈 Risk Score Trend</h2>
                <div class="h-64">
                    <canvas id="risk-chart"></canvas>
                </div>
            </div>
            
            <!-- Top Risky Actors -->
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4">🎯 Top Risky Actors</h2>
                <div id="risky-actors" class="space-y-3">
                    <p class="text-gray-500 text-center py-4">No data yet...</p>
                </div>
            </div>
        </div>

        <!-- Live Event Feed + Decision Explanation -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- Live Event Feed -->
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Live Event Feed</h2>
                <div id="event-feed" class="space-y-2 max-h-96 overflow-y-auto">
                    <p class="text-gray-500 text-center py-8">Events will appear here when simulation starts...</p>
                </div>
            </div>
            
            <!-- Decision Explanation Panel -->
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4">🧠 AI Decision Explanation</h2>
                <div id="explanation-panel" class="bg-gray-700 rounded-lg p-4 min-h-48">
                    <p class="text-gray-500 text-center py-8">Click on an event to see the AI's reasoning...</p>
                </div>
            </div>
        </div>

        <!-- Confluent Integration Status Badge -->
        <div class="bg-gray-800 rounded-lg p-6 mb-8">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-xl font-semibold">🔗 Confluent Cloud Integration</h2>
                <div id="full-integration-badge" class="hidden px-3 py-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full text-sm font-semibold">
                    ✨ Full Integration Active
                </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- Schema Registry Status -->
                <div class="bg-gray-700 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-gray-400 text-sm">Schema Registry</span>
                        <span id="sr-status" class="px-2 py-1 rounded text-xs font-semibold bg-gray-600">Checking...</span>
                    </div>
                    <div class="text-lg font-bold text-blue-400" id="sr-format">JSON</div>
                    <div class="text-xs text-gray-500 mt-1" title="Schema Registry ensures data consistency across all producers and consumers">
                        Data serialization format
                    </div>
                </div>
                <!-- ksqlDB Status -->
                <div class="bg-gray-700 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-gray-400 text-sm">ksqlDB</span>
                        <span id="ksql-status" class="px-2 py-1 rounded text-xs font-semibold bg-gray-600">Checking...</span>
                    </div>
                    <div class="text-lg font-bold text-purple-400" id="ksql-streams">-</div>
                    <div class="text-xs text-gray-500 mt-1" title="ksqlDB provides real-time stream processing with SQL">
                        Stream processing
                    </div>
                </div>
                <!-- Metrics API Status -->
                <div class="bg-gray-700 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-gray-400 text-sm">Metrics API</span>
                        <span id="metrics-api-status" class="px-2 py-1 rounded text-xs font-semibold bg-gray-600">Checking...</span>
                    </div>
                    <div class="text-lg font-bold text-cyan-400" id="cluster-id">-</div>
                    <div class="text-xs text-gray-500 mt-1" title="Real-time cluster metrics from Confluent Cloud">
                        Cluster monitoring
                    </div>
                </div>
            </div>
        </div>

        <!-- Kafka Metrics Panel -->
        <div class="bg-gray-800 rounded-lg p-6 mb-8">
            <h2 class="text-xl font-semibold mb-4">📊 Confluent Kafka Metrics</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="bg-gray-700 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-gray-400 text-sm">Connection Status</span>
                        <span id="kafka-status" class="px-2 py-1 rounded text-xs font-semibold bg-green-600">Connected</span>
                    </div>
                    <div class="text-xs text-gray-500">Confluent Cloud (US-East1)</div>
                </div>
                <div class="bg-gray-700 rounded-lg p-4">
                    <div class="text-3xl font-bold text-blue-400" id="kafka-messages">0</div>
                    <div class="text-gray-400 text-sm">Messages to Kafka</div>
                    <div class="text-xs text-gray-500 mt-1">Topic: enterprise-action-events</div>
                </div>
                <div class="bg-gray-700 rounded-lg p-4">
                    <div class="text-3xl font-bold text-purple-400"><span id="kafka-rate">0</span>/s</div>
                    <div class="text-gray-400 text-sm">Throughput</div>
                    <div class="text-xs text-gray-500 mt-1">Messages per second</div>
                </div>
            </div>
        </div>

        <!-- ksqlDB Analytics Panel -->
        <div class="bg-gray-800 rounded-lg p-6 mb-8">
            <h2 class="text-xl font-semibold mb-4">⚡ ksqlDB Real-Time Analytics</h2>
            <div id="ksqldb-panel">
                <div class="text-gray-500 text-center py-4" id="ksqldb-placeholder">
                    ksqlDB analytics will appear during simulation...
                </div>
                <div id="ksqldb-summaries" class="hidden">
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="text-gray-400 border-b border-gray-700">
                                    <th class="text-left py-2">Actor</th>
                                    <th class="text-center py-2">Events</th>
                                    <th class="text-center py-2">Avg Risk</th>
                                    <th class="text-center py-2">Max Risk</th>
                                    <th class="text-center py-2">High Risk</th>
                                    <th class="text-center py-2">Status</th>
                                </tr>
                            </thead>
                            <tbody id="ksqldb-table-body">
                            </tbody>
                        </table>
                    </div>
                    <div class="text-xs text-gray-500 mt-3">
                        📊 5-minute tumbling window aggregation via ksqlDB
                    </div>
                </div>
            </div>
        </div>

        <!-- Architecture -->
        <div class="mt-8 bg-gray-800 rounded-lg p-6">
            <h2 class="text-xl font-semibold mb-4">Architecture</h2>
            <pre class="text-xs text-gray-400 overflow-x-auto">
┌─────────────────────────────────────────────────────────────────┐
│                    CONFLUENT CLOUD KAFKA                        │
├─────────────────────────────────────────────────────────────────┤
│  [enterprise-action-events] → [risk-signals] → [risk-decisions] │
└─────────────────────────────────────────────────────────────────┘
          │                        │                │
    ┌─────┴─────┐           ┌─────┴─────┐    ┌─────┴─────┐
    │   Event   │           │  Signal   │    │  Decision │
    │ Producer  │           │ Processor │    │   Agent   │
    └───────────┘           └───────────┘    └─────┬─────┘
                                                   │
                                             ┌─────┴─────┐
                                             │  Vertex   │
                                             │ AI Gemini │
                                             └───────────┘
            </pre>
        </div>
    </div>

    <script>
        let ws;
        let eventFeed = document.getElementById('event-feed');
        let isFirstEvent = true;
        let riskChart;
        let lastBlockedCount = 0;

        // Initialize Chart
        function initChart() {
            const ctx = document.getElementById('risk-chart').getContext('2d');
            riskChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Risk Score',
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 1,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#9ca3af' }
                        },
                        x: { display: false }
                    },
                    plugins: { legend: { display: false } },
                    animation: { duration: 0 }
                }
            });
        }

        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                document.getElementById('status-text').textContent = 'Connected to server';
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = () => {
                document.getElementById('status-text').textContent = 'Disconnected. Reconnecting...';
                setTimeout(connect, 2000);
            };
        }

        function handleMessage(data) {
            if (data.type === 'metrics') {
                updateMetrics(data.data);
                updateKafkaMetrics(data.kafka);
                updateRiskChart(data.risk_trend);
                updateRiskyActors(data.top_actors);
                updateConfluentStatus(data.confluent_status);
                updateKsqlDBSummaries(data.ksqldb_summaries);
                if (data.progress !== undefined) {
                    document.getElementById('progress-bar').style.width = data.progress + '%';
                }
            } else if (data.type === 'event_processed') {
                addEventToFeed(data);
            } else if (data.type === 'simulation_started') {
                document.getElementById('btn-start').classList.add('hidden');
                document.getElementById('btn-stop').classList.remove('hidden');
                document.getElementById('status-text').textContent = `Processing ${data.total_events} events...`;
                isFirstEvent = true;
            } else if (data.type === 'simulation_complete') {
                document.getElementById('btn-start').classList.remove('hidden');
                document.getElementById('btn-stop').classList.add('hidden');
                document.getElementById('status-text').textContent = 'Simulation complete!';
                document.getElementById('progress-bar').style.width = '100%';
            } else if (data.type === 'metrics_reset') {
                document.getElementById('progress-bar').style.width = '0%';
                eventFeed.innerHTML = '<p class="text-gray-500 text-center py-8">Events will appear here when simulation starts...</p>';
                document.getElementById('explanation-panel').innerHTML = '<p class="text-gray-500 text-center py-8">Click on an event to see the AI\\'s reasoning...</p>';
                document.getElementById('risky-actors').innerHTML = '<p class="text-gray-500 text-center py-4">No data yet...</p>';
                document.getElementById('ksqldb-summaries').classList.add('hidden');
                document.getElementById('ksqldb-placeholder').classList.remove('hidden');
                isFirstEvent = true;
                lastBlockedCount = 0;
                if (riskChart) {
                    riskChart.data.labels = [];
                    riskChart.data.datasets[0].data = [];
                    riskChart.update();
                }
            }
        }

        function updateConfluentStatus(status) {
            if (!status) return;
            
            // Schema Registry
            const srStatus = document.getElementById('sr-status');
            const srFormat = document.getElementById('sr-format');
            if (status.schema_registry.connected) {
                srStatus.textContent = 'Connected';
                srStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-green-600';
                srFormat.textContent = status.schema_registry.format || 'Avro';
            } else {
                srStatus.textContent = 'Offline';
                srStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-gray-600';
            }
            
            // ksqlDB
            const ksqlStatus = document.getElementById('ksql-status');
            const ksqlStreams = document.getElementById('ksql-streams');
            if (status.ksqldb.connected) {
                ksqlStatus.textContent = 'Connected';
                ksqlStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-green-600';
                ksqlStreams.textContent = status.ksqldb.streams_ready ? 'Streams Ready' : 'Initializing';
            } else {
                ksqlStatus.textContent = 'Offline';
                ksqlStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-gray-600';
                ksqlStreams.textContent = '-';
            }
            
            // Metrics API
            const metricsStatus = document.getElementById('metrics-api-status');
            const clusterId = document.getElementById('cluster-id');
            if (status.metrics_api.connected) {
                metricsStatus.textContent = 'Connected';
                metricsStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-green-600';
                clusterId.textContent = status.metrics_api.cluster_id || 'Active';
            } else {
                metricsStatus.textContent = 'Offline';
                metricsStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-gray-600';
                clusterId.textContent = '-';
            }
            
            // Full integration badge
            const badge = document.getElementById('full-integration-badge');
            if (status.schema_registry.connected && status.ksqldb.connected && status.metrics_api.connected) {
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }

        function updateKsqlDBSummaries(summaries) {
            if (!summaries || summaries.length === 0) return;
            
            document.getElementById('ksqldb-placeholder').classList.add('hidden');
            document.getElementById('ksqldb-summaries').classList.remove('hidden');
            
            const tbody = document.getElementById('ksqldb-table-body');
            tbody.innerHTML = summaries.map(s => {
                const riskClass = s.avg_risk >= 0.6 ? 'text-red-400' : s.avg_risk >= 0.4 ? 'text-yellow-400' : 'text-green-400';
                const flagged = s.is_flagged ? '<span class="text-red-400">🚨 Flagged</span>' : '<span class="text-green-400">✓ Normal</span>';
                return `
                    <tr class="border-b border-gray-700">
                        <td class="py-2 font-mono text-sm">${s.actor_id}</td>
                        <td class="py-2 text-center">${s.event_count}</td>
                        <td class="py-2 text-center ${riskClass}">${(s.avg_risk * 100).toFixed(0)}%</td>
                        <td class="py-2 text-center">${(s.max_risk * 100).toFixed(0)}%</td>
                        <td class="py-2 text-center">${s.high_risk_count}</td>
                        <td class="py-2 text-center">${flagged}</td>
                    </tr>
                `;
            }).join('');
        }

        function updateMetrics(metrics) {
            document.getElementById('metric-events').textContent = metrics.events_produced;
            document.getElementById('metric-decisions').textContent = metrics.decisions_made;
            document.getElementById('metric-allowed').textContent = metrics.allowed;
            document.getElementById('metric-throttled').textContent = metrics.throttled;
            document.getElementById('metric-escalated').textContent = metrics.escalated;
            document.getElementById('metric-blocked').textContent = metrics.blocked;
            document.getElementById('metric-latency').textContent = metrics.avg_latency_ms.toFixed(1);
            
            if (metrics.blocked > lastBlockedCount) {
                const card = document.getElementById('blocked-card');
                card.classList.add('block-flash');
                setTimeout(() => card.classList.remove('block-flash'), 500);
                lastBlockedCount = metrics.blocked;
            }
        }

        function updateKafkaMetrics(kafka) {
            if (!kafka) return;
            document.getElementById('kafka-messages').textContent = kafka.messages_sent;
            document.getElementById('kafka-rate').textContent = kafka.messages_per_sec;
            
            const statusEl = document.getElementById('kafka-status');
            if (kafka.connection_status === 'connected') {
                statusEl.textContent = 'Connected';
                statusEl.className = 'px-2 py-1 rounded text-xs font-semibold bg-green-600';
            } else if (kafka.connection_status === 'error') {
                statusEl.textContent = 'Error';
                statusEl.className = 'px-2 py-1 rounded text-xs font-semibold bg-red-600';
            } else {
                statusEl.textContent = 'Connecting...';
                statusEl.className = 'px-2 py-1 rounded text-xs font-semibold bg-yellow-600';
            }
        }

        function updateRiskChart(riskTrend) {
            if (!riskTrend || !riskChart) return;
            const labels = riskTrend.map((_, i) => i);
            const data = riskTrend.map(r => r.risk_score);
            riskChart.data.labels = labels;
            riskChart.data.datasets[0].data = data;
            const avgRisk = data.length > 0 ? data.reduce((a, b) => a + b, 0) / data.length : 0;
            if (avgRisk >= 0.6) {
                riskChart.data.datasets[0].borderColor = '#ef4444';
                riskChart.data.datasets[0].backgroundColor = 'rgba(239, 68, 68, 0.1)';
            } else if (avgRisk >= 0.4) {
                riskChart.data.datasets[0].borderColor = '#f59e0b';
                riskChart.data.datasets[0].backgroundColor = 'rgba(245, 158, 11, 0.1)';
            } else {
                riskChart.data.datasets[0].borderColor = '#22c55e';
                riskChart.data.datasets[0].backgroundColor = 'rgba(34, 197, 94, 0.1)';
            }
            riskChart.update();
        }

        function updateRiskyActors(actors) {
            if (!actors || actors.length === 0) return;
            const container = document.getElementById('risky-actors');
            container.innerHTML = actors.map((actor, i) => {
                const riskClass = actor.avg_risk >= 0.6 ? 'risk-high' : actor.avg_risk >= 0.4 ? 'risk-medium' : 'risk-low';
                const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '•';
                return `
                    <div class="bg-gray-600 rounded p-3 flex justify-between items-center">
                        <div>
                            <span class="mr-2">${medal}</span>
                            <span class="font-mono text-sm">${actor.actor_id}</span>
                            <div class="text-xs text-gray-400">${actor.events} events, ${actor.blocked} blocked</div>
                        </div>
                        <div class="text-right">
                            <div class="text-lg font-bold ${riskClass}">${(actor.avg_risk * 100).toFixed(0)}%</div>
                            <div class="text-xs text-gray-400">avg risk</div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function showExplanation(data) {
            const panel = document.getElementById('explanation-panel');
            const decision = data.decision.decision;
            const decisionColors = { 'allow': 'text-green-400', 'throttle': 'text-yellow-400', 'escalate': 'text-orange-400', 'block': 'text-red-400' };
            const decisionIcons = { 'allow': '✅', 'throttle': '⏱️', 'escalate': '⚠️', 'block': '🚫' };
            panel.innerHTML = `
                <div class="mb-4">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-2xl">${decisionIcons[decision]}</span>
                        <span class="text-xl font-bold ${decisionColors[decision]}">${decision.toUpperCase()}</span>
                    </div>
                    <div class="text-sm text-gray-400">
                        Actor: <span class="font-mono">${data.event.actor_id}</span> | 
                        Action: ${data.event.action} | Latency: ${data.latency_ms}ms
                    </div>
                </div>
                <div class="border-t border-gray-600 pt-4">
                    <h4 class="text-sm font-semibold text-gray-300 mb-2">Analysis:</h4>
                    <pre class="text-sm text-gray-300 whitespace-pre-wrap">${data.explanation || 'No explanation available'}</pre>
                </div>
            `;
        }

        function addEventToFeed(data) {
            if (isFirstEvent) {
                eventFeed.innerHTML = '';
                isFirstEvent = false;
            }

            const decisionColors = {
                'allow': 'border-green-500 bg-green-900/20',
                'throttle': 'border-yellow-500 bg-yellow-900/20',
                'escalate': 'border-orange-500 bg-orange-900/20',
                'block': 'border-red-500 bg-red-900/20'
            };
            const decisionIcons = { 'allow': '✅', 'throttle': '⏱️', 'escalate': '⚠️', 'block': '🚫' };

            const decision = data.decision.decision;
            const colorClass = decisionColors[decision] || 'border-gray-500';
            const icon = decisionIcons[decision] || '❓';

            const card = document.createElement('div');
            card.className = `event-card border-l-4 ${colorClass} p-3 rounded cursor-pointer hover:bg-gray-700/50 transition`;
            card.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <span class="font-mono text-sm">${data.event.actor_id}</span>
                        <span class="text-gray-400 text-sm ml-2">${data.event.action}</span>
                    </div>
                    <div class="text-right">
                        <span class="text-lg">${icon}</span>
                        <span class="text-xs text-gray-400 ml-1">${data.latency_ms}ms</span>
                    </div>
                </div>
                <div class="text-xs text-gray-400 mt-1">
                    Risk: ${(data.signal.risk_score * 100).toFixed(0)}% | 
                    ${data.signal.risk_factors.slice(0, 2).join(', ') || 'No risk factors'}
                </div>
            `;
            
            card.onclick = () => showExplanation(data);
            if (decision === 'block') showExplanation(data);

            eventFeed.insertBefore(card, eventFeed.firstChild);
            while (eventFeed.children.length > 50) {
                eventFeed.removeChild(eventFeed.lastChild);
            }
        }

        // Slider value updates
        document.getElementById('event-count').oninput = (e) => {
            document.getElementById('event-count-val').textContent = e.target.value;
        };
        document.getElementById('attack-pct').oninput = (e) => {
            document.getElementById('attack-pct-val').textContent = e.target.value;
        };
        document.getElementById('duration').oninput = (e) => {
            document.getElementById('duration-val').textContent = e.target.value;
        };

        // Button handlers
        document.getElementById('btn-start').onclick = () => {
            ws.send(JSON.stringify({
                action: 'start_simulation',
                event_count: parseInt(document.getElementById('event-count').value),
                attack_percentage: parseInt(document.getElementById('attack-pct').value),
                duration_seconds: parseInt(document.getElementById('duration').value),
                use_ai: document.getElementById('use-ai').checked
            }));
        };

        document.getElementById('btn-stop').onclick = () => {
            ws.send(JSON.stringify({ action: 'stop_simulation' }));
        };

        document.getElementById('btn-reset').onclick = () => {
            ws.send(JSON.stringify({ action: 'reset_metrics' }));
        };

        // Initialize on load
        initChart();
        connect();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
