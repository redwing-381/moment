"""
API routes for AI Risk Gatekeeper.

This module contains all REST API endpoints for the dashboard.
"""

from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .state import state
from ai_risk_gatekeeper.utils.formatters import get_top_risky_actors

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Serve the landing page."""
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@router.get("/api/metrics")
async def get_metrics():
    """Get current metrics."""
    return {
        **state.get_metrics_dict(),
        "decision_stats": state.get_decision_stats_dict(),
        "decision_mode": state.decision_mode.value,
    }


@router.get("/api/decision-stats")
async def get_decision_stats():
    """Get decision engine statistics."""
    return {
        "mode": state.decision_mode.value,
        "stats": state.get_decision_stats_dict(),
        "cache_stats": state.hybrid_engine.cache_stats if state.hybrid_engine else {},
    }


@router.get("/api/confluent-status")
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


@router.get("/api/confluent-metrics")
async def get_confluent_metrics():
    """Get Confluent Cloud cluster metrics."""
    if state.confluent_metrics_client:
        metrics = await state.confluent_metrics_client.get_cluster_metrics()
        return metrics.to_dict()
    return {"status": "unavailable"}


@router.get("/api/ksqldb/user-risk-summaries")
async def get_ksqldb_summaries():
    """Get user risk summaries from ksqlDB."""
    if state.ksqldb_client:
        summaries = await state.ksqldb_client.get_user_risk_summaries(limit=10)
        return [s.to_dict() for s in summaries]
    return []


@router.get("/api/export-report")
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
        "top_risky_actors": get_top_risky_actors(state.actor_profiles, 10),
        "blocked_events": blocked_events[-20:],
        "risk_trend": list(state.risk_trend),
        "confluent_status": state.confluent_status,
    }
