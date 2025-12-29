"""
Simulation logic for AI Risk Gatekeeper.

This module handles running simulations and attack scenarios.
"""

import asyncio
import time
import uuid
import random
from datetime import datetime

from .state import state
from ai_risk_gatekeeper.agents import BehaviorPattern
from ai_risk_gatekeeper.models.events import EnterpriseActionEvent
from ai_risk_gatekeeper.agents.attack_scenarios import get_scenario
from ai_risk_gatekeeper.utils.formatters import generate_explanation, get_top_risky_actors


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
    
    # Make decision using hybrid engine if available
    if state.hybrid_engine:
        from ai_risk_gatekeeper.models.events import DecisionMode
        
        # Set mode based on use_ai flag
        if use_ai:
            # Use current mode (HYBRID or FULL_AI)
            if state.decision_mode == DecisionMode.FAST:
                state.hybrid_engine.set_mode(DecisionMode.HYBRID)
        else:
            # Force FAST mode when AI is disabled
            state.hybrid_engine.set_mode(DecisionMode.FAST)
        
        decision_result_obj = await state.hybrid_engine.decide(signal)
        decision_result = {
            "decision": decision_result_obj.decision,
            "confidence": decision_result_obj.confidence,
            "reason": decision_result_obj.reason,
        }
        latency_ms = decision_result_obj.latency_ms
        decision_source = decision_result_obj.source
    elif use_ai and state.decision_agent:
        decision_result = state.decision_agent.query_ai(signal)
        latency_ms = (time.perf_counter() - start_time) * 1000
        decision_source = "ai"
    else:
        decision_result = state.decision_agent._fallback_decision(signal, "speed-mode")
        latency_ms = (time.perf_counter() - start_time) * 1000
        decision_source = "rule"
    
    # Track latency
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
            
            # Get Confluent metrics if available
            confluent_metrics_data = None
            if state.confluent_metrics_client:
                try:
                    cm = await state.confluent_metrics_client.get_cluster_metrics()
                    confluent_metrics_data = cm.to_dict()
                except Exception:
                    pass
            
            # Get ksqlDB summaries periodically
            ksqldb_summaries = []
            if state.ksqldb_client and events_processed % 3 == 0:
                try:
                    summaries = await state.ksqldb_client.get_user_risk_summaries(limit=5)
                    ksqldb_summaries = [s.to_dict() for s in summaries]
                except Exception:
                    pass
            
            # Broadcast updated metrics
            await broadcast({
                "type": "metrics",
                "data": state.get_metrics_dict(),
                "kafka": state.get_kafka_metrics_dict(),
                "risk_trend": list(state.risk_trend),
                "top_actors": get_top_risky_actors(state.actor_profiles, 5),
                "progress": round(events_processed / total_events * 100, 1),
                "confluent_status": state.confluent_status,
                "confluent_metrics": confluent_metrics_data,
                "ksqldb_summaries": ksqldb_summaries,
                "scenario_name": scenario.name,
                "decision_stats": state.get_decision_stats_dict(),
                "decision_mode": state.decision_mode.value,
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
    
    random.shuffle(patterns)
    
    for i, pattern in enumerate(patterns):
        if not state.simulation_running:
            break
        
        try:
            event = state.producer.generate_event(pattern=pattern)
            result = await process_single_event(event, use_ai=use_ai)
            
            # Broadcast event result
            await broadcast(result)
            
            # Get Confluent metrics if available
            confluent_metrics_data = None
            if state.confluent_metrics_client:
                try:
                    cm = await state.confluent_metrics_client.get_cluster_metrics()
                    confluent_metrics_data = cm.to_dict()
                except Exception:
                    pass
            
            # Get ksqlDB summaries periodically
            ksqldb_summaries = []
            if state.ksqldb_client and i % 3 == 0:
                try:
                    summaries = await state.ksqldb_client.get_user_risk_summaries(limit=5)
                    ksqldb_summaries = [s.to_dict() for s in summaries]
                except Exception:
                    pass
            
            # Broadcast updated metrics
            await broadcast({
                "type": "metrics",
                "data": state.get_metrics_dict(),
                "kafka": state.get_kafka_metrics_dict(),
                "risk_trend": list(state.risk_trend),
                "top_actors": get_top_risky_actors(state.actor_profiles, 5),
                "progress": round((i + 1) / event_count * 100, 1),
                "confluent_status": state.confluent_status,
                "confluent_metrics": confluent_metrics_data,
                "ksqldb_summaries": ksqldb_summaries,
                "decision_stats": state.get_decision_stats_dict(),
                "decision_mode": state.decision_mode.value,
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
