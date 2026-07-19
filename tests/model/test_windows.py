from build_windows import FEATURES, build


def test_windows_never_mix_experiments() -> None:
    records = []
    for experiment_id in ("exp-a", "exp-b"):
        for index in range(60):
            records.append(
                {
                    "experiment_id": experiment_id,
                    "observed_at": f"2026-07-19T14:{index:02d}:00Z",
                    "label": "cpu_saturation",
                    "metrics": {name: index for name in FEATURES},
                }
            )

    windows = build(records)

    assert [item["experiment_id"] for item in windows] == ["exp-a", "exp-b"]
    assert all(len(item["window"]) == 60 for item in windows)
    assert all(len(row) == len(FEATURES) for item in windows for row in item["window"])
