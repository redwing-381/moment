"""
Formatting utilities for AI Risk Gatekeeper.

This module contains functions for generating human-readable explanations
and formatting data for display in the dashboard.
"""

from typing import Any


def generate_explanation(event: Any, signal: Any, decision_result: dict) -> str:
    """
    Generate human-readable explanation for a security decision.
    
    Args:
        event: The enterprise action event
        signal: The processed signal with risk score and factors
        decision_result: The decision made by the agent
        
    Returns:
        A formatted string explaining the decision
    """
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


def get_top_risky_actors(actor_profiles: dict, limit: int = 5) -> list:
    """
    Get top risky actors sorted by average risk score.
    
    Args:
        actor_profiles: Dictionary mapping actor_id to profile data
        limit: Maximum number of actors to return
        
    Returns:
        List of actor dictionaries sorted by risk
    """
    actors = []
    for actor_id, profile in actor_profiles.items():
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


def format_risk_factors(factors: list) -> list:
    """
    Format risk factors for display.
    
    Args:
        factors: List of risk factor identifiers
        
    Returns:
        List of human-readable factor descriptions
    """
    factor_descriptions = {
        "high_frequency": "High request frequency",
        "geo_anomaly": "Geographic anomaly detected",
        "sensitive_resource": "Sensitive resource access",
        "off_hours": "Off-hours activity",
        "privilege_escalation": "Privilege escalation attempt",
        "bulk_operation": "Bulk data operation",
        "new_device": "New device detected",
        "failed_auth": "Failed authentication attempts",
    }
    
    return [
        factor_descriptions.get(f, f.replace('_', ' ').title())
        for f in factors
    ]
