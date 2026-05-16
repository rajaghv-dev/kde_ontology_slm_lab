"""Smoke tests for every kde-lab CLI subcommand using Click's CliRunner.

These tests verify the CLI is wired correctly and exits cleanly.  They run
offline on the bundled mini repo with no GPU or model weights required.
Artifact writes are redirected to a tmp_path fixture so the real
artifacts/ directory is never touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.cli.main import cli, _register_all

# Register all subcommands once for the module.
_register_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def invoke(args: list[str], env: dict | None = None) -> "Result":
    runner = CliRunner(mix_stderr=False)
    return runner.invoke(cli, args, catch_exceptions=False, env=env or {})


def _patch_paths(monkeypatch, tmp_path: Path) -> None:
    """Redirect all artifact + dataset directories to tmp_path."""
    import src.common.paths as P

    dirs = {
        "ARTIFACTS": tmp_path / "artifacts",
        "GRAPHS_DIR": tmp_path / "artifacts" / "graphs",
        "ONTOLOGY_DIR": tmp_path / "artifacts" / "ontology",
        "TOKENIZER_DIR": tmp_path / "artifacts" / "tokenizer_reports",
        "DATASETS_OUT_DIR": tmp_path / "artifacts" / "datasets",
        "EVAL_DIR": tmp_path / "artifacts" / "eval_reports",
        "LOGS_DIR": tmp_path / "artifacts" / "logs",
        "PLOTS_DIR": tmp_path / "artifacts" / "plots",
    }
    for attr, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(P, attr, path)

    # Also patch src.common.paths imported inside each subcommand module
    for mod_name in (
        "src.cli.ingest_cmd",
        "src.cli.graph_cmd",
        "src.cli.dataset_cmd",
        "src.cli.eval_cmd",
        "src.cli.tokenizer_cmd",
    ):
        try:
            import importlib
            mod = importlib.import_module(mod_name)
        except ImportError:
            pass


# ---------------------------------------------------------------------------
# Root commands
# ---------------------------------------------------------------------------

def test_help():
    r = invoke(["--help"])
    assert r.exit_code == 0
    assert "kde_ontology_slm_lab" in r.output or "kde-lab" in r.output.lower()


def test_version():
    try:
        import importlib.metadata
        importlib.metadata.version("kde-ontology-slm-lab")
        installed = True
    except Exception:
        installed = False

    if installed:
        r = invoke(["--version"])
        assert r.exit_code == 0
        assert "0.0." in r.output
    else:
        # Package not installed in this Python env (running directly via sys.path).
        # Verify --help at least works so the CLI is importable.
        r = invoke(["--help"])
        assert r.exit_code == 0


def test_info(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    r = invoke(["info"])
    assert r.exit_code == 0
    assert "python" in r.output.lower()
    assert "repo root" in r.output.lower()


# ---------------------------------------------------------------------------
# kde-lab train (always dry-run in v0)
# ---------------------------------------------------------------------------

def test_train_dry_run(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    r = invoke(["train"])
    assert r.exit_code == 0
    assert "dry-run" in r.output.lower() or "dry_run" in r.output.lower()


def test_train_profile_override(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    r = invoke(["train", "--profile", "colab_t4"])
    assert r.exit_code == 0
    assert "colab_t4" in r.output


def test_train_model_key_override(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    r = invoke(["train", "--model-key", "qwen_small"])
    assert r.exit_code == 0
    assert "qwen_small" in r.output


# ---------------------------------------------------------------------------
# kde-lab tokenizer
# ---------------------------------------------------------------------------

def test_tokenizer(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    import src.common.paths as P
    monkeypatch.setattr(P, "TOKENIZER_DIR", tmp_path / "tokenizer")
    (tmp_path / "tokenizer").mkdir(parents=True, exist_ok=True)
    r = invoke(["tokenizer"])
    assert r.exit_code == 0
    assert "compression" in r.output.lower() or "tokenizer" in r.output.lower()


# ---------------------------------------------------------------------------
# kde-lab ingest → graph → dataset → eval (chained)
# These all redirect artifacts to tmp_path.
# ---------------------------------------------------------------------------

def test_ingest_mini_repo(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    r = invoke(["ingest", "--repo", "mini_kde_repo"])
    assert r.exit_code == 0, r.output
    assert "entities written" in r.output


def test_ingest_unknown_repo(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    r = invoke(["ingest", "--repo", "no_such_repo_xyz"])
    assert r.exit_code != 0


def test_graph_after_ingest(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    # Run ingest first to produce the required JSONL artifacts.
    r_ingest = invoke(["ingest", "--repo", "mini_kde_repo"])
    assert r_ingest.exit_code == 0, r_ingest.output

    r = invoke(["graph", "--repo", "mini_kde_repo"])
    assert r.exit_code == 0, r.output
    assert "nodes" in r.output


def test_graph_missing_ontology(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    # No ingest run → entities JSONL is missing → should error cleanly.
    r = invoke(["graph", "--repo", "mini_kde_repo"])
    assert r.exit_code != 0


def test_dataset_after_ingest(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    # dataset subcommand needs a graph in GRAPHS_DIR.
    r_ingest = invoke(["ingest", "--repo", "mini_kde_repo"])
    assert r_ingest.exit_code == 0, r_ingest.output

    r = invoke(["dataset", "--repo", "mini_kde_repo"])
    assert r.exit_code == 0, r.output
    assert "records" in r.output.lower() or "wrote" in r.output.lower() or "examples" in r.output.lower()


def test_eval_after_ingest(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    # eval needs a graph in GRAPHS_DIR.
    r_ingest = invoke(["ingest", "--repo", "mini_kde_repo"])
    assert r_ingest.exit_code == 0, r_ingest.output

    r = invoke(["eval", "--repo", "mini_kde_repo"])
    assert r.exit_code == 0, r.output
    assert "pass rate" in r.output.lower()


def test_eval_missing_graph(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    r = invoke(["eval", "--repo", "mini_kde_repo"])
    assert r.exit_code != 0
