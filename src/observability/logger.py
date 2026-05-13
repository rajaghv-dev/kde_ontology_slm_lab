"""Structured JSON logger for the observability stack.

Two destinations, one log call:
* stderr -- human-readable, the same format ``src.common.logging`` already uses.
* ``artifacts/logs/run-<trace_id>.jsonl`` -- one JSON object per line, easy for
  Loki / jq / pandas to ingest.

Why both? When you're at the terminal, you want colourless plain text. When
you're debugging a past run or feeding Grafana/Loki, you want structured fields.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from src.common.ids import trace_id as _new_trace_id
from src.common.logging import get_logger as _get_text_logger
from src.common.paths import LOGS_DIR

_TRACE_ID_ENV = "KDE_OBS_TRACE_ID"
_CONFIGURED: dict[str, logging.Logger] = {}


def _resolve_trace_id() -> str:
    tid = os.environ.get(_TRACE_ID_ENV)
    if not tid:
        tid = _new_trace_id()
        os.environ[_TRACE_ID_ENV] = tid
    return tid


class _JsonlFileHandler(logging.Handler):
    """Append each log record as one JSON object to a per-run JSONL file."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            payload: dict[str, Any] = {
                "ts": time.time(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            # Trace id is attached either via LoggerAdapter (.extra) or env.
            trace = getattr(record, "trace", None) or os.environ.get(_TRACE_ID_ENV)
            if trace:
                payload["trace"] = trace
            if record.exc_info:
                payload["exc_info"] = self.format(record).splitlines()[-5:]
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, sort_keys=True) + "\n")
        except Exception:  # pragma: no cover - never let logging blow up callers
            self.handleError(record)


def get_obs_logger(name: str, trace: str | None = None) -> logging.Logger | logging.LoggerAdapter:
    """Return a logger that writes both human text and JSONL.

    Reuses :func:`src.common.logging.get_logger` for the stderr handler and
    attaches a JSONL file handler keyed on the current run's trace id. Multiple
    calls are idempotent.
    """
    tid = trace or _resolve_trace_id()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = LOGS_DIR / f"run-{tid}.jsonl"

    text_logger = _get_text_logger(name, trace=tid)
    # text_logger may already be an adapter; we want the underlying Logger to
    # attach handlers exactly once.
    underlying = text_logger.logger if isinstance(text_logger, logging.LoggerAdapter) else text_logger

    key = f"{underlying.name}:{jsonl_path}"
    if key not in _CONFIGURED:
        # avoid duplicate file handlers if a parent logger already has one
        already = any(
            isinstance(h, _JsonlFileHandler) and h.path == jsonl_path
            for h in underlying.handlers
        )
        if not already:
            underlying.addHandler(_JsonlFileHandler(jsonl_path))
        _CONFIGURED[key] = underlying
    return text_logger
