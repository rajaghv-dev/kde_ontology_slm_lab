"""Canonical paths for the lab.

A learning project benefits from one place that resolves paths so each subsystem
does not roll its own. Every other module imports from here.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MINI_REPO = REPO_ROOT / "examples" / "mini_kde_repo"
ARTIFACTS = REPO_ROOT / "artifacts"
DATASETS = REPO_ROOT / "datasets"
CONFIGS = REPO_ROOT / "configs"

# Per-subsystem artifact dirs
GRAPHS_DIR = ARTIFACTS / "graphs"
ONTOLOGY_DIR = ARTIFACTS / "ontology"
TOKENIZER_DIR = ARTIFACTS / "tokenizer_reports"
DATASETS_OUT_DIR = ARTIFACTS / "datasets"
EVAL_DIR = ARTIFACTS / "eval_reports"
LOGS_DIR = ARTIFACTS / "logs"
PLOTS_DIR = ARTIFACTS / "plots"


def ensure_dirs() -> None:
    """Make sure every artifact subdir exists. Cheap and idempotent."""
    for p in (GRAPHS_DIR, ONTOLOGY_DIR, TOKENIZER_DIR, DATASETS_OUT_DIR,
              EVAL_DIR, LOGS_DIR, PLOTS_DIR):
        p.mkdir(parents=True, exist_ok=True)
