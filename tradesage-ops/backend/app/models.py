"""
TradeSage Ops — Pydantic models for alert ingestion and incident analysis output.

These schemas define the contract between the frontend, the API, and the agent network.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    """Alert severity levels following Prometheus convention."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertInput(BaseModel):
    """
    Incoming alert payload — compatible with Prometheus Alertmanager webhook format.

    Example:
        POST /api/alerts
        {
            "alert_id": "ALT-9021",
            "service": "user-db",
            "severity": "critical",
            "message": "Connection pool exhausted",
            "timestamp": "2026-06-26T10:45:00Z",
            "metrics": {"cpu_percent": 95, "active_connections": 5000, "error_rate": 12.3},
            "logs": [
                "ERROR 10:42:01 Connection timeout after 30s",
                "ERROR 10:42:05 Pool exhausted: 0/100 connections available",
                "WARN  10:42:10 Retry attempt 3/3 failed for replica-2"
            ],
            "labels": {"team": "platform", "env": "production"}
        }
    """
    alert_id: str = Field(..., description="Unique alert identifier")
    service: str = Field(..., description="Name of the originating service")
    severity: Severity = Field(default=Severity.CRITICAL, description="Alert severity")
    message: str = Field(..., description="Human-readable alert description")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp of the alert"
    )
    metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Key-value metrics snapshot (CPU, memory, latency, etc.)"
    )
    logs: Optional[List[str]] = Field(
        default=None,
        description="Recent log lines from the affected service"
    )
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Metadata labels (team, environment, region)"
    )


class AgentInsight(BaseModel):
    """Output from a single specialist agent."""
    agent_name: str = Field(..., description="Name of the agent that produced this insight")
    analysis: str = Field(..., description="The agent's analysis text")
    confidence: float = Field(
        default=0.85,
        ge=0.0, le=1.0,
        description="Agent's confidence in its analysis"
    )
    data_points: Optional[List[str]] = Field(
        default=None,
        description="Key data points the agent used"
    )


class IncidentReport(BaseModel):
    """
    Final incident report produced by the Coordinator Agent.
    This is the primary output of the TradeSage Ops pipeline.
    """
    incident_id: str = Field(..., description="Generated incident identifier")
    incident_summary: str = Field(..., description="One-paragraph executive summary")
    probable_root_cause: str = Field(..., description="Most likely root cause")
    blast_radius: List[str] = Field(
        default_factory=list,
        description="List of affected services"
    )
    blast_radius_narration: str = Field(
        default="",
        description="Human-readable explanation of the impact chain"
    )
    timeline: List[str] = Field(
        default_factory=list,
        description="Chronological list of events leading to the incident"
    )
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Step-by-step runbook actions"
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Overall confidence in the analysis"
    )
    explainability: str = Field(
        default="",
        description="Explanation of the reasoning chain"
    )
    agent_insights: List[AgentInsight] = Field(
        default_factory=list,
        description="Individual contributions from each specialist agent"
    )
    severity: str = Field(default="critical", description="Incident severity")
    status: str = Field(default="analyzing", description="Current incident status")
    estimated_revenue_impact: float = Field(default=0.0, description="Estimated revenue impact in USD/hour")
    evidence: List[str] = Field(default_factory=list, description="Key metrics and logs acting as proof of the root cause")
    next_investigation_steps: List[str] = Field(default_factory=list, description="Recommended next steps for the engineering team")

