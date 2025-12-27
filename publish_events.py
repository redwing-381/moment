#!/usr/bin/env python3
"""
Event Publisher - Send events to Kafka for real-time processing.

Run this in a separate terminal while run_realtime.py is running.

Usage:
    python publish_events.py                    # Publish 10 mixed events
    python publish_events.py --count 50         # Publish 50 events
    python publish_events.py --pattern attack   # Publish attack patterns
    python publish_events.py --continuous       # Keep publishing forever
"""

import sys
import time
import argparse
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from ai_risk_gatekeeper.agents import create_event_producer, BehaviorPattern
from ai_risk_gatekeeper.models.events import EnterpriseActionEvent
import uuid


# ANSI colors
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


PATTERNS = {
    "normal": [BehaviorPattern.NORMAL] * 10,
    "mixed": [
        BehaviorPattern.NORMAL,
        BehaviorPattern.NORMAL,
        BehaviorPattern.NORMAL,
        BehaviorPattern.HIGH_FREQUENCY,
        BehaviorPattern.NORMAL,
        BehaviorPattern.GEO_ANOMALY,
        BehaviorPattern.NORMAL,
        BehaviorPattern.SUSPICIOUS,
        BehaviorPattern.NORMAL,
        BehaviorPattern.PRIVILEGE_ESCALATION,
    ],
    "attack": [
        BehaviorPattern.HIGH_FREQUENCY,
        BehaviorPattern.GEO_ANOMALY,
        BehaviorPattern.SUSPICIOUS,
        BehaviorPattern.PRIVILEGE_ESCALATION,
        BehaviorPattern.HIGH_FREQUENCY,
    ],
    "flood": [BehaviorPattern.HIGH_FREQUENCY] * 20,
}


def publish_custom_event(producer, scenario: str):
    """Publish a custom scenario event."""
    scenarios = {
        "normal": EnterpriseActionEvent(
            actor_id=f"employee_{random.randint(1000, 9999)}",
            action="document_view",
            role="analyst",
            frequency_last_60s=random.randint(1, 5),
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="low"
        ),
        "suspicious": EnterpriseActionEvent(
            actor_id=f"user_{random.randint(1000, 9999)}",
            action="file_access",
            role="contractor",
            frequency_last_60s=random.randint(20, 40),
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="high"
        ),
        "exfiltration": EnterpriseActionEvent(
            actor_id=f"compromised_{random.randint(100, 999)}",
            action="bulk_export",
            role="developer",
            frequency_last_60s=random.randint(40, 60),
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="critical"
        ),
        "privilege": EnterpriseActionEvent(
            actor_id=f"intern_{random.randint(100, 999)}",
            action="admin_access",
            role="intern",
            frequency_last_60s=random.randint(10, 20),
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="critical"
        ),
    }
    
    event = scenarios.get(scenario, scenarios["normal"])
    
    start = time.perf_counter()
    producer._producer.produce(
        topic=producer.kafka_config.enterprise_action_events_topic,
        key=event.actor_id,
        value=event.to_json()
    )
    producer._producer.poll(0)
    pub_time = (time.perf_counter() - start) * 1000
    
    return event, pub_time


def main():
    parser = argparse.ArgumentParser(description="Publish events to Kafka")
    parser.add_argument("--count", type=int, default=10, help="Number of events")
    parser.add_argument("--pattern", choices=list(PATTERNS.keys()), default="mixed", help="Event pattern")
    parser.add_argument("--rate", type=float, default=1.0, help="Events per second")
    parser.add_argument("--continuous", action="store_true", help="Keep publishing forever")
    parser.add_argument("--scenario", choices=["normal", "suspicious", "exfiltration", "privilege"], 
                       help="Publish specific scenario")
    args = parser.parse_args()
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}📤 Event Publisher{Colors.END}\n")
    
    # Connect
    print(f"{Colors.YELLOW}Connecting to Kafka...{Colors.END}")
    producer = create_event_producer()
    print(f"{Colors.GREEN}✅ Connected{Colors.END}\n")
    
    patterns = PATTERNS[args.pattern]
    count = 0
    
    try:
        while True:
            if args.scenario:
                event, pub_time = publish_custom_event(producer, args.scenario)
            else:
                pattern = patterns[count % len(patterns)]
                event, pub_time = producer.generate_and_publish(pattern)
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Color based on risk indicators
            if event.frequency_last_60s > 20 or event.geo_change or event.resource_sensitivity == "critical":
                color = Colors.RED
            elif event.frequency_last_60s > 10 or event.resource_sensitivity == "high":
                color = Colors.YELLOW
            else:
                color = Colors.GREEN
            
            print(f"[{timestamp}] {color}Published:{Colors.END} {event.actor_id} | {event.action} | "
                  f"freq={event.frequency_last_60s} | geo={event.geo_change} | "
                  f"sens={event.resource_sensitivity} ({pub_time:.1f}ms)")
            
            count += 1
            
            if not args.continuous and count >= args.count:
                break
            
            time.sleep(1.0 / args.rate)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.END}")
    finally:
        producer.flush(timeout=5)
        producer.disconnect()
        print(f"\n{Colors.GREEN}Published {count} events{Colors.END}\n")


if __name__ == "__main__":
    main()
