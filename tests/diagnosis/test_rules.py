import pytest
from kylin_aiops_diagnosis.rules import classify_rules


@pytest.mark.parametrize(
    ("metrics", "expected"),
    [
        ({"cpu_percent": 95}, "cpu_saturation"),
        ({"memory_percent": 94}, "memory_pressure"),
        ({"disk_percent": 97}, "disk_full"),
        ({"service_up": 0}, "java_service_down"),
        ({"network_latency_ms": 250, "packet_loss_percent": 5}, "network_degradation"),
        ({"mysql_connections": 498, "mysql_max_connections": 500}, "mysql_connection_exhaustion"),
    ],
)
def test_six_safety_rules_are_deterministic(metrics, expected) -> None:
    result = classify_rules(metrics, evidence_ids=["ev-1"])

    assert result.fault_type == expected
    assert result.confidence >= 0.8
    assert result.evidence_refs == ["ev-1"]


def test_rule_result_requires_evidence() -> None:
    with pytest.raises(ValueError, match="Evidence"):
        classify_rules({"disk_percent": 99}, evidence_ids=[])
