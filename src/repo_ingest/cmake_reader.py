"""Regex-based CMake reader. Extract executable/library targets, their sources,
their link dependencies, and any ``add_subdirectory`` traversal hints.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RE_PROJECT = re.compile(r"project\s*\(\s*([\w\-]+)", re.IGNORECASE)
RE_ADD_EXE = re.compile(r"add_executable\s*\(\s*([\w\-]+)([^)]*)\)", re.IGNORECASE | re.DOTALL)
RE_ADD_LIB = re.compile(r"add_library\s*\(\s*([\w\-]+)([^)]*)\)", re.IGNORECASE | re.DOTALL)
RE_LINK = re.compile(r"target_link_libraries\s*\(\s*([\w\-]+)(.*?)\)", re.IGNORECASE | re.DOTALL)
RE_SUBDIR = re.compile(r"add_subdirectory\s*\(\s*([\w\-/]+)", re.IGNORECASE)


@dataclass
class CMakeTarget:
    name: str
    kind: str  # "executable" | "library"
    sources: list[str] = field(default_factory=list)
    link_libs: list[str] = field(default_factory=list)


@dataclass
class CMakeReadResult:
    path: Path
    project: str | None = None
    targets: list[CMakeTarget] = field(default_factory=list)
    subdirs: list[str] = field(default_factory=list)


def _parse_args(blob: str) -> list[str]:
    return [tok for tok in re.split(r"\s+", blob.strip()) if tok and not tok.startswith("#")]


def read_cmake(path: Path) -> CMakeReadResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    r = CMakeReadResult(path=path)

    proj = RE_PROJECT.search(text)
    if proj:
        r.project = proj.group(1)

    for m in RE_ADD_EXE.finditer(text):
        name = m.group(1)
        srcs = _parse_args(m.group(2))
        r.targets.append(CMakeTarget(name=name, kind="executable", sources=srcs))
    for m in RE_ADD_LIB.finditer(text):
        name = m.group(1)
        srcs = _parse_args(m.group(2))
        r.targets.append(CMakeTarget(name=name, kind="library", sources=srcs))

    for m in RE_LINK.finditer(text):
        target = m.group(1)
        libs = [t for t in _parse_args(m.group(2)) if t.upper() not in {"PRIVATE", "PUBLIC", "INTERFACE"}]
        for t in r.targets:
            if t.name == target:
                t.link_libs.extend(libs)
                break

    for m in RE_SUBDIR.finditer(text):
        r.subdirs.append(m.group(1))

    return r
