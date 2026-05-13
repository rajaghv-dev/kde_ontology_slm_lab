"""Every generated SFT example must satisfy the published JSONL schema."""
from tests.test_graph_build import _build_full_bundle

from src.dataset.qa_generator import generate
from src.graph.builder import build_graph

REQUIRED_TOP_KEYS = {"id", "task_type", "instruction", "input", "output",
                     "evidence", "negative_examples", "metadata"}
REQUIRED_EV_KEYS = {"file", "line_start", "line_end", "symbol", "relation", "confidence"}
ALLOWED_TASK_TYPES = {"architecture_qa", "code_navigation", "debugging",
                      "traceability", "tool_use", "repair"}


def test_examples_have_required_shape():
    g = build_graph(_build_full_bundle())
    records = generate(g)
    assert records, "generator returned nothing"
    for rec in records:
        assert REQUIRED_TOP_KEYS.issubset(rec.keys()), set(rec.keys())
        assert rec["task_type"] in ALLOWED_TASK_TYPES, rec["task_type"]
        for ev in rec["evidence"]:
            assert REQUIRED_EV_KEYS.issubset(ev.keys()), ev


def test_examples_are_unique():
    g = build_graph(_build_full_bundle())
    records = generate(g)
    seen = set()
    for rec in records:
        key = (rec["instruction"], rec["output"])
        assert key not in seen, f"duplicate example: {key}"
        seen.add(key)
