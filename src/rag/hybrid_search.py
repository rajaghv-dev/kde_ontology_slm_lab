"""Late-fusion hybrid search: graph retriever + vector store.

Why fuse?
---------
* The graph retriever is great at *structural* queries ("which class emits
  X?") but blind to semantic paraphrase.
* The vector store is great at *semantic* recall but cannot follow edges.
* Reciprocal-rank fusion is the simplest combiner that does not need
  calibrated scores. It treats each list as a ranking and sums
  ``1 / (k_rrf + rank)`` across lists.

The result is a list of ``HybridHit`` records, ranked by fused score, with
each hit annotated with which legs contributed to it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import numpy as np

from src.rag.embeddings import Embedder, default_embedder
from src.rag.graph_retriever import retrieve as graph_retrieve
from src.rag.vector_store import VectorStore


@dataclass
class HybridHit:
    id: str
    score: float
    sources: list[str] = field(default_factory=list)  # subset of {"graph", "vector"}
    payload: dict[str, Any] = field(default_factory=dict)


def _rrf_score(rank: int, k_rrf: int = 60) -> float:
    """Reciprocal-rank fusion weight. ``k_rrf=60`` is the canonical value
    from Cormack et al. 2009 and works well across heterogeneous lists.
    """
    return 1.0 / (k_rrf + rank)


def hybrid_search(
    g: nx.MultiDiGraph,
    store: VectorStore,
    query: str,
    k: int = 5,
    embedder: Embedder | None = None,
    k_rrf: int = 60,
) -> list[HybridHit]:
    """Return top-``k`` fused hits from the graph retriever and the vector store.

    Both legs are queried independently for ``k`` candidates, then fused with
    reciprocal-rank fusion. The function is pure: same inputs -> same output.
    """
    emb = embedder or default_embedder()

    # --- Graph leg -----------------------------------------------------
    ret = graph_retrieve(g, query, k=k)
    graph_hits: list[tuple[str, dict]] = []
    seen_g: set[str] = set()
    for item in ret.items:
        # The graph retriever returns EvidenceItems whose entity_id is the
        # canonical key. Skip duplicate ids (the retriever already dedupes
        # by node, but seed terms can repeat in some configs).
        if item.entity_id in seen_g:
            continue
        seen_g.add(item.entity_id)
        graph_hits.append((item.entity_id, {
            "name": item.name, "type": item.type,
            "file": item.source_path, "line": item.source_line,
            "relation": item.relation, "confidence": item.confidence,
        }))

    # --- Vector leg ----------------------------------------------------
    if len(store) > 0:
        qvec = emb.embed(query)
        vector_hits = store.query(qvec, k=k)
    else:
        vector_hits = []

    # --- Fuse ----------------------------------------------------------
    fused: dict[str, HybridHit] = {}
    for rank, (gid, payload) in enumerate(graph_hits):
        fused.setdefault(gid, HybridHit(id=gid, score=0.0, payload=dict(payload)))
        fused[gid].score += _rrf_score(rank, k_rrf)
        if "graph" not in fused[gid].sources:
            fused[gid].sources.append("graph")

    for rank, (vid, _score, payload) in enumerate(vector_hits):
        fused.setdefault(vid, HybridHit(id=vid, score=0.0, payload=dict(payload)))
        fused[vid].score += _rrf_score(rank, k_rrf)
        if "vector" not in fused[vid].sources:
            fused[vid].sources.append("vector")
        # Don't overwrite graph-provided payload, but fill in missing keys.
        for key, val in payload.items():
            fused[vid].payload.setdefault(key, val)

    ranked = sorted(fused.values(), key=lambda h: h.score, reverse=True)
    return ranked[:k]


def build_vector_index_from_graph(
    g: nx.MultiDiGraph,
    embedder: Embedder | None = None,
) -> VectorStore:
    """Convenience helper: embed every graph node and put it in a VectorStore.

    Useful for example runners and tests that want a populated index without
    duplicating boilerplate.
    """
    emb = embedder or default_embedder()
    store = VectorStore(dim=emb.dim)
    ids: list[str] = []
    texts: list[str] = []
    payloads: list[dict] = []
    for nid, attrs in g.nodes(data=True):
        name = attrs.get("name", "")
        type_ = attrs.get("type", "")
        text = f"{type_} {name}".strip()
        if not text:
            continue
        ids.append(nid)
        texts.append(text)
        payloads.append({"name": name, "type": type_,
                         "file": attrs.get("source_path", ""),
                         "line": attrs.get("source_line", 0)})
    if texts:
        vectors = emb.embed_many(texts)
        store.add_many(ids, np.asarray(vectors), payloads)
    return store
