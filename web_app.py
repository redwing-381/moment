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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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
from ai_risk_gatekeeper.agents.attack_scenarios import get_scenario, get_all_scenarios, AttackScenario

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

# Mount static files and configure templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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

from ai_risk_gatekeeper.utils.formatters import generate_explanation, get_top_risky_actors as _get_top_risky_actors


def get_top_risky_actors(limit: int = 5) -> list:
    """Get top risky actors sorted by average risk score."""
    return _get_top_risky_actors(state.actor_profiles, limit)
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
async def home(request: Request):
    """Serve the main dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


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
            elif msg.get("action") == "run_scenario":
                scenario_id = msg.get("scenario_id")
                use_ai = msg.get("use_ai", False)
                asyncio.create_task(run_attack_scenario(scenario_id, use_ai))
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


async def run_attack_scenario(scenario_id: str, use_ai: bool = False):
    """Run a predefined attack scenario."""
    if state.simulation_running:
        return
    
    scenario = get_scenario(scenario_id)
    if not scenario:
        await broadcast({"type": "error", "message": f"Unknown scenario: {scenario_id}"})
        return
    
    state.simulation_running = True
    await broadcast({
        "type": "scenario_started",
        "scenario": {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "icon": scenario.icon,
            "expected_blocks": scenario.expected_blocks,
        }
    })
    
    total_events = sum(e.repeat for e in scenario.events)
    events_processed = 0
    
    for event_config in scenario.events:
        if not state.simulation_running:
            break
        
        for _ in range(event_config.repeat):
            if not state.simulation_running:
                break
            
            # Create event from config
            event = EnterpriseActionEvent(
                actor_id=scenario.actor_id,
                action=event_config.action,
                role=event_config.role,
                frequency_last_60s=event_config.frequency,
                geo_change=event_config.geo_change,
                timestamp=int(time.time() * 1000),
                session_id=str(uuid.uuid4()),
                resource_sensitivity=event_config.sensitivity
            )
            
            result = await process_single_event(event, use_ai=use_ai)
            events_processed += 1
            
            # Broadcast event result
            await broadcast(result)
            
            # Broadcast updated metrics with scenario info
            confluent_metrics_data = None
            if state.confluent_metrics_client:
                try:
                    cm = await state.confluent_metrics_client.get_cluster_metrics()
                    confluent_metrics_data = cm.to_dict()
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
                "progress": round(events_processed / total_events * 100, 1),
                "confluent_status": state.confluent_status,
                "confluent_metrics": confluent_metrics_data,
                "scenario_name": scenario.name,
            })
            
            await asyncio.sleep(event_config.delay_ms / 1000)
    
    state.simulation_running = False
    try:
        state.producer.flush(timeout=5)
    except Exception:
        pass
    
    # Send scenario complete with summary
    await broadcast({
        "type": "scenario_complete",
        "scenario": scenario.name,
        "summary": {
            "total_events": events_processed,
            "blocked": state.metrics["blocked"],
            "expected_blocks": scenario.expected_blocks,
            "detection_rate": round(state.metrics["blocked"] / max(scenario.expected_blocks, 1) * 100, 1),
        }
    })


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


@app.get("/api/export-report")
async def export_report():
    """Generate a report of the current simulation results."""
    if state.metrics["events_produced"] == 0:
        return {"error": "No simulation data to export"}
    
    # Get blocked events from recent events
    blocked_events = [
        {
            "timestamp": e.get("timestamp"),
            "actor_id": e.get("event", {}).get("actor_id"),
            "action": e.get("event", {}).get("action"),
            "risk_score": e.get("signal", {}).get("risk_score"),
            "explanation": e.get("explanation", "")[:200],
        }
        for e in list(state.recent_events)
        if e.get("decision", {}).get("decision") == "block"
    ]
    
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_events": state.metrics["events_produced"],
            "decisions_made": state.metrics["decisions_made"],
            "blocked": state.metrics["blocked"],
            "allowed": state.metrics["allowed"],
            "escalated": state.metrics["escalated"],
            "throttled": state.metrics["throttled"],
            "avg_latency_ms": round(state.metrics["avg_latency_ms"], 2),
            "block_rate": round(state.metrics["blocked"] / max(state.metrics["events_produced"], 1) * 100, 1),
        },
        "top_risky_actors": get_top_risky_actors(10),
        "blocked_events": blocked_events[-20:],  # Last 20 blocked events
        "risk_trend": list(state.risk_trend),
        "confluent_status": state.confluent_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
