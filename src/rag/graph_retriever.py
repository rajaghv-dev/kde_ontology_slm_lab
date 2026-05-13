"""Graph retriever: take a natural-language query, return ranked graph evidence."""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from src.traceability.symptom_to_code import EvidenceItem, trace


@dataclass
class Retrieval:
    query: str
    items: list[EvidenceItem]


def retrieve(g: nx.MultiDiGraph, query: str, k: int = 5) -> Retrieval:
    """For v0 we route every query through the traceability path. That gives
    us symptom-style queries *and* architecture queries for free — both end up
    looking like "find candidate entities by name, expand one hop".
    """
    tr = trace(g, symptom=query, k=k)
    return Retrieval(query=query, items=tr.evidence)
