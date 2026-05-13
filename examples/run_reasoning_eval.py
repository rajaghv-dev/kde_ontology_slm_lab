"""Grade the RAG baseline against the hand-authored eval set.

This is a thin wrapper around the ``kde-lab eval`` CLI subcommand, kept as a
script so a learner can read every step on one page.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import networkx as nx

from src.common.logging import get_logger
from src.common.paths import EVAL_DIR, GRAPHS_DIR, ensure_dirs
from src.dataset.jsonl_writer import write_jsonl
from src.eval.answer_grader import grade
from src.eval.eval_set_builder import mini_repo_eval_set
from src.eval.report import aggregate
from src.eval.report import save as save_report
from src.rag.answer_with_evidence import answer


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the RAG-baseline reasoning eval.")
    p.add_argument("--repo", default="mini_repo",
                   help="Graph file in artifacts/graphs/ to query against.")
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
    log = get_logger("examples.eval")

    graph_path = GRAPHS_DIR / f"{args.repo}.json"
    if not graph_path.exists():
        log.error(f"no graph at {graph_path}. Run examples/run_mini_repo_pipeline.py first.")
        return 1

    g = _load_graph(graph_path)
    items = mini_repo_eval_set()

    grades = []
    answers_out = []
    for item in items:
        a = answer(g, item["question"], k=6)
        grades.append(grade(a.text, item))
        answers_out.append({
            "id": item["id"], "question": item["question"],
            "answer": a.text, "evidence_refs": a.evidence_refs,
        })

    rep_data = aggregate(grades)
    write_jsonl(EVAL_DIR / f"{args.repo}_answers.jsonl", answers_out)
    jp, mp = save_report(rep_data, EVAL_DIR, name=f"{args.repo}_eval")

    n_pass = sum(1 for r in grades if r.passed)
    print(f"items              : {len(items)}")
    print(f"pass rate          : {rep_data['overall_pass_rate']:.2%}  "
          f"({n_pass} / {len(grades)})")
    print(f"mean recall        : {rep_data['overall_mean_recall']:.2%}")
    print(f"json report        : {jp}")
    print(f"markdown report    : {mp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
