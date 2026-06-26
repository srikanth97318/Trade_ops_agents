"""
TradeSage Ops — Dependency Agent

Specialist agent that maps service relationships and determines the blast radius.
Knows the service dependency graph and can infer which services are affected
when one service fails.

In production, this would integrate with service mesh data (Istio), Kubernetes
service discovery, or a CMDB. Here it uses a built-in dependency graph
that models a realistic e-commerce microservices architecture.
"""

import logging
from typing import List, Dict
from app.utils.llm import call_gemini
from app.models import AgentInsight

logger = logging.getLogger(__name__)

# Realistic e-commerce service dependency graph
# Format: service -> list of services it depends on (upstream)
DEPENDENCY_GRAPH: Dict[str, List[str]] = {
    "api-gateway":       ["auth-service", "orders-service", "payments-service", "catalog-service"],
    "auth-service":      ["user-db", "redis-cache"],
    "orders-service":    ["user-db", "payments-service", "inventory-service", "notification-service"],
    "payments-service":  ["user-db", "stripe-api", "redis-cache"],
    "catalog-service":   ["product-db", "redis-cache", "search-service"],
    "inventory-service": ["product-db"],
    "search-service":    ["elasticsearch"],
    "notification-service": ["email-gateway", "redis-cache"],
    "user-db":           [],
    "product-db":        [],
    "redis-cache":       [],
    "stripe-api":        [],
    "elasticsearch":     [],
    "email-gateway":     [],
    "checkout-api":      ["orders-service", "payments-service", "inventory-service"],
    "load-balancer":     ["api-gateway"],
}

# Reverse mapping: service -> list of services that depend on it (downstream)
REVERSE_DEPS: Dict[str, List[str]] = {}
for service, deps in DEPENDENCY_GRAPH.items():
    for dep in deps:
        if dep not in REVERSE_DEPS:
            REVERSE_DEPS[dep] = []
        REVERSE_DEPS[dep].append(service)


class DependencyAgent:
    """
    Maps service dependencies and calculates blast radius for an incident.
    """

    name = "Dependency Agent"

    def analyze(self, service: str) -> AgentInsight:
        """
        Determine the blast radius for a failure in the given service.

        Args:
            service: The name of the failed service

        Returns:
            AgentInsight with dependency analysis and blast radius
        """
        # Find all downstream (affected) services
        affected = self._get_affected_services(service)
        upstream = DEPENDENCY_GRAPH.get(service, [])

        prompt = f"""You are an expert SRE dependency analyst. Service '{service}' has failed.

Upstream dependencies (services it depends on): {upstream or ['None — this is a leaf service']}
Downstream services (services that depend on it): {affected or ['None identified']}

Full dependency graph context:
{self._format_graph_context(service)}

Explain:
1. The chain of impact from {service} failing
2. Which user-facing functionality is affected
3. The estimated percentage of users impacted

Be concise. 3-4 sentences. Use specific service names."""

        fallback = self._build_mock_analysis(service, affected, upstream)

        analysis = call_gemini(prompt, fallback)

        data_points = [
            f"Failed service: {service}",
            f"Upstream deps: {', '.join(upstream) if upstream else 'None'}",
            f"Downstream affected: {', '.join(affected) if affected else 'None identified'}",
        ]

        return AgentInsight(
            agent_name=self.name,
            analysis=analysis,
            confidence=0.92,
            data_points=data_points
        )

    def get_blast_radius(self, service: str) -> List[str]:
        """Return the list of affected services (public helper)."""
        return self._get_affected_services(service)

    def get_blast_radius_narration(self, service: str, affected: List[str]) -> str:
        """Generate a human-readable blast radius narration."""
        if not affected:
            return f"Service '{service}' failure is isolated. No downstream services are affected."

        # Categorize affected services
        user_facing = [s for s in affected if s in ["api-gateway", "checkout-api", "catalog-service", "auth-service"]]
        internal = [s for s in affected if s not in user_facing]

        narration = f"The failure in '{service}' cascades to {len(affected)} downstream services. "

        if user_facing:
            narration += f"User-facing services affected: {', '.join(user_facing)}. "
            narration += "Customers will experience degraded service including "

            impacts = []
            if "checkout-api" in affected or "payments-service" in affected:
                impacts.append("failed purchases")
            if "auth-service" in affected:
                impacts.append("login failures")
            if "catalog-service" in affected:
                impacts.append("product search issues")
            if "orders-service" in affected:
                impacts.append("order processing delays")

            if impacts:
                narration += ", ".join(impacts) + ". "
            else:
                narration += "intermittent errors and slow page loads. "

        unaffected = ["catalog-service", "search-service"] if "product-db" not in [service] + affected else []
        if unaffected:
            narration += f"Services like {', '.join(unaffected[:2])} remain operational."

        return narration

    def _get_affected_services(self, service: str) -> List[str]:
        """BFS to find all downstream services affected by a failure."""
        affected = []
        visited = set()
        queue = [service]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current != service:
                affected.append(current)
            # Add all services that depend on current
            for downstream in REVERSE_DEPS.get(current, []):
                if downstream not in visited:
                    queue.append(downstream)

        return affected

    def _format_graph_context(self, service: str) -> str:
        """Format the relevant portion of the dependency graph."""
        lines = [f"  {service} is depended on by: {REVERSE_DEPS.get(service, ['nothing'])}"]
        for dep in DEPENDENCY_GRAPH.get(service, []):
            lines.append(f"  {service} depends on: {dep}")
        return "\n".join(lines)

    def _build_mock_analysis(self, service: str, affected: List[str], upstream: List[str]) -> str:
        """Build a context-aware mock analysis."""
        if not affected:
            return f"Service '{service}' is a leaf node with no downstream dependencies. The failure is isolated. However, if {service} is a data store, check for services with hardcoded connections."

        return (
            f"Service '{service}' failure propagates to {len(affected)} downstream services: "
            f"{', '.join(affected[:5])}. "
            f"{'This affects user-facing functionality including checkout and authentication. ' if any(s in affected for s in ['checkout-api', 'auth-service', 'api-gateway']) else ''}"
            f"Estimated impact: {'40-60%' if len(affected) > 3 else '10-25%'} of active users."
        )
