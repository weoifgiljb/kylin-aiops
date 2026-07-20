"""MindSpore temporal classifier construction and Ascend checkpoint inference."""

from pathlib import Path

from .app import CLASSES, FEATURE_NAMES, PredictionResponse


def require_mindspore():
    try:
        import mindspore as ms
        from mindspore import nn
    except ImportError as exc:
        raise RuntimeError(
            "MindSpore is not installed. Install the CANN-compatible Ascend build from the "
            "offline bundle, then run tools/verify_ascend.py before training."
        ) from exc
    return ms, nn


def build_network():
    ms, nn = require_mindspore()

    class TemporalClassifier(nn.Cell):
        def __init__(self) -> None:
            super().__init__()
            self.network = nn.SequentialCell(
                nn.Conv1d(len(FEATURE_NAMES), 32, kernel_size=3, pad_mode="pad", padding=1),
                nn.ReLU(),
                nn.Conv1d(32, 64, kernel_size=3, pad_mode="pad", padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool1d(1),
                nn.Flatten(),
                nn.Dense(64, len(CLASSES)),
            )

        def construct(self, features):
            return self.network(features)

    return ms, TemporalClassifier()


class MindSporePredictor:
    def __init__(self, checkpoint: Path, device_target: str = "Ascend") -> None:
        ms, network = build_network()
        ms.set_context(mode=ms.GRAPH_MODE, device_target=device_target)
        ms.load_checkpoint(str(checkpoint), net=network)
        network.set_train(False)
        self.ms = ms
        self.network = network

    def predict(self, window: list[list[float]]) -> PredictionResponse:
        import numpy as np

        array = np.asarray(window, dtype=np.float32).T[None, ...]
        logits = self.network(self.ms.Tensor(array))
        probabilities_array = self.ms.ops.softmax(logits, axis=1).asnumpy()[0]
        probabilities = {
            label: float(probabilities_array[index]) for index, label in enumerate(CLASSES)
        }
        predicted = max(probabilities, key=probabilities.get)
        return PredictionResponse(
            predicted_class=predicted,
            probabilities=probabilities,
            backend="mindspore_ascend",
        )
