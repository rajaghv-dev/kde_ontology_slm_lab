"""Top-level `kde-lab` CLI.

This module wires a click group and delegates each subcommand to its own
file in `src/cli/`. Heavy imports (networkx, the readers, the dataset
generator) live inside the per-command handlers so plain `kde-lab info`
stays fast and dependency-light.

Run it via the console-script entry point declared in pyproject.toml:

    kde-lab --help
    kde-lab info
    kde-lab pipeline
"""
from __future__ import annotations

import click


@click.group(help="kde_ontology_slm_lab — KDE-aware small-language-model lab.")
@click.version_option(message="%(version)s", package_name="kde-ontology-slm-lab")
def cli() -> None:
    """Root command group. Subcommands are registered below."""


def _register_all() -> None:
    """Attach every subcommand to the root group.

    Each command module exposes a `register(cli)` function so we never
    import the heavy bits until the user actually calls the subcommand.
    """
    # Lazy imports so `kde-lab --help` and `kde-lab info` stay cheap.
    from src.cli import (
        dataset_cmd,
        eval_cmd,
        graph_cmd,
        ingest_cmd,
        tokenizer_cmd,
        train_cmd,
    )

    ingest_cmd.register(cli)
    graph_cmd.register(cli)
    tokenizer_cmd.register(cli)
    dataset_cmd.register(cli)
    train_cmd.register(cli)
    eval_cmd.register(cli)


@cli.command("info", help="Print versions, paths, and what each config enables.")
def info_cmd() -> None:
    """Lightweight diagnostic that loads only the YAML configs."""
    import platform
    import sys

    from src.common.config import load_yaml
    from src.common.paths import (
        ARTIFACTS,
        CONFIGS,
        DATASETS,
        MINI_REPO,
        REPO_ROOT,
    )

    click.echo("kde-lab info")
    click.echo("-" * 60)
    click.echo(f"python              : {sys.version.split()[0]} ({platform.platform()})")
    click.echo(f"repo root           : {REPO_ROOT}")
    click.echo(f"configs dir         : {CONFIGS}")
    click.echo(f"artifacts dir       : {ARTIFACTS}")
    click.echo(f"datasets dir        : {DATASETS}")
    click.echo(f"mini kde repo       : {MINI_REPO}  "
               f"(exists={MINI_REPO.exists()})")

    click.echo("")
    click.echo("Configs:")
    for fname in ("repos.yaml", "models.yaml", "tokenizer.yaml", "ontology.yaml",
                  "dataset.yaml", "training.yaml", "eval.yaml"):
        path = CONFIGS / fname
        data = load_yaml(path)
        click.echo(f"  - {fname:<16}  exists={path.exists()}  "
                   f"top_keys={sorted(list(data.keys()))[:6]}")

    # Per-config feature summary (deliberately shallow; details belong in the
    # subcommands themselves).
    repos = load_yaml(CONFIGS / "repos.yaml").get("repos", []) or []
    enabled_repos = [r.get("name") for r in repos if r.get("enabled")]
    click.echo("")
    click.echo(f"enabled repos       : {enabled_repos or '(none)'}")

    models = load_yaml(CONFIGS / "models.yaml").get("models", {}) or {}
    click.echo(f"declared models     : {sorted(models.keys())}")

    ds = load_yaml(CONFIGS / "dataset.yaml").get("generators", {}) or {}
    on_gens = [k for k, v in ds.items() if v]
    click.echo(f"dataset generators  : {on_gens or '(none)'}")

    ev = load_yaml(CONFIGS / "eval.yaml").get("benchmarks", []) or []
    click.echo(f"eval benchmarks     : {ev or '(none)'}")


@cli.command("pipeline", help="Run the full vertical slice on the mini repo.")
def pipeline_cmd() -> None:
    """Delegate to examples/run_mini_repo_pipeline.py.

    The script itself adds the repo root to sys.path and emits its own
    summary banner, so we just call its main() and forward the exit code.
    """
    # Lazy import: the pipeline pulls in networkx, the per-format readers,
    # and the extractor — we don't want to load any of that for `info`.
    from examples.run_mini_repo_pipeline import main as run_pipeline
    raise SystemExit(run_pipeline())


def main() -> None:
    """Entry point declared in pyproject.toml's [project.scripts].

    Registers all subcommands then hands off to click.
    """
    _register_all()
    cli()


if __name__ == "__main__":
    main()
