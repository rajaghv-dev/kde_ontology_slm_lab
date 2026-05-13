"""Ontology schema.

This module is the single source of truth for what kinds of things live in the
KDE knowledge graph and how they relate. Keep it small enough that you can hold
the whole thing in your head. Extending it is the right move when a new
relation type is justified by an actual query the lab needs to answer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- Entity types ----------------------------------------------------------
ENTITY_TYPES = frozenset({
    "Repository", "Module", "BuildTarget", "SourceFile", "HeaderFile",
    "CppClass", "Function", "Method", "Signal", "Slot", "QmlFile",
    "QmlComponent", "Property", "DbusService", "DbusInterface", "DbusMethod",
    "DbusSignal", "ConfigFile", "ConfigGroup", "ConfigKey", "Plugin",
    "DesktopFile", "Service", "LogCategory", "LogEvent", "TestCase",
    "BugReport", "Commit", "Symptom", "RootCause", "Fix",
    "EvaluationQuestion", "DatasetExample",
})

# --- Relation types --------------------------------------------------------
RELATION_TYPES = frozenset({
    "CONTAINS", "BUILDS", "DEFINES", "DECLARES", "CALLS", "EMITS",
    "CONNECTS_TO", "HANDLES", "IMPLEMENTS", "EXPOSES_DBUS", "CALLS_DBUS",
    "READS_CONFIG", "WRITES_CONFIG", "LOADS_PLUGIN", "REGISTERS_SERVICE",
    "LOGS_TO", "TESTED_BY", "CHANGED_BY", "FIXES", "CAUSES",
    "OBSERVED_IN", "RELATED_TO", "ANSWERED_BY", "SUPPORTED_BY_EVIDENCE",
})


@dataclass
class Entity:
    id: str
    type: str
    name: str
    qualified_name: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    source_path: str = ""
    source_line: int = 0

    def __post_init__(self) -> None:
        if self.type not in ENTITY_TYPES:
            raise ValueError(f"unknown entity type {self.type!r}; add it to ENTITY_TYPES first")
        if not self.qualified_name:
            self.qualified_name = self.name


@dataclass
class Relation:
    src: str  # entity id
    rel: str  # relation type
    dst: str  # entity id
    properties: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rel not in RELATION_TYPES:
            raise ValueError(f"unknown relation type {self.rel!r}; add it to RELATION_TYPES first")
