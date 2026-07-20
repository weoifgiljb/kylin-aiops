"""Experiment-grouped dataset splitting that prevents adjacent-window leakage."""

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class ExperimentSample:
    experiment_id: str
    features: list[float]
    label: int


@dataclass(frozen=True)
class DatasetSplit:
    train: list[ExperimentSample]
    validation: list[ExperimentSample]
    test: list[ExperimentSample]


def split_by_experiment(samples: list[ExperimentSample], seed: int) -> DatasetSplit:
    experiment_ids = sorted({sample.experiment_id for sample in samples})
    if len(experiment_ids) < 3:
        raise ValueError("At least three experiments are required for an isolated split")
    Random(seed).shuffle(experiment_ids)

    train_end = max(1, int(len(experiment_ids) * 0.6))
    validation_end = max(train_end + 1, int(len(experiment_ids) * 0.8))
    validation_end = min(validation_end, len(experiment_ids) - 1)
    train_ids = set(experiment_ids[:train_end])
    validation_ids = set(experiment_ids[train_end:validation_end])
    test_ids = set(experiment_ids[validation_end:])

    return DatasetSplit(
        train=[sample for sample in samples if sample.experiment_id in train_ids],
        validation=[sample for sample in samples if sample.experiment_id in validation_ids],
        test=[sample for sample in samples if sample.experiment_id in test_ids],
    )
