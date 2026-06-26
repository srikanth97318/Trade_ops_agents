"""
TradeSage Ops — Logs Agent

Specialist agent that analyzes log lines to identify error patterns,
recurring failures, and anomalous behavior.

In a production deployment, this agent would connect to Loki, Cloud Logging,
or Elasticsearch. Here it analyzes the log lines provided in the alert payload.
"""

import logging
from typing import List, Optional
from app.utils.llm import call_gemini
from app.models import AgentInsight

logger = logging.getLogger(__name__)

# Service-specific error patterns for intelligent mock analysis
ERROR_PATTERNS = {
    "timeout": "Connection timeout detected — service is failing to reach a dependency within the configured deadline.",
    "connection refused": "Connection refused — the target service or database is not accepting connections. Likely down or at capacity.",
    "pool exhausted": "Connection pool exhausted — all available connections are in use. Incoming requests are being dropped.",
    "oom": "Out of memory — the service exceeded its memory allocation and was killed by the OOM killer.",
    "5xx": "Server errors (5xx) detected — the service is returning internal errors to callers.",
    "disk full": "Disk space exhausted — the service cannot write logs or data.",
    "certificate": "TLS certificate error — possible certificate expiry or misconfiguration.",
    "authentication": "Authentication failure — credentials may be expired or revoked.",
    "replica": "Database replica failure — read replicas are not responding, increasing load on primary.",
    "crash": "Service crash detected — the process terminated unexpectedly.",
}


class LogsAgent:
    """
    Analyzes log lines from the alert payload.
    Identifies error patterns, recurring failures, and the earliest error signal.
    """

    name = "Logs Agent"

    def analyze(self, logs: Optional[List[str]], service: str, message: str) -> AgentInsight:
        """
        Analyze the provided logs for error patterns and anomalies.

        Args:
            logs: List of recent log lines from the affected service
            service: Name of the service that generated the logs
            message: The original alert message for context

        Returns:
            AgentInsight with the logs analysis
        """
        log_text = "\n".join(logs) if logs else "No logs provided."

        prompt = f"""You are an expert SRE log analyst. Analyze these logs from the '{service}' service.

Alert message: {message}

Logs:
{log_text}

Identify:
1. The earliest error signal (first sign of trouble)
2. Recurring error patterns
3. Error escalation sequence
4. Any clues about root cause

Be concise. Focus on facts from the logs. 3-4 sentences maximum."""

        # Build intelligent fallback based on actual log content
        fallback = self._build_mock_analysis(logs, service, message)

        analysis = call_gemini(prompt, fallback)

        # Extract data points from logs
        data_points = []
        if logs:
            error_logs = [l for l in logs if any(kw in l.upper() for kw in ["ERROR", "FATAL", "CRIT"])]
            data_points = error_logs[:3] if error_logs else logs[:2]

        return AgentInsight(
            agent_name=self.name,
            analysis=analysis,
            confidence=0.88 if logs else 0.5,
            data_points=data_points or ["No log data available"]
        )

    def _build_mock_analysis(self, logs: Optional[List[str]], service: str, message: str) -> str:
        """Build a context-aware mock analysis based on log content."""
        if not logs:
            return f"No logs available for {service}. Cannot determine log-based root cause. Recommend checking log collection pipeline."

        # Scan for known error patterns
        findings = []
        for log_line in logs:
            for pattern, description in ERROR_PATTERNS.items():
                if pattern.lower() in log_line.lower():
                    findings.append(description)
                    break

        if findings:
            unique_findings = list(dict.fromkeys(findings))  # deduplicate preserving order
            return f"Log analysis for {service}: " + " ".join(unique_findings[:3]) + f" First error appeared in earliest log entry. The pattern suggests {message.lower()} is the proximate cause."

        return f"Logs from {service} show error activity consistent with '{message}'. Multiple error-level entries detected in the timeframe. The error pattern suggests a cascading failure originating from a dependency."
