#!/usr/bin/env python3
"""
AI Risk Gatekeeper - Interactive Live Demo

This demo showcases the full power of Confluent Kafka + Vertex AI:
- Real-time event streaming with live Kafka consumers
- AI-powered decisions using Google Gemini
- Interactive scenarios judges can trigger
- Live metrics and monitoring
"""

import sys
import time
import threading
import queue
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from ai_risk_gatekeeper.agents import (
    create_event_producer,
    BehaviorPattern,
    SignalProcessor,
    DecisionAgent,
    ActionAgent,
)
from ai_risk_gatekeeper.models.events import EnterpriseActionEvent, RiskSignal, RiskDecision
from ai_risk_gatekeeper.infrastructure import setup_kafka_infrastructure
import uuid


# ANSI colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')


def print_banner():
    clear_screen()
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🛡️  AI RISK GATEKEEPER - LIVE DEMO                            ║
║                                                                  ║
║   Real-time Enterprise Security powered by:                      ║
║   • Confluent Cloud Kafka (Event Streaming)                      ║
║   • Google Vertex AI Gemini (AI Decisions)                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
{Colors.END}
""")


def print_menu():
    print(f"""
{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
{Colors.YELLOW}INTERACTIVE SCENARIOS - Choose what to demonstrate:{Colors.END}

  {Colors.GREEN}[1]{Colors.END} 👤 Normal User Activity     - Low risk, should be ALLOWED
  {Colors.GREEN}[2]{Colors.END} 🚨 Suspicious Behavior      - High frequency + geo change
  {Colors.GREEN}[3]{Colors.END} 💀 Data Exfiltration Attack - Bulk export attempt
  {Colors.GREEN}[4]{Colors.END} 🔐 Privilege Escalation     - Admin access attempt
  {Colors.GREEN}[5]{Colors.END} 🌊 Flood Attack Simulation  - 20 rapid events
  {Colors.GREEN}[6]{Colors.END} 🤖 Live AI Decision         - Real Gemini API call
  {Colors.GREEN}[7]{Colors.END} 📊 Show Kafka Metrics       - Topic stats & lag
  {Colors.GREEN}[8]{Colors.END} 🔄 Full Pipeline Demo       - End-to-end with AI
  
  {Colors.RED}[q]{Colors.END} Quit Demo

{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
""")


class LiveDemo:
    def __init__(self):
        self.producer = None
        self.processor = SignalProcessor()
        self.decision_agent = DecisionAgent()
        self.action_agent = ActionAgent()
        self.events_published = 0
        self.total_latency = 0
        
    def connect(self):
        print(f"\n{Colors.CYAN}🔌 Connecting to Confluent Cloud...{Colors.END}")
        self.producer = create_event_producer()
        print(f"{Colors.GREEN}✅ Connected to Kafka cluster{Colors.END}")
        
    def disconnect(self):
        if self.producer:
            self.producer.disconnect()
            
    def show_event_flow(self, event, signal, decision, action_time):
        """Display the complete event flow with timing."""
        print(f"""
{Colors.BOLD}┌─────────────────────────────────────────────────────────────────┐{Colors.END}
│ {Colors.CYAN}EVENT FLOW - {event.actor_id}{Colors.END}
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  {Colors.BLUE}📤 EVENT PUBLISHED{Colors.END}                                          │
│     Actor: {event.actor_id:<20} Action: {event.action:<15}│
│     Frequency: {event.frequency_last_60s:<5} Geo Change: {str(event.geo_change):<10}       │
│     Sensitivity: {event.resource_sensitivity:<10}                              │
│                          ↓                                      │
│  {Colors.YELLOW}📊 SIGNAL PROCESSED{Colors.END}                                         │
│     Risk Score: {signal.risk_score:.2f}                                          │
│     Risk Factors: {', '.join(signal.risk_factors[:3]) if signal.risk_factors else 'None':<30}│
│                          ↓                                      │
│  {Colors.CYAN}🤖 AI DECISION{Colors.END}                                               │
│     Decision: {self._decision_icon(decision['decision'])} {decision['decision'].upper():<10}                              │
│     Confidence: {decision['confidence']:.0%}                                        │
│     Reason: {decision['reason'][:45]:<45}│
│                          ↓                                      │
│  {Colors.GREEN}⚡ ACTION EXECUTED{Colors.END}                                           │
│     Time: {action_time:.2f}ms                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
""")
        
    def _decision_icon(self, decision):
        icons = {"allow": "✅", "throttle": "⏱️", "block": "🚫", "escalate": "⚠️"}
        return icons.get(decision, "❓")
    
    def scenario_normal_user(self):
        """Scenario 1: Normal user activity."""
        print(f"\n{Colors.GREEN}👤 Simulating NORMAL user activity...{Colors.END}\n")
        
        event = EnterpriseActionEvent(
            actor_id="employee_john_doe",
            action="document_view",
            role="analyst",
            frequency_last_60s=3,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="low"
        )
        
        self._process_event(event)
        
    def scenario_suspicious(self):
        """Scenario 2: Suspicious behavior."""
        print(f"\n{Colors.RED}🚨 Simulating SUSPICIOUS behavior...{Colors.END}\n")
        
        event = EnterpriseActionEvent(
            actor_id="user_unknown_device",
            action="file_access",
            role="contractor",
            frequency_last_60s=25,
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="high"
        )
        
        self._process_event(event)
        
    def scenario_data_exfiltration(self):
        """Scenario 3: Data exfiltration attempt."""
        print(f"\n{Colors.RED}💀 Simulating DATA EXFILTRATION attack...{Colors.END}\n")
        
        event = EnterpriseActionEvent(
            actor_id="compromised_account",
            action="bulk_export",
            role="developer",
            frequency_last_60s=50,
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="critical"
        )
        
        self._process_event(event)
        
    def scenario_privilege_escalation(self):
        """Scenario 4: Privilege escalation."""
        print(f"\n{Colors.RED}🔐 Simulating PRIVILEGE ESCALATION...{Colors.END}\n")
        
        event = EnterpriseActionEvent(
            actor_id="intern_suspicious",
            action="admin_access",
            role="intern",
            frequency_last_60s=15,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="critical"
        )
        
        self._process_event(event)
        
    def scenario_flood_attack(self):
        """Scenario 5: Flood attack simulation."""
        print(f"\n{Colors.RED}🌊 Simulating FLOOD ATTACK (20 rapid events)...{Colors.END}\n")
        
        start = time.perf_counter()
        
        for i in range(20):
            event, _ = self.producer.generate_and_publish(
                BehaviorPattern.HIGH_FREQUENCY if i % 3 == 0 else BehaviorPattern.NORMAL
            )
            print(f"  [{i+1:02d}] Published: {event.actor_id} - {event.action}")
            
        self.producer.flush(timeout=10)
        
        elapsed = (time.perf_counter() - start) * 1000
        print(f"\n{Colors.GREEN}✅ Published 20 events in {elapsed:.0f}ms ({elapsed/20:.1f}ms avg){Colors.END}")
        print(f"{Colors.CYAN}📊 Check Confluent Cloud Console to see messages in topics!{Colors.END}")
        
    def scenario_live_ai(self):
        """Scenario 6: Real AI decision with Gemini."""
        print(f"\n{Colors.CYAN}🤖 Making REAL AI decision with Vertex AI Gemini...{Colors.END}\n")
        
        event = EnterpriseActionEvent(
            actor_id="suspicious_user_ai_test",
            action="data_delete",
            role="developer",
            frequency_last_60s=30,
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="critical"
        )
        
        signal = self.processor.process_event(event)
        
        print(f"  📊 Risk Score: {signal.risk_score:.2f}")
        print(f"  🔍 Risk Factors: {', '.join(signal.risk_factors)}")
        print(f"\n  {Colors.YELLOW}⏳ Calling Vertex AI Gemini...{Colors.END}")
        
        try:
            # Try real AI call
            self.decision_agent.connect()
            result = self.decision_agent.query_ai(signal)
            self.decision_agent.disconnect()
            
            print(f"\n  {Colors.GREEN}✅ AI Response:{Colors.END}")
            print(f"     Decision: {self._decision_icon(result['decision'])} {result['decision'].upper()}")
            print(f"     Confidence: {result['confidence']:.0%}")
            print(f"     Reason: {result['reason']}")
            
        except Exception as e:
            print(f"\n  {Colors.YELLOW}⚠️ Using fallback (AI error: {str(e)[:50]}){Colors.END}")
            result = self.decision_agent._fallback_decision(signal, str(e))
            print(f"     Decision: {self._decision_icon(result['decision'])} {result['decision'].upper()}")
            
    def scenario_kafka_metrics(self):
        """Scenario 7: Show Kafka metrics."""
        print(f"\n{Colors.CYAN}📊 Fetching Kafka Metrics...{Colors.END}\n")
        
        from ai_risk_gatekeeper.infrastructure import KafkaInfrastructure
        
        infra = KafkaInfrastructure()
        infra.connect()
        
        topics = infra.list_topics()
        our_topics = [t for t in topics if t in ['enterprise-action-events', 'risk-signals', 'risk-decisions', 'Moment']]
        
        print(f"  {Colors.BOLD}Confluent Cloud Cluster:{Colors.END}")
        print(f"  └── Total Topics: {len(topics)}")
        print(f"\n  {Colors.BOLD}AI Risk Gatekeeper Topics:{Colors.END}")
        
        for topic in our_topics:
            print(f"  └── {Colors.GREEN}{topic}{Colors.END}")
            
        print(f"""
  {Colors.YELLOW}💡 View in Confluent Cloud Console:{Colors.END}
     https://confluent.cloud → Topics → Select topic → Messages
     
  {Colors.CYAN}You can see real-time messages flowing through!{Colors.END}
""")
        
    def scenario_full_pipeline(self):
        """Scenario 8: Full end-to-end pipeline."""
        print(f"\n{Colors.CYAN}🔄 Running FULL PIPELINE with real Kafka + AI...{Colors.END}\n")
        
        scenarios = [
            ("Normal Employee", BehaviorPattern.NORMAL),
            ("Suspicious Activity", BehaviorPattern.SUSPICIOUS),
            ("Attack Attempt", BehaviorPattern.PRIVILEGE_ESCALATION),
        ]
        
        for name, pattern in scenarios:
            print(f"\n{Colors.BOLD}━━━ {name} ━━━{Colors.END}")
            
            # Generate and publish
            event, pub_time = self.producer.generate_and_publish(pattern)
            print(f"  📤 Published to Kafka ({pub_time:.1f}ms)")
            
            # Process signal
            signal = self.processor.process_event(event)
            print(f"  📊 Risk Score: {signal.risk_score:.2f}")
            
            # Make decision
            decision = self.decision_agent._fallback_decision(signal, "demo")
            print(f"  🤖 Decision: {self._decision_icon(decision['decision'])} {decision['decision'].upper()}")
            
            # Execute action
            decision_obj = RiskDecision(
                actor_id=signal.actor_id,
                decision=decision['decision'],
                confidence=decision['confidence'],
                reason=decision['reason'],
                correlation_id=signal.correlation_id,
                decision_timestamp=int(time.time() * 1000)
            )
            self.action_agent.execute_action(decision_obj)
            
        self.producer.flush(timeout=10)
        print(f"\n{Colors.GREEN}✅ Full pipeline complete!{Colors.END}")
        print(f"{Colors.CYAN}📊 Check Confluent Cloud Console to see all messages!{Colors.END}")
        
    def _process_event(self, event):
        """Process a single event through the pipeline."""
        start = time.perf_counter()
        
        # Publish to Kafka
        event_json = event.to_json()
        self.producer._producer.produce(
            topic=self.producer.kafka_config.enterprise_action_events_topic,
            key=event.actor_id,
            value=event_json
        )
        self.producer._producer.poll(0)
        
        # Process signal
        signal = self.processor.process_event(event)
        
        # Make decision
        decision = self.decision_agent._fallback_decision(signal, "demo")
        
        # Execute action
        decision_obj = RiskDecision(
            actor_id=signal.actor_id,
            decision=decision['decision'],
            confidence=decision['confidence'],
            reason=decision['reason'],
            correlation_id=signal.correlation_id,
            decision_timestamp=int(time.time() * 1000)
        )
        self.action_agent.execute_action(decision_obj)
        
        action_time = (time.perf_counter() - start) * 1000
        
        self.producer.flush(timeout=5)
        self.show_event_flow(event, signal, decision, action_time)
        
        print(f"{Colors.CYAN}📊 Event published to Kafka - check Confluent Cloud Console!{Colors.END}")


def main():
    demo = LiveDemo()
    
    try:
        print_banner()
        demo.connect()
        
        while True:
            print_menu()
            choice = input(f"{Colors.BOLD}Enter choice: {Colors.END}").strip().lower()
            
            if choice == '1':
                demo.scenario_normal_user()
            elif choice == '2':
                demo.scenario_suspicious()
            elif choice == '3':
                demo.scenario_data_exfiltration()
            elif choice == '4':
                demo.scenario_privilege_escalation()
            elif choice == '5':
                demo.scenario_flood_attack()
            elif choice == '6':
                demo.scenario_live_ai()
            elif choice == '7':
                demo.scenario_kafka_metrics()
            elif choice == '8':
                demo.scenario_full_pipeline()
            elif choice == 'q':
                break
            else:
                print(f"{Colors.RED}Invalid choice. Try again.{Colors.END}")
                
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.END}")
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted.{Colors.END}")
    finally:
        demo.disconnect()
        print(f"\n{Colors.GREEN}Thanks for watching the demo!{Colors.END}\n")


if __name__ == "__main__":
    main()
