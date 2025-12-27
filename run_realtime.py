#!/usr/bin/env python3
"""
AI Risk Gatekeeper - Real-Time Mode

Runs all agents as independent Kafka consumers/producers.
Use this for continuous real-time processing.

Usage:
    python run_realtime.py              # Run consumers only
    python run_realtime.py --produce    # Also generate test events
"""

import sys
import time
import threading
import argparse
import signal
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ai_risk_gatekeeper.agents import (
    create_event_producer,
    BehaviorPattern,
    SignalProcessor,
    DecisionAgent,
    ActionAgent,
)
from ai_risk_gatekeeper.infrastructure import setup_kafka_infrastructure

console = Console()


class RealTimeSystem:
    """Manages all agents running in real-time."""
    
    def __init__(self):
        self.signal_processor = None
        self.decision_agent = None
        self.action_agent = None
        self.producer = None
        self.threads = []
        self.running = False
        
    def start(self):
        """Start all agents."""
        console.print(Panel(
            "[bold cyan]🛡️ AI Risk Gatekeeper - Real-Time Mode[/bold cyan]",
            box=box.DOUBLE
        ))
        
        with console.status("[cyan]Connecting to Kafka...[/cyan]"):
            if not setup_kafka_infrastructure():
                console.print("[red]Failed to connect to Kafka![/red]")
                return False
        
        console.print("[green]✓[/green] Kafka connected\n")
        self.running = True
        
        # Start agents
        agents = [
            ("Signal Processor", "enterprise-action-events", self._start_signal_processor),
            ("Decision Agent", "risk-signals", self._start_decision_agent),
            ("Action Agent", "risk-decisions", self._start_action_agent),
        ]
        
        for name, topic, start_fn in agents:
            start_fn()
            console.print(f"[green]✓[/green] {name} running (consuming: {topic})")
        
        console.print("\n[bold green]All agents running![/bold green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        return True
    
    def _start_signal_processor(self):
        self.signal_processor = SignalProcessor()
        self.signal_processor.connect()
        t = threading.Thread(target=self._run_signal_processor, daemon=True)
        t.start()
        self.threads.append(t)
    
    def _start_decision_agent(self):
        self.decision_agent = DecisionAgent()
        self.decision_agent.connect()
        t = threading.Thread(target=self._run_decision_agent, daemon=True)
        t.start()
        self.threads.append(t)
    
    def _start_action_agent(self):
        self.action_agent = ActionAgent()
        self.action_agent.connect()
        t = threading.Thread(target=self._run_action_agent, daemon=True)
        t.start()
        self.threads.append(t)
        
    def _run_signal_processor(self):
        while self.running:
            try:
                self.signal_processor.run(max_events=1, timeout=0.5)
            except Exception as e:
                if self.running:
                    console.print(f"[red]Signal Processor error: {e}[/red]")
    
    def _run_decision_agent(self):
        while self.running:
            try:
                self.decision_agent.run(max_signals=1, timeout=0.5)
            except Exception as e:
                if self.running:
                    console.print(f"[red]Decision Agent error: {e}[/red]")
    
    def _run_action_agent(self):
        while self.running:
            try:
                self.action_agent.run(max_decisions=1, timeout=0.5)
            except Exception as e:
                if self.running:
                    console.print(f"[red]Action Agent error: {e}[/red]")
    
    def start_producer(self, rate: float = 1.0):
        """Start event producer."""
        console.print(f"[cyan]Starting Event Producer ({rate} events/sec)...[/cyan]")
        self.producer = create_event_producer()
        
        patterns = [
            BehaviorPattern.NORMAL,
            BehaviorPattern.NORMAL,
            BehaviorPattern.HIGH_FREQUENCY,
            BehaviorPattern.GEO_ANOMALY,
            BehaviorPattern.SUSPICIOUS,
        ]
        
        def produce_loop():
            idx = 0
            while self.running:
                pattern = patterns[idx % len(patterns)]
                event, _ = self.producer.generate_and_publish(pattern)
                timestamp = datetime.now().strftime("%H:%M:%S")
                console.print(f"[dim]{timestamp}[/dim] 📤 {event.actor_id} | {event.action}")
                idx += 1
                time.sleep(1.0 / rate)
            self.producer.flush(timeout=5)
        
        t = threading.Thread(target=produce_loop, daemon=True)
        t.start()
        self.threads.append(t)
        console.print("[green]✓[/green] Event Producer running\n")
    
    def stop(self):
        """Stop all agents."""
        console.print("\n[yellow]Stopping agents...[/yellow]")
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
        
        for t in self.threads:
            t.join(timeout=2)
        
        self._print_stats()
        console.print("[green]All agents stopped.[/green]\n")
    
    def _print_stats(self):
        """Print statistics."""
        table = Table(title="Statistics", box=box.SIMPLE)
        table.add_column("Agent", style="cyan")
        table.add_column("Processed", justify="right")
        
        if self.signal_processor:
            table.add_row("Signal Processor", str(self.signal_processor.stats["events_processed"]))
        if self.decision_agent:
            table.add_row("Decision Agent", str(self.decision_agent.stats["decisions_made"]))
        if self.action_agent:
            table.add_row("Action Agent", str(self.action_agent.stats["actions_executed"]))
        
        console.print(table)


def main():
    parser = argparse.ArgumentParser(description="AI Risk Gatekeeper - Real-Time Mode")
    parser.add_argument("--produce", action="store_true", help="Generate test events")
    parser.add_argument("--rate", type=float, default=1.0, help="Events per second")
    args = parser.parse_args()
    
    system = RealTimeSystem()
    
    def signal_handler(sig, frame):
        system.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    if not system.start():
        sys.exit(1)
    
    if args.produce:
        system.start_producer(rate=args.rate)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        system.stop()


if __name__ == "__main__":
    main()
