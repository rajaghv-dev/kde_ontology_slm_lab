"""Smoke test: scan the bundled mini repo and confirm each format reader
yields the things we expect.
"""
from src.common.paths import MINI_REPO
from src.repo_ingest.cmake_reader import read_cmake
from src.repo_ingest.cpp_reader import read_cpp
from src.repo_ingest.dbus_reader import read_dbus
from src.repo_ingest.desktop_file_reader import read_desktop
from src.repo_ingest.kconfig_reader import read_kconfig
from src.repo_ingest.log_reader import read_log
from src.repo_ingest.qml_reader import read_qml
from src.repo_ingest.scanner import scan


def test_scan_finds_all_kinds():
    rep = scan(MINI_REPO)
    kinds = {f.kind for f in rep.files}
    assert {"cmake", "cpp_source", "cpp_header", "qml", "dbus",
            "kconfig", "desktop", "log"}.issubset(kinds)


def test_cpp_reader_finds_class_and_signals():
    res = read_cpp(MINI_REPO / "src" / "kfilesearcher.h")
    assert res.is_qobject
    names = {f.name for f in res.findings if f.kind == "signal"}
    assert {"resultsReady", "searchFailed", "currentPathChanged"}.issubset(names)


def test_qml_reader_links_to_cpp_type():
    res = read_qml(MINI_REPO / "qml" / "SearchView.qml")
    assert res.root_component == "ApplicationWindow"
    assert "KFileSearcher" in res.used_types


def test_cmake_reader_finds_target():
    res = read_cmake(MINI_REPO / "CMakeLists.txt")
    assert res.project == "MiniSearch"
    assert any(t.name == "minisearch" for t in res.targets)


def test_dbus_reader_finds_methods():
    res = read_dbus(MINI_REPO / "dbus" / "org.kde.minisearch.xml")
    assert res.interfaces
    iface = res.interfaces[0]
    method_names = {m.name for m in iface.methods}
    assert {"searchPath", "cancel"}.issubset(method_names)


def test_kconfig_reader_finds_max_results():
    res = read_kconfig(MINI_REPO / "kconfig" / "minisearch.kcfg")
    names = {e.name for e in res.entries}
    assert "MaxResults" in names


def test_desktop_reader():
    res = read_desktop(MINI_REPO / "desktop" / "minisearch.desktop")
    assert res.name == "MiniSearch"
    assert res.dbus_activatable is True


def test_log_reader_finds_backend_category():
    res = read_log(MINI_REPO / "logs" / "minisearch.log")
    assert "minisearch.backend" in res.categories
