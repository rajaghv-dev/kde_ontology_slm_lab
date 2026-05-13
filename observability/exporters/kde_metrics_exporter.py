"""Replay JSONL metrics from the lab into a Prometheus exposition endpoint.

What this exists for
--------------------
The lab's metrics are *always* written as JSONL under ``artifacts/metrics/``.
That sink is fine for offline analysis but Prometheus speaks the OpenMetrics
text format over HTTP. This script bridges the two:

1. Watch ``--metrics-dir`` (default ``artifacts/metrics``) for new lines in
   any ``run-*.jsonl`` file.
2. Translate each record into the matching ``prometheus_client`` counter,
   gauge, or histogram (inferred from the canonical metric name).
3. Serve ``/metrics`` on ``--port`` (default 9101) so Prometheus -- whether
   running locally or in docker-compose -- can scrape it.

The script is intentionally simple: it polls files every second and tracks
file offsets in memory. For a learning lab, that is plenty.

Run it alongside the pipeline:

    python -m observability.exporters.kde_metrics_exporter --port 9101
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Metric-name -> kind mapping derived from the conventions in
# src/observability/metrics.py and the lab's documented metric list.
_COUNTERS: set[str] = {
    "kde_ingest_files_total",
    "kde_ingest_symbols_total",
    "kde_ontology_entities_total",
    "kde_ontology_relations_total",
    "kde_graph_nodes_total",
    "kde_graph_edges_total",
    "kde_dataset_examples_total",
}
_HISTOGRAMS: set[str] = {
    "kde_rag_latency_seconds",
    "kde_answer_latency_seconds",
}
_GAUGES: set[str] = {
    "kde_tokenizer_tokens_per_term",
    "kde_tokenizer_compression_ratio",
    "kde_dataset_evidence_coverage_ratio",
    "kde_training_loss",
    "kde_eval_component_accuracy",
    "kde_eval_evidence_precision",
    "kde_eval_hallucination_rate",
    "kde_eval_command_safety_score",
}

_ALLOWED_LABELS: tuple[str, ...] = (
    "repo",
    "component",
    "task_type",
    "split",
    "model_family",
    "adapter_name",
)


def _lazy_prom() -> Any:
    try:
        import prometheus_client as pc
    except ImportError as e:  # pragma: no cover
        print(
            "prometheus_client is required to run the exporter. Install it with:\n"
            "    pip install prometheus_client",
            file=sys.stderr,
        )
        raise SystemExit(2) from e
    return pc


class Exporter:
    """Build and update prometheus_client objects from JSONL rows."""

    def __init__(self) -> None:
        pc = _lazy_prom()
        self._pc = pc
        self._objects: dict[str, Any] = {}
        for name in _COUNTERS:
            self._objects[name] = pc.Counter(name, name, list(_ALLOWED_LABELS))
        for name in _GAUGES:
            self._objects[name] = pc.Gauge(name, name, list(_ALLOWED_LABELS))
        for name in _HISTOGRAMS:
            self._objects[name] = pc.Histogram(name, name, list(_ALLOWED_LABELS))

    def apply(self, record: dict[str, Any]) -> None:
        name = record.get("metric")
        if name not in self._objects:
            return
        value = float(record.get("value", 0))
        labels = {k: str(record.get("labels", {}).get(k, "")) for k in _ALLOWED_LABELS}
        obj = self._objects[name].labels(**labels)
        if name in _COUNTERS:
            if value >= 0:
                obj.inc(value)
        elif name in _GAUGES:
            obj.set(value)
        elif name in _HISTOGRAMS:
            obj.observe(value)


def _tail(metrics_dir: Path, exporter: Exporter, poll_seconds: float = 1.0) -> None:
    offsets: dict[Path, int] = {}
    while True:
        for path in sorted(metrics_dir.glob("run-*.jsonl")):
            try:
                size = path.stat().st_size
            except FileNotFoundError:
                continue
            start = offsets.get(path, 0)
            if size <= start:
                continue
            with path.open("r", encoding="utf-8") as f:
                f.seek(start)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    exporter.apply(record)
                offsets[path] = f.tell()
        time.sleep(poll_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9101, help="HTTP port to expose /metrics on")
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=Path("artifacts/metrics"),
        help="Directory containing run-*.jsonl metric files",
    )
    args = parser.parse_args(argv)

    args.metrics_dir.mkdir(parents=True, exist_ok=True)
    pc = _lazy_prom()
    exporter = Exporter()
    pc.start_http_server(args.port)
    print(f"[kde-exporter] serving /metrics on :{args.port} from {args.metrics_dir}")
    try:
        _tail(args.metrics_dir, exporter)
    except KeyboardInterrupt:  # pragma: no cover
        print("[kde-exporter] shutting down")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
