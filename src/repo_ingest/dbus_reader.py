"""D-Bus introspection XML reader."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class DBusMember:
    kind: str  # "method" | "signal"
    name: str
    args: list[tuple[str, str, str]] = field(default_factory=list)  # (name, type, direction)


@dataclass
class DBusInterface:
    name: str
    methods: list[DBusMember] = field(default_factory=list)
    signals: list[DBusMember] = field(default_factory=list)


@dataclass
class DBusReadResult:
    path: Path
    interfaces: list[DBusInterface] = field(default_factory=list)


def read_dbus(path: Path) -> DBusReadResult:
    tree = ET.parse(path)
    root = tree.getroot()
    r = DBusReadResult(path=path)
    for iface in root.findall("interface"):
        di = DBusInterface(name=iface.get("name", "<unknown>"))
        for method in iface.findall("method"):
            args = [(a.get("name", ""), a.get("type", ""), a.get("direction", "in"))
                    for a in method.findall("arg")]
            di.methods.append(DBusMember(kind="method", name=method.get("name", ""), args=args))
        for sig in iface.findall("signal"):
            args = [(a.get("name", ""), a.get("type", ""), "out") for a in sig.findall("arg")]
            di.signals.append(DBusMember(kind="signal", name=sig.get("name", ""), args=args))
        r.interfaces.append(di)
    return r
