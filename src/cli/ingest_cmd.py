"""`kde-lab ingest` — scan a repo, run per-format readers, persist the ontology + graph."""
from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("ingest", help="Scan a repo and extract ontology + graph artifacts.")
    @click.option("--repo", "repo_name", default="mini_kde_repo", show_default=True,
                  help="Name of an entry in configs/repos.yaml (must be enabled).")
    def ingest(repo_name: str) -> None:
        # Lazy imports: pulls in networkx, the readers, and the extractor.
        from pathlib import Path

        from src.common.config import load_yaml
        from src.common.ids import make_id
        from src.common.logging import get_logger
        from src.common.paths import CONFIGS, GRAPHS_DIR, ONTOLOGY_DIR, REPO_ROOT, ensure_dirs
        from src.dataset.jsonl_writer import write_jsonl
        from src.graph.builder import build_graph, save_graphml, save_json
        from src.ontology.extractor import (
            ExtractionBundle,
            from_cmake,
            from_cpp,
            from_dbus,
            from_desktop,
            from_kconfig,
            from_log,
            from_qml,
        )
        from src.ontology.schema import Entity
        from src.repo_ingest.cmake_reader import read_cmake
        from src.repo_ingest.cpp_reader import read_cpp
        from src.repo_ingest.dbus_reader import read_dbus
        from src.repo_ingest.desktop_file_reader import read_desktop
        from src.repo_ingest.kconfig_reader import read_kconfig
        from src.repo_ingest.log_reader import read_log
        from src.repo_ingest.qml_reader import read_qml
        from src.repo_ingest.scanner import scan

        log = get_logger("cli.ingest")
        ensure_dirs()

        cfg = load_yaml(CONFIGS / "repos.yaml")
        repos = cfg.get("repos", []) or []
        entry = next((r for r in repos if r.get("name") == repo_name), None)
        if entry is None:
            raise click.ClickException(
                f"repo {repo_name!r} not found in configs/repos.yaml; "
                f"known: {[r.get('name') for r in repos]}"
            )
        if not entry.get("enabled", False):
            raise click.ClickException(
                f"repo {repo_name!r} is disabled in configs/repos.yaml; "
                f"flip enabled: true after pointing path: at a real checkout."
            )

        repo_path = Path(entry["path"])
        if not repo_path.is_absolute():
            repo_path = (REPO_ROOT / repo_path).resolve()
        if not repo_path.exists():
            raise click.ClickException(f"path does not exist: {repo_path}")

        log.info(f"scanning {repo_path}")
        report = scan(repo_path)
        log.info(f"scanned {len(report.files)} files")

        bundle = ExtractionBundle()
        repo_id = bundle.add_entity(Entity(
            id=make_id("Repository", repo_path.name),
            type="Repository", name=repo_path.name, source_path=str(repo_path),
        ))
        for sf in report.by_kind("cmake"):
            from_cmake(bundle, read_cmake(sf.path), repo_id)
        for sf in report.by_kind("cpp_header") + report.by_kind("cpp_source"):
            from_cpp(bundle, read_cpp(sf.path))
        for sf in report.by_kind("qml"):
            from_qml(bundle, read_qml(sf.path))
        for sf in report.by_kind("dbus"):
            from_dbus(bundle, read_dbus(sf.path))
        for sf in report.by_kind("kconfig"):
            from_kconfig(bundle, read_kconfig(sf.path))
        for sf in report.by_kind("desktop"):
            from_desktop(bundle, read_desktop(sf.path))
        for sf in report.by_kind("log"):
            from_log(bundle, read_log(sf.path))

        # Persist ontology entities for later graph rebuilds.
        onto_path = ONTOLOGY_DIR / f"{repo_name}_entities.jsonl"
        n_ent = write_jsonl(onto_path, [e.__dict__ for e in bundle.entities.values()])
        rel_path = ONTOLOGY_DIR / f"{repo_name}_relations.jsonl"
        n_rel = write_jsonl(rel_path, [r.__dict__ for r in bundle.relations])

        # Build and save the graph immediately so the rest of the pipeline can use it.
        g = build_graph(bundle)
        json_path = save_json(g, GRAPHS_DIR / f"{repo_name}.json")
        graphml_path = save_graphml(g, GRAPHS_DIR / f"{repo_name}.graphml")

        click.echo(f"entities written     : {n_ent}  ({onto_path})")
        click.echo(f"relations written    : {n_rel}  ({rel_path})")
        click.echo(f"graph json           : {json_path}")
        click.echo(f"graph graphml        : {graphml_path}")
