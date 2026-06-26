"""
TradeSage Ops — FastAPI Application

The main API server following the Cloud Run deployment pattern from
the Google Cloud Agent Starter Pack.

Endpoints:
    POST /api/alerts          — Ingest an alert and trigger multi-agent analysis
    GET  /api/alerts/demo     — Trigger a demo alert for testing
    GET  /api/incidents       — List all analyzed incidents
    GET  /api/incidents/{id}  — Get a specific incident report
    GET  /health              — Health check (Cloud Run readiness probe)
"""

import logging
import os
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

from app.models import AlertInput, IncidentReport, Severity
from app.agents.coordinator import CoordinatorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("tradesage-ops")

# ─── Initialize FastAPI ─────────────────────────────────────────────────
app = FastAPI(
    title="TradeSage Ops",
    description="AI-Powered Incident Command Center for DevOps/SRE Teams",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Initialize Agent Network ──────────────────────────────────────────
coordinator = CoordinatorAgent()

# ─── In-memory incident store ──────────────────────────────────────────
incident_store: Dict[str, IncidentReport] = {}


# ─── API Endpoints ─────────────────────────────────────────────────────

@app.post("/api/alerts", response_model=IncidentReport)
async def process_alert(alert: AlertInput):
    """
    Ingest an alert and trigger the multi-agent incident analysis pipeline.

    This is the primary endpoint. It accepts a Prometheus-style alert,
    runs it through the agent network (Logs → Metrics → Dependencies → Runbook),
    and returns a complete incident report.
    """
    logger.info(f"Received alert: {alert.alert_id} for service '{alert.service}'")
    try:
        report = coordinator.process_alert(alert)
        incident_store[report.incident_id] = report
        logger.info(f"Incident {report.incident_id} created with confidence {report.confidence_score}")
        return report
    except Exception as e:
        logger.error(f"Error processing alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")


DEMO_SCENARIOS = {
    "db_outage": AlertInput(
        alert_id="ALT-DB-101",
        service="user-db",
        severity=Severity.CRITICAL,
        message="Database connection timeout — replica set unreachable",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metrics={
            "cpu_percent": 98.2,
            "memory_percent": 88.5,
            "active_connections": 0,
            "error_rate": 100.0,
            "latency_ms": 10000,
        },
        logs=[
            "FATAL: Database replication connection lost",
            "ERROR: Connection timeout after 10s waiting for replica-1",
            "ERROR: Read-only mode fallback failed",
            "CRITICAL: Primary database failed health checks — restarting node",
        ],
        labels={"team": "database", "env": "production", "region": "us-west1"}
    ),
    "redis_failure": AlertInput(
        alert_id="ALT-RED-202",
        service="redis-cache",
        severity=Severity.CRITICAL,
        message="Redis cache cluster OOM — maxmemory limit reached",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metrics={
            "cpu_percent": 85.0,
            "memory_percent": 99.8,
            "active_connections": 12000,
            "error_rate": 45.2,
            "latency_ms": 450,
        },
        logs=[
            "WARNING: Redis memory consumption exceeds maxmemory configuration",
            "FATAL: Redis command failed: OOM command not allowed when used memory > 'maxmemory'",
            "ERROR: Connection reset by peer",
            "ERROR: Cache lookup failed for auth-token-session-key",
        ],
        labels={"team": "platform", "env": "production", "region": "us-east1"}
    ),
    "memory_leak": AlertInput(
        alert_id="ALT-MEM-303",
        service="auth-service",
        severity=Severity.WARNING,
        message="Memory leak detected — RSS memory drifting upwards",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metrics={
            "cpu_percent": 45.5,
            "memory_percent": 94.2,
            "active_connections": 450,
            "error_rate": 2.1,
            "latency_ms": 120,
        },
        logs=[
            "INFO: Garbage collection reclaimed 12MB (total heap 1840MB)",
            "WARN: Heap memory usage approaching max limit (94% consumed)",
            "ERROR: OutOfMemoryError in auth-token-generation-pool",
            "INFO: JVM starting thread dump post OOM event",
        ],
        labels={"team": "security", "env": "staging", "region": "us-central1"}
    ),
    "pod_crash": AlertInput(
        alert_id="ALT-K8S-404",
        service="orders-service",
        severity=Severity.CRITICAL,
        message="Kubernetes pod crash loop back-off — CrashLoopBackOff",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metrics={
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "active_connections": 0,
            "error_rate": 88.0,
            "latency_ms": 0,
        },
        logs=[
            "FATAL: Failed to read configurations from Vault secret path",
            "CRITICAL: App exited with exit code 1",
            "WARNING: Kubelet Liveness probe failed for container orders-service",
            "ERROR: Back-off restarting failed container",
        ],
        labels={"team": "orders", "env": "production", "region": "europe-west1"}
    ),
    "bad_deployment": AlertInput(
        alert_id="ALT-DEP-505",
        service="checkout-api",
        severity=Severity.CRITICAL,
        message="Checkout service failed deployment verification — HTTP 500 Spike",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metrics={
            "cpu_percent": 35.0,
            "memory_percent": 55.0,
            "active_connections": 2200,
            "error_rate": 35.8,
            "latency_ms": 180,
        },
        logs=[
            "INFO: Deployment v2.4.1 initialized",
            "ERROR: Undefined method 'process_payment_v2' for CheckoutController",
            "ERROR: TypeError: Cannot read property 'id' of undefined at Checkout.tsx:42",
            "FATAL: Application startup verification failed, aborting traffic routing",
        ],
        labels={"team": "checkout", "env": "production", "region": "us-east4"}
    ),
    "external_api": AlertInput(
        alert_id="ALT-API-606",
        service="payments-service",
        severity=Severity.CRITICAL,
        message="Stripe API gateway outage — Connection refused by Stripe endpoints",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metrics={
            "cpu_percent": 24.1,
            "memory_percent": 48.0,
            "active_connections": 150,
            "error_rate": 98.5,
            "latency_ms": 5000,
        },
        logs=[
            "WARNING: Delayed response from api.stripe.com (timeout threshold set to 5s)",
            "ERROR: Stripe API connection timeout while finalizing transaction tx_923847",
            "ERROR: Payment confirmation failed downstream",
            "FATAL: Stripe service unreachable — connection refused",
        ],
        labels={"team": "payments", "env": "production", "region": "us-east1"}
    ),
    "high_latency": AlertInput(
        alert_id="ALT-LAT-707",
        service="api-gateway",
        severity=Severity.WARNING,
        message="API Gateway response latency spike — p99 latency > 3500ms",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metrics={
            "cpu_percent": 75.0,
            "memory_percent": 64.0,
            "active_connections": 8500,
            "error_rate": 4.5,
            "latency_ms": 3800,
        },
        logs=[
            "WARN: Request processing time exceeded 3000ms limit for path /api/orders",
            "WARN: Gateway timed out waiting for upstream orders-service response",
            "INFO: Connection pool usage: 98/100 active connections",
            "ERROR: Downstream connection timeout on orders-service, failing open with status 504",
        ],
        labels={"team": "routing", "env": "production", "region": "us-west2"}
    )
}


@app.get("/api/alerts/demo", response_model=IncidentReport)
async def demo_alert(scenario: str = "db_outage"):
    """
    Trigger a demo alert for testing the full pipeline.
    
    Valid scenarios:
    - db_outage
    - redis_failure
    - memory_leak
    - pod_crash
    - bad_deployment
    - external_api
    - high_latency
    """
    if scenario not in DEMO_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario. Choose from: {', '.join(DEMO_SCENARIOS.keys())}"
        )
    
    alert = DEMO_SCENARIOS[scenario]
    # Update timestamp to now
    alert.timestamp = datetime.utcnow().isoformat() + "Z"
    
    report = coordinator.process_alert(alert)
    incident_store[report.incident_id] = report
    return report



@app.get("/api/incidents")
async def list_incidents():
    """List all analyzed incidents."""
    return {
        "count": len(incident_store),
        "incidents": [
            {
                "incident_id": r.incident_id,
                "summary": r.incident_summary,
                "severity": r.severity,
                "confidence": r.confidence_score,
                "status": r.status,
            }
            for r in incident_store.values()
        ]
    }


@app.get("/api/incidents/{incident_id}", response_model=IncidentReport)
async def get_incident(incident_id: str):
    """Get a specific incident report by ID."""
    report = incident_store.get(incident_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return report


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run readiness probes."""
    return {
        "status": "healthy",
        "service": "tradesage-ops",
        "agents": ["logs", "metrics", "dependency", "runbook", "coordinator"],
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


# ─── Serve Frontend Static Files ───────────────────────────────────────
frontend_build_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"

if frontend_build_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_build_dir / "assets")), name="assets")

    @app.get("/", response_model=None)
    async def serve_frontend():
        return FileResponse(str(frontend_build_dir / "index.html"))

    @app.get("/{full_path:path}", response_model=None)
    async def serve_spa(full_path: str):
        if full_path.startswith(("api/", "health")):
            raise HTTPException(status_code=404)
        file_path = frontend_build_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_build_dir / "index.html"))
else:
    @app.get("/", response_class=HTMLResponse)
    async def serve_dev_instructions():
        return """
        <html>
            <head>
                <title>TradeSage Ops Backend</title>
                <style>
                    body {
                        background-color: #0b0f19;
                        color: #f3f4f6;
                        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                        padding: 20px;
                        text-align: center;
                    }
                    .container {
                        max-width: 600px;
                        background-color: #111827;
                        border: 1px solid #1f2937;
                        border-radius: 12px;
                        padding: 30px;
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    }
                    h1 {
                        color: #60a5fa;
                        font-size: 24px;
                        margin-bottom: 15px;
                    }
                    p {
                        color: #9ca3af;
                        font-size: 14px;
                        line-height: 1.5;
                    }
                    code {
                        background-color: #1f2937;
                        color: #f3f4f6;
                        padding: 3px 6px;
                        border-radius: 4px;
                        font-family: monospace;
                        font-size: 13px;
                        border: 1px solid #374151;
                    }
                    .btn {
                        display: inline-block;
                        margin-top: 20px;
                        background-color: #3b82f6;
                        color: white;
                        padding: 10px 20px;
                        border-radius: 6px;
                        text-decoration: none;
                        font-weight: 6px;
                        font-size: 13px;
                    }
                    .btn:hover {
                        background-color: #2563eb;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>TradeSage Ops Backend Active</h1>
                    <p>
                        The backend API is running successfully on port 8080!
                    </p>
                    <p>
                        Since the production frontend build was not found at <code>frontend/dist</code>, the dashboard is not served directly from this port.
                    </p>
                    <hr style="border: 0; border-top: 1px solid #1f2937; margin: 20px 0;" />
                    <div style="text-align: left; font-size: 13px;">
                        <p><strong>To launch the development dashboard:</strong></p>
                        <ol style="color: #9ca3af; padding-left: 20px; line-height: 1.6;">
                            <li>Open a terminal in the project root.</li>
                            <li>Change directory: <code>cd tradesage-ops/frontend</code></li>
                            <li>Run <code>npm run dev</code></li>
                            <li>Open <a href="http://localhost:5173" target="_blank" style="color: #3b82f6; text-decoration: none;">http://localhost:5173</a> in your browser.</li>
                        </ol>
                        
                        <p style="margin-top: 20px;"><strong>Useful API Links:</strong></p>
                        <ul style="color: #9ca3af; padding-left: 20px; line-height: 1.6;">
                            <li>Health Check: <a href="/health" style="color: #3b82f6; text-decoration: none;">/health</a></li>
                            <li>Demo Incident: <a href="/api/alerts/demo?scenario=db_outage" style="color: #3b82f6; text-decoration: none;">/api/alerts/demo?scenario=db_outage</a></li>
                        </ul>
                    </div>
                </div>
            </body>
        </html>
        """


# ─── Main Execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
