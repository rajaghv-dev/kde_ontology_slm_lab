"""Sanity tests for the ontology schema."""
import pytest

from src.ontology.schema import ENTITY_TYPES, RELATION_TYPES, Entity, Relation


def test_known_entity_type_allowed():
    e = Entity(id="x", type="CppClass", name="Foo")
    assert e.qualified_name == "Foo"


def test_unknown_entity_type_rejected():
    with pytest.raises(ValueError):
        Entity(id="x", type="NotAThing", name="Foo")


def test_known_relation_type_allowed():
    r = Relation(src="a", rel="EMITS", dst="b")
    assert r.rel == "EMITS"


def test_unknown_relation_type_rejected():
    with pytest.raises(ValueError):
        Relation(src="a", rel="NOT_A_REL", dst="b")


def test_core_kde_concepts_present():
    for needed in ("CppClass", "Signal", "Slot", "QmlComponent", "DbusInterface",
                   "DbusMethod", "ConfigKey", "LogCategory", "Symptom"):
        assert needed in ENTITY_TYPES, needed


def test_core_relations_present():
    for needed in ("EMITS", "HANDLES", "READS_CONFIG", "EXPOSES_DBUS",
                   "LOGS_TO", "CONNECTS_TO", "DEFINES"):
        assert needed in RELATION_TYPES, needed
