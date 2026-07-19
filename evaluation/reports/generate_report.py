import argparse
import csv
import hashlib
import html
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from kylin_aiops_model.evaluation import TrialPrediction, evaluate_trials

THRESHOLDS = {
    "detection_f1": 0.85,
    "severity_macro_f1": 0.80,
    "root_cause_top1": 0.80,
    "root_cause_top3": 0.95,
    "propagation_edge_f1": 0.80,
    "remediation_success_rate": 0.80,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_trials(path: Path) -> list[TrialPrediction]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [
        TrialPrediction(
            experiment_id=item["experiment_id"],
            ground_truth_type=item["ground_truth_type"],
            predicted_type=item["predicted_type"],
            ground_truth_root=item["ground_truth_root"],
            predicted_roots=item["predicted_roots"],
            remediation_succeeded=item["remediation_succeeded"],
            ground_truth_severity=item["ground_truth_severity"],
            predicted_severity=item["predicted_severity"],
            ground_truth_edges={tuple(edge) for edge in item.get("ground_truth_edges", [])},
            predicted_edges={tuple(edge) for edge in item.get("predicted_edges", [])},
        )
        for item in records
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    trials = load_trials(args.trials)
    metrics = asdict(evaluate_trials(trials))
    revision_result = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=False, capture_output=True, text=True
    )
    revision = revision_result.stdout.strip() if revision_result.returncode == 0 else "uncommitted"
    report = {
        "trial_count": len(trials),
        "seed": args.seed,
        "code_revision": revision or "uncommitted",
        "model_sha256": sha256(args.model) if args.model else None,
        "metrics": metrics,
        "thresholds": THRESHOLDS,
        "passed": len(trials) >= 120
        and all(metrics.get(key, 0) >= value for key, value in THRESHOLDS.items()),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (args.output_dir / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "actual", "threshold", "passed"])
        for key, threshold in THRESHOLDS.items():
            writer.writerow([key, metrics.get(key, 0), threshold, metrics.get(key, 0) >= threshold])
    rows = "".join(
        f"<tr><td>{html.escape(key)}</td><td>{metrics.get(key, 0):.3f}</td>"
        f"<td>{threshold:.3f}</td></tr>"
        for key, threshold in THRESHOLDS.items()
    )
    (args.output_dir / "report.html").write_text(
        f"<!doctype html><meta charset='utf-8'><title>Kylin AIOps evaluation</title>"
        f"<h1>评测结果：{'通过' if report['passed'] else '未通过'}</h1>"
        f"<p>试验数：{report['trial_count']}；随机种子：{args.seed}</p>"
        f"<table border='1'><tr><th>指标</th><th>实测</th><th>门槛</th></tr>{rows}</table>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
