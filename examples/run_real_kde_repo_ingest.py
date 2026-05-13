"""Ingest + graph build against a real (user-supplied) KDE repo checkout.

Why this script exists
----------------------
The lab's vertical slice (``examples/run_mini_repo_pipeline.py``) runs against
the synthetic ``examples/mini_kde_repo``. This script is the equivalent for a
*real* KDE module the learner has cloned themselves — e.g. ``kio``,
``plasma-workspace``, or ``baloo``.

It deliberately stops at the *graph* step: the downstream dataset / RAG /
eval steps are independent of repo size and the vertical-slice driver
covers them.

Usage:
    python examples/run_real_kde_repo_ingest.py --repo /path/to/kio
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the repo importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.ids import make_id, trace_id
from src.common.logging import get_logger
from src.common.paths import GRAPHS_DIR, ensure_dirs
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest a real KDE repo and build the graph.")
    p.add_argument("--repo", required=True, type=Path,
                   help="Path to a KDE module checkout (e.g. /path/to/kio).")
    p.add_argument("--name", default=None,
                   help="Override the repo name used for the output filenames.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    ensure_dirs()
    log = get_logger("examples.real_repo_ingest")
    tid = trace_id()

    repo = args.repo
    if not repo.exists():
        log.error(f"repo not found at {repo}")
        return 1

    name = args.name or repo.name
    log.info(f"trace={tid} scanning {repo}")
    report = scan(repo)
    log.info(f"trace={tid} scanned {len(report.files)} files")

    bundle = ExtractionBundle()
    repo_id = bundle.add_entity(Entity(
        id=make_id("Repository", name), type="Repository",
        name=name, source_path=str(repo),
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

    g = build_graph(bundle)
    jp = save_json(g, GRAPHS_DIR / f"{name}.json")
    gp = save_graphml(g, GRAPHS_DIR / f"{name}.graphml")
    log.info(f"trace={tid} graph saved: {jp}, {gp}")

    print(f"repo                : {repo}")
    print(f"files scanned       : {len(report.files)}")
    print(f"entities            : {len(bundle.entities)}")
    print(f"relations           : {len(bundle.relations)}")
    print(f"graph (json)        : {jp}")
    print(f"graph (graphml)     : {gp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
