"""Turn the per-format reader output into Entity + Relation lists.

This is the glue between the messy per-format world (CMake, C++, QML, D-Bus,
KConfig, desktop entry, log) and the clean ontology schema.

Each extractor function is deliberately small and side-effect-free so the
unit tests can feed it a single reader result and assert on the output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.common.ids import make_id
from src.ontology.schema import Entity, Relation
from src.repo_ingest.cmake_reader import CMakeReadResult
from src.repo_ingest.cpp_reader import CppReadResult
from src.repo_ingest.dbus_reader import DBusReadResult
from src.repo_ingest.desktop_file_reader import DesktopReadResult
from src.repo_ingest.kconfig_reader import KConfigReadResult
from src.repo_ingest.log_reader import LogReadResult
from src.repo_ingest.qml_reader import QmlReadResult


@dataclass
class ExtractionBundle:
    entities: dict[str, Entity] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)

    def add_entity(self, e: Entity) -> str:
        if e.id not in self.entities:
            self.entities[e.id] = e
        return e.id

    def add_relation(self, r: Relation) -> None:
        self.relations.append(r)


# -- per-format extractors ---------------------------------------------------

def _norm_source_id(file_kind: str, path: Path | str) -> str:
    """Generate the same id whether the path is absolute, relative to the
    CMakeLists, or basename-only. Source files in our ontology are identified
    by their *file name* — good enough for KDE-scale repos and matches the
    common error-message style ("Foo.cpp:42").
    """
    p = Path(str(path))
    return make_id(file_kind, p.name.lower())


def from_cmake(bundle: ExtractionBundle, res: CMakeReadResult, repo_id: str) -> None:
    if res.project:
        mod_id = bundle.add_entity(Entity(
            id=make_id("Module", res.project),
            type="Module", name=res.project,
            source_path=str(res.path),
        ))
        bundle.add_relation(Relation(src=repo_id, rel="CONTAINS", dst=mod_id))
        owner_id = mod_id
    else:
        owner_id = repo_id

    for t in res.targets:
        tid = bundle.add_entity(Entity(
            id=make_id("BuildTarget", t.name),
            type="BuildTarget", name=t.name,
            properties={"kind": t.kind, "link_libs": ",".join(t.link_libs)},
            source_path=str(res.path),
        ))
        bundle.add_relation(Relation(src=owner_id, rel="BUILDS", dst=tid))
        for src in t.sources:
            file_kind = "HeaderFile" if src.lower().endswith((".h", ".hpp")) else "SourceFile"
            sid = bundle.add_entity(Entity(
                id=_norm_source_id(file_kind, src),
                type=file_kind, name=Path(src).name,
                qualified_name=src, source_path=src,
            ))
            bundle.add_relation(Relation(src=tid, rel="CONTAINS", dst=sid))


def from_cpp(bundle: ExtractionBundle, res: CppReadResult) -> None:
    file_kind = "HeaderFile" if res.path.suffix.lower() in {".h", ".hpp"} else "SourceFile"
    fid = bundle.add_entity(Entity(
        id=_norm_source_id(file_kind, res.path),
        type=file_kind, name=res.path.name,
        qualified_name=str(res.path), source_path=str(res.path),
    ))

    # If the file implements methods of a class declared elsewhere (typical .cpp/.h split),
    # ensure a class entity exists so we can route findings to it.
    implicit_class_id: str | None = None
    if not res.declared_classes and res.implemented_classes:
        primary = res.implemented_classes[0]
        implicit_class_id = bundle.add_entity(Entity(
            id=make_id("CppClass", primary),
            type="CppClass", name=primary,
            properties={"parent": "", "is_qobject": str(res.is_qobject)},
            source_path=str(res.path), source_line=1,
        ))
        bundle.add_relation(Relation(src=fid, rel="DEFINES", dst=implicit_class_id))

    last_class_id: str | None = implicit_class_id
    for f in res.findings:
        if f.kind == "class":
            cid = bundle.add_entity(Entity(
                id=make_id("CppClass", f.name),
                type="CppClass", name=f.name,
                properties={"parent": f.extra.get("parent", ""), "is_qobject": str(res.is_qobject)},
                source_path=str(res.path), source_line=f.line,
            ))
            bundle.add_relation(Relation(src=fid, rel="DEFINES", dst=cid))
            last_class_id = cid
        elif f.kind in {"signal", "slot", "property", "method"}:
            etype = {"signal": "Signal", "slot": "Slot", "property": "Property", "method": "Method"}[f.kind]
            owner = last_class_id or fid
            sid = bundle.add_entity(Entity(
                id=make_id(etype, f"{owner}::{f.name}"),
                type=etype, name=f.name,
                source_path=str(res.path), source_line=f.line,
            ))
            rel = "EMITS" if f.kind == "signal" else "HANDLES" if f.kind == "slot" else "DECLARES"
            bundle.add_relation(Relation(src=owner, rel=rel, dst=sid))
        elif f.kind == "log_category":
            lid = bundle.add_entity(Entity(
                id=make_id("LogCategory", f.name),
                type="LogCategory", name=f.name,
                source_path=str(res.path), source_line=f.line,
            ))
            bundle.add_relation(Relation(src=(last_class_id or fid), rel="LOGS_TO", dst=lid))
        elif f.kind == "kconfig_read":
            kid = bundle.add_entity(Entity(
                id=make_id("ConfigKey", f.name),
                type="ConfigKey", name=f.name,
                source_path="", source_line=0,
            ))
            bundle.add_relation(Relation(src=(last_class_id or fid), rel="READS_CONFIG", dst=kid))
        elif f.kind == "include":
            # we keep includes as a low-priority relation; record only KDE/Qt-style ones
            if f.name.startswith(("K", "Q", "KF6", "KConfig", "KIO", "Plasma")):
                hid = bundle.add_entity(Entity(
                    id=make_id("HeaderFile", f.name),
                    type="HeaderFile", name=f.name,
                    qualified_name=f.name, source_path=f.name,
                ))
                bundle.add_relation(Relation(src=fid, rel="RELATED_TO", dst=hid,
                                             properties={"kind": "include"}))


def from_qml(bundle: ExtractionBundle, res: QmlReadResult) -> None:
    qid = bundle.add_entity(Entity(
        id=make_id("QmlFile", str(res.path)),
        type="QmlFile", name=res.path.name,
        qualified_name=str(res.path), source_path=str(res.path),
    ))
    if res.root_component:
        cid = bundle.add_entity(Entity(
            id=make_id("QmlComponent", f"{res.path.stem}::{res.root_component}"),
            type="QmlComponent", name=res.root_component,
            source_path=str(res.path),
        ))
        bundle.add_relation(Relation(src=qid, rel="DEFINES", dst=cid))
        for used in res.used_types:
            # try to bridge a QML-used type to its C++ class entity
            ucid = make_id("CppClass", used)
            bundle.add_relation(Relation(src=cid, rel="CONNECTS_TO", dst=ucid,
                                         properties={"via": "qmlRegisterType"}))


def from_dbus(bundle: ExtractionBundle, res: DBusReadResult) -> None:
    for iface in res.interfaces:
        iid = bundle.add_entity(Entity(
            id=make_id("DbusInterface", iface.name),
            type="DbusInterface", name=iface.name,
            source_path=str(res.path),
        ))
        for m in iface.methods:
            mid = bundle.add_entity(Entity(
                id=make_id("DbusMethod", f"{iface.name}.{m.name}"),
                type="DbusMethod", name=m.name,
                properties={"interface": iface.name},
                source_path=str(res.path),
            ))
            bundle.add_relation(Relation(src=iid, rel="EXPOSES_DBUS", dst=mid))
        for s in iface.signals:
            sid = bundle.add_entity(Entity(
                id=make_id("DbusSignal", f"{iface.name}.{s.name}"),
                type="DbusSignal", name=s.name,
                properties={"interface": iface.name},
                source_path=str(res.path),
            ))
            bundle.add_relation(Relation(src=iid, rel="EXPOSES_DBUS", dst=sid))


def from_kconfig(bundle: ExtractionBundle, res: KConfigReadResult) -> None:
    file_id = bundle.add_entity(Entity(
        id=make_id("ConfigFile", str(res.path)),
        type="ConfigFile", name=res.path.name,
        properties={"kcfgfile": res.kcfgfile or ""},
        source_path=str(res.path),
    ))
    for g in res.groups:
        gid = bundle.add_entity(Entity(
            id=make_id("ConfigGroup", f"{res.path.stem}::{g}"),
            type="ConfigGroup", name=g,
            source_path=str(res.path),
        ))
        bundle.add_relation(Relation(src=file_id, rel="CONTAINS", dst=gid))
    for entry in res.entries:
        kid = bundle.add_entity(Entity(
            id=make_id("ConfigKey", entry.name),
            type="ConfigKey", name=entry.name,
            properties={
                "type": entry.type, "default": entry.default,
                "label": entry.label, "group": entry.group,
            },
            source_path=str(res.path),
        ))
        gid = make_id("ConfigGroup", f"{res.path.stem}::{entry.group}")
        bundle.add_relation(Relation(src=gid, rel="CONTAINS", dst=kid))


def from_desktop(bundle: ExtractionBundle, res: DesktopReadResult) -> None:
    if not res.name:
        return
    did = bundle.add_entity(Entity(
        id=make_id("DesktopFile", str(res.path)),
        type="DesktopFile", name=res.name,
        properties={
            "exec": res.exec_ or "",
            "icon": res.icon or "",
            "dbus_activatable": str(res.dbus_activatable),
            "categories": ",".join(res.categories),
        },
        source_path=str(res.path),
    ))
    if res.dbus_activatable:
        sid = bundle.add_entity(Entity(
            id=make_id("Service", f"{res.path}::dbus"),
            type="Service", name=res.name,
            properties={"activation": "DBusActivatable"},
            source_path=str(res.path),
        ))
        bundle.add_relation(Relation(src=did, rel="REGISTERS_SERVICE", dst=sid,
                                     properties={"note": "DBusActivatable"}))


def from_log(bundle: ExtractionBundle, res: LogReadResult) -> None:
    for cat in res.categories:
        bundle.add_entity(Entity(
            id=make_id("LogCategory", cat),
            type="LogCategory", name=cat,
            source_path=str(res.path),
        ))
    for ev in res.events:
        eid = bundle.add_entity(Entity(
            id=make_id("LogEvent", f"{res.path.name}:{ev.line_number}"),
            type="LogEvent", name=ev.message[:60],
            properties={"level": ev.level, "ts": ev.timestamp, "category": ev.category},
            source_path=str(res.path), source_line=ev.line_number,
        ))
        bundle.add_relation(Relation(src=eid, rel="OBSERVED_IN",
                                     dst=make_id("LogCategory", ev.category)))
