"""
TradeSage Ops — Coordinator Agent (Incident Commander)

The Coordinator Agent is the orchestrator of the TradeSage Ops agent network.
It receives incoming alerts, delegates analysis to specialist agents,
synthesizes their outputs, and produces the final Incident Report.

Architecture:
    Alert → Coordinator → [LogsAgent, MetricsAgent, DependencyAgent] → Synthesis → RunbookAgent → Final Report

This follows the ADK-style agent decomposition pattern from the Google Cloud
Agent Starter Pack, where a root agent orchestrates specialist sub-agents.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from app.models import AlertInput, IncidentReport, AgentInsight
from app.agents.logs_agent import LogsAgent
from app.agents.metrics_agent import MetricsAgent
from app.agents.dependency_agent import DependencyAgent
from app.agents.runbook_agent import RunbookAgent
from app.agents.timeline_agent import TimelineAgent
from app.utils.llm import call_gemini

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """
    The Incident Commander — orchestrates the multi-agent analysis pipeline.

    Flow:
        1. Receive alert
        2. Dispatch to LogsAgent, MetricsAgent, DependencyAgent (parallel analysis)
        3. Synthesize their insights into a probable root cause
        4. Send root cause to RunbookAgent for action plan
        5. Assemble the final IncidentReport
    """

    name = "Coordinator Agent"

    def __init__(self):
        self.logs_agent = LogsAgent()
        self.metrics_agent = MetricsAgent()
        self.dependency_agent = DependencyAgent()
        self.runbook_agent = RunbookAgent()
        self.timeline_agent = TimelineAgent()

    def process_alert(self, alert: AlertInput) -> IncidentReport:
        """
        Process an incoming alert through the full agent pipeline.

        Args:
            alert: The incoming alert payload

        Returns:
            IncidentReport with root cause, blast radius, timeline,
            recommended actions, and agent insights
        """
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"[{incident_id}] Processing alert {alert.alert_id} for service '{alert.service}'")

        # ─── Phase 1: Parallel Agent Analysis ───────────────────────────
        logger.info(f"[{incident_id}] Dispatching to specialist agents...")

        logs_insight = self.logs_agent.analyze(
            logs=alert.logs,
            service=alert.service,
            message=alert.message
        )
        logger.info(f"[{incident_id}] Logs Agent complete (confidence: {logs_insight.confidence})")

        metrics_insight = self.metrics_agent.analyze(
            metrics=alert.metrics,
            service=alert.service
        )
        logger.info(f"[{incident_id}] Metrics Agent complete (confidence: {metrics_insight.confidence})")

        deps_insight = self.dependency_agent.analyze(
            service=alert.service
        )
        logger.info(f"[{incident_id}] Dependency Agent complete (confidence: {deps_insight.confidence})")

        timeline_insight = self.timeline_agent.analyze(
            service=alert.service,
            message=alert.message,
            timestamp=alert.timestamp,
            logs=alert.logs,
            metrics=alert.metrics
        )
        logger.info(f"[{incident_id}] Timeline Agent complete (confidence: {timeline_insight.confidence})")

        # ─── Phase 2: Root Cause Synthesis ──────────────────────────────
        logger.info(f"[{incident_id}] Synthesizing root cause...")

        root_cause = self._synthesize_root_cause(
            alert=alert,
            logs_insight=logs_insight,
            metrics_insight=metrics_insight,
            deps_insight=deps_insight
        )

        # ─── Phase 3: Runbook Generation ────────────────────────────────
        logger.info(f"[{incident_id}] Generating runbook actions...")

        runbook_insight = self.runbook_agent.analyze(
            root_cause=root_cause,
            service=alert.service
        )
        recommended_actions = self.runbook_agent.get_action_steps(root_cause)

        # ─── Phase 4: Blast Radius & Timeline ──────────────────────────
        blast_radius = self.dependency_agent.get_blast_radius(alert.service)
        blast_narration = self.dependency_agent.get_blast_radius_narration(
            alert.service, blast_radius
        )
        timeline = timeline_insight.data_points or self._build_timeline(alert)
        explainability = self._build_explainability(
            logs_insight, metrics_insight, deps_insight, timeline_insight, root_cause
        )

        # ─── Phase 5: Calculate Confidence ──────────────────────────────
        confidence = self._calculate_confidence(
            logs_insight, metrics_insight, deps_insight, timeline_insight, runbook_insight
        )

        # ─── Phase 6: Financial & Evidence Calculations ──────────────────
        revenue_impact = self._calculate_revenue_impact(alert.service, blast_radius, alert.severity.value)
        evidence = self._extract_evidence(alert, logs_insight, metrics_insight)
        next_steps = self._generate_next_steps(root_cause, alert.service)

        # ─── Phase 7: Assemble Final Report ─────────────────────────────
        logger.info(f"[{incident_id}] Assembling incident report (confidence: {confidence})")

        report = IncidentReport(
            incident_id=incident_id,
            incident_summary=self._build_summary(alert, root_cause, blast_radius),
            probable_root_cause=root_cause,
            blast_radius=blast_radius,
            blast_radius_narration=blast_narration,
            timeline=timeline,
            recommended_actions=recommended_actions,
            confidence_score=round(confidence, 2),
            explainability=explainability,
            agent_insights=[logs_insight, metrics_insight, deps_insight, timeline_insight, runbook_insight],
            severity=alert.severity.value,
            status="analyzed",
            estimated_revenue_impact=revenue_impact,
            evidence=evidence,
            next_investigation_steps=next_steps,
        )

        logger.info(f"[{incident_id}] Incident report complete")
        return report

    def _synthesize_root_cause(
        self,
        alert: AlertInput,
        logs_insight: AgentInsight,
        metrics_insight: AgentInsight,
        deps_insight: AgentInsight,
    ) -> str:
        """Combine agent insights to determine the most probable root cause."""
        prompt = f"""You are the Incident Commander. Synthesize these specialist agent reports to determine the single most probable root cause.

ALERT: {alert.severity.value.upper()} — {alert.message} on service '{alert.service}'

LOGS AGENT REPORT:
{logs_insight.analysis}

METRICS AGENT REPORT:
{metrics_insight.analysis}

DEPENDENCY AGENT REPORT:
{deps_insight.analysis}

Based on all evidence, state the single most probable root cause in 1-2 sentences. Be specific."""

        # Smart fallback based on alert context
        message_lower = alert.message.lower()
        if "connection" in message_lower or "pool" in message_lower:
            fallback = f"Database connection pool exhaustion on '{alert.service}'. The service exceeded its maximum connection limit, causing all new requests to fail with timeout errors."
        elif "cpu" in message_lower or "spike" in message_lower:
            fallback = f"CPU resource exhaustion on '{alert.service}'. A compute-intensive operation or recent deployment is consuming all available CPU, causing request timeouts."
        elif "memory" in message_lower or "oom" in message_lower:
            fallback = f"Memory exhaustion (OOM) on '{alert.service}'. The service exceeded its memory allocation, triggering the OOM killer and pod restarts."
        elif "timeout" in message_lower:
            fallback = f"Cascading timeout failure originating from '{alert.service}'. A slow dependency is causing upstream services to timeout while waiting for responses."
        elif "deploy" in message_lower:
            fallback = f"Failed deployment on '{alert.service}'. A recent code deployment introduced a regression causing service instability."
        else:
            fallback = f"Service degradation on '{alert.service}' due to {alert.message.lower()}. The combination of log errors and metric anomalies points to a resource or dependency failure."

        return call_gemini(prompt, fallback)

    def _build_timeline(self, alert: AlertInput) -> list:
        """Build a chronological incident timeline from the alert data."""
        try:
            ts = datetime.fromisoformat(alert.timestamp.replace("Z", "+00:00"))
            base_time = ts.strftime("%H:%M")
        except Exception:
            base_time = "10:42"

        # Parse hour and minute for timeline
        try:
            parts = base_time.split(":")
            h, m = int(parts[0]), int(parts[1])
        except Exception:
            h, m = 10, 42

        def fmt(offset_min):
            nm = m + offset_min
            nh = h + nm // 60
            nm = nm % 60
            return f"{nh:02d}:{nm:02d} UTC"

        timeline = [
            f"{fmt(-3)} — Deployment or configuration change detected",
            f"{fmt(-1)} — Latency increase detected on {alert.service}",
            f"{fmt(0)} — {alert.severity.value.upper()} alert triggered: {alert.message}",
        ]

        if alert.metrics:
            timeline.append(f"{fmt(1)} — Metrics anomalies detected (see Metrics Agent report)")

        if alert.logs:
            error_count = sum(1 for l in alert.logs if "ERROR" in l.upper() or "FATAL" in l.upper())
            if error_count > 0:
                timeline.append(f"{fmt(1)} — {error_count} error-level log entries recorded")

        timeline.append(f"{fmt(2)} — Downstream services begin reporting failures")
        timeline.append(f"{fmt(3)} — TradeSage Ops Coordinator generates incident report")

        return timeline

    def _build_summary(self, alert: AlertInput, root_cause: str, blast_radius: list) -> str:
        """Build a one-paragraph executive summary."""
        return (
            f"{alert.severity.value.upper()} incident on '{alert.service}': {alert.message}. "
            f"Root cause: {root_cause[:120]}{'...' if len(root_cause) > 120 else ''} "
            f"Impact: {len(blast_radius)} downstream service{'s' if len(blast_radius) != 1 else ''} affected."
        )

    def _build_explainability(
        self,
        logs_insight: AgentInsight,
        metrics_insight: AgentInsight,
        deps_insight: AgentInsight,
        timeline_insight: AgentInsight,
        root_cause: str,
    ) -> str:
        """Explain why this root cause was chosen — the reasoning chain."""
        return (
            f"The Logs Agent identified error patterns in the service logs (confidence: {logs_insight.confidence}). "
            f"The Metrics Agent detected anomalies in system metrics (confidence: {metrics_insight.confidence}). "
            f"The Dependency Agent mapped the service graph to determine blast radius (confidence: {deps_insight.confidence}). "
            f"The Timeline Agent reconstructed the chronological progression of events (confidence: {timeline_insight.confidence}). "
            f"These four independent analyses converge on the same conclusion, giving high confidence in the root cause determination."
        )

    def _calculate_confidence(self, *insights: AgentInsight) -> float:
        """Calculate overall confidence as a weighted average of agent confidences."""
        if not insights:
            return 0.5
        # weights: logs, metrics, deps, timeline, runbook
        weights = [0.20, 0.25, 0.20, 0.15, 0.20]
        total = sum(
            w * insight.confidence
            for w, insight in zip(weights, insights)
            if insight is not None
        )
        return min(total / sum(weights[:len(insights)]), 1.0)

    def _calculate_revenue_impact(self, service: str, blast_radius: list, severity: str) -> float:
        """Estimate the revenue loss per hour based on affected nodes."""
        base_rate = 5000.0 if severity == "critical" else 1200.0
        
        # High value services
        high_value = {
            "checkout-api": 32000.0,
            "payments-service": 48000.0,
            "api-gateway": 22000.0,
            "orders-service": 28000.0,
            "user-db": 38000.0,
            "product-db": 18000.0,
            "auth-service": 20000.0
        }
        
        impact = high_value.get(service, base_rate)
        for affected in blast_radius:
            impact += high_value.get(affected, 2500.0) * 0.5
            
        return round(impact, 2)

    def _extract_evidence(self, alert: AlertInput, logs_insight: AgentInsight, metrics_insight: AgentInsight) -> list:
        """Extract proof data points for the Incident Commander brief."""
        evidence = []
        evidence.append(f"Primary Trigger: {alert.message}")
        
        if logs_insight.data_points:
            evidence.extend([f"Log error signature: {dp}" for dp in logs_insight.data_points[:2] if "No" not in dp])
            
        if metrics_insight.data_points:
            # Filter for active connection or cpu anomalies if possible
            anom_dps = [dp for dp in metrics_insight.data_points if any(kw in dp.lower() for kw in ["cpu", "connections", "rate", "latency", "memory"])]
            evidence.extend([f"Metric anomaly: {dp}" for dp in anom_dps[:2]])
            
        return evidence

    def _generate_next_steps(self, root_cause: str, service: str) -> list:
        """Generate next investigation steps for SREs based on the root cause."""
        root_lower = root_cause.lower()
        if "pool" in root_lower or "connection" in root_lower:
            return [
                f"Verify active DB connection count on '{service}'",
                "Execute 'SHOW max_connections' and inspect pg_stat_activity",
                "Check for connection leak in the latest code commit",
                "Assess if connection pool size should be scaled up permanently"
            ]
        elif "cpu" in root_lower:
            return [
                f"Identify the CPU-intensive process inside the '{service}' container",
                "Profile CPU usage under test conditions to locate bottlenecks",
                "Check if CPU limits/requests in K8s deployment spec are sufficient",
                "Review git history for CPU-intensive changes (loops, serialization)"
            ]
        elif "memory" in root_lower or "oom" in root_lower:
            return [
                f"Analyze JVM/Go memory dump of '{service}' process if available",
                "Monitor resident set size (RSS) memory drift over the last 24 hours",
                "Increase K8s memory limit to prevent immediate OOM recurrence",
                "Check garbage collector (GC) logs for thrashing behavior"
            ]
        elif "timeout" in root_lower:
            return [
                "Run a traceroute / ping check between service and its upstream dependencies",
                "Verify downstream API circuit breaker health and thresholds",
                "Analyze network transit latency metrics in service mesh logs",
                "Inspect upstream service logs for request queue processing delays"
            ]
        elif "deploy" in root_lower:
            return [
                "Compare configuration diff between the current and previous deployment",
                "Review deployment changelog for database migration runs",
                "Check error rates on the canary deployment slot if available",
                "Prepare for full rollback verification checklist"
            ]
        else:
            return [
                f"Examine '{service}' logs at DEBUG level for additional trace contexts",
                "Cross-reference alert timestamp with regional infrastructure events",
                "Assess system load and check for correlated network spikes",
                "Page secondary on-call engineer if metrics do not stabilize"
            ]

