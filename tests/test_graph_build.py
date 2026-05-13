"""Build the full graph from the mini repo and assert the high-value
relations exist.
"""
from src.common.paths import MINI_REPO
from src.graph.builder import build_graph
from src.graph.queries import (
    config_keys_read_by,
    find_by_name,
    log_categories_of,
    signals_emitted_by,
)
from src.ontology.extractor import (
    ExtractionBundle,
    from_cmake, from_cpp, from_dbus, from_desktop, from_kconfig,
    from_log, from_qml,
)
from src.ontology.schema import Entity
from src.common.ids import make_id
from src.repo_ingest.cmake_reader import read_cmake
from src.repo_ingest.cpp_reader import read_cpp
from src.repo_ingest.dbus_reader import read_dbus
from src.repo_ingest.desktop_file_reader import read_desktop
from src.repo_ingest.kconfig_reader import read_kconfig
from src.repo_ingest.log_reader import read_log
from src.repo_ingest.qml_reader import read_qml
from src.repo_ingest.scanner import scan


def _build_full_bundle() -> ExtractionBundle:
    rep = scan(MINI_REPO)
    bundle = ExtractionBundle()
    rid = bundle.add_entity(Entity(id=make_id("Repository", MINI_REPO.name),
                                   type="Repository", name=MINI_REPO.name))
    for sf in rep.by_kind("cmake"):
        from_cmake(bundle, read_cmake(sf.path), rid)
    for sf in rep.by_kind("cpp_header") + rep.by_kind("cpp_source"):
        from_cpp(bundle, read_cpp(sf.path))
    for sf in rep.by_kind("qml"):
        from_qml(bundle, read_qml(sf.path))
    for sf in rep.by_kind("dbus"):
        from_dbus(bundle, read_dbus(sf.path))
    for sf in rep.by_kind("kconfig"):
        from_kconfig(bundle, read_kconfig(sf.path))
    for sf in rep.by_kind("desktop"):
        from_desktop(bundle, read_desktop(sf.path))
    for sf in rep.by_kind("log"):
        from_log(bundle, read_log(sf.path))
    return bundle


def test_kfilesearcher_emits_resultsReady():
    bundle = _build_full_bundle()
    g = build_graph(bundle)
    cls_nodes = find_by_name(g, "KFileSearcher", types=("CppClass",))
    assert cls_nodes, "KFileSearcher class node not found"
    sigs = signals_emitted_by(g, cls_nodes[0])
    sig_names = {g.nodes[s].get("name") for s in sigs}
    assert "resultsReady" in sig_names


def test_kfilesearcher_reads_max_results():
    bundle = _build_full_bundle()
    g = build_graph(bundle)
    cls_nodes = find_by_name(g, "KFileSearcher", types=("CppClass",))
    keys = config_keys_read_by(g, cls_nodes[0])
    key_names = {g.nodes[k].get("name") for k in keys}
    assert "MaxResults" in key_names


def test_backend_logs_to_minisearch_backend_category():
    bundle = _build_full_bundle()
    g = build_graph(bundle)
    cls_nodes = find_by_name(g, "KFileSearchBackend", types=("CppClass",))
    cats = log_categories_of(g, cls_nodes[0])
    cat_names = {g.nodes[c].get("name") for c in cats}
    assert "minisearch.backend" in cat_names
