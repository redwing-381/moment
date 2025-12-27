# 🛡️ AI Risk Gatekeeper

**Real-time AI-powered Enterprise Security using Confluent Kafka + Google Vertex AI**

> Transform reactive security into proactive protection with sub-350ms risk decisions

---

## 🎯 What This Does

```
Employee Action → Kafka Stream → AI Analysis → Block/Allow/Escalate
     (10ms)         (50ms)         (200ms)         (100ms)
                                                    
                    Total: <350ms end-to-end
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Confluent Cloud account
- Google Cloud account with Vertex AI enabled

### Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/ai-risk-gatekeeper.git
cd ai-risk-gatekeeper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your credentials
```

---

## 🎮 Running

### Hackathon Demo (Recommended)
```bash
python hackathon_demo.py
```
Beautiful interactive demo with scenarios:
- 👤 Normal User → ALLOW
- 💀 Data Exfiltration → BLOCK
- 🤖 Live AI Decision with Gemini
- 🌊 Flood Attack (20 events)

### Real-Time Mode
```bash
# Run all agents as Kafka consumers
python run_realtime.py

# Also generate test events
python run_realtime.py --produce --rate 2
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONFLUENT CLOUD KAFKA                        │
├─────────────────────────────────────────────────────────────────┤
│  [enterprise-action-events] → [risk-signals] → [risk-decisions] │
└─────────────────────────────────────────────────────────────────┘
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
```

---

## 📊 Risk Scoring

| Factor | Weight | High Risk |
|--------|--------|-----------|
| Frequency | 30% | >20/min |
| Geo Change | 25% | Location anomaly |
| Sensitivity | 25% | Critical resource |
| Role-Action | 20% | Suspicious combo |

| Risk Score | Decision |
|------------|----------|
| 0.0 - 0.3 | ✅ ALLOW |
| 0.3 - 0.5 | ⏱️ THROTTLE |
| 0.5 - 0.8 | ⚠️ ESCALATE |
| 0.8 - 1.0 | 🚫 BLOCK |

---

## 🧪 Testing

```bash
pytest tests/ -v
# 31 tests passing
```

---

## 📁 Project Structure

```
ai-risk-gatekeeper/
├── hackathon_demo.py         # Interactive demo
├── run_realtime.py           # Real-time mode
├── ai_risk_gatekeeper/
│   ├── agents/               # Event Producer, Signal Processor, Decision Agent, Action Agent
│   ├── config/               # Settings management
│   ├── infrastructure/       # Kafka setup
│   └── models/               # Data schemas
├── tests/                    # 31 unit/integration tests
├── docs/                     # Requirements & Design docs
└── .env.example              # Configuration template
```

---

## 📈 Performance

| Component | Target | Actual |
|-----------|--------|--------|
| Event Publishing | <100ms | ~1ms |
| Signal Processing | <50ms | ~10ms |
| AI Decision | <200ms | ~150ms |
| **End-to-End** | **<350ms** | **~170ms** |

---

## 📄 License

MIT
