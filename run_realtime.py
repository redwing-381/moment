#!/usr/bin/env python3
"""
AI Risk Gatekeeper - Real-Time Mode

Runs all agents as independent consumers/producers processing events
through Kafka in real-time. Each agent runs in its own thread.

Usage:
    python run_realtime.py              # Run all agents (consumers only)
    python run_realtime.py --produce    # Also generate test events
    python run_realtime.py --produce --rate 2  # Generate 2 events/second
"""

import sys
import time
import threading
import argparse
import signal
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
from ai_risk_gatekeeper.infrastructure import setup_kafka_infrastructure


# ANSI colors
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


class RealTimeSystem:
    """Manages all agents running in real-time."""
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self.signal_processor = None
        self.decision_agent = None
        self.action_agent = None
        self.producer = None
        self.threads = []
        self.running = False
        
    def start(self):
        """Start all agents."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}🛡️  AI Risk Gatekeeper - Real-Time Mode{Colors.END}\n")
        
        # Verify Kafka connectivity
        print(f"{Colors.YELLOW}Verifying Kafka connectivity...{Colors.END}")
        if not setup_kafka_infrastructure():
            print(f"{Colors.RED}Failed to connect to Kafka!{Colors.END}")
            return False
        print(f"{Colors.GREEN}✅ Kafka connected{Colors.END}\n")
        
        self.running = True
        
        # Start Signal Processor
        print(f"{Colors.CYAN}Starting Signal Processor...{Colors.END}")
        self.signal_processor = SignalProcessor()
        self.signal_processor.connect()
        t1 = threading.Thread(target=self._run_signal_processor, daemon=True)
        t1.start()
        self.threads.append(t1)
        print(f"{Colors.GREEN}✅ Signal Processor running (consuming: enterprise-action-events){Colors.END}")
        
        # Start Decision Agent
        print(f"{Colors.CYAN}Starting Decision Agent...{Colors.END}")
        self.decision_agent = DecisionAgent()
        self.decision_agent.connect()
        t2 = threading.Thread(target=self._run_decision_agent, daemon=True)
        t2.start()
        self.threads.append(t2)
        ai_status = "with Vertex AI" if self.use_ai else "fallback mode"
        print(f"{Colors.GREEN}✅ Decision Agent running ({ai_status}, consuming: risk-signals){Colors.END}")
        
        # Start Action Agent
        print(f"{Colors.CYAN}Starting Action Agent...{Colors.END}")
        self.action_agent = ActionAgent()
        self.action_agent.connect()
        t3 = threading.Thread(target=self._run_action_agent, daemon=True)
        t3.start()
        self.threads.append(t3)
        print(f"{Colors.GREEN}✅ Action Agent running (consuming: risk-decisions){Colors.END}")
        
        print(f"\n{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
        print(f"{Colors.GREEN}All agents running! Waiting for events...{Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.END}")
        print(f"{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}\n")
        
        return True
    
    def _run_signal_processor(self):
        """Run signal processor loop."""
        while self.running:
            try:
                self.signal_processor.run(max_events=1, timeout=0.5)
            except Exception as e:
                if self.running:
                    print(f"{Colors.RED}Signal Processor error: {e}{Colors.END}")
    
    def _run_decision_agent(self):
        """Run decision agent loop."""
        while self.running:
            try:
                self.decision_agent.run(max_signals=1, timeout=0.5)
            except Exception as e:
                if self.running:
                    print(f"{Colors.RED}Decision Agent error: {e}{Colors.END}")
    
    def _run_action_agent(self):
        """Run action agent loop."""
        while self.running:
            try:
                self.action_agent.run(max_decisions=1, timeout=0.5)
            except Exception as e:
                if self.running:
                    print(f"{Colors.RED}Action Agent error: {e}{Colors.END}")
    
    def start_producer(self, rate: float = 1.0, patterns: list = None):
        """Start event producer in a separate thread."""
        print(f"\n{Colors.CYAN}Starting Event Producer (rate: {rate} events/sec)...{Colors.END}")
        self.producer = create_event_producer()
        
        if patterns is None:
            # Mix of normal and suspicious patterns
            patterns = [
                BehaviorPattern.NORMAL,
                BehaviorPattern.NORMAL,
                BehaviorPattern.NORMAL,
                BehaviorPattern.HIGH_FREQUENCY,
                BehaviorPattern.GEO_ANOMALY,
                BehaviorPattern.SUSPICIOUS,
                BehaviorPattern.PRIVILEGE_ESCALATION,
            ]
        
        def produce_loop():
            idx = 0
            while self.running:
                pattern = patterns[idx % len(patterns)]
                event, pub_time = self.producer.generate_and_publish(pattern)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] 📤 Published: {event.actor_id} | {event.action} | freq={event.frequency_last_60s} | geo_change={event.geo_change}")
                
                idx += 1
                time.sleep(1.0 / rate)
            
            self.producer.flush(timeout=5)
        
        t = threading.Thread(target=produce_loop, daemon=True)
        t.start()
        self.threads.append(t)
        print(f"{Colors.GREEN}✅ Event Producer running{Colors.END}\n")
    
    def stop(self):
        """Stop all agents."""
        print(f"\n{Colors.YELLOW}Stopping agents...{Colors.END}")
        self.running = False
        
        if self.signal_processor:
            self.signal_processor.stop()
            self.signal_processor.disconnect()
        
        if self.decision_agent:
            self.decision_agent.stop()
            self.decision_agent.disconnect()
        
        if self.action_agent:
            self.action_agent.stop()
            self.action_agent.disconnect()
        
        if self.producer:
            self.producer.disconnect()
        
        # Wait for threads
        for t in self.threads:
            t.join(timeout=2)
        
        self.print_stats()
        print(f"{Colors.GREEN}All agents stopped.{Colors.END}\n")
    
    def print_stats(self):
        """Print statistics from all agents."""
        print(f"\n{Colors.BOLD}━━━ Statistics ━━━{Colors.END}")
        
        if self.signal_processor:
            stats = self.signal_processor.stats
            print(f"Signal Processor: {stats['events_processed']} processed, {stats['events_failed']} failed")
        
        if self.decision_agent:
            stats = self.decision_agent.stats
            print(f"Decision Agent: {stats['decisions_made']} decisions, {stats['ai_failures']} AI failures")
        
        if self.action_agent:
            stats = self.action_agent.stats
            print(f"Action Agent: {stats['actions_executed']} executed")
            print(f"  ✅ Allows: {stats['allows']}")
            print(f"  ⏱️  Throttles: {stats['throttles']}")
            print(f"  🚫 Blocks: {stats['blocks']}")
            print(f"  ⚠️  Escalations: {stats['escalations']}")


def main():
    parser = argparse.ArgumentParser(description="AI Risk Gatekeeper - Real-Time Mode")
    parser.add_argument("--produce", action="store_true", help="Also generate test events")
    parser.add_argument("--rate", type=float, default=1.0, help="Events per second (default: 1)")
    parser.add_argument("--no-ai", action="store_true", help="Use fallback instead of Vertex AI")
    args = parser.parse_args()
    
    system = RealTimeSystem(use_ai=not args.no_ai)
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        system.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start system
    if not system.start():
        sys.exit(1)
    
    # Optionally start producer
    if args.produce:
        system.start_producer(rate=args.rate)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        system.stop()


if __name__ == "__main__":
    main()
