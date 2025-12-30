# 🛡️ Moment

**Real-time AI-powered Enterprise Security Platform**

> Built for **AI Partner Catalyst: Accelerate Innovation 2025** Hackathon

[![Live Demo](https://img.shields.io/badge/Live%20Demo-moment--682177088008.asia--south1.run.app-blue?style=for-the-badge)](https://moment-682177088008.asia-south1.run.app)
[![Confluent](https://img.shields.io/badge/Confluent-Kafka%20%7C%20Schema%20Registry%20%7C%20ksqlDB-orange?style=for-the-badge)](https://confluent.cloud)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI%20%7C%20Cloud%20Run-4285F4?style=for-the-badge)](https://cloud.google.com)

---

## 🎯 The Problem

Enterprise security teams face an impossible challenge: **millions of user actions per day**, but traditional SIEM tools are batch-based and reactive. By the time an insider threat is detected, the damage is done.

## 💡 Our Solution

**Moment** processes every enterprise action in real-time through Confluent Kafka, applies AI-powered risk analysis using Google Vertex AI (Gemini), and makes intelligent block/allow decisions in under 100ms.

```
Employee Action → Kafka Stream → AI Analysis → Block/Allow/Escalate
     (10ms)         (50ms)         (40ms)           (instant)
                                                    
                    Total: <100ms end-to-end
```

---

## 🌐 Live Demo

**👉 [https://moment-682177088008.asia-south1.run.app](https://moment-682177088008.asia-south1.run.app)**

### Try These Attack Scenarios:
1. **🕵️ Insider Threat** - Watch privilege escalation get detected
2. **🔐 Brute Force** - See high-frequency login attempts blocked
3. **📤 Data Exfiltration** - Observe bulk downloads with geo anomalies flagged

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONFLUENT CLOUD (Full Stack)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│   │ enterprise-      │    │   risk-signals   │    │  risk-decisions  │     │
│   │ action-events    │───▶│                  │───▶│                  │     │
│   └──────────────────┘    └──────────────────┘    └──────────────────┘     │
│            │                       │                       │               │
│   ┌────────┴────────┐    ┌────────┴────────┐    ┌────────┴────────┐       │
│   │ Schema Registry │    │     ksqlDB      │    │   Metrics API   │       │
│   │   (Avro)        │    │ (Aggregations)  │    │  (Monitoring)   │       │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
          │                        │                        │
    ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐
    │   Event   │           │  Signal   │           │  Decision │
    │ Producer  │           │ Processor │           │   Agent   │
    └───────────┘           └───────────┘           └─────┬─────┘
                                                          │
                                                    ┌─────┴─────┐
                                                    │ Vertex AI │
                                                    │  Gemini   │
                                                    └───────────┘
```

---

## 🔧 Tech Stack

### Confluent Cloud (Full Stack)
| Component | Purpose |
|-----------|---------|
| **Apache Kafka** | Real-time event streaming with 3 topics |
| **Schema Registry** | Avro serialization for data contracts |
| **ksqlDB** | Real-time windowed aggregations (5-min tumbling windows) |
| **Metrics API** | Live cluster monitoring in dashboard |

### Google Cloud
| Component | Purpose |
|-----------|---------|
| **Vertex AI (Gemini 2.5 Flash)** | Intelligent risk decisions with explainability |
| **Cloud Run** | Serverless deployment with auto-scaling |
| **Container Registry** | Docker image storage |
| **Cloud Build** | CI/CD pipeline |

### Application
| Component | Purpose |
|-----------|---------|
| **Python/FastAPI** | High-performance async backend |
| **WebSockets** | Real-time dashboard updates |
| **Chart.js** | Risk trend visualization |
| **Vanilla JS (ES Modules)** | Modular frontend architecture |

---

## 📊 Risk Scoring Algorithm

### Risk Factors
| Factor | Weight | High Risk Trigger |
|--------|--------|-------------------|
| Action Frequency | 30% | >20 actions/min |
| Geo Anomaly | 25% | Location change detected |
| Resource Sensitivity | 25% | Critical/confidential access |
| Role-Action Mismatch | 20% | Suspicious permission combo |

### Decision Matrix
| Risk Score | Decision | Action |
|------------|----------|--------|
| 0.0 - 0.3 | ✅ ALLOW | Normal activity |
| 0.3 - 0.5 | ⏱️ THROTTLE | Rate limit applied |
| 0.5 - 0.8 | ⚠️ ESCALATE | Alert security team |
| 0.8 - 1.0 | 🚫 BLOCK | Immediate prevention |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Confluent Cloud account
- Google Cloud account with Vertex AI enabled

### Installation

```bash
# Clone repository
git clone git@github.com:redwing-381/moment.git
cd moment

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Confluent and Google Cloud credentials
```

### Run Locally

```bash
python web_app.py
# Open http://localhost:8080
```

---

## 🐳 Deployment

### Docker
```bash
docker build -t moment .
docker run -p 8080:8080 --env-file .env moment
```

### Google Cloud Run
```bash
# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/moment

# Deploy
gcloud run deploy moment \
  --image gcr.io/YOUR_PROJECT_ID/moment \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated
```

---

## 📁 Project Structure

```
moment/
├── web_app.py                    # FastAPI entry point
├── ai_risk_gatekeeper/
│   ├── web/                      # FastAPI app, routes, WebSocket
│   │   ├── app.py                # Application factory
│   │   ├── routes.py             # REST API endpoints
│   │   ├── websocket.py          # Real-time WebSocket handler
│   │   └── simulation.py         # Attack scenario simulation
│   ├── agents/
│   │   ├── event_producer.py     # Kafka event generation
│   │   ├── signal_processor.py   # Risk score calculation
│   │   ├── decision_agent.py     # Vertex AI integration
│   │   ├── schema_registry.py    # Avro serialization
│   │   ├── ksqldb_client.py      # ksqlDB queries
│   │   └── confluent_metrics.py  # Metrics API client
│   ├── models/                   # Data schemas
│   └── config/                   # Settings management
├── static/
│   ├── css/dashboard.css         # Design system
│   └── js/modules/               # ES modules (15 files)
├── templates/
│   ├── dashboard.html            # Main dashboard
│   ├── landing.html              # Landing page with 3D globe
│   └── partials/                 # Reusable components
└── tests/                        # Unit/integration tests
```

---

## ✨ Key Features

- **🔴 Real-time Event Stream** - Watch events flow through the pipeline
- **📈 Risk Trend Chart** - Visualize threat landscape over time
- **🏆 Top Risky Actors** - Leaderboard of suspicious users
- **🤖 AI Explanations** - Understand why decisions were made
- **🎭 Attack Scenarios** - Pre-built threat simulations
- **🔔 Audio/Visual Alerts** - Immediate notification on blocks
- **🌙 Dark/Light Mode** - Professional UI with theme toggle
- **📊 Confluent Dashboard** - Live Kafka metrics and ksqlDB data

---

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## 👥 Team

Built with ❤️ for **AI Partner Catalyst: Accelerate Innovation 2025**

---

## 📄 License

MIT
