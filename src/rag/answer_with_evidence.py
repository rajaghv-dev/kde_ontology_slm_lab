"""Render an answer that cites its graph evidence inline.

The v0 answerer does *not* invoke any LLM — it composes a deterministic
markdown answer from the retrieved evidence. That gives us a baseline the
fine-tuned model must beat (or at least match) on the eval suite. The
``fine-tune-only`` and ``hybrid`` modes live under ``src/training/`` once
we have weights to compare against.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from src.rag.graph_retriever import Retrieval, retrieve


@dataclass
class Answer:
    query: str
    text: str
    evidence_refs: list[dict]  # list of {file, line, symbol, relation, confidence}


def _format_evidence_block(ret: Retrieval) -> tuple[str, list[dict]]:
    lines: list[str] = []
    refs: list[dict] = []
    for i, item in enumerate(ret.items, start=1):
        loc = f"{item.source_path}:{item.source_line}" if item.source_path else "<no-source>"
        ref_line = (f"[{i}] {item.type} `{item.name}` — {loc} "
                    f"(rel={item.relation or 'seed'}, conf={item.confidence:.2f})")
        lines.append(ref_line)
        refs.append({
            "file": item.source_path,
            "line": item.source_line,
            "symbol": item.name,
            "relation": item.relation or "seed",
            "confidence": item.confidence,
        })
    return "\n".join(lines), refs


def answer(g: nx.MultiDiGraph, query: str, k: int = 5) -> Answer:
    ret = retrieve(g, query, k=k)
    if not ret.items:
        return Answer(query=query,
                      text=("I cannot find any related entities in the current graph. "
                            "If this is a real symptom, point me at the affected component "
                            "or include a log category and I will re-check."),
                      evidence_refs=[])

    components = sorted({i.name for i in ret.items if i.type in {"CppClass", "QmlComponent"}})
    logs = sorted({i.name for i in ret.items if i.type == "LogCategory"})
    configs = sorted({i.name for i in ret.items if i.type == "ConfigKey"})
    dbus_methods = sorted({i.name for i in ret.items if i.type == "DbusMethod"})

    bits: list[str] = [f"Answer to: {query}"]
    if components:
        bits.append("Likely components: " + ", ".join(components))
    if logs:
        bits.append("Logs to watch: " + ", ".join(f"`{x}`" for x in logs))
    if configs:
        bits.append("Config keys involved: " + ", ".join(f"`{x}`" for x in configs))
    if dbus_methods:
        bits.append("D-Bus methods of interest: " + ", ".join(f"`{x}`" for x in dbus_methods))
    bits.append("")
    bits.append("Evidence:")

    ev_block, refs = _format_evidence_block(ret)
    bits.append(ev_block)

    return Answer(query=query, text="\n".join(bits), evidence_refs=refs)
