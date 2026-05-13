"""Observability stack for kde_ontology_slm_lab.

Why a dedicated package?
------------------------
The lab follows the "OCT" framework (Observability, Control, Traceability).
Every pipeline action emits a structured event so a learner can later answer
"what happened, why, and how did inputs flow through the system?" without
rerunning the pipeline.

Two modes
~~~~~~~~~
1. **No-install mode (default).** Metrics are appended as JSONL under
   ``artifacts/metrics/run-<trace_id>.jsonl``. Logs go to
   ``artifacts/logs/run-<trace_id>.jsonl``. No Docker, no Prometheus, no
   Grafana. Everything still works.
2. **Local docker-compose mode (opt-in).** When ``prometheus_client`` is
   installed and ``observability/docker-compose.yml`` is brought up, the same
   API also exports Prometheus counters/gauges/histograms and OTLP traces.

The default code path **must never** require optional deps. Every optional
backend is lazy-imported and silently disabled if missing.
"""
from __future__ import annotations

from .metrics import (
    Counter,
    Gauge,
    Histogram,
    counter,
    gauge,
    histogram,
    start_http_server,
    time_block,
)
from .logger import get_obs_logger
from .traces import span

__all__ = [
    "Counter",
    "Gauge",
    "Histogram",
    "counter",
    "gauge",
    "histogram",
    "histogram",
    "start_http_server",
    "time_block",
    "get_obs_logger",
    "span",
]
