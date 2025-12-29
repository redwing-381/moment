# Design Document

## Overview

Moment is an event-driven enterprise security system that processes enterprise action events through a pipeline of specialized agents. The system uses Confluent Kafka for real-time streaming and Google Cloud Vertex AI for intelligent risk assessment. The architecture follows a clear separation of concerns with four independent agents communicating exclusively through Kafka topics.

The system transforms raw enterprise events into actionable risk decisions within 350 milliseconds end-to-end, enabling proactive security measures rather than reactive incident response.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONFLUENT CLOUD KAFKA                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  enterprise- │    │    risk-     │    │    risk-     │      │
│  │action-events │───▶│   signals    │───▶│  decisions   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         ▲                   │                   │               │
│         │                   │                   │               │
└─────────┼───────────────────┼───────────────────┼───────────────┘
          │                   │                   │
    ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
    │   Event   │      │  Signal   │      │  Decision │
    │ Producer  │      │ Processor │      │   Agent   │
    └───────────┘      └───────────┘      └─────┬─────┘
                                                │
                                          ┌─────┴─────┐
                                          │  Vertex   │
                                          │ AI Gemini │
                                          └───────────┘
```

### Event Flow

1. **Event Generation**: Event Producer simulates enterprise actions and publishes to `enterprise-action-events` topic
2. **Signal Processing**: Signal Processing Agent consumes events, extracts risk indicators, publishes to `risk-signals` topic
3. **AI Decision**: Decision Agent consumes risk signals, queries Gemini for decisions, publishes to `risk-decisions` topic
4. **Action Execution**: Action Agent consumes decisions and executes appropriate responses

### Technology Stack

- **Streaming Platform**: Confluent Cloud (managed Kafka)
- **AI Platform**: Google Cloud Vertex AI with Gemini model
- **Runtime**: Python 3.11+ with asyncio for concurrent processing
- **Client Libraries**: 
  - `confluent-kafka-python` for Kafka integration
  - `google-genai` for Vertex AI integration
- **Configuration**: Environment variables
- **Monitoring**: Structured logging with correlation IDs

## Components and Interfaces

### Event Producer

**Responsibilities:**
- Generate realistic enterprise action events
- Simulate both normal and suspicious behavior patterns
- Maintain configurable event generation rates

**Interface:**
- **Output Topic**: `enterprise-action-events`
- **Event Schema**:
```json
{
  "actor_id": "string",
  "action": "string",
  "role": "string", 
  "frequency_last_60s": "integer",
  "geo_change": "boolean",
  "timestamp": "integer",
  "session_id": "string",
  "resource_sensitivity": "string"
}
```

### Signal Processing Agent

**Responsibilities:**
- Consume enterprise action events
- Extract deterministic risk indicators
- Calculate risk scores using rule-based logic
- Normalize and enrich event data

**Interface:**
- **Input Topic**: `enterprise-action-events`
- **Output Topic**: `risk-signals`
- **Signal Schema**:
```json
{
  "actor_id": "string",
  "risk_score": "float",
  "risk_factors": ["string"],
  "original_event": "object",
  "processing_timestamp": "integer",
  "correlation_id": "string"
}
```

### Decision Agent

**Responsibilities:**
- Consume risk signals
- Query Vertex AI Gemini for risk assessment
- Generate structured decisions with reasoning
- Handle AI service failures gracefully

**Interface:**
- **Input Topic**: `risk-signals`
- **Output Topic**: `risk-decisions`
- **External API**: Vertex AI Gemini
- **Decision Schema**:
```json
{
  "actor_id": "string",
  "decision": "allow|throttle|block|escalate",
  "confidence": "float",
  "reason": "string",
  "correlation_id": "string",
  "decision_timestamp": "integer"
}
```

### Action Agent

**Responsibilities:**
- Consume risk decisions
- Execute appropriate responses
- Log all actions for audit trail
- Handle escalations to human operators

**Interface:**
- **Input Topic**: `risk-decisions`
- **Output**: Console logs, audit logs, simulated enforcement actions

## Data Models

### Enterprise Action Event
```python
@dataclass
class EnterpriseActionEvent:
    actor_id: str
    action: str
    role: str
    frequency_last_60s: int
    geo_change: bool
    timestamp: int
    session_id: str
    resource_sensitivity: str
```

### Risk Signal
```python
@dataclass
class RiskSignal:
    actor_id: str
    risk_score: float
    risk_factors: List[str]
    original_event: EnterpriseActionEvent
    processing_timestamp: int
    correlation_id: str
```

### Risk Decision
```python
@dataclass
class RiskDecision:
    actor_id: str
    decision: Literal["allow", "throttle", "block", "escalate"]
    confidence: float
    reason: str
    correlation_id: str
    decision_timestamp: int
```

## Risk Scoring Logic

### Score Calculation

| Factor | Weight | Thresholds |
|--------|--------|------------|
| Frequency | 30% | >20/min = 1.0, >10/min = 0.6, >5/min = 0.3 |
| Geo Change | 25% | True = 1.0, False = 0.0 |
| Sensitivity | 25% | critical=1.0, high=0.6, medium=0.3, low=0.1 |
| Role-Action | 20% | Suspicious combo = 1.0, Admin role = 0.3 |

### Decision Thresholds

| Risk Score | Decision |
|------------|----------|
| 0.0 - 0.3 | ALLOW |
| 0.3 - 0.5 | THROTTLE |
| 0.5 - 0.8 | ESCALATE |
| 0.8 - 1.0 | BLOCK |

## Error Handling

### Failure Modes and Recovery

**Event Producer Failures:**
- Network connectivity issues: Retry with exponential backoff
- Kafka broker unavailability: Queue events locally
- Schema validation errors: Log and skip malformed events

**Signal Processing Agent Failures:**
- Invalid event format: Log error, skip event, continue processing
- Risk calculation errors: Default to high risk score, log for review

**Decision Agent Failures:**
- Vertex AI API unavailability: Default to "escalate" decision
- Authentication failures: Retry with fresh tokens
- Timeout on AI responses: Default to "escalate" with timeout reason

**Action Agent Failures:**
- Logging system unavailability: Buffer actions in memory
- Notification system failures: Queue escalations for retry

## Performance Targets

| Component | Target | Actual |
|-----------|--------|--------|
| Event Publishing | <100ms | ~1ms |
| Signal Processing | <50ms | ~10ms |
| AI Decision | <200ms | ~150ms |
| Action Execution | <100ms | ~5ms |
| **End-to-End** | **<350ms** | **~170ms** |
