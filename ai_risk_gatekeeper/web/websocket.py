"""
WebSocket handling for AI Risk Gatekeeper.

This module manages real-time WebSocket connections and message broadcasting.
"""

import asyncio
import json
from collections import deque
from fastapi import WebSocket, WebSocketDisconnect

from .state import state
from .simulation import run_simulation, run_attack_scenario


async def broadcast(message: dict):
    """Send message to all connected WebSocket clients."""
    dead_clients = []
    for client in state.connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            dead_clients.append(client)
    for client in dead_clients:
        if client in state.connected_clients:
            state.connected_clients.remove(client)


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    state.connected_clients.append(websocket)
    
    # Send current metrics on connect
    await websocket.send_json({
        "type": "metrics",
        "data": state.get_metrics_dict()
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            action = msg.get("action")
            
            if action == "start_simulation":
                asyncio.create_task(run_simulation(
                    event_count=msg.get("event_count", 50),
                    attack_percentage=msg.get("attack_percentage", 20),
                    duration_seconds=msg.get("duration_seconds", 10),
                    use_ai=msg.get("use_ai", False),
                ))
            
            elif action == "run_scenario":
                scenario_id = msg.get("scenario_id")
                use_ai = msg.get("use_ai", False)
                asyncio.create_task(run_attack_scenario(scenario_id, use_ai))
            
            elif action == "stop_simulation":
                state.simulation_running = False
            
            elif action == "reset_metrics":
                state.reset_metrics()
                await broadcast({"type": "metrics_reset"})
                
    except WebSocketDisconnect:
        if websocket in state.connected_clients:
            state.connected_clients.remove(websocket)
