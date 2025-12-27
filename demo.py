#!/usr/bin/env python3
"""
AI Risk Gatekeeper - Demo Script

This script demonstrates the complete event processing pipeline,
showing both normal operations and suspicious behavior detection.
"""

import sys
import time
import logging
from dotenv import load_dotenv

load_dotenv()

from ai_risk_gatekeeper.agents import (
    create_event_producer,
    BehaviorPattern,
    SignalProcessor,
    DecisionAgent,
    ActionAgent,
)
from ai_risk_gatekeeper.models.events import EnterpriseActionEvent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print demo banner."""
    print("\n" + "=" * 60)
    print("   🛡️  AI Risk Gatekeeper - Live Demo")
    print("   Real-time Enterprise Security with AI")
    print("=" * 60 + "\n")


def demo_event_generation():
    """Demonstrate event generation and publishing."""
    print("\n📤 DEMO 1: Event Generation & Publishing")
    print("-" * 40)
    
    producer = create_event_producer()
    
    try:
        # Normal events
        print("\n🟢 Generating NORMAL behavior events...")
        for i in range(3):
            event, time_ms = producer.generate_and_publish(BehaviorPattern.NORMAL)
            print(f"   [{i+1}] actor={event.actor_id} action={event.action} "
                  f"freq={event.frequency_last_60s} ({time_ms:.1f}ms)")
        
        # Suspicious events
        print("\n🔴 Generating SUSPICIOUS behavior events...")
        patterns = [
            (BehaviorPattern.HIGH_FREQUENCY, "High Frequency"),
            (BehaviorPattern.GEO_ANOMALY, "Geo Anomaly"),
            (BehaviorPattern.PRIVILEGE_ESCALATION, "Privilege Escalation"),
        ]
        
        for pattern, name in patterns:
            event, time_ms = producer.generate_and_publish(pattern)
            print(f"   [{name}] actor={event.actor_id} action={event.action} "
                  f"freq={event.frequency_last_60s} geo={event.geo_change}")
        
        producer.flush(timeout=10)
        print(f"\n✅ Published {producer.stats['events_produced']} events to Kafka")
        
    finally:
        producer.disconnect()


def demo_signal_processing():
    """Demonstrate signal processing."""
    print("\n📊 DEMO 2: Signal Processing")
    print("-" * 40)
    
    processor = SignalProcessor()
    
    # Create test events
    events = [
        EnterpriseActionEvent(
            actor_id="user_normal",
            action="file_read",
            role="developer",
            frequency_last_60s=3,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id="session_1",
            resource_sensitivity="low"
        ),
        EnterpriseActionEvent(
            actor_id="user_suspicious",
            action="bulk_export",
            role="developer",
            frequency_last_60s=45,
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id="session_2",
            resource_sensitivity="critical"
        ),
    ]
    
    print("\n🔍 Processing events and calculating risk scores...")
    for event in events:
        signal = processor.process_event(event)
        risk_level = "🟢 LOW" if signal.risk_score < 0.3 else \
                     "🟡 MEDIUM" if signal.risk_score < 0.6 else "🔴 HIGH"
        
        print(f"\n   Actor: {signal.actor_id}")
        print(f"   Risk Score: {signal.risk_score:.2f} {risk_level}")
        print(f"   Risk Factors: {', '.join(signal.risk_factors) or 'None'}")


def demo_decision_making():
    """Demonstrate AI decision making (using fallback)."""
    print("\n🤖 DEMO 3: AI Decision Making")
    print("-" * 40)
    
    from ai_risk_gatekeeper.models.events import RiskSignal
    import uuid
    
    # Create test signals
    signals = [
        RiskSignal(
            actor_id="user_safe",
            risk_score=0.15,
            risk_factors=[],
            original_event=EnterpriseActionEvent(
                actor_id="user_safe", action="file_read", role="developer",
                frequency_last_60s=2, geo_change=False,
                timestamp=int(time.time() * 1000),
                session_id="s1", resource_sensitivity="low"
            ),
            processing_timestamp=int(time.time() * 1000),
            correlation_id=str(uuid.uuid4())
        ),
        RiskSignal(
            actor_id="user_risky",
            risk_score=0.85,
            risk_factors=["high_frequency_activity", "geographic_anomaly", "sensitive_resource_critical"],
            original_event=EnterpriseActionEvent(
                actor_id="user_risky", action="bulk_export", role="developer",
                frequency_last_60s=50, geo_change=True,
                timestamp=int(time.time() * 1000),
                session_id="s2", resource_sensitivity="critical"
            ),
            processing_timestamp=int(time.time() * 1000),
            correlation_id=str(uuid.uuid4())
        ),
    ]
    
    agent = DecisionAgent()
    
    print("\n🧠 Making risk decisions (using fallback logic)...")
    for signal in signals:
        result = agent._fallback_decision(signal, "Demo mode")
        decision_icon = {
            "allow": "✅", "throttle": "⏱️", "block": "🚫", "escalate": "⚠️"
        }.get(result["decision"], "❓")
        
        print(f"\n   Actor: {signal.actor_id}")
        print(f"   Risk Score: {signal.risk_score:.2f}")
        print(f"   Decision: {decision_icon} {result['decision'].upper()}")
        print(f"   Confidence: {result['confidence']:.0%}")
        print(f"   Reason: {result['reason']}")


def demo_action_execution():
    """Demonstrate action execution."""
    print("\n⚡ DEMO 4: Action Execution")
    print("-" * 40)
    
    from ai_risk_gatekeeper.models.events import RiskDecision
    
    decisions = [
        RiskDecision(
            actor_id="user_001",
            decision="allow",
            confidence=0.9,
            reason="Normal behavior pattern",
            correlation_id="corr_1",
            decision_timestamp=int(time.time() * 1000)
        ),
        RiskDecision(
            actor_id="user_002",
            decision="throttle",
            confidence=0.7,
            reason="Elevated frequency detected",
            correlation_id="corr_2",
            decision_timestamp=int(time.time() * 1000)
        ),
        RiskDecision(
            actor_id="user_003",
            decision="block",
            confidence=0.95,
            reason="Critical security violation",
            correlation_id="corr_3",
            decision_timestamp=int(time.time() * 1000)
        ),
        RiskDecision(
            actor_id="user_004",
            decision="escalate",
            confidence=0.6,
            reason="Requires human review",
            correlation_id="corr_4",
            decision_timestamp=int(time.time() * 1000)
        ),
    ]
    
    agent = ActionAgent()
    
    print("\n🎯 Executing actions based on decisions...")
    for decision in decisions:
        agent.execute_action(decision)
    
    print(f"\n📊 Action Stats: {agent.stats}")


def main():
    """Run the complete demo."""
    print_banner()
    
    try:
        demo_event_generation()
        time.sleep(1)
        
        demo_signal_processing()
        time.sleep(1)
        
        demo_decision_making()
        time.sleep(1)
        
        demo_action_execution()
        
        print("\n" + "=" * 60)
        print("   🎉 Demo Complete!")
        print("   The AI Risk Gatekeeper is ready for production.")
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
