"""Symptom-to-code-path: given a user symptom string, produce a ranked
list of likely components, log categories, config keys, and tests.

The v0 algorithm is keyword-based — it pulls candidate entities by name match,
then expands one hop along high-signal relations (EMITS, READS_CONFIG,
LOGS_TO, EXPOSES_DBUS, TESTED_BY). It is intentionally simple. Once we have
real eval data the algorithm gets upgraded; in v0, the goal is to make the
trace *readable* and the evidence *citable*.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from src.graph.queries import find_by_name

KEY_RELATIONS = ("EMITS", "READS_CONFIG", "LOGS_TO", "EXPOSES_DBUS",
                 "CONNECTS_TO", "TESTED_BY", "DEFINES", "CONTAINS", "BUILDS")


@dataclass
class EvidenceItem:
    entity_id: str
    type: str
    name: str
    source_path: str
    source_line: int
    confidence: float
    reason: str
    relation: str = ""


@dataclass
class Trace:
    symptom: str
    seed_terms: list[str] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)

    def by_type(self, type_: str) -> list[EvidenceItem]:
        return [e for e in self.evidence if e.type == type_]


def _seed_terms(symptom: str) -> list[str]:
    """Pull plausible-entity tokens out of a symptom string.

    We keep CamelCase tokens (likely class names), tokens with K/Q/KIO prefix,
    and any whitespace-token that looks like a KDE concept word.
    """
    raw = symptom.replace(",", " ").replace(".", " ").split()
    out: list[str] = []
    candidates = {"slow", "crash", "freeze", "stuck", "loop", "leak", "hang",
                  "folder", "search", "results", "file", "config", "log",
                  "thumbnail", "indexing", "dbus", "kio", "kwin", "plasma"}
    for tok in raw:
        if len(tok) <= 2:
            continue
        if tok[0].isupper() or tok.lower() in candidates:
            out.append(tok)
    return out


def trace(g: nx.MultiDiGraph, symptom: str, k: int = 5, max_hops: int = 3) -> Trace:
    """Produce a Trace whose evidence is the top ``k`` related entities,
    plus their up-to-``max_hops`` neighbours along ``KEY_RELATIONS``.

    If no seed terms match, we return empty evidence rather than guessing — an
    off-topic question deserves an honest "I don't know" rather than a
    plausible-looking false positive.
    """
    tr = Trace(symptom=symptom, seed_terms=_seed_terms(symptom))

    seeds: list[tuple[str, str]] = []
    seen: set[str] = set()
    for term in tr.seed_terms:
        for nid in find_by_name(g, term):
            if nid in seen:
                continue
            seen.add(nid)
            seeds.append((nid, term))
            if len(seeds) >= k:
                break

    if not seeds:
        return tr  # honest empty trace

    for nid, reason in seeds:
        d = g.nodes[nid]
        tr.evidence.append(EvidenceItem(
            entity_id=nid, type=d.get("type", "?"), name=d.get("name", ""),
            source_path=d.get("source_path", ""), source_line=d.get("source_line", 0),
            confidence=0.8, reason=f"name-match on '{reason}'",
        ))

    # Breadth-first 2-hop expansion. Confidence falls off with depth.
    frontier: list[tuple[str, int]] = [(nid, 0) for nid, _ in seeds]
    while frontier:
        node, depth = frontier.pop(0)
        if depth >= max_hops:
            continue
        for _, dst, k_rel in g.out_edges(node, keys=True):
            if k_rel not in KEY_RELATIONS or dst in seen:
                continue
            seen.add(dst)
            dd = g.nodes[dst]
            tr.evidence.append(EvidenceItem(
                entity_id=dst, type=dd.get("type", "?"), name=dd.get("name", ""),
                source_path=dd.get("source_path", ""), source_line=dd.get("source_line", 0),
                confidence=0.6 - 0.15 * depth, reason=f"{depth + 1}-hop via {k_rel}",
                relation=k_rel,
            ))
            frontier.append((dst, depth + 1))
    return tr
