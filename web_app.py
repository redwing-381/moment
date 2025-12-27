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
        self.simulation_running = False


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connections on startup."""
    try:
        state.producer = EventProducer()
        state.producer.connect()
        state.processor = SignalProcessor()
        state.decision_agent = DecisionAgent()
        state.decision_agent.connect()
        print("✓ All agents connected")
    except Exception as e:
        print(f"Warning: Could not connect agents: {e}")
    
    yield
    
    # Cleanup
    if state.producer:
        state.producer.disconnect()
    if state.decision_agent:
        state.decision_agent.disconnect()


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


async def process_single_event(event: EnterpriseActionEvent, use_ai: bool = False) -> dict:
    """Process a single event through the pipeline."""
    start_time = time.perf_counter()
    
    # Publish to Kafka
    state.producer.publish_event(event)
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
                await run_simulation(
                    event_count=msg.get("event_count", 50),
                    attack_percentage=msg.get("attack_percentage", 20),
                    duration_seconds=msg.get("duration_seconds", 10),
                    use_ai=msg.get("use_ai", False),
                )
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
        
        event = state.producer.generate_event(pattern=pattern)
        result = await process_single_event(event, use_ai=use_ai)
        
        # Broadcast event result
        await broadcast(result)
        
        # Broadcast updated metrics
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
            "progress": round((i + 1) / event_count * 100, 1),
        })
        
        await asyncio.sleep(delay)
    
    state.simulation_running = False
    state.producer.flush(timeout=5)
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
            <div class="bg-gray-800 rounded-lg p-4 text-center">
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

        <!-- Live Event Feed -->
        <div class="bg-gray-800 rounded-lg p-6">
            <h2 class="text-xl font-semibold mb-4">Live Event Feed</h2>
            <div id="event-feed" class="space-y-2 max-h-96 overflow-y-auto">
                <p class="text-gray-500 text-center py-8">Events will appear here when simulation starts...</p>
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
                isFirstEvent = true;
            }
        }

        function updateMetrics(metrics) {
            document.getElementById('metric-events').textContent = metrics.events_produced;
            document.getElementById('metric-decisions').textContent = metrics.decisions_made;
            document.getElementById('metric-allowed').textContent = metrics.allowed;
            document.getElementById('metric-throttled').textContent = metrics.throttled;
            document.getElementById('metric-escalated').textContent = metrics.escalated;
            document.getElementById('metric-blocked').textContent = metrics.blocked;
            document.getElementById('metric-latency').textContent = metrics.avg_latency_ms.toFixed(1);
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
            const decisionIcons = {
                'allow': '✅',
                'throttle': '⏱️',
                'escalate': '⚠️',
                'block': '🚫'
            };

            const decision = data.decision.decision;
            const colorClass = decisionColors[decision] || 'border-gray-500';
            const icon = decisionIcons[decision] || '❓';

            const card = document.createElement('div');
            card.className = `event-card border-l-4 ${colorClass} p-3 rounded`;
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

            eventFeed.insertBefore(card, eventFeed.firstChild);
            
            // Keep only last 50 events in DOM
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

        // Connect on load
        connect();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
