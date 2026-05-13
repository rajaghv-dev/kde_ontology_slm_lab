"""Simple log reader.

We expect lines in the shape ``<ts>  <level>  <category>  <message>``. KDE's
``QLoggingCategory`` writes a closely related format. The lab uses log events
to power the symptom-to-component traceability path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

LINE_RE = re.compile(r"^(?P<ts>\S+)\s+(?P<level>\w+)\s+(?P<cat>\S+)\s+(?P<msg>.*)$")


@dataclass
class LogEvent:
    timestamp: str
    level: str
    category: str
    message: str
    line_number: int


@dataclass
class LogReadResult:
    path: Path
    events: list[LogEvent] = field(default_factory=list)
    categories: set[str] = field(default_factory=set)


def read_log(path: Path) -> LogReadResult:
    r = LogReadResult(path=path)
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        ev = LogEvent(
            timestamp=m.group("ts"),
            level=m.group("level"),
            category=m.group("cat"),
            message=m.group("msg"),
            line_number=i,
        )
        r.events.append(ev)
        r.categories.add(ev.category)
    return r
