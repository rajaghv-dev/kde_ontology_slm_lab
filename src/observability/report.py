"""Roll up JSONL metrics + logs into a single Markdown report.

This is the "no-Grafana" equivalent of a dashboard: a Markdown file you can
commit, diff, and read in a PR.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.common.paths import ARTIFACTS, EVAL_DIR, LOGS_DIR

METRICS_DIR = ARTIFACTS / "metrics"
REPORT_PATH = EVAL_DIR / "observability_report.md"


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _collect_metrics() -> list[dict[str, Any]]:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for p in sorted(METRICS_DIR.glob("run-*.jsonl")):
        rows.extend(_iter_jsonl(p))
    return rows


def _collect_logs() -> list[dict[str, Any]]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for p in sorted(LOGS_DIR.glob("run-*.jsonl")):
        rows.extend(_iter_jsonl(p))
    return rows


def _collect_spans() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in sorted(LOGS_DIR.glob("traces-*.jsonl")):
        rows.extend(_iter_jsonl(p))
    return rows


def _stage_durations(spans: list[dict[str, Any]]) -> list[tuple[str, float]]:
    durations: dict[str, float] = defaultdict(float)
    for s in spans:
        start, end = s.get("start_ns"), s.get("end_ns")
        if start is None or end is None:
            continue
        durations[s.get("name", "<unnamed>")] += (end - start) / 1e9
    return sorted(durations.items(), key=lambda kv: -kv[1])


def _top_warnings(logs: list[dict[str, Any]], k: int = 5) -> list[tuple[str, int]]:
    msgs = Counter(
        l.get("message", "") for l in logs if l.get("level") in {"WARNING", "ERROR", "CRITICAL"}
    )
    return msgs.most_common(k)


def _error_rate(logs: list[dict[str, Any]]) -> float:
    if not logs:
        return 0.0
    errs = sum(1 for l in logs if l.get("level") in {"ERROR", "CRITICAL"})
    return errs / len(logs)


def _last_n_metric(metrics: list[dict[str, Any]], name: str, n: int = 10) -> list[float]:
    vals = [m["value"] for m in metrics if m.get("metric") == name]
    return vals[-n:]


def build_report(out_path: Path | None = None) -> Path:
    """Materialise the Markdown report and return its path."""
    metrics = _collect_metrics()
    logs = _collect_logs()
    spans = _collect_spans()
    out_path = out_path or REPORT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Observability report")
    lines.append("")
    lines.append(
        f"Sources: {len(metrics)} metric rows, {len(logs)} log rows, "
        f"{len(spans)} spans."
    )
    lines.append("")

    lines.append("## Pipeline stage durations")
    lines.append("")
    stages = _stage_durations(spans)
    if not stages:
        lines.append("_no spans recorded yet_")
    else:
        lines.append("| stage | seconds |")
        lines.append("|-------|---------|")
        for name, secs in stages:
            lines.append(f"| {name} | {secs:.3f} |")
    lines.append("")

    lines.append("## Top warnings")
    lines.append("")
    warns = _top_warnings(logs)
    if not warns:
        lines.append("_no warnings or errors logged_")
    else:
        lines.append("| count | message |")
        lines.append("|-------|---------|")
        for msg, count in warns:
            lines.append(f"| {count} | {msg} |")
    lines.append("")

    lines.append("## Error rate")
    lines.append("")
    lines.append(f"{_error_rate(logs):.2%} of log lines were ERROR/CRITICAL.")
    lines.append("")

    lines.append("## Eval pass rate over time (last 10 values)")
    lines.append("")
    accs = _last_n_metric(metrics, "kde_eval_component_accuracy")
    if not accs:
        lines.append("_no kde_eval_component_accuracy values yet_")
    else:
        lines.append("```")
        for v in accs:
            lines.append(f"{v:.4f}")
        lines.append("```")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


if __name__ == "__main__":  # pragma: no cover - manual entry
    print(build_report())
