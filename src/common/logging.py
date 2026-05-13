"""One log configuration for the entire lab.

The lab follows the OCT framework: every pipeline action emits a structured log
line tagged with a trace id so you can connect cause to effect across modules
even without a Prometheus/Loki stack installed.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def get_logger(name: str, trace: str | None = None) -> logging.Logger:
    """Return a configured logger. Idempotent: first call configures the root."""
    global _CONFIGURED
    if not _CONFIGURED:
        h = logging.StreamHandler(sys.stderr)
        fmt = "%(asctime)s %(levelname)-5s %(name)s %(message)s"
        h.setFormatter(logging.Formatter(fmt))
        root = logging.getLogger()
        root.handlers = [h]
        root.setLevel(logging.INFO)
        _CONFIGURED = True
    log = logging.getLogger(name)
    if trace:
        log = logging.LoggerAdapter(log, {"trace": trace})  # type: ignore[assignment]
    return log
