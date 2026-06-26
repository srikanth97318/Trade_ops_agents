"""
TradeSage Ops — Runbook Agent

Specialist agent that synthesizes step-by-step mitigation plans
based on the identified root cause.

In production, this would search Confluence, Google Docs, wiki pages,
and internal runbook repositories. Here it uses a built-in knowledge base
of common SRE runbook procedures.
"""

import logging
from typing import List, Optional
from app.utils.llm import call_gemini
from app.models import AgentInsight

logger = logging.getLogger(__name__)

# Built-in runbook knowledge base — maps root cause patterns to step-by-step actions
RUNBOOK_KB = {
    "connection pool": {
        "title": "Runbook #12 — Database Connection Pool Exhaustion",
        "steps": [
            "Immediately scale up database read replicas to distribute load",
            "Increase connection pool size in service configuration (max_connections: 200 → 500)",
            "Restart affected service pods to reset stale connections: kubectl rollout restart deployment/<service>",
            "Monitor connection count and latency for 5 minutes post-restart",
            "If issue persists, check for connection leaks in recent deployments",
            "Run: SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction' to find leaked connections",
        ]
    },
    "cpu": {
        "title": "Runbook #7 — CPU Spike / Resource Exhaustion",
        "steps": [
            "Check if a recent deployment introduced CPU-intensive code: git log --since='1 hour ago'",
            "Scale horizontally: kubectl scale deployment/<service> --replicas=<current+2>",
            "Profile the service for hot code paths if CPU remains high",
            "Check for infinite loops or unoptimized database queries",
            "If caused by deployment, rollback: kubectl rollout undo deployment/<service>",
            "Set up HPA (Horizontal Pod Autoscaler) if not already configured",
        ]
    },
    "memory": {
        "title": "Runbook #9 — Memory Exhaustion / OOM Kill",
        "steps": [
            "Check for memory leaks: kubectl top pods -n <namespace>",
            "Increase memory limits in deployment spec temporarily",
            "Restart affected pods: kubectl delete pod <pod-name>",
            "Review recent code changes for memory-intensive operations",
            "Enable memory profiling in the next deployment",
            "Check garbage collection settings (for JVM/Go services)",
        ]
    },
    "timeout": {
        "title": "Runbook #15 — Service Timeout Cascade",
        "steps": [
            "Identify the slow dependency causing timeouts",
            "Increase timeout values temporarily to prevent cascading failures",
            "Enable circuit breaker pattern if not already active",
            "Check network connectivity between services: kubectl exec -it <pod> -- curl <dependency-url>",
            "Review DNS resolution: nslookup <service-name>",
            "If database-related, check for table locks: SELECT * FROM pg_locks WHERE NOT granted",
        ]
    },
    "deployment": {
        "title": "Runbook #3 — Bad Deployment Rollback",
        "steps": [
            "Confirm deployment timing correlates with incident: kubectl rollout history deployment/<service>",
            "Rollback immediately: kubectl rollout undo deployment/<service>",
            "Verify rollback success: kubectl rollout status deployment/<service>",
            "Monitor error rate for 5 minutes post-rollback",
            "Mark the failing commit in the CI/CD pipeline",
            "Conduct post-mortem on what the deployment changed",
        ]
    },
    "disk": {
        "title": "Runbook #20 — Disk Space Exhaustion",
        "steps": [
            "Check disk usage: df -h",
            "Identify large files: du -sh /* | sort -hr | head -20",
            "Clear old logs: journalctl --vacuum-time=1d",
            "Remove unused Docker images: docker system prune -af",
            "Expand the persistent volume if on cloud storage",
            "Set up log rotation if not configured",
        ]
    },
}

# Default runbook for unrecognized patterns
DEFAULT_RUNBOOK = {
    "title": "Runbook #0 — General Incident Response",
    "steps": [
        "Verify the alert is genuine (not a monitoring false positive)",
        "Check service health: kubectl get pods -n <namespace>",
        "Review recent deployments: kubectl rollout history deployment/<service>",
        "Check dependency health: curl -s <dependency>/health",
        "Collect logs for the last 15 minutes: kubectl logs <pod> --since=15m",
        "Escalate to on-call engineer if not resolved within 10 minutes",
    ]
}


class RunbookAgent:
    """
    Synthesizes step-by-step runbook actions based on the root cause analysis.
    """

    name = "Runbook Agent"

    def analyze(self, root_cause: str, service: str) -> AgentInsight:
        """
        Generate a runbook response plan based on the probable root cause.

        Args:
            root_cause: The probable root cause identified by the coordinator
            service: The affected service name

        Returns:
            AgentInsight with step-by-step runbook actions
        """
        prompt = f"""You are an expert SRE runbook author. Based on this root cause for service '{service}':

Root cause: {root_cause}

Generate a step-by-step runbook response plan. Include:
1. Immediate mitigation (stop the bleeding)
2. Investigation commands
3. Verification steps
4. Prevention measures

Format as numbered steps. Be specific with commands. 5-7 steps maximum."""

        # Match root cause to known runbook
        matched_runbook = self._match_runbook(root_cause)
        steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(matched_runbook["steps"]))
        fallback = f"Matched: {matched_runbook['title']}\n\n{steps_text}"

        analysis = call_gemini(prompt, fallback)

        return AgentInsight(
            agent_name=self.name,
            analysis=analysis,
            confidence=0.85,
            data_points=[matched_runbook["title"]]
        )

    def get_action_steps(self, root_cause: str) -> List[str]:
        """Return the list of recommended actions (public helper)."""
        matched = self._match_runbook(root_cause)
        return matched["steps"]

    def _match_runbook(self, root_cause: str) -> dict:
        """Match a root cause description to the most relevant runbook."""
        root_cause_lower = root_cause.lower()
        for keyword, runbook in RUNBOOK_KB.items():
            if keyword in root_cause_lower:
                return runbook
        return DEFAULT_RUNBOOK
