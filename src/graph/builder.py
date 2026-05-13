"""Turn an ExtractionBundle into a NetworkX MultiDiGraph and emit JSON / GraphML."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from src.ontology.extractor import ExtractionBundle


def build_graph(bundle: ExtractionBundle) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for ent in bundle.entities.values():
        g.add_node(
            ent.id,
            type=ent.type,
            name=ent.name,
            qualified_name=ent.qualified_name,
            source_path=ent.source_path,
            source_line=ent.source_line,
            **{f"prop_{k}": v for k, v in ent.properties.items()},
        )
    for rel in bundle.relations:
        # If a relation points at an id we don't have, drop it silently. This is a
        # learning-grade design choice: we prefer a clean graph over noisy edges.
        if rel.src not in g.nodes or rel.dst not in g.nodes:
            continue
        g.add_edge(rel.src, rel.dst, key=rel.rel, rel=rel.rel,
                   **{f"prop_{k}": v for k, v in rel.properties.items()})
    return g


def to_json(g: nx.MultiDiGraph) -> dict[str, Any]:
    return {
        "nodes": [{"id": n, **d} for n, d in g.nodes(data=True)],
        "edges": [{"src": u, "dst": v, **d} for u, v, d in g.edges(data=True)],
    }


def save_json(g: nx.MultiDiGraph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_json(g), f, indent=2)
    return path


def save_graphml(g: nx.MultiDiGraph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(g, path)
    return path
