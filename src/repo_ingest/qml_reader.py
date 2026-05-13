"""Regex-based QML reader.

Pull out the imports (which point to a C++ module via qmlRegisterType), the
top-level component type, and any references to C++ types so the graph can
link a QML view to its backend.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RE_IMPORT = re.compile(r"^\s*import\s+([\w.]+)\s+([\d.]+)", re.MULTILINE)
RE_ROOT_COMPONENT = re.compile(r"^\s*([A-Z][A-Za-z0-9_]*)\s*\{", re.MULTILINE)
RE_USE_TYPE = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\s*\{")
RE_PROPERTY_BINDING = re.compile(r"^\s*(\w+)\s*:\s*[^\n]+", re.MULTILINE)


@dataclass
class QmlReadResult:
    path: Path
    imports: list[tuple[str, str]] = field(default_factory=list)  # (module, version)
    root_component: str | None = None
    used_types: list[str] = field(default_factory=list)


def read_qml(path: Path) -> QmlReadResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    r = QmlReadResult(path=path)
    r.imports = [(m.group(1), m.group(2)) for m in RE_IMPORT.finditer(text)]

    root = RE_ROOT_COMPONENT.search(text)
    if root:
        r.root_component = root.group(1)

    types = {m.group(1) for m in RE_USE_TYPE.finditer(text)}
    # ApplicationWindow / Column / Row / ListView / Text / Label / TextField / Button
    builtins = {"ApplicationWindow", "Column", "Row", "Rectangle", "Item", "Text", "Label",
                "TextField", "Button", "ListView", "ListModel"}
    r.used_types = sorted(t for t in types if t not in builtins)
    return r
