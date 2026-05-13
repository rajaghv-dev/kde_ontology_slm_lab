"""KConfig (.kcfg) XML reader."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class KConfigEntry:
    name: str
    type: str
    default: str
    label: str
    group: str
    minimum: str | None = None
    maximum: str | None = None


@dataclass
class KConfigReadResult:
    path: Path
    kcfgfile: str | None = None
    groups: list[str] = field(default_factory=list)
    entries: list[KConfigEntry] = field(default_factory=list)


def _local(tag: str) -> str:
    """Strip XML namespace from an ElementTree tag."""
    return tag.rsplit("}", 1)[-1]


def read_kconfig(path: Path) -> KConfigReadResult:
    tree = ET.parse(path)
    root = tree.getroot()
    r = KConfigReadResult(path=path)

    for child in root:
        if _local(child.tag) == "kcfgfile":
            r.kcfgfile = child.get("name")
        elif _local(child.tag) == "group":
            gname = child.get("name", "<no-name>")
            r.groups.append(gname)
            for entry in child:
                if _local(entry.tag) != "entry":
                    continue
                label = ""
                default = ""
                minimum = None
                maximum = None
                for sub in entry:
                    tag = _local(sub.tag)
                    if tag == "label":
                        label = (sub.text or "").strip()
                    elif tag == "default":
                        default = (sub.text or "").strip()
                    elif tag == "min":
                        minimum = (sub.text or "").strip()
                    elif tag == "max":
                        maximum = (sub.text or "").strip()
                r.entries.append(KConfigEntry(
                    name=entry.get("name", ""),
                    type=entry.get("type", ""),
                    default=default,
                    label=label,
                    group=gname,
                    minimum=minimum,
                    maximum=maximum,
                ))
    return r
