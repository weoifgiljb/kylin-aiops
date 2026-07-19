from kylin_aiops_model.dataset import ExperimentSample, split_by_experiment


def test_dataset_split_never_leaks_experiment_between_partitions() -> None:
    samples = [
        ExperimentSample(
            experiment_id=f"exp-{index // 3}",
            features=[float(index)],
            label=index % 7,
        )
        for index in range(90)
    ]

    split = split_by_experiment(samples, seed=42)
    train_ids = {sample.experiment_id for sample in split.train}
    validation_ids = {sample.experiment_id for sample in split.validation}
    test_ids = {sample.experiment_id for sample in split.test}

    assert not train_ids & validation_ids
    assert not train_ids & test_ids
    assert not validation_ids & test_ids
    assert train_ids | validation_ids | test_ids == {sample.experiment_id for sample in samples}
