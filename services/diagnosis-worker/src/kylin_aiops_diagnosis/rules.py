"""Safety-first deterministic rules that can override probabilistic model output."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleResult:
    fault_type: str
    severity: str
    confidence: float
    evidence_refs: list[str]


def classify_rules(metrics: dict[str, float], evidence_ids: list[str]) -> RuleResult:
    if not evidence_ids:
        raise ValueError("Rule diagnosis requires at least one Evidence ID")

    connections = metrics.get("mysql_connections", 0)
    max_connections = max(metrics.get("mysql_max_connections", 0), 1)
    rules = [
        (metrics.get("service_up", 1) < 0.5, "java_service_down", "critical", 1.0),
        (metrics.get("disk_percent", 0) >= 95, "disk_full", "critical", 0.98),
        (
            connections / max_connections >= 0.95,
            "mysql_connection_exhaustion",
            "critical",
            0.96,
        ),
        (
            metrics.get("network_latency_ms", 0) >= 200
            or metrics.get("packet_loss_percent", 0) >= 2,
            "network_degradation",
            "high",
            0.90,
        ),
        (metrics.get("cpu_percent", 0) >= 90, "cpu_saturation", "high", 0.88),
        (metrics.get("memory_percent", 0) >= 90, "memory_pressure", "high", 0.88),
    ]
    for matched, fault_type, severity, confidence in rules:
        if matched:
            return RuleResult(fault_type, severity, confidence, list(evidence_ids))
    return RuleResult("normal", "info", 0.8, list(evidence_ids))
