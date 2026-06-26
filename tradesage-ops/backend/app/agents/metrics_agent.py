"""
TradeSage Ops — Metrics Agent

Specialist agent that analyzes system metrics (CPU, memory, latency, error rate,
throughput) to detect anomalies and correlate with the incident.

In production, this would query Prometheus, Cloud Monitoring, or Datadog.
Here it analyzes the metrics snapshot provided in the alert payload.
"""

import logging
from typing import Dict, Any, Optional
from app.utils.llm import call_gemini
from app.models import AgentInsight

logger = logging.getLogger(__name__)

# Threshold definitions for anomaly detection
THRESHOLDS = {
    "cpu_percent": {"warning": 70, "critical": 90, "unit": "%"},
    "cpu": {"warning": 70, "critical": 90, "unit": "%"},
    "memory_percent": {"warning": 75, "critical": 90, "unit": "%"},
    "memory": {"warning": 75, "critical": 90, "unit": "%"},
    "latency_ms": {"warning": 500, "critical": 2000, "unit": "ms"},
    "latency": {"warning": 500, "critical": 2000, "unit": "ms"},
    "error_rate": {"warning": 1.0, "critical": 5.0, "unit": "%"},
    "active_connections": {"warning": 500, "critical": 1000, "unit": ""},
    "connections": {"warning": 500, "critical": 1000, "unit": ""},
    "throughput_rps": {"warning": None, "critical": None, "unit": "req/s"},  # anomaly = drop
    "disk_usage": {"warning": 80, "critical": 95, "unit": "%"},
}


class MetricsAgent:
    """
    Analyzes system metrics to detect spikes, drops, and anomalous behavior.
    """

    name = "Metrics Agent"

    def analyze(self, metrics: Optional[Dict[str, Any]], service: str) -> AgentInsight:
        """
        Analyze the metrics snapshot for anomalies.

        Args:
            metrics: Key-value dict of metric names to values
            service: Name of the affected service

        Returns:
            AgentInsight with metrics analysis
        """
        if not metrics:
            return AgentInsight(
                agent_name=self.name,
                analysis=f"No metrics data provided for {service}. Unable to perform quantitative analysis.",
                confidence=0.3,
                data_points=["No metrics available"]
            )

        # Run anomaly detection
        anomalies = self._detect_anomalies(metrics)

        metrics_text = "\n".join(f"  {k}: {v}" for k, v in metrics.items())

        prompt = f"""You are an expert SRE metrics analyst. Analyze these metrics from '{service}':

{metrics_text}

Detected anomalies: {anomalies if anomalies else 'None detected against standard thresholds'}

Identify:
1. Which metrics are abnormal and by how much
2. Correlation between metrics (e.g., high CPU + high connections = overload)
3. What the metrics pattern suggests about root cause

Be concise. 3-4 sentences maximum. Focus on the numbers."""

        fallback = self._build_mock_analysis(metrics, service, anomalies)

        analysis = call_gemini(prompt, fallback)

        data_points = [f"{k}: {v}" for k, v in metrics.items()]

        return AgentInsight(
            agent_name=self.name,
            analysis=analysis,
            confidence=0.90 if anomalies else 0.70,
            data_points=data_points
        )

    def _detect_anomalies(self, metrics: Dict[str, Any]) -> list:
        """Detect metrics that exceed warning/critical thresholds."""
        anomalies = []
        for key, value in metrics.items():
            if not isinstance(value, (int, float)):
                continue
            key_lower = key.lower()
            for threshold_key, thresholds in THRESHOLDS.items():
                if threshold_key in key_lower:
                    if thresholds["critical"] and value >= thresholds["critical"]:
                        anomalies.append(f"CRITICAL: {key}={value}{thresholds['unit']} (threshold: {thresholds['critical']})")
                    elif thresholds["warning"] and value >= thresholds["warning"]:
                        anomalies.append(f"WARNING: {key}={value}{thresholds['unit']} (threshold: {thresholds['warning']})")
                    break
        return anomalies

    def _build_mock_analysis(self, metrics: Dict[str, Any], service: str, anomalies: list) -> str:
        """Build a context-aware mock analysis."""
        if anomalies:
            anomaly_summary = "; ".join(anomalies[:3])
            return (
                f"Metrics analysis for {service} reveals significant anomalies: {anomaly_summary}. "
                f"The correlation between these metrics suggests resource exhaustion under load. "
                f"The pattern is consistent with a cascading failure triggered by a dependency bottleneck."
            )
        return (
            f"Metrics for {service} are within normal operating ranges. "
            f"No significant anomalies detected. The issue may be intermittent or originate from a downstream dependency."
        )
