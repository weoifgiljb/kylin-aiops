from fastapi.testclient import TestClient
from kylin_aiops_model.app import FEATURE_NAMES, create_app


def test_model_service_rejects_non_60_step_windows() -> None:
    response = TestClient(create_app()).post(
        "/v1/predict",
        json={"experiment_id": "exp-1", "window": [[0.0] * len(FEATURE_NAMES)]},
    )

    assert response.status_code == 422


def test_rule_fallback_returns_seven_class_probabilities() -> None:
    window = [[0.0] * len(FEATURE_NAMES) for _ in range(60)]
    for row in window:
        row[FEATURE_NAMES.index("service_up")] = 1.0
    window[-1][FEATURE_NAMES.index("cpu_percent")] = 99.0
    response = TestClient(create_app()).post(
        "/v1/predict", json={"experiment_id": "exp-1", "window": window}
    )

    assert response.status_code == 200
    assert response.json()["predicted_class"] == "cpu_saturation"
    assert set(response.json()["probabilities"]) == {
        "normal",
        "cpu_saturation",
        "memory_pressure",
        "disk_full",
        "java_service_down",
        "network_degradation",
        "mysql_connection_exhaustion",
    }
    assert response.json()["backend"] == "deterministic_fallback"
