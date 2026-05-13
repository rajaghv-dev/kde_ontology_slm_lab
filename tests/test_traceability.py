"""The flagship sanity check: the symptom 'MiniSearch is slow on large folders'
should turn up KFileSearcher + KFileSearchBackend + minisearch.backend log.
"""
from tests.test_graph_build import _build_full_bundle  # reuse helper

from src.graph.builder import build_graph
from src.traceability.symptom_to_code import trace


def test_slow_folder_symptom_finds_backend():
    g = build_graph(_build_full_bundle())
    tr = trace(g, "MiniSearch is slow when opening folders with many files", k=6)
    names = {e.name for e in tr.evidence}
    assert names & {"KFileSearcher", "KFileSearchBackend"}, names
    # The trace should also expose the log category for the user to inspect.
    cats = {e.name for e in tr.evidence if e.type == "LogCategory"}
    assert "minisearch.backend" in cats or names & {"minisearch.backend"}
