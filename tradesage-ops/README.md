# TradeSage Ops — AI SRE Incident Command Center

TradeSage Ops is a production-quality, multi-agent AI incident response command center built with Google's **Agent Development Kit (ADK)**, **Gemini 2.5 Flash**, **Vertex AI**, and **Google Cloud Run**.

It automates site reliability engineering (SRE) workflows by acting as an **Incident Commander (Coordinator Agent)** that dispatches telemetry payloads to five dedicated specialist sub-agents, aggregates their findings, computes financial impacts, isolates blast radiuses, and synthesizes a step-by-step recovery runbook.

---

## 🏗️ Architecture

TradeSage Ops leverages a modular hierarchical agent layout. When a monitoring system triggers an alert, it is ingested by the FastAPI backend and sent to the **Coordinator Agent** (Incident Commander).

```
                      +---------------------------------------+
                      |         Alert Ingestion Portal        |
                      |        (FastAPI /api/alerts)          |
                      +-------------------+-------------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      |      Coordinator Agent (Commander)     |
                      +-------------------+-------------------+
                                          |
        +------------------+--------------+------------+-----------------+
        |                  |              |            |                 |
        v                  v              v            v                 v
+-------+------+   +-------+------+   +---+---+   +----+-----+   +-------+------+
|  Logs Agent  |   |Metrics Agent |   |Deps   |   |Timeline  |   |Runbook Agent |
| (Log Errors) |   | (CPU/Mem/Lat)|   |Agent  |   |  Agent   |   | (Recovery KB)|
+-------+------+   +-------+------+   +---+---+   +----+-----+   +-------+------+
        |                  |              |            |                 |
        +------------------+--------------+------------+-----------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      |       Coordinator Synthesis Panel     |
                      |   Calculates revenue impact, evidence,|
                      |      and aggregates final report      |
                      +-------------------+-------------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      |   Futuristic Enterprise SRE Portal    |
                      |       (Vite / React / Tailwind)       |
                      +---------------------------------------+
```

### The Specialist Agents
1. **Logs Agent**: Analyzes service logs, detects error clusters and exceptions, patterns, and outputs a confidence score.
2. **Metrics Agent**: Inspects CPU, Memory, Latency, Error Rate, and Connection spikes against thresholds to isolate bottlenecks.
3. **Dependency Agent**: Queries the microservices dependency graph, calculates downstream cascading impacts, and maps the blast radius.
4. **Timeline Agent**: Synthesizes logs, alerts, metrics, and deployment history to reconstruct a chronological event story.
5. **Runbook Agent**: Searches operational documentation / recovery knowledge bases to output step-by-step mitigation commands.

---

## 📂 Project Structure

```
tradesage-ops/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── __init__.py          # Exports all SRE agents
│   │   │   ├── coordinator.py       # Orchestrator (Incident Commander)
│   │   │   ├── dependency_agent.py  # Service graph & blast radius mapper
│   │   │   ├── logs_agent.py        # System log parser
│   │   │   ├── metrics_agent.py     # CPU/Mem threshold analyzer
│   │   │   ├── runbook_agent.py     # Step-by-step mitigation plans
│   │   │   └── timeline_agent.py    # Event sequences reconstruction
│   │   ├── utils/
│   │   │   └── llm.py               # Gemini 2.5 Flash GenAI integrations
│   │   └── models.py                # Pydantic schemas for data validation
│   ├── main.py                      # FastAPI App entrypoint & demo scenarios
│   ├── requirements.txt             # Python dependencies (google-genai, fastapi)
│   └── Dockerfile                   # Cloud Run container definition
└── frontend/
    ├── src/
    │   ├── App.tsx                  # SRE Control Center Dashboard UI
    │   ├── index.css                # Custom layouts & CSS classes
    │   └── main.tsx                 # Vite mounting
    ├── tailwind.config.js           # Custom futuristic dark mode theme colors
    ├── vite.config.ts               # SPA routing & API proxy setup
    └── package.json                 # Node dependencies (Framer Motion, Lucide)
```

---

## ⚡ Local Development

### 1. Backend Setup
Make sure you have python 3.10+ installed.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set your Gemini API Key (Optional: if not set, the platform will use pre-cached, intelligent mock data fallbacks, ensuring all 7 scenarios render completely):
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

Start the FastAPI app:
```bash
python main.py
```
*Backend will run at `http://localhost:8080`.*

### 2. Frontend Setup
In a new terminal window:

```bash
cd frontend
npm install
npm run dev
```
*Vite dev server will launch at `http://localhost:5173`. Any API calls to `/api` are automatically proxied to the backend at `http://localhost:8080`.*

---

## 🚀 Google Cloud Run Deployment

TradeSage Ops is fully compatible with Google Cloud Run. Follow these simple commands to containerize and host.

### 1. Build and push backend image to Artifact Registry
Ensure you have created a repository in Artifact Registry:
```bash
# Create artifact registry repo
gcloud artifacts repositories create tradesage-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="TradeSage Ops Docker Repo"

# Authenticate docker
gcloud auth configure-docker us-central1-docker.pkg.dev
```

Build and push backend container:
```bash
cd backend
docker build -t us-central1-docker.pkg.dev/$(gcloud config get-value project)/tradesage-repo/backend:latest .
docker push us-central1-docker.pkg.dev/$(gcloud config get-value project)/tradesage-repo/backend:latest
```

### 2. Build Frontend Production SPA
The FastAPI backend is set up to automatically host the static production-built frontend assets from `frontend/dist` directory if present.

Build your frontend:
```bash
cd frontend
npm run build
```

Then, copy the `dist` folder directly to the backend to package them into one unified service container:
```bash
cp -r dist ../backend/frontend/
```

Now rebuild the backend Docker image containing both:
```bash
cd ../backend
docker build -t us-central1-docker.pkg.dev/$(gcloud config get-value project)/tradesage-repo/tradesage-ops:latest .
docker push us-central1-docker.pkg.dev/$(gcloud config get-value project)/tradesage-repo/tradesage-ops:latest
```

### 3. Deploy to Cloud Run
Deploy the single-package container to Cloud Run and mount the Gemini API Key secret:

```bash
gcloud run deploy tradesage-ops \
    --image=us-central1-docker.pkg.dev/$(gcloud config get-value project)/tradesage-repo/tradesage-ops:latest \
    --platform=managed \
    --region=us-central1 \
    --allow-unauthenticated \
    --set-env-vars="GEMINI_API_KEY=your-api-key"
```

---

## 📊 Predefined Incident Scenarios
Use the left sidebar on the dashboard to test the following 7 SRE scenarios:
1. **Database Outage**: Primary connection timeout; replica set unreachable.
2. **Redis Cache Failure**: OOM conditions preventing auth token writes.
3. **Memory Leak**: Auth service JVM heap drifting continuously.
4. **Kubernetes Pod Crash**: Orders-service CrashLoopBackOff.
5. **Bad Deployment**: HTTP 500 error spike post release v2.4.1.
6. **External API Outage**: Payment gateway endpoint timeouts (Stripe API down).
7. **High Latency Spike**: API gateway timeout cascade.
