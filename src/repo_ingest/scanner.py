"""Walk a repo and classify files for the per-format readers."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

KIND_BY_EXT = {
    ".cpp": "cpp_source",
    ".cc": "cpp_source",
    ".cxx": "cpp_source",
    ".h": "cpp_header",
    ".hpp": "cpp_header",
    ".qml": "qml",
    ".kcfg": "kconfig",
    ".desktop": "desktop",
    ".xml": "xml",
    ".cmake": "cmake_module",
    ".md": "markdown",
    ".log": "log",
}

CMAKE_FILENAME = "CMakeLists.txt"
DBUS_HINT_DIR = "dbus"  # we treat XML under a `dbus/` dir as D-Bus introspection


@dataclass
class ScannedFile:
    path: Path
    kind: str
    rel_path: str  # relative to the repo root


@dataclass
class ScanReport:
    repo_root: Path
    files: list[ScannedFile] = field(default_factory=list)

    def by_kind(self, kind: str) -> list[ScannedFile]:
        return [f for f in self.files if f.kind == kind]


def classify(path: Path) -> str | None:
    """Map a path to a kind. Returns ``None`` for unrecognised files."""
    if path.name == CMAKE_FILENAME:
        return "cmake"
    suffix = path.suffix.lower()
    kind = KIND_BY_EXT.get(suffix)
    if kind == "xml" and DBUS_HINT_DIR in path.parts:
        return "dbus"
    return kind


def scan(repo_root: Path) -> ScanReport:
    """Walk ``repo_root`` recursively and classify every file we recognise."""
    report = ScanReport(repo_root=repo_root)
    for p in sorted(repo_root.rglob("*")):
        if not p.is_file() or any(part.startswith(".") for part in p.parts):
            continue
        kind = classify(p)
        if kind is None:
            continue
        report.files.append(ScannedFile(path=p, kind=kind, rel_path=str(p.relative_to(repo_root))))
    return report
