import pytest
from kylin_aiops_model.evaluation import TrialPrediction, evaluate_trials


def test_evaluation_computes_detection_and_root_cause_metrics() -> None:
    trials = [
        TrialPrediction("exp-1", "cpu", "cpu", "web-01", ["web-01"], True),
        TrialPrediction("exp-2", "memory", "memory", "app-01", ["db-01", "app-01"], True),
        TrialPrediction("exp-3", "disk", "normal", "db-01", ["app-01"], False),
    ]

    result = evaluate_trials(trials)

    assert result.detection_f1 == pytest.approx(0.8)
    assert result.root_cause_top1 == pytest.approx(0.5)
    assert result.root_cause_top3 == pytest.approx(1.0)
    assert result.remediation_success_rate == pytest.approx(2 / 3)


def test_evaluation_computes_severity_and_propagation_f1() -> None:
    trials = [
        TrialPrediction(
            "exp-1",
            "cpu",
            "cpu",
            "web-01",
            ["web-01"],
            True,
            ground_truth_severity="high",
            predicted_severity="high",
            ground_truth_edges={("web-01", "app-01")},
            predicted_edges={("web-01", "app-01")},
        ),
        TrialPrediction(
            "exp-2",
            "memory",
            "memory",
            "app-01",
            ["app-01"],
            False,
            ground_truth_severity="critical",
            predicted_severity="high",
            ground_truth_edges={("app-01", "db-01")},
            predicted_edges=set(),
        ),
    ]

    result = evaluate_trials(trials)

    assert result.severity_macro_f1 == pytest.approx(1 / 3)
    assert result.propagation_edge_f1 == pytest.approx(2 / 3)
