"""Generate the SFT JSONL from a previously built graph.

Prerequisite: ``artifacts/graphs/mini_repo.json`` exists. Run
``python examples/run_mini_repo_pipeline.py`` first if it does not.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import networkx as nx

from src.common.logging import get_logger
from src.common.paths import DATASETS_OUT_DIR, GRAPHS_DIR, ensure_dirs
from src.dataset.jsonl_writer import write_jsonl
from src.dataset.qa_generator import generate as generate_sft


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate SFT dataset from a saved graph.")
    p.add_argument("--repo", default="mini_repo",
                   help="Which graph (in artifacts/graphs/) to read.")
    p.add_argument("--n", type=int, default=None,
                   help="Optional cap on the number of records written.")
    p.add_argument("--out", type=Path, default=None,
                   help="Override the JSONL output path.")
    return p.parse_args(argv)


def _load_graph(path: Path) -> nx.MultiDiGraph:
    with path.open("r", encoding="utf-8") as f:
        blob = json.load(f)
    g: nx.MultiDiGraph = nx.MultiDiGraph()
    for n in blob.get("nodes", []):
        nid = n["id"]
        attrs = {k: v for k, v in n.items() if k != "id"}
        g.add_node(nid, **attrs)
    for e in blob.get("edges", []):
        src, dst = e["src"], e["dst"]
        attrs = {k: v for k, v in e.items() if k not in {"src", "dst"}}
        g.add_edge(src, dst, key=attrs.get("rel"), **attrs)
    return g


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    ensure_dirs()
    log = get_logger("examples.dataset")

    graph_path = GRAPHS_DIR / f"{args.repo}.json"
    if not graph_path.exists():
        log.error(f"no graph at {graph_path}. Run examples/run_mini_repo_pipeline.py first.")
        return 1

    g = _load_graph(graph_path)
    log.info(f"loaded graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")

    records = generate_sft(g)
    if args.n is not None:
        records = records[: args.n]

    out_path = args.out or (DATASETS_OUT_DIR / f"{args.repo}_sft_v0.jsonl")
    n_written = write_jsonl(out_path, records)

    print(f"records written      : {n_written}")
    print(f"dataset jsonl        : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
