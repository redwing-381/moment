# 🛡️ AI Risk Gatekeeper

**Real-time AI-powered Enterprise Security using Confluent Kafka + Google Vertex AI**

> Transform reactive security into proactive protection with sub-350ms risk decisions

---

## 🎯 What This Does

The AI Risk Gatekeeper monitors enterprise actions in real-time and makes instant security decisions:

```
Employee Action → Kafka Stream → AI Analysis → Block/Allow/Escalate
     (10ms)         (50ms)         (200ms)         (100ms)
                                                    
                    Total: <350ms end-to-end
```

---

## 🏗️ Architecture

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

### Agents

| Agent | Role | Input Topic | Output Topic |
|-------|------|-------------|--------------|
| **Event Producer** | Generates enterprise action events | - | `enterprise-action-events` |
| **Signal Processor** | Calculates risk scores & identifies risk factors | `enterprise-action-events` | `risk-signals` |
| **Decision Agent** | AI-powered risk decisions via Vertex AI Gemini | `risk-signals` | `risk-decisions` |
| **Action Agent** | Executes allow/throttle/block/escalate actions | `risk-decisions` | - |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Confluent Cloud account ([sign up free](https://confluent.cloud))
- Google Cloud account with Vertex AI enabled

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-risk-gatekeeper.git
cd ai-risk-gatekeeper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Confluent Cloud and Vertex AI credentials
```

### Configuration

1. **Confluent Cloud Setup:**
   - Create a cluster at https://confluent.cloud
   - Create API keys (Cluster → API Keys → Create Key)
   - Copy bootstrap server, API key, and secret to `.env`

2. **Vertex AI Setup:**
   - Enable Vertex AI API in Google Cloud Console
   - Create a service account with "Vertex AI User" role
   - Download JSON key and set path in `.env`

---

## 🎮 Running the System

### Option 1: Real-Time Mode (Recommended)

Run all agents as independent Kafka consumers/producers:

```bash
# Terminal 1: Start all agents
python run_realtime.py

# Terminal 2: Publish events
python publish_events.py --continuous --rate 2
```

Or run everything together:
```bash
python run_realtime.py --produce --rate 1
```

### Option 2: Interactive Demo

```bash
python live_demo.py
```

Interactive menu with scenarios:
- Normal user activity → ALLOW
- Suspicious behavior → THROTTLE/BLOCK
- Data exfiltration attack → BLOCK
- Privilege escalation → ESCALATE
- Flood attack simulation
- Live AI decision with Vertex AI

### Option 3: Quick Demo

```bash
python demo.py
```

---

## 📊 Risk Scoring

Events are scored based on:

| Factor | Weight | High Risk Indicators |
|--------|--------|---------------------|
| **Frequency** | 30% | >20 actions/minute |
| **Geo Change** | 25% | Location anomaly detected |
| **Sensitivity** | 25% | Critical resource access |
| **Role-Action** | 20% | Suspicious combinations (intern + admin_access) |

### Decision Thresholds

| Risk Score | Decision |
|------------|----------|
| 0.0 - 0.3 | ✅ ALLOW |
| 0.3 - 0.5 | ⏱️ THROTTLE |
| 0.5 - 0.8 | ⚠️ ESCALATE |
| 0.8 - 1.0 | 🚫 BLOCK |

---

## 🤖 AI Integration

**Google Vertex AI Gemini** analyzes risk signals and provides:
- **Decision**: allow / throttle / block / escalate
- **Confidence Score**: 0-100%
- **Reasoning**: Human-readable explanation

Example AI Response:
```json
{
  "decision": "block",
  "confidence": 0.95,
  "reason": "High-frequency bulk export from new geographic location indicates potential data exfiltration attempt"
}
```

---

## 💡 Confluent Features Used

| Feature | How We Use It |
|---------|---------------|
| **Kafka Topics** | 3 topics for event pipeline |
| **Partitioning** | Events partitioned by actor_id for ordering |
| **SASL/SSL** | Secure authentication to Confluent Cloud |
| **Consumer Groups** | Each agent has its own consumer group |
| **Exactly-Once** | Acks=all for reliable delivery |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=ai_risk_gatekeeper
```

31 tests covering:
- Configuration management
- Data models and serialization
- Risk scoring logic
- Agent integration

---

## 📁 Project Structure

```
ai-risk-gatekeeper/
├── run_realtime.py           # Real-time mode runner
├── publish_events.py         # Event publisher CLI
├── live_demo.py              # Interactive demo
├── demo.py                   # Quick demo
├── ai_risk_gatekeeper/
│   ├── agents/
│   │   ├── event_producer.py    # Generates events → Kafka
│   │   ├── signal_processor.py  # Calculates risk scores
│   │   ├── decision_agent.py    # AI-powered decisions
│   │   └── action_agent.py      # Executes responses
│   ├── infrastructure/
│   │   └── kafka_setup.py       # Topic management
│   ├── models/
│   │   └── events.py            # Data schemas
│   └── config/
│       └── settings.py          # Configuration
├── tests/                       # Unit & integration tests
├── .env.example                 # Environment template
└── requirements.txt             # Dependencies
```

---

## 📈 Performance

| Component | Target | Actual |
|-----------|--------|--------|
| Event Publishing | <100ms | ~1ms |
| Signal Processing | <50ms | ~10ms |
| AI Decision | <200ms | ~150ms |
| Action Execution | <100ms | ~5ms |
| **End-to-End** | **<350ms** | **~170ms** |

---

## 🔗 Links

- **Confluent Cloud Console**: https://confluent.cloud
- **Vertex AI Console**: https://console.cloud.google.com/vertex-ai
- **Confluent Kafka Python**: https://docs.confluent.io/kafka-clients/python/current/overview.html

---

## 📄 License

MIT
