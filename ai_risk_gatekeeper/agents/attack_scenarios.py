"""
Attack Scenario Presets for demo purposes.

Predefined attack patterns that simulate realistic security threats.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ScenarioType(Enum):
    INSIDER_THREAT = "insider_threat"
    BRUTE_FORCE = "brute_force"
    DATA_EXFILTRATION = "data_exfiltration"


@dataclass
class EventConfig:
    """Configuration for a single event in a scenario."""
    action: str
    role: str
    frequency: int
    geo_change: bool
    sensitivity: str
    delay_ms: int = 200
    repeat: int = 1


@dataclass
class AttackScenario:
    """A predefined attack scenario for demonstration."""
    id: str
    name: str
    description: str
    icon: str
    actor_id: str
    events: List[EventConfig] = field(default_factory=list)
    duration_seconds: int = 15
    expected_blocks: int = 0


# Predefined Attack Scenarios
INSIDER_THREAT = AttackScenario(
    id="insider_threat",
    name="Insider Threat",
    description="Employee gradually escalates privileges and downloads sensitive data",
    icon="🕵️",
    actor_id="insider_jane",
    duration_seconds=20,
    expected_blocks=5,
    events=[
        # Phase 1: Normal activity (building trust)
        EventConfig(action="email_send", role="analyst", frequency=2, geo_change=False, sensitivity="low", delay_ms=300),
        EventConfig(action="report_view", role="analyst", frequency=3, geo_change=False, sensitivity="low", delay_ms=300),
        EventConfig(action="dashboard_access", role="analyst", frequency=2, geo_change=False, sensitivity="medium", delay_ms=300),
        # Phase 2: Escalation begins
        EventConfig(action="admin_access", role="analyst", frequency=5, geo_change=False, sensitivity="high", delay_ms=400),
        EventConfig(action="config_change", role="analyst", frequency=8, geo_change=False, sensitivity="high", delay_ms=400),
        # Phase 3: Data access
        EventConfig(action="file_download", role="analyst", frequency=12, geo_change=False, sensitivity="critical", delay_ms=500, repeat=3),
        EventConfig(action="bulk_export", role="analyst", frequency=20, geo_change=False, sensitivity="critical", delay_ms=500, repeat=2),
        # Phase 4: Cover tracks
        EventConfig(action="data_delete", role="admin", frequency=25, geo_change=True, sensitivity="critical", delay_ms=600, repeat=2),
    ]
)

BRUTE_FORCE = AttackScenario(
    id="brute_force",
    name="Brute Force Attack",
    description="High-frequency login attempts from a single source",
    icon="🔨",
    actor_id="attacker_bot",
    duration_seconds=15,
    expected_blocks=8,
    events=[
        # Rapid login attempts
        EventConfig(action="login_attempt", role="unknown", frequency=50, geo_change=False, sensitivity="high", delay_ms=100, repeat=5),
        EventConfig(action="login_attempt", role="unknown", frequency=80, geo_change=False, sensitivity="high", delay_ms=80, repeat=5),
        EventConfig(action="login_attempt", role="unknown", frequency=100, geo_change=False, sensitivity="high", delay_ms=50, repeat=5),
        # Trying different endpoints
        EventConfig(action="api_access", role="unknown", frequency=60, geo_change=False, sensitivity="high", delay_ms=100, repeat=3),
        EventConfig(action="admin_access", role="unknown", frequency=70, geo_change=False, sensitivity="critical", delay_ms=100, repeat=3),
    ]
)

DATA_EXFILTRATION = AttackScenario(
    id="data_exfiltration",
    name="Data Exfiltration",
    description="Bulk data download with geographic anomalies indicating compromised account",
    icon="📤",
    actor_id="compromised_user",
    duration_seconds=18,
    expected_blocks=6,
    events=[
        # Initial access from normal location
        EventConfig(action="file_read", role="developer", frequency=3, geo_change=False, sensitivity="medium", delay_ms=400),
        EventConfig(action="dashboard_access", role="developer", frequency=4, geo_change=False, sensitivity="low", delay_ms=400),
        # Sudden geo change - account compromised!
        EventConfig(action="file_download", role="developer", frequency=15, geo_change=True, sensitivity="high", delay_ms=300, repeat=2),
        EventConfig(action="bulk_export", role="developer", frequency=25, geo_change=True, sensitivity="critical", delay_ms=300, repeat=3),
        # Massive data grab
        EventConfig(action="database_query", role="developer", frequency=40, geo_change=True, sensitivity="critical", delay_ms=200, repeat=3),
        EventConfig(action="file_download", role="developer", frequency=50, geo_change=True, sensitivity="critical", delay_ms=150, repeat=4),
        # Attempting to cover tracks
        EventConfig(action="log_delete", role="admin", frequency=30, geo_change=True, sensitivity="critical", delay_ms=500),
    ]
)


# All scenarios indexed by ID
SCENARIOS = {
    "insider_threat": INSIDER_THREAT,
    "brute_force": BRUTE_FORCE,
    "data_exfiltration": DATA_EXFILTRATION,
}


def get_scenario(scenario_id: str) -> Optional[AttackScenario]:
    """Get a scenario by ID."""
    return SCENARIOS.get(scenario_id)


def get_all_scenarios() -> List[AttackScenario]:
    """Get all available scenarios."""
    return list(SCENARIOS.values())
