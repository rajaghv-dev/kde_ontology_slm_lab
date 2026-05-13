"""Stable identifier construction for ontology entities.

A traceability system is only as good as its identifiers. We derive each
entity's id from (entity_type, qualified_name) so the same class produces the
same id across runs, across machines, across the dataset pipeline, and across
RAG queries.
"""
from __future__ import annotations

import hashlib


def make_id(entity_type: str, qualified_name: str) -> str:
    """Return a short, deterministic id for an entity.

    Format: ``kde:<entity_type>:<8-char-hash>``. The hash is over the lower-cased
    qualified name so capitalisation variations (e.g. CMake target casing)
    don't produce duplicates.
    """
    h = hashlib.sha1(qualified_name.lower().encode("utf-8")).hexdigest()[:8]
    return f"kde:{entity_type}:{h}"


def trace_id() -> str:
    """Return a short id usable to correlate one pipeline run across logs."""
    import os, time
    raw = f"{os.getpid()}-{time.time_ns()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
