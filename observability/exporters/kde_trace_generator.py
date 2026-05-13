"""Generate a small batch of fake spans for smoke-testing Tempo / Grafana.

Writes a single ``artifacts/logs/traces-fake.jsonl`` file with a parent
"pipeline" span and a few child stage spans. Field shape matches the real
``src.observability.traces`` emitter.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

STAGES = [
    ("scan", 0.05, "repo_ingest"),
    ("extract", 0.12, "ontology"),
    ("graph_build", 0.03, "graph"),
    ("tokenizer", 0.02, "tokenizer"),
    ("dataset_gen", 0.04, "dataset"),
    ("rag_answer", 0.18, "rag"),
    ("eval", 0.07, "eval"),
]


def _new_id(n: int = 16) -> str:
    return uuid.uuid4().hex[:n]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/logs/traces-fake.jsonl"))
    parser.add_argument("--trace-id", default="fakebaadf00d")
    args = parser.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    parent_id = _new_id()
    base_ns = time.time_ns()
    spans = []
    parent = {
        "trace_id": args.trace_id,
        "span_id": parent_id,
        "parent_id": None,
        "name": "pipeline",
        "start_ns": base_ns,
        "end_ns": base_ns,  # will be patched below
        "labels": {"component": "pipeline"},
    }
    spans.append(parent)

    cursor = base_ns
    for name, secs, component in STAGES:
        start = cursor
        end = start + int(secs * 1e9)
        spans.append(
            {
                "trace_id": args.trace_id,
                "span_id": _new_id(),
                "parent_id": parent_id,
                "name": name,
                "start_ns": start,
                "end_ns": end,
                "labels": {"component": component},
            }
        )
        cursor = end
    parent["end_ns"] = cursor

    with args.out.open("w", encoding="utf-8") as f:
        for s in spans:
            f.write(json.dumps(s, sort_keys=True) + "\n")
    print(f"wrote {len(spans)} spans to {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
