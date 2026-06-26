"""
TradeSage Ops — Timeline Agent

Specialist agent that analyzes incident timeline data, including alert triggers,
deployment history, log timestamps, and metric deviations to generate a
chronological reconstruction of the event.

In production, this would query CI/CD systems, alert managers, and log management tools.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.utils.llm import call_gemini
from app.models import AgentInsight

logger = logging.getLogger(__name__)


class TimelineAgent:
    """
    Analyzes event sequences to reconstruct a detailed chronological timeline.
    """

    name = "Timeline Agent"

    def analyze(
        self,
        service: str,
        message: str,
        timestamp: str,
        logs: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> AgentInsight:
        """
        Build a chronological timeline based on incident context.

        Args:
            service: The affected service name
            message: The alert message
            timestamp: The timestamp of the alert
            logs: Optional recent log lines
            metrics: Optional metrics snapshot

        Returns:
            AgentInsight containing the timeline analysis and event sequence.
        """
        logs_text = "\n".join(logs) if logs else "No logs available."
        metrics_text = str(metrics) if metrics else "No metrics available."

        prompt = f"""You are an expert SRE incident timeline investigator. Reconstruct a chronological timeline of the incident for service '{service}'.

Alert: {message}
Timestamp: {timestamp}
Logs:
{logs_text}
Metrics:
{metrics_text}

Analyze the sequence of events. Find:
1. When did the first deviation occur relative to the alert?
2. When did the alert trigger?
3. When did downstream impacts begin?
4. What is the chronological progression?

Be concise. State the sequence of key events with times. Format as 4-5 bullet points with times."""

        fallback = self._build_mock_analysis(service, message, timestamp, logs, metrics)
        analysis = call_gemini(prompt, fallback)

        # Build data points for the insight
        timeline_events = self.get_timeline_list(service, message, timestamp, logs, metrics)

        return AgentInsight(
            agent_name=self.name,
            analysis=analysis,
            confidence=0.90,
            data_points=timeline_events
        )

    def get_timeline_list(
        self,
        service: str,
        message: str,
        timestamp: str,
        logs: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Generate a list of formatted timeline events.
        """
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            ts = datetime.utcnow()

        def fmt_time(offset_minutes: int) -> str:
            event_time = ts + timedelta(minutes=offset_minutes)
            return event_time.strftime("%H:%M:%S UTC")

        events = []

        # Step 1: Pre-incident event (e.g. deployment or config change)
        msg_lower = message.lower()
        if "deploy" in msg_lower or "crash" in msg_lower:
            events.append(f"{fmt_time(-5)} — Deployment trigger: release v2.4.1 deployed to '{service}' cluster")
        elif "pool" in msg_lower or "connection" in msg_lower:
            events.append(f"{fmt_time(-6)} — Batch database synchronization job initiated")
            events.append(f"{fmt_time(-4)} — Sharp increase in active DB connections on '{service}'")
        elif "memory" in msg_lower or "oom" in msg_lower:
            events.append(f"{fmt_time(-8)} — Config change: memory limits adjusted for '{service}' pod")
            events.append(f"{fmt_time(-4)} — Memory consumption crossed 85% threshold")
        else:
            events.append(f"{fmt_time(-5)} — Configuration drift detected on service deployment")

        # Step 2: Early warnings
        events.append(f"{fmt_time(-2)} — Latency spike detected on '{service}' upstream router")

        # Step 3: The alert itself
        events.append(f"{fmt_time(0)} — P1 ALERT: '{message}' triggered for '{service}'")

        # Step 4: Cascade effects
        if metrics:
            err_rate = metrics.get("error_rate", 0)
            if err_rate > 5:
                events.append(f"{fmt_time(1)} — Error rate exceeded critical threshold ({err_rate}%)")
            else:
                events.append(f"{fmt_time(1)} — Metrics anomaly: resource consumption limits reached")

        if logs:
            events.append(f"{fmt_time(2)} — Multiple error signatures registered in application logs")

        events.append(f"{fmt_time(3)} — Downstream service degradation cascades to gateway layer")

        return events

    def _build_mock_analysis(
        self,
        service: str,
        message: str,
        timestamp: str,
        logs: Optional[List[str]],
        metrics: Optional[Dict[str, Any]],
    ) -> str:
        """Build context-aware mock timeline text."""
        events = self.get_timeline_list(service, message, timestamp, logs, metrics)
        bullet_points = "\n".join(f"- {evt}" for evt in events)
        return (
            f"Chronological incident reconstruction for '{service}':\n"
            f"{bullet_points}\n"
            f"Conclusion: The event sequence indicates a sudden onset incident triggered by upstream modifications, "
            f"propagating within 2 minutes to downstream API handlers."
        )
