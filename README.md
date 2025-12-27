# 🛡️ Moment - AI Risk Gatekeeper

**Real-time AI-powered Enterprise Security using Confluent Kafka + Google Vertex AI**

> Transform reactive security into proactive protection with sub-350ms risk decisions

## 🌐 Live Demo

**Try it now:** [https://moment-682177088008.asia-south1.run.app](https://moment-682177088008.asia-south1.run.app)

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
git clone https://github.com/yourusername/moment.git
cd moment

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

### Web Dashboard
```bash
python web_app.py
# Open http://localhost:8080
```

### Terminal Demo
```bash
python hackathon_demo.py
```

### Real-Time Mode
```bash
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

## 🐳 Deployment

### Docker
```bash
docker build -t moment .
docker run -p 8080:8080 --env-file .env moment
```

### Google Cloud Run
```bash
./deploy.sh
```

---

## 📁 Project Structure

```
moment/
├── web_app.py                # FastAPI web dashboard
├── hackathon_demo.py         # Terminal demo
├── run_realtime.py           # Real-time mode
├── Dockerfile                # Container config
├── deploy.sh                 # Cloud Run deployment
├── ai_risk_gatekeeper/
│   ├── agents/               # Event Producer, Signal Processor, Decision Agent
│   ├── config/               # Settings management
│   ├── infrastructure/       # Kafka setup
│   └── models/               # Data schemas
├── tests/                    # Unit/integration tests
└── docs/                     # Design documentation
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

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## 📄 License

MIT
