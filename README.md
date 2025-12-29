# 🛡️ Moment

**Real-time AI-powered Enterprise Security Platform**

> Confluent Kafka + Google Vertex AI for sub-100ms risk decisions

## 🌐 Live Demo

**Try it now:** [https://moment-682177088008.asia-south1.run.app](https://moment-682177088008.asia-south1.run.app)

---

## 🎯 What This Does

```
Employee Action → Kafka Stream → AI Analysis → Block/Allow/Escalate
     (10ms)         (50ms)         (100ms)        (10ms)
                                                    
                    Total: <200ms end-to-end
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

### Confluent Stack
- **Kafka**: Real-time event streaming
- **Schema Registry**: Avro serialization
- **ksqlDB**: Windowed aggregations
- **Metrics API**: Cluster monitoring

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
├── web_app.py                # FastAPI entry point
├── ai_risk_gatekeeper/
│   ├── web/                  # FastAPI app, routes, WebSocket
│   ├── agents/               # Event Producer, Signal Processor, Decision Agent
│   ├── config/               # Settings management
│   ├── models/               # Data schemas
│   └── utils/                # Formatters, helpers
├── static/
│   ├── css/                  # Dashboard styles
│   └── js/                   # Dashboard JavaScript
├── templates/                # HTML templates
├── tests/                    # Unit/integration tests
└── docs/                     # Design documentation
```

---

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## 📄 License

MIT
