"""Reader for ``.desktop`` entries — INI-shaped, freedesktop spec."""
from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DesktopReadResult:
    path: Path
    name: str | None = None
    exec_: str | None = None
    icon: str | None = None
    categories: list[str] = field(default_factory=list)
    dbus_activatable: bool = False
    raw: dict[str, str] = field(default_factory=dict)


def read_desktop(path: Path) -> DesktopReadResult:
    cp = ConfigParser(interpolation=None)
    cp.optionxform = str  # preserve case so X-KDE-* keys survive
    cp.read(path, encoding="utf-8")
    section = "Desktop Entry"
    r = DesktopReadResult(path=path)
    if section not in cp:
        return r
    items = dict(cp[section])
    r.raw = items
    r.name = items.get("Name")
    r.exec_ = items.get("Exec")
    r.icon = items.get("Icon")
    r.categories = [c for c in (items.get("Categories", "") or "").split(";") if c]
    r.dbus_activatable = items.get("DBusActivatable", "").strip().lower() == "true"
    return r
