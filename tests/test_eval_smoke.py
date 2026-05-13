"""End-to-end smoke: build graph -> answer eval items -> grade -> aggregate."""
from tests.test_graph_build import _build_full_bundle

from src.eval.answer_grader import grade
from src.eval.eval_set_builder import mini_repo_eval_set
from src.eval.report import aggregate
from src.graph.builder import build_graph
from src.rag.answer_with_evidence import answer


def test_pipeline_evaluates_end_to_end():
    g = build_graph(_build_full_bundle())
    items = mini_repo_eval_set()
    grades = [grade(answer(g, it["question"], k=6).text, it) for it in items]
    rep = aggregate(grades)
    assert rep["n"] == len(items)
    # The baseline RAG should pass at least one item (likely several).
    assert rep["overall_pass_rate"] > 0.0
