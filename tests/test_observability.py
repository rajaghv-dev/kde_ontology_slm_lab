"""Tests for the no-install observability stack.

We exercise:
* counter increments and gauge set/inc/dec,
* histogram observation,
* forbidden / unknown labels raising ValueError,
* the JSON sink writing valid JSONL,
* ``time_block`` measuring something non-zero,
* spans nesting parent/child correctly,
* the report rolling up metrics + logs.

Tests redirect the JSONL output to a per-test tmp dir by monkeypatching the
module-level path constants. We do not require ``prometheus_client``.
"""
from __future__ import annotations

import importlib
import json
import time
from pathlib import Path

import pytest


@pytest.fixture()
def obs(monkeypatch, tmp_path: Path):
    """Reload observability modules with artifact paths pointing at tmp_path."""
    metrics_dir = tmp_path / "metrics"
    logs_dir = tmp_path / "logs"
    eval_dir = tmp_path / "eval_reports"
    metrics_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    eval_dir.mkdir(parents=True)

    # Force a fresh trace id and clear any cached run file in modules.
    monkeypatch.setenv("KDE_OBS_TRACE_ID", "test00trace")

    import src.observability.metrics as metrics_mod
    import src.observability.logger as logger_mod
    import src.observability.traces as traces_mod
    import src.observability.report as report_mod

    importlib.reload(metrics_mod)
    importlib.reload(logger_mod)
    importlib.reload(traces_mod)
    importlib.reload(report_mod)

    monkeypatch.setattr(metrics_mod, "_METRICS_DIR", metrics_dir)
    monkeypatch.setattr(metrics_mod, "_RUN_FILE", None)
    monkeypatch.setattr(logger_mod, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(traces_mod, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(report_mod, "METRICS_DIR", metrics_dir)
    monkeypatch.setattr(report_mod, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(report_mod, "REPORT_PATH", eval_dir / "observability_report.md")

    return {
        "metrics": metrics_mod,
        "logger": logger_mod,
        "traces": traces_mod,
        "report": report_mod,
        "metrics_dir": metrics_dir,
        "logs_dir": logs_dir,
        "eval_dir": eval_dir,
    }


def _read_metric_rows(metrics_dir: Path) -> list[dict]:
    rows = []
    for p in sorted(metrics_dir.glob("run-*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def test_counter_inc_writes_jsonl(obs):
    c = obs["metrics"].counter("kde_ingest_files_total", {"repo": "miniA"})
    c.inc()
    c.inc(2)
    rows = _read_metric_rows(obs["metrics_dir"])
    assert len(rows) == 2
    assert rows[0]["metric"] == "kde_ingest_files_total"
    assert rows[0]["value"] == 1.0
    assert rows[1]["value"] == 2.0
    assert rows[0]["labels"] == {"repo": "miniA"}


def test_counter_rejects_negative(obs):
    c = obs["metrics"].counter("kde_ingest_files_total", {"repo": "x"})
    with pytest.raises(ValueError):
        c.inc(-1)


def test_gauge_set_inc_dec(obs):
    g = obs["metrics"].gauge("kde_graph_nodes_total", {"repo": "miniA"})
    g.set(10)
    g.inc(2)
    g.dec(5)
    rows = _read_metric_rows(obs["metrics_dir"])
    values = [r["value"] for r in rows]
    assert values == [10.0, 2.0, -5.0]


def test_histogram_observes(obs):
    h = obs["metrics"].histogram("kde_rag_latency_seconds", {"component": "rag"})
    h.observe(0.123)
    rows = _read_metric_rows(obs["metrics_dir"])
    assert rows[0]["metric"] == "kde_rag_latency_seconds"
    assert rows[0]["value"] == pytest.approx(0.123)


def test_forbidden_labels_raise(obs):
    with pytest.raises(ValueError, match="forbidden"):
        obs["metrics"].counter("kde_ingest_files_total", {"file_path": "/x"})
    with pytest.raises(ValueError, match="forbidden"):
        obs["metrics"].counter("kde_ingest_files_total", {"trace_id": "abc"})


def test_unknown_labels_raise(obs):
    with pytest.raises(ValueError, match="unknown"):
        obs["metrics"].counter("kde_ingest_files_total", {"nope": "x"})


def test_time_block_records_positive_duration(obs):
    with obs["metrics"].time_block("kde_answer_latency_seconds", {"component": "rag"}):
        time.sleep(0.01)
    rows = _read_metric_rows(obs["metrics_dir"])
    assert rows[-1]["metric"] == "kde_answer_latency_seconds"
    assert rows[-1]["value"] >= 0.005


def test_jsonl_is_valid_json_per_line(obs):
    c = obs["metrics"].counter("kde_ingest_symbols_total", {"repo": "miniA"})
    for _ in range(5):
        c.inc()
    path = next(obs["metrics_dir"].glob("run-*.jsonl"))
    for line in path.read_text().splitlines():
        assert json.loads(line)  # raises on bad json


def test_span_nesting(obs):
    with obs["traces"].span("stage_a", {"component": "ingest"}) as outer:
        with obs["traces"].span("stage_b", {"component": "ontology"}) as inner:
            pass
    span_files = list(obs["logs_dir"].glob("traces-*.jsonl"))
    assert span_files, "no spans written"
    spans = [json.loads(l) for l in span_files[0].read_text().splitlines() if l.strip()]
    assert {s["name"] for s in spans} == {"stage_a", "stage_b"}
    by_name = {s["name"]: s for s in spans}
    assert by_name["stage_b"]["parent_id"] == by_name["stage_a"]["span_id"]
    assert by_name["stage_a"]["parent_id"] is None
    # both ended
    assert by_name["stage_a"]["end_ns"] >= by_name["stage_a"]["start_ns"]


def test_report_rolls_up(obs):
    obs["metrics"].counter("kde_ingest_files_total", {"repo": "miniA"}).inc()
    g = obs["metrics"].gauge("kde_eval_component_accuracy", {"split": "val"})
    g.set(0.81)
    with obs["traces"].span("ingest"):
        time.sleep(0.001)
    out = obs["report"].build_report()
    assert out.exists()
    text = out.read_text()
    assert "Observability report" in text
    assert "ingest" in text
    assert "0.81" in text or "0.8100" in text


def test_start_http_server_is_safe_without_prom(obs):
    # If prometheus_client is not installed, this must not raise.
    obs["metrics"].start_http_server(port=0)
