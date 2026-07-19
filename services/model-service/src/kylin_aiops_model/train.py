"""Ascend training entrypoint.

The target host must provide the CANN-matched MindSpore wheel. Dataset records are
JSONL objects with experiment_id, label and a 60x12 window. Splitting is always by
experiment_id through dataset.split_by_experiment.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from .app import CLASSES, FEATURE_NAMES
from .dataset import ExperimentSample, split_by_experiment
from .mindspore_tcn import build_network


def load_samples(path: Path) -> list[ExperimentSample]:
    samples: list[ExperimentSample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        flat = [value for row in record["window"] for value in row]
        samples.append(
            ExperimentSample(
                experiment_id=record["experiment_id"],
                features=flat,
                label=CLASSES.index(record["label"]),
            )
        )
    return samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    ms, network = build_network()
    ms.set_seed(args.seed)
    ms.set_context(mode=ms.GRAPH_MODE, device_target="Ascend")
    split = split_by_experiment(load_samples(args.dataset), seed=args.seed)
    if not split.train or not split.validation or not split.test:
        raise RuntimeError("Isolated train/validation/test partitions must all be non-empty")
    def generator(samples: list[ExperimentSample]):
        for sample in samples:
            features = (
                np.asarray(sample.features, dtype=np.float32)
                .reshape(60, len(FEATURE_NAMES))
                .T
            )
            yield features, np.int32(sample.label)

    train_dataset = ms.dataset.GeneratorDataset(
        lambda: generator(split.train),
        column_names=["features", "label"],
        shuffle=True,
    ).batch(32)
    validation_dataset = ms.dataset.GeneratorDataset(
        lambda: generator(split.validation),
        column_names=["features", "label"],
        shuffle=False,
    ).batch(32)
    optimizer = ms.nn.Adam(network.trainable_params(), learning_rate=1e-3)
    loss = ms.nn.SoftmaxCrossEntropyWithLogits(sparse=True, reduction="mean")
    model = ms.Model(network, loss_fn=loss, optimizer=optimizer, metrics={"accuracy"})
    model.train(args.epochs, train_dataset, dataset_sink_mode=True)
    validation_metrics = model.eval(validation_dataset, dataset_sink_mode=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    ms.save_checkpoint(network, str(args.output))
    manifest = {
        "seed": args.seed,
        "epochs": args.epochs,
        "train_experiments": sorted({sample.experiment_id for sample in split.train}),
        "validation_experiments": sorted({sample.experiment_id for sample in split.validation}),
        "test_experiments": sorted({sample.experiment_id for sample in split.test}),
        "validation_metrics": validation_metrics,
        "device_target": ms.get_context("device_target"),
        "note": "Acceptance requires npu-smi evidence and full blind-test evaluation output.",
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
