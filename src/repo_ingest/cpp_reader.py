"""Regex-based C++ reader.

We extract the structures that matter for the KDE ontology: classes, Q_OBJECT
status, Q_PROPERTY, signals, slots, public methods, log-category macros,
included headers, and KConfig-group reads. We are NOT building a real C++
parser — we are extracting *enough* to populate the graph.

When the regex gets confused, we err on the side of recording nothing. The
ontology layer can reconcile gaps from other sources (Doxygen, kernel-doc,
header annotations) in v0.1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RE_CLASS = re.compile(r"\bclass\s+(\w+)(?:\s*:\s*public\s+(\w+(?:::\w+)*))?\s*\{", re.MULTILINE)
RE_QOBJECT = re.compile(r"\bQ_OBJECT\b")
RE_QPROPERTY = re.compile(r"Q_PROPERTY\s*\(\s*[\w<>:]+\s+(\w+)\s+", re.MULTILINE)
RE_SIGNAL_BLOCK = re.compile(r"(?:Q_SIGNALS|signals)\s*:(.+?)(?=public|protected|private|\};)", re.DOTALL)
RE_SLOTS_BLOCK = re.compile(r"(?:public|protected|private)\s+(?:Q_SLOTS|slots)\s*:(.+?)(?=public|protected|private|\};)", re.DOTALL)
RE_FUNC = re.compile(r"\b(\w+(?:::\w+)?)\s*\(([^)]*)\)\s*(?:const)?\s*[;{]")
RE_LOG_CATEGORY = re.compile(r"Q_LOGGING_CATEGORY\s*\(\s*\w+\s*,\s*\"([^\"]+)\"\s*\)")
RE_INCLUDE = re.compile(r'^\s*#\s*include\s+[<"]([^">]+)[">]', re.MULTILINE)
RE_KCONFIG_READENTRY = re.compile(r'readEntry\s*\(\s*"([^"]+)"')
# Class-qualified definitions, e.g. `void KFileSearcher::searchPath(...)`. We use these
# to figure out the ambient class in a .cpp file even when no `class X {` block appears.
RE_QUALIFIED_DEF = re.compile(r"\b(\w+)::(\w+)\s*\(", re.MULTILINE)


@dataclass
class CppFinding:
    kind: str  # "class" | "signal" | "slot" | "property" | "method" | "log_category" | "kconfig_read" | "include"
    name: str
    extra: dict[str, str] = field(default_factory=dict)
    line: int = 0


@dataclass
class CppReadResult:
    path: Path
    is_qobject: bool
    findings: list[CppFinding] = field(default_factory=list)
    # Class names this file *defines* (via `class X {`) and class names it
    # *implements* (via `X::foo` method bodies). The extractor uses these to
    # link findings to the right class entity even across header/source splits.
    declared_classes: list[str] = field(default_factory=list)
    implemented_classes: list[str] = field(default_factory=list)


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _signatures_from_block(block: str) -> list[str]:
    """Pull out the names declared in a signals/slots block.

    We look for ``name(`` patterns. This catches things like
    ``void resultsReady(QStringList);``.
    """
    out: list[str] = []
    for m in RE_FUNC.finditer(block):
        name = m.group(1).split("::")[-1]
        if name in {"if", "for", "while", "switch", "return"}:
            continue
        out.append(name)
    return out


def read_cpp(path: Path) -> CppReadResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    result = CppReadResult(path=path, is_qobject=bool(RE_QOBJECT.search(text)))

    for m in RE_INCLUDE.finditer(text):
        result.findings.append(CppFinding(kind="include", name=m.group(1), line=_line_of(text, m.start())))

    for m in RE_CLASS.finditer(text):
        cls = m.group(1)
        parent = m.group(2) or ""
        result.declared_classes.append(cls)
        result.findings.append(CppFinding(
            kind="class", name=cls,
            extra={"parent": parent},
            line=_line_of(text, m.start()),
        ))

    # Track which classes have methods implemented in this file (e.g. `KFileSearcher::foo`).
    for m in RE_QUALIFIED_DEF.finditer(text):
        cls = m.group(1)
        # skip namespaces / known non-classes (basic heuristic: must start uppercase)
        if not cls or not cls[0].isupper() or cls in result.implemented_classes:
            continue
        result.implemented_classes.append(cls)

    for m in RE_QPROPERTY.finditer(text):
        result.findings.append(CppFinding(kind="property", name=m.group(1), line=_line_of(text, m.start())))

    for m in RE_SIGNAL_BLOCK.finditer(text):
        for name in _signatures_from_block(m.group(1)):
            result.findings.append(CppFinding(kind="signal", name=name, line=_line_of(text, m.start())))

    for m in RE_SLOTS_BLOCK.finditer(text):
        for name in _signatures_from_block(m.group(1)):
            result.findings.append(CppFinding(kind="slot", name=name, line=_line_of(text, m.start())))

    for m in RE_LOG_CATEGORY.finditer(text):
        result.findings.append(CppFinding(kind="log_category", name=m.group(1), line=_line_of(text, m.start())))

    for m in RE_KCONFIG_READENTRY.finditer(text):
        result.findings.append(CppFinding(kind="kconfig_read", name=m.group(1), line=_line_of(text, m.start())))

    return result
