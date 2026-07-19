import pytest
from kylin_aiops_diagnosis.mindie import MindIEOutput, validate_mindie_output


def test_mindie_output_must_only_reference_available_evidence() -> None:
    output = MindIEOutput(
        summary="数据库连接耗尽",
        root_cause="db-01",
        severity="high",
        propagation_path=["db-01", "app-01"],
        evidence_refs=["ev-invented"],
        recommended_steps=["检查连接"],
        action_candidates=[],
        confidence=0.8,
    )

    with pytest.raises(ValueError, match="unknown Evidence ID"):
        validate_mindie_output(output, available_evidence_ids={"ev-real"})


def test_mindie_output_with_real_evidence_is_accepted() -> None:
    output = MindIEOutput(
        summary="数据库连接耗尽",
        root_cause="db-01",
        severity="high",
        propagation_path=["db-01", "app-01"],
        evidence_refs=["ev-real"],
        recommended_steps=["检查连接"],
        action_candidates=["terminate_fault_db_sessions"],
        confidence=0.8,
    )

    assert validate_mindie_output(output, {"ev-real"}) is output
