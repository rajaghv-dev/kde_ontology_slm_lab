"""Interactive (or one-shot) RAG demo against the saved mini-repo graph.

Run modes
---------
* ``python examples/run_rag_answer_demo.py --query "Which signals does KFileSearcher emit?"``
* ``python examples/run_rag_answer_demo.py``  (prompts for a query on stdin)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import networkx as nx

from src.common.logging import get_logger
from src.common.paths import GRAPHS_DIR, ensure_dirs
from src.rag.answer_with_evidence import answer


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RAG answer demo over a saved graph.")
    p.add_argument("--repo", default="mini_repo",
                   help="Graph file in artifacts/graphs/ to query against.")
    p.add_argument("--query", default=None, help="One-shot query. If omitted, prompt on stdin.")
    p.add_argument("--k", type=int, default=6, help="How many evidence items to retrieve.")
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
    log = get_logger("examples.rag_demo")

    graph_path = GRAPHS_DIR / f"{args.repo}.json"
    if not graph_path.exists():
        log.error(f"no graph at {graph_path}. Run examples/run_mini_repo_pipeline.py first.")
        return 1

    g = _load_graph(graph_path)

    if args.query:
        query = args.query
    else:
        try:
            query = input("Query: ").strip()
        except EOFError:
            log.error("no query provided on stdin; pass --query instead.")
            return 2
        if not query:
            log.error("empty query; nothing to do.")
            return 2

    a = answer(g, query, k=args.k)
    print()
    print(a.text)
    print()
    print(f"({len(a.evidence_refs)} evidence references)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
