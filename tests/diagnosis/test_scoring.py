from datetime import UTC, datetime

import pytest
from kylin_aiops_diagnosis.scoring import (
    CandidateSignals,
    DiagnosisInput,
    diagnose,
)


def test_root_cause_score_uses_locked_plan_weights() -> None:
    signals = CandidateSignals(
        temporal_precedence=0.8,
        topology_causality=0.9,
        symptom_match=0.5,
        local_anomaly_strength=1.0,
    )

    assert signals.root_cause_score() == pytest.approx(0.8)


def test_diagnosis_requires_real_evidence_references() -> None:
    item = DiagnosisInput(
        incident_id="inc-1",
        candidate="db-01",
        model_probability=0.9,
        rule_confidence=0.8,
        signals=CandidateSignals(1, 1, 1, 1),
        evidence_ids=[],
        observed_at=datetime.now(UTC),
    )

    with pytest.raises(ValueError, match="Evidence ID"):
        diagnose([item])


def test_diagnosis_ranks_candidates_and_combines_confidence() -> None:
    now = datetime.now(UTC)
    result = diagnose(
        [
            DiagnosisInput(
                incident_id="inc-1",
                candidate="app-01",
                model_probability=0.7,
                rule_confidence=0.5,
                signals=CandidateSignals(0.5, 0.5, 0.7, 0.6),
                evidence_ids=["ev-app"],
                observed_at=now,
            ),
            DiagnosisInput(
                incident_id="inc-1",
                candidate="db-01",
                model_probability=0.9,
                rule_confidence=0.8,
                signals=CandidateSignals(1.0, 1.0, 0.9, 0.9),
                evidence_ids=["ev-db-metric", "ev-db-log"],
                observed_at=now,
            ),
        ]
    )

    assert result.root_cause == "db-01"
    assert result.anomaly_confidence == pytest.approx(0.86)
    assert result.evidence_refs == ["ev-db-metric", "ev-db-log"]
