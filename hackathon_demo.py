#!/usr/bin/env python3
"""
AI Risk Gatekeeper - Hackathon Demo

Beautiful terminal UI for demonstrating the system to judges.
"""

import sys
import time
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from ai_risk_gatekeeper.agents import (
    create_event_producer,
    BehaviorPattern,
    SignalProcessor,
    DecisionAgent,
    ActionAgent,
)
from ai_risk_gatekeeper.models.events import EnterpriseActionEvent, RiskSignal, RiskDecision

console = Console()


def print_banner():
    """Print the main banner."""
    console.clear()
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║   🛡️  AI RISK GATEKEEPER                                          ║
    ║                                                                   ║
    ║   Real-time Enterprise Security                                   ║
    ║   Powered by Confluent Kafka + Google Vertex AI                   ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="cyan bold", box=box.DOUBLE))


def print_architecture():
    """Print the architecture diagram."""
    arch = """
    ┌─────────────────────────────────────────────────────────────────┐
    │                    CONFLUENT CLOUD KAFKA                        │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │   [enterprise-action-events] → [risk-signals] → [risk-decisions]│
    │            │                        │                │          │
    └────────────┼────────────────────────┼────────────────┼──────────┘
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
    """
    console.print(Panel(arch, title="[bold]Architecture[/bold]", border_style="blue"))


def print_menu():
    """Print the interactive menu."""
    table = Table(show_header=False, box=box.ROUNDED, border_style="yellow")
    table.add_column("Key", style="green bold", width=6)
    table.add_column("Scenario", style="white")
    table.add_column("Expected", style="dim")
    
    table.add_row("1", "👤 Normal User Activity", "→ ALLOW")
    table.add_row("2", "🚨 Suspicious Behavior", "→ THROTTLE")
    table.add_row("3", "💀 Data Exfiltration Attack", "→ BLOCK")
    table.add_row("4", "🔐 Privilege Escalation", "→ ESCALATE")
    table.add_row("5", "🌊 Flood Attack (20 events)", "→ Mixed")
    table.add_row("6", "🤖 Live AI Decision", "→ Real Gemini")
    table.add_row("", "", "")
    table.add_row("q", "Quit Demo", "")
    
    console.print(Panel(table, title="[bold yellow]Select Scenario[/bold yellow]", border_style="yellow"))


def create_event_table(event: EnterpriseActionEvent) -> Table:
    """Create a table showing event details."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Actor", event.actor_id)
    table.add_row("Action", event.action)
    table.add_row("Role", event.role)
    table.add_row("Frequency", f"{event.frequency_last_60s}/min")
    table.add_row("Geo Change", "🌍 Yes" if event.geo_change else "No")
    table.add_row("Sensitivity", event.resource_sensitivity.upper())
    
    return table


def create_signal_table(signal: RiskSignal) -> Table:
    """Create a table showing signal details."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Field", style="yellow")
    table.add_column("Value", style="white")
    
    # Color code risk score
    score = signal.risk_score
    if score >= 0.8:
        score_style = "red bold"
    elif score >= 0.5:
        score_style = "yellow bold"
    else:
        score_style = "green bold"
    
    table.add_row("Risk Score", Text(f"{score:.0%}", style=score_style))
    table.add_row("Risk Factors", ", ".join(signal.risk_factors[:3]) if signal.risk_factors else "None")
    
    return table


def create_decision_panel(decision: dict) -> Panel:
    """Create a panel showing the decision."""
    dec = decision["decision"]
    conf = decision["confidence"]
    reason = decision["reason"]
    
    # Style based on decision
    styles = {
        "allow": ("✅ ALLOW", "green"),
        "throttle": ("⏱️  THROTTLE", "yellow"),
        "block": ("🚫 BLOCK", "red"),
        "escalate": ("⚠️  ESCALATE", "magenta"),
    }
    
    label, color = styles.get(dec, ("❓ UNKNOWN", "white"))
    
    content = f"""
[{color} bold]{label}[/{color} bold]

[dim]Confidence:[/dim] {conf:.0%}
[dim]Reason:[/dim] {reason[:80]}
    """
    
    return Panel(content, title="[bold]AI Decision[/bold]", border_style=color)


class HackathonDemo:
    def __init__(self):
        self.producer = None
        self.processor = SignalProcessor()
        self.decision_agent = DecisionAgent()
        self.action_agent = ActionAgent()
        
    def connect(self):
        """Connect to Kafka."""
        with console.status("[cyan]Connecting to Confluent Cloud...[/cyan]"):
            self.producer = create_event_producer()
            time.sleep(0.5)
        console.print("[green]✓[/green] Connected to Kafka cluster")
        
    def disconnect(self):
        """Disconnect from Kafka."""
        if self.producer:
            self.producer.disconnect()
    
    def run_scenario(self, name: str, event: EnterpriseActionEvent, use_ai: bool = False):
        """Run a single scenario with beautiful output."""
        console.print()
        console.rule(f"[bold]{name}[/bold]", style="cyan")
        console.print()
        
        # Step 1: Show Event
        console.print("[bold blue]📤 STEP 1: Event Published to Kafka[/bold blue]")
        console.print(Panel(create_event_table(event), border_style="blue"))
        
        # Publish to Kafka
        start = time.perf_counter()
        self.producer._producer.produce(
            topic=self.producer.kafka_config.enterprise_action_events_topic,
            key=event.actor_id,
            value=event.to_json()
        )
        self.producer._producer.poll(0)
        pub_time = (time.perf_counter() - start) * 1000
        console.print(f"[dim]Published in {pub_time:.1f}ms[/dim]\n")
        
        time.sleep(0.3)
        
        # Step 2: Show Signal
        console.print("[bold yellow]📊 STEP 2: Risk Signal Processed[/bold yellow]")
        signal = self.processor.process_event(event)
        console.print(Panel(create_signal_table(signal), border_style="yellow"))
        
        time.sleep(0.3)
        
        # Step 3: Show Decision
        console.print("[bold magenta]🤖 STEP 3: AI Decision[/bold magenta]")
        
        if use_ai:
            with console.status("[magenta]Querying Vertex AI Gemini...[/magenta]"):
                try:
                    self.decision_agent.connect()
                    decision = self.decision_agent.query_ai(signal)
                    self.decision_agent.disconnect()
                except Exception as e:
                    decision = self.decision_agent._fallback_decision(signal, str(e))
        else:
            decision = self.decision_agent._fallback_decision(signal, "demo")
        
        console.print(create_decision_panel(decision))
        
        # Step 4: Action
        console.print()
        action_icons = {
            "allow": "[green]✓ Action: Permitted[/green]",
            "throttle": "[yellow]⏱ Action: Rate Limited[/yellow]",
            "block": "[red]✗ Action: Blocked[/red]",
            "escalate": "[magenta]! Action: Sent to Security Team[/magenta]",
        }
        console.print(action_icons.get(decision["decision"], "Action: Unknown"))
        
        self.producer.flush(timeout=5)
        
        # Total time
        total_time = (time.perf_counter() - start) * 1000
        console.print(f"\n[dim]Total pipeline time: {total_time:.0f}ms[/dim]")
        
    def scenario_normal(self):
        """Normal user scenario."""
        event = EnterpriseActionEvent(
            actor_id="john.doe@company.com",
            action="document_view",
            role="analyst",
            frequency_last_60s=3,
            geo_change=False,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="low"
        )
        self.run_scenario("👤 Normal User Activity", event)
        
    def scenario_suspicious(self):
        """Suspicious behavior scenario."""
        event = EnterpriseActionEvent(
            actor_id="unknown_device_user",
            action="file_download",
            role="contractor",
            frequency_last_60s=25,
            geo_change=True,
            timestamp=int(time.time() * 1000),
            session_id=str(uuid.uuid4()),
            resource_sensitivity="high"
        )
        self.run_scenario("🚨 Suspicious Behavior", event)
        
    def scenario_exfiltration(self):
        """Data exfiltration scenario."""
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
        self.run_scenario("💀 Data Exfiltration Attack", event)
        
    def scenario_privilege(self):
        """Privilege escalation scenario."""
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
        self.run_scenario("🔐 Privilege Escalation", event)
        
    def scenario_flood(self):
        """Flood attack scenario."""
        console.print()
        console.rule("[bold]🌊 Flood Attack Simulation[/bold]", style="red")
        console.print()
        
        console.print("[bold]Publishing 20 events rapidly...[/bold]\n")
        
        table = Table(box=box.SIMPLE)
        table.add_column("#", style="dim", width=4)
        table.add_column("Actor", style="cyan")
        table.add_column("Action", style="white")
        table.add_column("Risk", style="yellow")
        table.add_column("Decision", justify="center")
        
        start = time.perf_counter()
        
        patterns = [BehaviorPattern.NORMAL, BehaviorPattern.HIGH_FREQUENCY, BehaviorPattern.SUSPICIOUS]
        
        for i in range(20):
            pattern = patterns[i % 3]
            event, _ = self.producer.generate_and_publish(pattern)
            signal = self.processor.process_event(event)
            decision = self.decision_agent._fallback_decision(signal, "demo")
            
            dec_icons = {"allow": "✅", "throttle": "⏱️", "block": "🚫", "escalate": "⚠️"}
            
            table.add_row(
                str(i + 1),
                event.actor_id[:20],
                event.action,
                f"{signal.risk_score:.0%}",
                dec_icons.get(decision["decision"], "?")
            )
        
        self.producer.flush(timeout=10)
        elapsed = (time.perf_counter() - start) * 1000
        
        console.print(table)
        console.print(f"\n[green bold]✓ 20 events processed in {elapsed:.0f}ms ({elapsed/20:.1f}ms avg)[/green bold]")
        
    def scenario_live_ai(self):
        """Live AI decision scenario."""
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
        self.run_scenario("🤖 Live AI Decision (Real Gemini)", event, use_ai=True)


def main():
    demo = HackathonDemo()
    
    try:
        print_banner()
        print_architecture()
        demo.connect()
        
        while True:
            console.print()
            print_menu()
            
            choice = console.input("\n[bold]Enter choice: [/bold]").strip().lower()
            
            if choice == "1":
                demo.scenario_normal()
            elif choice == "2":
                demo.scenario_suspicious()
            elif choice == "3":
                demo.scenario_exfiltration()
            elif choice == "4":
                demo.scenario_privilege()
            elif choice == "5":
                demo.scenario_flood()
            elif choice == "6":
                demo.scenario_live_ai()
            elif choice == "q":
                break
            else:
                console.print("[red]Invalid choice[/red]")
                continue
            
            console.print()
            console.input("[dim]Press Enter to continue...[/dim]")
            print_banner()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]")
    finally:
        demo.disconnect()
        console.print("\n[green]Thanks for watching! 🎉[/green]\n")


if __name__ == "__main__":
    main()
