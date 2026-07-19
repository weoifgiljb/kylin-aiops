from dataclasses import dataclass


@dataclass(frozen=True)
class TrialPrediction:
    experiment_id: str
    ground_truth_type: str
    predicted_type: str
    ground_truth_root: str
    predicted_roots: list[str]
    remediation_succeeded: bool
    ground_truth_severity: str = "unknown"
    predicted_severity: str = "unknown"
    ground_truth_edges: set[tuple[str, str]] | None = None
    predicted_edges: set[tuple[str, str]] | None = None


@dataclass(frozen=True)
class EvaluationMetrics:
    detection_f1: float
    root_cause_top1: float
    root_cause_top3: float
    remediation_success_rate: float
    severity_macro_f1: float = 0.0
    propagation_edge_f1: float = 0.0


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_trials(trials: list[TrialPrediction]) -> EvaluationMetrics:
    if not trials:
        raise ValueError("At least one trial is required")
    true_positive = sum(
        trial.ground_truth_type != "normal" and trial.predicted_type != "normal"
        for trial in trials
    )
    false_negative = sum(
        trial.ground_truth_type != "normal" and trial.predicted_type == "normal"
        for trial in trials
    )
    false_positive = sum(
        trial.ground_truth_type == "normal" and trial.predicted_type != "normal"
        for trial in trials
    )
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    detection_f1 = _ratio(2 * precision * recall, precision + recall)

    detected = [trial for trial in trials if trial.predicted_type != "normal"]
    top1 = _ratio(
        sum(
            bool(trial.predicted_roots)
            and trial.predicted_roots[0] == trial.ground_truth_root
            for trial in detected
        ),
        len(detected),
    )
    top3 = _ratio(
        sum(trial.ground_truth_root in trial.predicted_roots[:3] for trial in detected),
        len(detected),
    )
    remediation = _ratio(sum(trial.remediation_succeeded for trial in trials), len(trials))
    severities = sorted({trial.ground_truth_severity for trial in trials})
    severity_scores: list[float] = []
    for severity in severities:
        severity_tp = sum(
            trial.ground_truth_severity == severity and trial.predicted_severity == severity
            for trial in trials
        )
        severity_fp = sum(
            trial.ground_truth_severity != severity and trial.predicted_severity == severity
            for trial in trials
        )
        severity_fn = sum(
            trial.ground_truth_severity == severity and trial.predicted_severity != severity
            for trial in trials
        )
        severity_precision = _ratio(severity_tp, severity_tp + severity_fp)
        severity_recall = _ratio(severity_tp, severity_tp + severity_fn)
        severity_scores.append(
            _ratio(2 * severity_precision * severity_recall, severity_precision + severity_recall)
        )
    severity_macro_f1 = _ratio(sum(severity_scores), len(severity_scores))

    edge_tp = edge_fp = edge_fn = 0
    for trial in trials:
        truth = trial.ground_truth_edges or set()
        prediction = trial.predicted_edges or set()
        edge_tp += len(truth & prediction)
        edge_fp += len(prediction - truth)
        edge_fn += len(truth - prediction)
    edge_precision = _ratio(edge_tp, edge_tp + edge_fp)
    edge_recall = _ratio(edge_tp, edge_tp + edge_fn)
    propagation_edge_f1 = _ratio(
        2 * edge_precision * edge_recall,
        edge_precision + edge_recall,
    )
    return EvaluationMetrics(
        detection_f1,
        top1,
        top3,
        remediation,
        severity_macro_f1,
        propagation_edge_f1,
    )
