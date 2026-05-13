"""Generate a small batch of fake JSONL logs and metrics for smoke-testing.

The goal is to give a learner something to look at in Grafana before they
run the full pipeline:

* 20 fake log lines under ``artifacts/logs/run-fake.jsonl``
* 5 fake metric rows under ``artifacts/metrics/run-fake.jsonl``

Both files use the exact field shape the real observability stack emits.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

LEVELS = ["INFO", "INFO", "INFO", "WARNING", "ERROR"]
LOGGERS = ["pipeline", "repo_ingest.scanner", "ontology.extractor", "rag.answer"]
MESSAGES = [
    "scanned file",
    "extracted entity",
    "built relation",
    "tokenizer compression below baseline",
    "dataset example missing evidence",
    "rag retrieval returned 0 chunks",
]


def _write_logs(path: Path, n: int, trace: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    with path.open("w", encoding="utf-8") as f:
        for i in range(n):
            record = {
                "ts": now + i,
                "level": random.choice(LEVELS),
                "logger": random.choice(LOGGERS),
                "message": random.choice(MESSAGES),
                "trace": trace,
            }
            f.write(json.dumps(record, sort_keys=True) + "\n")


def _write_metrics(path: Path, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    seeds = [
        ("kde_ingest_files_total", {"repo": "miniA", "component": "repo_ingest"}, 1.0),
        ("kde_ontology_entities_total", {"repo": "miniA", "component": "ontology"}, 1.0),
        ("kde_graph_nodes_total", {"repo": "miniA", "component": "graph"}, 1.0),
        ("kde_dataset_evidence_coverage_ratio", {"task_type": "qa", "split": "val"}, 0.83),
        ("kde_eval_component_accuracy", {"split": "val", "component": "hybrid"}, 0.72),
    ]
    with path.open("w", encoding="utf-8") as f:
        for i in range(n):
            metric, labels, value = seeds[i % len(seeds)]
            record = {
                "ts": now + i,
                "metric": metric,
                "value": value + random.random() * 0.01,
                "labels": labels,
            }
            f.write(json.dumps(record, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, default=Path("artifacts/logs/run-fake.jsonl"))
    parser.add_argument("--metrics", type=Path, default=Path("artifacts/metrics/run-fake.jsonl"))
    parser.add_argument("--trace", default="fakebaadf00d")
    parser.add_argument("--n-logs", type=int, default=20)
    parser.add_argument("--n-metrics", type=int, default=5)
    args = parser.parse_args(argv)
    _write_logs(args.logs, args.n_logs, args.trace)
    _write_metrics(args.metrics, args.n_metrics)
    print(f"wrote {args.n_logs} log lines to {args.logs}")
    print(f"wrote {args.n_metrics} metric rows to {args.metrics}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
