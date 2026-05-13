"""The RAG layer should produce non-empty evidence for in-domain queries
and the no-evidence fallback for clearly off-topic ones.
"""
from tests.test_graph_build import _build_full_bundle

from src.graph.builder import build_graph
from src.rag.answer_with_evidence import answer


def test_in_domain_query_carries_evidence():
    g = build_graph(_build_full_bundle())
    a = answer(g, "Which signals does KFileSearcher emit?")
    assert a.evidence_refs, "expected evidence references"
    assert "KFileSearcher" in a.text


def test_off_topic_query_falls_back_cleanly():
    g = build_graph(_build_full_bundle())
    a = answer(g, "what is the weather on mars")
    # Either empty refs or a fallback message that does not invent a KDE class.
    assert "KFileSearcher" not in a.text or a.evidence_refs == []
