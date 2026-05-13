"""Minimal trace-span helper.

A trace is a tree of spans. Each span captures "this much wall-clock time was
spent doing this named thing, with these labels, while we held this parent."
Even without an OTLP collector, having spans on disk lets a learner explain
why one pipeline run was slow vs. another.

If ``opentelemetry`` happens to be installed, the same context manager also
emits a real OTLP span so Grafana Tempo can render the timeline. Otherwise it
silently no-ops the OTel side and just writes JSONL.
"""
from __future__ import annotations

import contextvars
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.common.ids import trace_id as _new_trace_id
from src.common.paths import LOGS_DIR
from .metrics import _validate_labels

_TRACE_ID_ENV = "KDE_OBS_TRACE_ID"
_LOCK = threading.Lock()
_CURRENT_SPAN: contextvars.ContextVar["Span | None"] = contextvars.ContextVar(
    "kde_obs_current_span", default=None
)


def _resolve_trace_id() -> str:
    tid = os.environ.get(_TRACE_ID_ENV)
    if not tid:
        tid = _new_trace_id()
        os.environ[_TRACE_ID_ENV] = tid
    return tid


def _spans_file(trace_id: str) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"traces-{trace_id}.jsonl"


@dataclass
class Span:
    """One node in the trace tree."""

    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    start_ns: int
    end_ns: int | None = None
    labels: dict[str, str] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "labels": dict(self.labels),
        }


# ---------------------------------------------------------------------------
# Optional OpenTelemetry backend (lazy)
# ---------------------------------------------------------------------------

_OTEL_TRACER: Any = None
_OTEL_TRIED = False


def _otel_tracer() -> Any | None:
    global _OTEL_TRACER, _OTEL_TRIED
    if _OTEL_TRIED:
        return _OTEL_TRACER
    _OTEL_TRIED = True
    try:  # pragma: no cover - optional dep
        from opentelemetry import trace as otel_trace

        _OTEL_TRACER = otel_trace.get_tracer("kde_ontology_slm_lab")
    except ImportError:
        _OTEL_TRACER = None
    return _OTEL_TRACER


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@contextmanager
def span(name: str, labels: dict[str, str] | None = None):
    """Open a span; yields the Span object so callers can attach extra fields."""
    validated = _validate_labels(labels)
    parent = _CURRENT_SPAN.get()
    trace_id = parent.trace_id if parent else _resolve_trace_id()
    new_span = Span(
        name=name,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        parent_id=parent.span_id if parent else None,
        start_ns=time.time_ns(),
        labels=validated,
    )
    token = _CURRENT_SPAN.set(new_span)

    otel_cm = None
    tracer = _otel_tracer()
    if tracer is not None:  # pragma: no cover - optional dep
        otel_cm = tracer.start_as_current_span(name)
        otel_cm.__enter__()

    try:
        yield new_span
    finally:
        new_span.end_ns = time.time_ns()
        # write to JSONL sink, always
        path = _spans_file(trace_id)
        with _LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(new_span.to_record(), sort_keys=True) + "\n")
        if otel_cm is not None:  # pragma: no cover - optional dep
            otel_cm.__exit__(None, None, None)
        _CURRENT_SPAN.reset(token)
