"""High-value graph queries the lab uses repeatedly.

Each query is small enough to read in one screen. Add new queries here as
specific debugging questions emerge — do not generalise prematurely.
"""
from __future__ import annotations

from typing import Iterable

import networkx as nx


def nodes_of_type(g: nx.MultiDiGraph, type_: str) -> list[str]:
    return [n for n, d in g.nodes(data=True) if d.get("type") == type_]


def out_edges_by_rel(g: nx.MultiDiGraph, node: str, rel: str) -> list[tuple[str, str]]:
    return [(node, dst) for _, dst, k in g.out_edges(node, keys=True) if k == rel]


def neighbors_by_rel(g: nx.MultiDiGraph, node: str, rel: str) -> list[str]:
    return [dst for _, dst in out_edges_by_rel(g, node, rel)]


def signals_emitted_by(g: nx.MultiDiGraph, class_node: str) -> list[str]:
    """Return Signal node ids that the given CppClass emits."""
    return neighbors_by_rel(g, class_node, "EMITS")


def config_keys_read_by(g: nx.MultiDiGraph, class_node: str) -> list[str]:
    return neighbors_by_rel(g, class_node, "READS_CONFIG")


def log_categories_of(g: nx.MultiDiGraph, class_node: str) -> list[str]:
    return neighbors_by_rel(g, class_node, "LOGS_TO")


def dbus_methods_of(g: nx.MultiDiGraph, iface_node: str) -> list[str]:
    return [dst for dst in neighbors_by_rel(g, iface_node, "EXPOSES_DBUS")
            if g.nodes[dst].get("type") == "DbusMethod"]


def qml_backend_for(g: nx.MultiDiGraph, qml_component_node: str) -> list[str]:
    """The C++ classes a QML component points at via CONNECTS_TO (qmlRegisterType)."""
    out: list[str] = []
    for _, dst, k in g.out_edges(qml_component_node, keys=True):
        if k == "CONNECTS_TO" and g.nodes[dst].get("type") == "CppClass":
            out.append(dst)
    return out


def find_by_name(g: nx.MultiDiGraph, name: str, types: Iterable[str] | None = None) -> list[str]:
    types_set = set(types) if types else None
    name_l = name.lower()
    out = []
    for n, d in g.nodes(data=True):
        if types_set and d.get("type") not in types_set:
            continue
        nm = (d.get("name") or "").lower()
        qn = (d.get("qualified_name") or "").lower()
        if name_l in nm or name_l in qn:
            out.append(n)
    return out
