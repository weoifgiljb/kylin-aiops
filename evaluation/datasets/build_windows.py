"""Convert ordered telemetry JSONL into isolated 60-step model windows."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

FEATURES = [
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


def build(records: list[dict], length: int = 60, stride: int = 10) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["experiment_id"]].append(record)
    windows: list[dict] = []
    for experiment_id, experiment_records in sorted(grouped.items()):
        ordered = sorted(experiment_records, key=lambda item: item["observed_at"])
        for start in range(0, len(ordered) - length + 1, stride):
            chunk = ordered[start : start + length]
            windows.append(
                {
                    "experiment_id": experiment_id,
                    "label": chunk[-1]["label"],
                    "window": [
                        [float(row["metrics"].get(key, 0.0)) for key in FEATURES]
                        for row in chunk
                    ],
                }
            )
    return windows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line
    ]
    windows = build(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in windows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
