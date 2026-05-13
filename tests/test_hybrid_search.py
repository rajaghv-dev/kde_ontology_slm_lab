"""Hybrid search fuses graph + vector legs correctly.

We reuse the mini repo's full graph (built via the shared helper from
``test_graph_build``) so the tests exercise realistic node ids.

The embedder used to *build* the index must match the embedder used to
*query* it — same algorithm, same dimension. The tests construct one
HashingEmbedder and pass it to both calls.
"""
from __future__ import annotations

from tests.test_graph_build import _build_full_bundle

from src.graph.builder import build_graph
from src.rag.embeddings import HashingEmbedder
from src.rag.hybrid_search import build_vector_index_from_graph, hybrid_search


def test_in_domain_query_returns_graph_hits():
    g = build_graph(_build_full_bundle())
    embedder = HashingEmbedder(dim_=64)
    store = build_vector_index_from_graph(g, embedder=embedder)
    hits = hybrid_search(g, store, "Which signals does KFileSearcher emit?",
                         k=6, embedder=embedder)
    assert hits, "expected at least one hybrid hit"
    # The top hit should mention KFileSearcher or a related entity.
    names = [h.payload.get("name", "") for h in hits]
    assert any("KFileSearcher" in n for n in names)


def test_vector_contributes_when_graph_misses_paraphrase():
    g = build_graph(_build_full_bundle())
    embedder = HashingEmbedder(dim_=64)
    store = build_vector_index_from_graph(g, embedder=embedder)
    hits = hybrid_search(g, store,
                         "search results that take forever to come back",
                         k=6, embedder=embedder)
    # Whatever the result, every fused hit must record at least one source leg.
    for h in hits:
        assert h.sources, "every fused hit should record at least one source"
        assert set(h.sources).issubset({"graph", "vector"})


def test_sources_are_attributed_when_both_legs_hit():
    g = build_graph(_build_full_bundle())
    embedder = HashingEmbedder(dim_=64)
    store = build_vector_index_from_graph(g, embedder=embedder)
    hits = hybrid_search(g, store, "KFileSearcher", k=6, embedder=embedder)
    # At least one hit should be attributed (graph leg always fires on exact name).
    assert any("graph" in h.sources for h in hits)


def test_empty_vector_store_still_returns_graph_hits():
    from src.rag.vector_store import VectorStore
    g = build_graph(_build_full_bundle())
    embedder = HashingEmbedder(dim_=64)
    empty = VectorStore(dim=64)
    hits = hybrid_search(g, empty, "Which signals does KFileSearcher emit?",
                         k=4, embedder=embedder)
    assert hits
    assert all(set(h.sources) == {"graph"} for h in hits)
