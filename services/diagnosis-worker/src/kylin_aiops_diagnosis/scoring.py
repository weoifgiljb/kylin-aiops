from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CandidateSignals:
    temporal_precedence: float
    topology_causality: float
    symptom_match: float
    local_anomaly_strength: float

    def root_cause_score(self) -> float:
        values = (
            self.temporal_precedence,
            self.topology_causality,
            self.symptom_match,
            self.local_anomaly_strength,
        )
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("Root-cause signals must be between 0 and 1")
        return (
            0.35 * self.temporal_precedence
            + 0.30 * self.topology_causality
            + 0.20 * self.symptom_match
            + 0.15 * self.local_anomaly_strength
        )


@dataclass(frozen=True)
class DiagnosisInput:
    incident_id: str
    candidate: str
    model_probability: float
    rule_confidence: float
    signals: CandidateSignals
    evidence_ids: list[str]
    observed_at: datetime


@dataclass(frozen=True)
class DiagnosisResult:
    incident_id: str
    root_cause: str
    anomaly_confidence: float
    root_cause_score: float
    evidence_refs: list[str]
    ranked_candidates: list[str]


def diagnose(items: list[DiagnosisInput]) -> DiagnosisResult:
    if not items:
        raise ValueError("At least one diagnosis candidate is required")
    incident_ids = {item.incident_id for item in items}
    if len(incident_ids) != 1:
        raise ValueError("Diagnosis candidates must belong to one incident")
    for item in items:
        if not item.evidence_ids:
            raise ValueError(f"Candidate {item.candidate} requires at least one Evidence ID")
        if not 0 <= item.model_probability <= 1 or not 0 <= item.rule_confidence <= 1:
            raise ValueError("Model and rule confidence must be between 0 and 1")

    ranked = sorted(items, key=lambda item: item.signals.root_cause_score(), reverse=True)
    winner = ranked[0]
    return DiagnosisResult(
        incident_id=winner.incident_id,
        root_cause=winner.candidate,
        anomaly_confidence=0.60 * winner.model_probability + 0.40 * winner.rule_confidence,
        root_cause_score=winner.signals.root_cause_score(),
        evidence_refs=list(winner.evidence_ids),
        ranked_candidates=[item.candidate for item in ranked],
    )
