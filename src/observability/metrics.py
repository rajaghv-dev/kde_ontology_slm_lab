"""Metrics primitives with a JSON-sink default and an optional Prometheus sink.

Learning notes
--------------
A metric is a stream of numeric observations carrying a name and a small set of
labels. In production you point that stream at Prometheus. In a learning lab
you usually want it durable, diff-able, and queryable from a notebook --
JSONL on disk is perfect for that.

This module gives you both:

* The **JSON sink** is always on. Every observation is appended to
  ``artifacts/metrics/run-<trace_id>.jsonl`` as one record per line.
* The **Prometheus sink** is opt-in. If ``prometheus_client`` is importable,
  Counter/Gauge/Histogram objects are also created and updated in-process,
  ready to be served by ``start_http_server``.

Safe-label policy
~~~~~~~~~~~~~~~~~
High-cardinality labels (file paths, symbol ids, trace ids, ...) blow up
Prometheus's index, so they are forbidden at the *label* level. They still
appear in the JSONL because that sink is just an append-only file. Any
forbidden label raises ``ValueError`` so mistakes surface at runtime.
"""
from __future__ import annotations

import json
import os
import threading
import time
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.common.ids import trace_id as _new_trace_id
from src.common.paths import ARTIFACTS

# ---------------------------------------------------------------------------
# Label policy
# ---------------------------------------------------------------------------

ALLOWED_LABELS: frozenset[str] = frozenset(
    {"repo", "component", "task_type", "split", "model_family", "adapter_name"}
)
FORBIDDEN_LABELS: frozenset[str] = frozenset(
    {"file_path", "symbol_id", "trace_id", "question_id", "dataset_example_id"}
)


def _validate_labels(labels: dict[str, str] | None) -> dict[str, str]:
    """Reject high-cardinality labels and unknown keys with a clear error."""
    if not labels:
        return {}
    bad_forbidden = set(labels) & FORBIDDEN_LABELS
    if bad_forbidden:
        raise ValueError(
            f"forbidden high-cardinality labels: {sorted(bad_forbidden)}. "
            f"allowed labels are: {sorted(ALLOWED_LABELS)}"
        )
    bad_unknown = set(labels) - ALLOWED_LABELS
    if bad_unknown:
        raise ValueError(
            f"unknown labels: {sorted(bad_unknown)}. "
            f"allowed labels are: {sorted(ALLOWED_LABELS)}"
        )
    # normalise to strings, since prometheus_client requires str label values
    return {k: str(v) for k, v in labels.items()}


# ---------------------------------------------------------------------------
# Sinks
# ---------------------------------------------------------------------------

_METRICS_DIR = ARTIFACTS / "metrics"
_TRACE_ID_ENV = "KDE_OBS_TRACE_ID"
_PROM_WARNED = False
_LOCK = threading.Lock()
_RUN_TRACE_ID: str | None = None
_RUN_FILE: Path | None = None


def _resolve_run_file() -> Path:
    """Return (and cache) the JSONL path for this process's run."""
    global _RUN_TRACE_ID, _RUN_FILE
    if _RUN_FILE is not None:
        return _RUN_FILE
    _METRICS_DIR.mkdir(parents=True, exist_ok=True)
    tid = os.environ.get(_TRACE_ID_ENV) or _new_trace_id()
    os.environ.setdefault(_TRACE_ID_ENV, tid)
    _RUN_TRACE_ID = tid
    _RUN_FILE = _METRICS_DIR / f"run-{tid}.jsonl"
    return _RUN_FILE


def _write_record(metric: str, value: float, labels: dict[str, str]) -> None:
    """Append one observation to the JSON sink. Thread-safe."""
    record = {
        "ts": time.time(),
        "metric": metric,
        "value": value,
        "labels": labels,
    }
    line = json.dumps(record, sort_keys=True) + "\n"
    path = _resolve_run_file()
    with _LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)


# ---------------------------------------------------------------------------
# Lazy Prometheus backend
# ---------------------------------------------------------------------------

_PROM: Any = None
_PROM_OBJECTS: dict[tuple[str, str], Any] = {}


def _prom() -> Any | None:
    """Return ``prometheus_client`` if available, else None (once-warned)."""
    global _PROM, _PROM_WARNED
    if _PROM is not None:
        return _PROM
    try:  # pragma: no cover - dep is optional
        import prometheus_client as _pc

        _PROM = _pc
        return _PROM
    except ImportError:
        if not _PROM_WARNED:
            warnings.warn(
                "prometheus_client not installed; metrics will only be written "
                "to artifacts/metrics/*.jsonl. Install it to also expose a "
                "Prometheus endpoint.",
                stacklevel=3,
            )
            _PROM_WARNED = True
        return None


def _prom_object(kind: str, name: str, label_keys: tuple[str, ...]) -> Any | None:
    """Get-or-create a prometheus_client object, keyed by (kind, name)."""
    pc = _prom()
    if pc is None:
        return None
    key = (kind, name)
    if key in _PROM_OBJECTS:
        return _PROM_OBJECTS[key]
    if kind == "counter":
        obj = pc.Counter(name, name, list(label_keys))
    elif kind == "gauge":
        obj = pc.Gauge(name, name, list(label_keys))
    elif kind == "histogram":
        obj = pc.Histogram(name, name, list(label_keys))
    else:  # pragma: no cover - defensive
        raise ValueError(f"unknown prom metric kind: {kind}")
    _PROM_OBJECTS[key] = obj
    return obj


# ---------------------------------------------------------------------------
# Thin wrappers exposed as the public API
# ---------------------------------------------------------------------------


class _Base:
    """Common machinery: validate labels, record into the JSON sink."""

    kind: str = ""

    def __init__(self, name: str, labels: dict[str, str] | None = None) -> None:
        self.name = name
        self.labels = _validate_labels(labels)
        # eagerly construct the prom object so labels-keys are stable
        self._prom_obj = _prom_object(self.kind, name, tuple(self.labels))

    def _record(self, value: float) -> None:
        _write_record(self.name, value, self.labels)

    def _prom_labelled(self) -> Any | None:
        if self._prom_obj is None:
            return None
        if not self.labels:
            return self._prom_obj
        return self._prom_obj.labels(**self.labels)


class Counter(_Base):
    kind = "counter"

    def inc(self, value: float = 1.0) -> None:
        if value < 0:
            raise ValueError("counters cannot decrease")
        self._record(value)
        p = self._prom_labelled()
        if p is not None:  # pragma: no cover - optional dep
            p.inc(value)


class Gauge(_Base):
    kind = "gauge"

    def set(self, value: float) -> None:
        self._record(value)
        p = self._prom_labelled()
        if p is not None:  # pragma: no cover - optional dep
            p.set(value)

    def inc(self, value: float = 1.0) -> None:
        self._record(value)
        p = self._prom_labelled()
        if p is not None:  # pragma: no cover - optional dep
            p.inc(value)

    def dec(self, value: float = 1.0) -> None:
        self._record(-value)
        p = self._prom_labelled()
        if p is not None:  # pragma: no cover - optional dep
            p.dec(value)


class Histogram(_Base):
    kind = "histogram"

    def observe(self, value: float) -> None:
        self._record(value)
        p = self._prom_labelled()
        if p is not None:  # pragma: no cover - optional dep
            p.observe(value)


# ---------------------------------------------------------------------------
# Factory helpers + time_block
# ---------------------------------------------------------------------------


def counter(name: str, labels: dict[str, str] | None = None) -> Counter:
    """Return a new ``Counter`` bound to ``name`` and validated ``labels``."""
    return Counter(name, labels)


def gauge(name: str, labels: dict[str, str] | None = None) -> Gauge:
    """Return a new ``Gauge`` bound to ``name`` and validated ``labels``."""
    return Gauge(name, labels)


def histogram(name: str, labels: dict[str, str] | None = None) -> Histogram:
    """Return a new ``Histogram`` bound to ``name`` and validated ``labels``."""
    return Histogram(name, labels)


@contextmanager
def time_block(metric_name: str, labels: dict[str, str] | None = None):
    """Measure wall-clock time of a code block and emit a histogram observation."""
    h = histogram(metric_name, labels)
    t0 = time.perf_counter()
    try:
        yield h
    finally:
        elapsed = time.perf_counter() - t0
        h.observe(elapsed)


def start_http_server(port: int = 9101) -> None:
    """Expose the Prometheus metrics endpoint, if the optional dep is installed.

    A no-op (with a one-time warning) when ``prometheus_client`` is unavailable.
    """
    pc = _prom()
    if pc is None:
        return
    pc.start_http_server(port)  # pragma: no cover - optional dep
