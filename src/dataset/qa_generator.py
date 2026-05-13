"""Generate evidence-grounded SFT examples from the KDE knowledge graph.

Every example carries an ``evidence`` list pointing at the entities that
justify the answer. The schema mirrors the project prompt:

    {
      "id", "task_type", "instruction", "input", "output",
      "evidence": [{"file", "line_start", "line_end", "symbol",
                    "relation", "confidence"}],
      "negative_examples", "metadata"
    }

Templates intentionally cover several ``task_type`` values so a single graph
produces architecture, code-navigation, debugging, traceability, and tool-use
examples in one pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import networkx as nx

from src.common.ids import make_id
from src.graph.queries import (
    config_keys_read_by,
    dbus_methods_of,
    log_categories_of,
    nodes_of_type,
    qml_backend_for,
    signals_emitted_by,
)


@dataclass
class Example:
    record: dict

    def is_valid(self) -> bool:
        rec = self.record
        return bool(rec.get("instruction")) and bool(rec.get("output")) and bool(rec.get("evidence"))


def _evidence_from_node(g: nx.MultiDiGraph, nid: str, relation: str,
                       confidence: float) -> dict:
    d = g.nodes[nid]
    return {
        "file": d.get("source_path", ""),
        "line_start": d.get("source_line", 0) or 0,
        "line_end": d.get("source_line", 0) or 0,
        "symbol": d.get("name", ""),
        "relation": relation,
        "confidence": confidence,
    }


def _make_record(task_type: str, instruction: str, output: str,
                 evidence: list[dict], **metadata) -> dict:
    eid = make_id("DatasetExample", f"{task_type}::{instruction[:60]}")
    return {
        "id": eid,
        "task_type": task_type,
        "instruction": instruction,
        "input": "",
        "output": output,
        "evidence": evidence,
        "negative_examples": [],
        "metadata": {
            "generated_by": "rule",
            "difficulty": metadata.get("difficulty", "easy"),
            "license": "synthetic",
            "split": metadata.get("split", "train"),
            "component": metadata.get("component", ""),
            "repo": "mini_kde_repo",
        },
    }


# -- Templates --------------------------------------------------------------

def template_signal_emission(g: nx.MultiDiGraph) -> Iterator[Example]:
    for cls in nodes_of_type(g, "CppClass"):
        sigs = signals_emitted_by(g, cls)
        if not sigs:
            continue
        name = g.nodes[cls].get("name", "")
        sig_names = [g.nodes[s].get("name", "") for s in sigs]
        instruction = f"Which signals does the {name} class emit?"
        output = (f"{name} emits the following signals: " + ", ".join(sig_names) + "."
                  if sig_names else f"{name} emits no signals.")
        evidence = [_evidence_from_node(g, cls, "DEFINES", 0.9)]
        evidence += [_evidence_from_node(g, s, "EMITS", 0.9) for s in sigs]
        yield Example(_make_record(
            task_type="architecture_qa", instruction=instruction, output=output,
            evidence=evidence, component=name,
        ))


def template_config_keys(g: nx.MultiDiGraph) -> Iterator[Example]:
    for cls in nodes_of_type(g, "CppClass"):
        keys = config_keys_read_by(g, cls)
        if not keys:
            continue
        name = g.nodes[cls].get("name", "")
        key_names = [g.nodes[k].get("name", "") for k in keys]
        instruction = f"Which KConfig keys does {name} read at runtime?"
        output = f"{name} reads " + ", ".join(key_names) + " from its KConfig."
        evidence = [_evidence_from_node(g, cls, "DEFINES", 0.9)]
        evidence += [_evidence_from_node(g, k, "READS_CONFIG", 0.85) for k in keys]
        yield Example(_make_record(
            task_type="code_navigation", instruction=instruction, output=output,
            evidence=evidence, component=name,
        ))


def template_qml_backend(g: nx.MultiDiGraph) -> Iterator[Example]:
    for comp in nodes_of_type(g, "QmlComponent"):
        backends = qml_backend_for(g, comp)
        if not backends:
            continue
        cname = g.nodes[comp].get("name", "")
        bn = [g.nodes[b].get("name", b) for b in backends]
        instruction = f"Which C++ class is the QML component {cname} backed by?"
        output = f"{cname} is backed by {', '.join(bn)} (registered via qmlRegisterType)."
        evidence = [_evidence_from_node(g, comp, "DEFINES", 0.9)]
        for b in backends:
            if b in g.nodes:
                evidence.append(_evidence_from_node(g, b, "CONNECTS_TO", 0.7))
        yield Example(_make_record(
            task_type="code_navigation", instruction=instruction, output=output,
            evidence=evidence, component=cname,
        ))


def template_log_to_component(g: nx.MultiDiGraph) -> Iterator[Example]:
    for cls in nodes_of_type(g, "CppClass"):
        cats = log_categories_of(g, cls)
        if not cats:
            continue
        cname = g.nodes[cls].get("name", "")
        cat_names = [g.nodes[c].get("name", "") for c in cats]
        instruction = (f"When debugging {cname}, which log category should I "
                       f"enable to see runtime traces?")
        output = ("Enable the log category " + ", ".join(cat_names)
                  + f". Example: QT_LOGGING_RULES='{cat_names[0]}.debug=true' (KDE/Qt).")
        evidence = [_evidence_from_node(g, cls, "DEFINES", 0.85)]
        evidence += [_evidence_from_node(g, c, "LOGS_TO", 0.8) for c in cats]
        yield Example(_make_record(
            task_type="debugging", instruction=instruction, output=output,
            evidence=evidence, component=cname,
        ))


def template_dbus_methods(g: nx.MultiDiGraph) -> Iterator[Example]:
    for iface in nodes_of_type(g, "DbusInterface"):
        methods = dbus_methods_of(g, iface)
        if not methods:
            continue
        iname = g.nodes[iface].get("name", "")
        mnames = [g.nodes[m].get("name", "") for m in methods]
        instruction = f"Which D-Bus methods does the {iname} interface expose?"
        output = (f"{iname} exposes: " + ", ".join(mnames) + ".\n"
                  f"You can call them with `qdbus {iname} /<obj> <method>`.")
        evidence = [_evidence_from_node(g, iface, "EXPOSES_DBUS", 0.95)]
        evidence += [_evidence_from_node(g, m, "EXPOSES_DBUS", 0.95) for m in methods]
        yield Example(_make_record(
            task_type="tool_use", instruction=instruction, output=output,
            evidence=evidence, component=iname,
        ))


def template_refusal(g: nx.MultiDiGraph) -> Iterator[Example]:
    """An ``I don't know from available evidence`` example."""
    yield Example(_make_record(
        task_type="architecture_qa",
        instruction="What signal does the imaginary class KFooBarMaker emit?",
        output=("I do not see a class named KFooBarMaker in the indexed repo. "
                "If you have a path or header for it, share that and I can re-check; "
                "otherwise this name does not match any class in the current graph."),
        evidence=[{"file": "", "line_start": 0, "line_end": 0, "symbol": "",
                   "relation": "NEGATIVE_EVIDENCE", "confidence": 1.0}],
        difficulty="easy", component="unknown",
    ))


TEMPLATES = (
    template_signal_emission,
    template_config_keys,
    template_qml_backend,
    template_log_to_component,
    template_dbus_methods,
    template_refusal,
)


def generate(g: nx.MultiDiGraph) -> list[dict]:
    """Run every template and return a deduplicated list of valid records."""
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for tmpl in TEMPLATES:
        for ex in tmpl(g):
            if not ex.is_valid():
                continue
            key = (ex.record["instruction"], ex.record["output"])
            if key in seen:
                continue
            seen.add(key)
            out.append(ex.record)
    return out
