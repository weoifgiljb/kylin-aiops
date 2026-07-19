from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

FEATURE_NAMES = [
    "cpu_percent",
    "memory_percent",
    "disk_percent",
    "load_1m",
    "process_count",
    "connection_count",
    "nginx_5xx_rate",
    "response_ms",
    "jvm_thread_count",
    "db_connections_ratio",
    "network_loss_percent",
    "service_up",
]

CLASSES = [
    "normal",
    "cpu_saturation",
    "memory_pressure",
    "disk_full",
    "java_service_down",
    "network_degradation",
    "mysql_connection_exhaustion",
]


class PredictionRequest(BaseModel):
    experiment_id: str = Field(min_length=1)
    window: list[list[float]]

    @model_validator(mode="after")
    def validate_shape(self):
        if len(self.window) != 60:
            raise ValueError("window must contain exactly 60 time steps")
        if any(len(row) != len(FEATURE_NAMES) for row in self.window):
            raise ValueError(f"each time step must contain {len(FEATURE_NAMES)} features")
        return self


class PredictionResponse(BaseModel):
    predicted_class: str
    probabilities: dict[str, float]
    backend: Literal["mindspore_ascend", "deterministic_fallback"]


class DeterministicFallback:
    def predict(self, window: list[list[float]]) -> PredictionResponse:
        latest = dict(zip(FEATURE_NAMES, window[-1], strict=True))
        predicted = "normal"
        if latest["service_up"] < 0.5:
            predicted = "java_service_down"
        elif latest["db_connections_ratio"] >= 0.90:
            predicted = "mysql_connection_exhaustion"
        elif latest["network_loss_percent"] >= 5:
            predicted = "network_degradation"
        elif latest["disk_percent"] >= 90:
            predicted = "disk_full"
        elif latest["memory_percent"] >= 90:
            predicted = "memory_pressure"
        elif latest["cpu_percent"] >= 90:
            predicted = "cpu_saturation"
        probabilities = {name: 0.03 for name in CLASSES}
        probabilities[predicted] = 0.82
        return PredictionResponse(
            predicted_class=predicted,
            probabilities=probabilities,
            backend="deterministic_fallback",
        )


def create_app(predictor=None) -> FastAPI:
    app = FastAPI(title="Kylin AIOps Model Service", version="0.1.0")
    app.state.predictor = predictor or DeterministicFallback()

    @app.get("/healthz")
    def healthz() -> dict:
        return {
            "status": "ok",
            "backend": type(app.state.predictor).__name__,
            "feature_count": len(FEATURE_NAMES),
            "window_steps": 60,
        }

    @app.post("/v1/predict", response_model=PredictionResponse)
    def predict(payload: PredictionRequest) -> PredictionResponse:
        return app.state.predictor.predict(payload.window)

    return app


app = create_app()
