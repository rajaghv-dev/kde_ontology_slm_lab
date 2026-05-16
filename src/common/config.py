"""YAML config loader. Falls back to sensible defaults so the lab runs without
any config tuning.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursive dict merge: overlay wins for scalars; nested dicts are merged."""
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_yaml(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load a YAML file, returning ``default`` (or ``{}``) when the file is absent."""
    if not path.exists():
        return dict(default or {})
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected a YAML mapping at top level of {path}, got {type(data).__name__}")
    return data
