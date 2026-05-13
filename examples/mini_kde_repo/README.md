# mini_kde_repo

A **synthetic mini KDE-style repo** used as the offline fixture for the entire `kde_ontology_slm_lab` pipeline.

It mimics a fictional KDE application called **MiniSearch** — a tiny file-search tool — touching every layer the lab cares about:

- CMake build (`CMakeLists.txt`)
- C++ headers + sources (`src/`)
- QML UI (`qml/`)
- D-Bus interface (`dbus/org.kde.minisearch.xml`)
- KConfig schema (`kconfig/minisearch.kcfg`)
- Desktop entry (`desktop/minisearch.desktop`)
- Unit test (`tests/tst_kfilesearcher.cpp`)
- Synthetic log (`logs/minisearch.log`)
- CMake module file (`cmake/MiniSearchConfig.cmake`)

The scenario embedded in the fixture (used by the traceability and eval modules):

> **Symptom**: MiniSearch becomes slow when searching folders with many files.

The graph + traceability code is expected to walk from that symptom to:
`QML SearchView` → `KFileSearcher` (C++) → `KFileSearchBackend::scanDirectory` → KConfig key `MaxResults` → D-Bus method `searchPath` → log category `minisearch.backend` → test `tst_kfilesearcher::testLargeFolderScan`.

This is small enough to read end-to-end in five minutes and large enough to exercise every ontology relation type.

Nothing here is meant to be a real KDE application — it is a **teaching artifact**.
