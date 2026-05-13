# 03 — KDE ontology design

An ontology is just a vocabulary of *what kinds of things exist* and *how they relate*. The lab's ontology lives in one file: [../src/ontology/schema.py](../src/ontology/schema.py). It is small enough to hold in your head, which is the point. If a new entity type or relation does not justify itself with a concrete query the lab needs to answer, it does not belong.

This chapter explains the design choices, walks the 32 entity types and 24 relation types, and shows one worked example: how `KFileSearcher` becomes a `CppClass` node with three `EMITS` edges and a `READS_CONFIG` edge.

## Why an ontology at all

A KDE codebase has multiple file formats, each with its own grammar: C++, QML, CMake, D-Bus XML, KConfig XML, desktop files, log lines. If you train an SLM on raw text you get a model that can autocomplete each format in isolation and confuse them with each other. Worse, you cannot tell the model *why* an answer is wrong, because the model has no notion of what a `Signal` is versus a `DbusSignal`.

An explicit ontology gives you three things:

1. **A schema for evidence.** Every dataset example points at typed entities. The model learns to say *"`KFileSearcher` emits `resultsReady`"* knowing that `KFileSearcher` is a `CppClass` and `resultsReady` is a `Signal`.
2. **A target for retrieval.** Graph queries ask typed questions ("give me all `ConfigKey` nodes read by this `CppClass`"). That is a thousand times more precise than vector similarity in source text.
3. **A contract for hallucination control.** If the model produces a name with no matching node in the graph, the grader can catch it programmatically. Chapter [11_failure_modes.md](11_failure_modes.md) operationalises this as the *hallucinated APIs* failure mode.

## Two tiny frozensets, one rule

The schema is two frozensets plus two dataclasses:

```python
ENTITY_TYPES = frozenset({
    "Repository", "Module", "BuildTarget", "SourceFile", "HeaderFile",
    "CppClass", "Function", "Method", "Signal", "Slot", "QmlFile",
    "QmlComponent", "Property", "DbusService", "DbusInterface", "DbusMethod",
    "DbusSignal", "ConfigFile", "ConfigGroup", "ConfigKey", "Plugin",
    "DesktopFile", "Service", "LogCategory", "LogEvent", "TestCase",
    "BugReport", "Commit", "Symptom", "RootCause", "Fix",
    "EvaluationQuestion", "DatasetExample",
})

RELATION_TYPES = frozenset({
    "CONTAINS", "BUILDS", "DEFINES", "DECLARES", "CALLS", "EMITS",
    "CONNECTS_TO", "HANDLES", "IMPLEMENTS", "EXPOSES_DBUS", "CALLS_DBUS",
    "READS_CONFIG", "WRITES_CONFIG", "LOADS_PLUGIN", "REGISTERS_SERVICE",
    "LOGS_TO", "TESTED_BY", "CHANGED_BY", "FIXES", "CAUSES",
    "OBSERVED_IN", "RELATED_TO", "ANSWERED_BY", "SUPPORTED_BY_EVIDENCE",
})
```

The rule, enforced in `Entity.__post_init__` and `Relation.__post_init__`, is: if you instantiate an `Entity` or `Relation` with an unknown type, you get a `ValueError`. Want a new type? You must add it to the frozenset first. That keeps the vocabulary from sprawling silently.

## Entity type families

Grouping the 32 types by concern makes them easier to remember:

### Build / code (10)

| Type        | What it is                                           | Example in mini repo                   |
|-------------|------------------------------------------------------|----------------------------------------|
| Repository  | The whole repo                                       | `mini_kde_repo`                        |
| Module      | A `project()` from CMake                             | `mini_search`                          |
| BuildTarget | An executable or library                             | (from `add_executable(...)`)           |
| SourceFile  | A `.cpp`                                             | `kfilesearcher.cpp`                    |
| HeaderFile  | A `.h` / `.hpp`                                      | `kfilesearcher.h`                      |
| CppClass    | `class Foo : public Bar { ... }`                     | `KFileSearcher`, `KFileSearchBackend`  |
| Function    | Free function (rare in KDE QObject world)            | (none in mini repo)                    |
| Method      | Member function                                      | `KFileSearcher::currentPath`           |
| Signal      | `Q_SIGNALS:` entry                                   | `resultsReady`, `searchFailed`         |
| Slot        | `Q_SLOTS:` entry                                     | `searchPath`, `cancel`                 |

### Runtime / IPC (7)

| Type           | What it is                            | Example                                  |
|----------------|---------------------------------------|------------------------------------------|
| QmlFile        | A `.qml`                              | `SearchView.qml`                         |
| QmlComponent   | A root `Capitalised { ... }` block    | `ApplicationWindow`                      |
| Property       | `Q_PROPERTY(...)`                     | `currentPath`, `maxResults`              |
| DbusService    | A well-known D-Bus name (v0.1)        | `org.kde.minisearch` (as service)        |
| DbusInterface  | An `<interface name="..."/>` element  | `org.kde.minisearch` (as interface)      |
| DbusMethod     | A `<method name="..."/>`              | `searchPath`, `cancel`, `currentPath`    |
| DbusSignal     | A `<signal name="..."/>`              | `resultsReady`, `searchFailed`           |

### Config / plugins (5)

| Type        | What it is                          | Example                          |
|-------------|-------------------------------------|----------------------------------|
| ConfigFile  | A `.kcfg` schema                    | `minisearch.kcfg`                |
| ConfigGroup | A `<group name="..."/>`             | `Search`, `Ui`                   |
| ConfigKey   | A `<entry name="..."/>` (also `readEntry`) | `MaxResults`, `IncludeHidden` |
| Plugin      | A pluginspec, KCM, KIO worker       | (v0.1)                           |
| DesktopFile | A `.desktop` entry                  | `MiniSearch`                     |

### Observability / lifecycle (5)

| Type          | What it is                       | Example                                       |
|---------------|----------------------------------|-----------------------------------------------|
| Service       | A long-running session service   | (v0.1, when systemd integration lands)        |
| LogCategory   | A `Q_LOGGING_CATEGORY` name      | `minisearch.backend`, `minisearch`            |
| LogEvent      | One log line                     | `scan complete processed= 312044 hits= 100`   |
| TestCase      | `tst_*.cpp` or ctest test entry  | `tst_kfilesearcher`                           |
| BugReport     | An issue / bug                   | (v0.1)                                        |

### Story / dataset (5)

| Type                | What it is                           | When it shows up                |
|---------------------|--------------------------------------|---------------------------------|
| Commit              | A git commit                         | When `repo.commits` are ingested|
| Symptom             | A user-visible failure               | Eval items                      |
| RootCause           | The diagnosis                        | Synthesized after debugging     |
| Fix                 | The patch / workaround               | Synthesized after debugging     |
| EvaluationQuestion  | One eval item                        | Built by [../src/eval/eval_set_builder.py](../src/eval/eval_set_builder.py) |
| DatasetExample      | One SFT/DPO record                   | Written by [../src/dataset/qa_generator.py](../src/dataset/qa_generator.py) |

That tour covers 32 types. Some are sparse in v0 and become more useful when you ingest a real KDE repo with commits, bug reports, and full plugin discovery.

## Relation type families

Twenty-four relations, also grouped by concern:

- **Structural:** `CONTAINS`, `BUILDS`, `DEFINES`, `DECLARES`, `IMPLEMENTS`.
- **Behavioural:** `CALLS`, `EMITS`, `HANDLES`, `CONNECTS_TO`, `READS_CONFIG`, `WRITES_CONFIG`, `LOGS_TO`, `LOADS_PLUGIN`, `REGISTERS_SERVICE`.
- **IPC:** `EXPOSES_DBUS`, `CALLS_DBUS`.
- **Causal / debugging:** `CAUSES`, `FIXES`, `CHANGED_BY`, `OBSERVED_IN`.
- **Bookkeeping:** `TESTED_BY`, `RELATED_TO`, `ANSWERED_BY`, `SUPPORTED_BY_EVIDENCE`.

`RELATED_TO` is the safety valve. The C++ extractor uses it for `#include` edges that point at KDE/Qt headers we have not seen as full entities yet (see `from_cpp` in [../src/ontology/extractor.py](../src/ontology/extractor.py)). When a v0.1 extension hardens an inclusion edge into a real `CppClass` reference, the `RELATED_TO` is replaced with the appropriate typed relation. Keeping the soft edge in v0 lets the graph stay dense without lying about semantics.

## One worked example: `KFileSearcher`

Open [../examples/mini_kde_repo/src/kfilesearcher.h](../examples/mini_kde_repo/src/kfilesearcher.h) and [../examples/mini_kde_repo/src/kfilesearcher.cpp](../examples/mini_kde_repo/src/kfilesearcher.cpp). The C++ reader produces, roughly:

```
CppReadResult(path=kfilesearcher.h,
  is_qobject=True,
  declared_classes=["KFileSearcher"],
  findings=[
    CppFinding(kind="include",  name="QObject",       line=4),
    CppFinding(kind="include",  name="QString",       line=5),
    CppFinding(kind="class",    name="KFileSearcher", line=12),
    CppFinding(kind="property", name="currentPath",   line=15),
    CppFinding(kind="property", name="maxResults",    line=16),
    CppFinding(kind="slot",     name="searchPath",    line=28),
    CppFinding(kind="slot",     name="cancel",        line=28),
    CppFinding(kind="signal",   name="currentPathChanged", line=32),
    CppFinding(kind="signal",   name="maxResultsChanged",  line=32),
    CppFinding(kind="signal",   name="resultsReady",       line=32),
    CppFinding(kind="signal",   name="searchFailed",       line=32),
  ])
```

(The `kfilesearcher.cpp` reader sees `KFileSearcher::KFileSearcher`, etc., and reports `implemented_classes=["KFileSearcher"]` plus a `kconfig_read` finding for `"MaxResults"`.)

The extractor in `from_cpp` does:

```
fid = Entity(SourceFile, "kfilesearcher.cpp")            # via _norm_source_id
cid = Entity(CppClass, "KFileSearcher")                  # from declared_classes
fid --DEFINES--> cid

for each signal:
    sid = Entity(Signal, f"{cid}::{signal_name}")
    cid --EMITS--> sid

for each slot:
    sid = Entity(Slot, f"{cid}::{slot_name}")
    cid --HANDLES--> sid

for the kconfig_read("MaxResults"):
    kid = Entity(ConfigKey, "MaxResults")
    cid --READS_CONFIG--> kid

for the include of <QObject>:
    hid = Entity(HeaderFile, "QObject")
    fid --RELATED_TO[kind=include]--> hid
```

The graph after just this slice:

```
SourceFile(kfilesearcher.cpp) --DEFINES--> CppClass(KFileSearcher)
                                  |  |  |  |
                                  |  |  |  +-- EMITS  --> Signal(resultsReady)
                                  |  |  +----- EMITS  --> Signal(searchFailed)
                                  |  +-------- EMITS  --> Signal(currentPathChanged)
                                  +----------- EMITS  --> Signal(maxResultsChanged)
                                  |
                                  +----------- HANDLES --> Slot(searchPath)
                                  +----------- HANDLES --> Slot(cancel)
                                  |
                                  +-- READS_CONFIG ---> ConfigKey(MaxResults)
                                  |
                                  +-- LOGS_TO --------> LogCategory(minisearch.backend)
                                                        (added later via from_log)
```

That is the subgraph the eval suite expects when asked *"Which signals does KFileSearcher emit?"* — see [../src/eval/eval_set_builder.py](../src/eval/eval_set_builder.py) item `eval:01:signal-emitted`.

## Cross-file linking: header vs. source

KDE C++ splits a class across a `.h` (declaration) and a `.cpp` (implementation). The header has `class KFileSearcher : public QObject { ... };`. The source has `KFileSearcher::KFileSearcher(...) { ... }`. A naive ingestion produces *two* `CppClass` entities or, worse, none — neither file alone contains both signatures.

We avoid that with the deterministic id from [../src/common/ids.py](../src/common/ids.py): `make_id("CppClass", "KFileSearcher")` is the same hash whether produced by the header path or the source path. The extractor uses `declared_classes` if the file has `class X {`, and falls back to `implemented_classes[0]` otherwise (`from_cpp` in [../src/ontology/extractor.py](../src/ontology/extractor.py)):

```
if not res.declared_classes and res.implemented_classes:
    primary = res.implemented_classes[0]
    implicit_class_id = bundle.add_entity(Entity(
        id=make_id("CppClass", primary),
        type="CppClass", name=primary,
        ...
    ))
```

This is one of those *small but load-bearing* design decisions. Without it, the `READS_CONFIG` edge from the `.cpp` reader would land on the source file rather than on the class, and the eval question about `MaxResults` would fail because the retriever expands from `KFileSearcher` and would never reach the key.

## When the ontology is wrong

The right time to extend the ontology is when you have a query you want to answer that the current vocabulary cannot express. Examples that might come up at v0.1:

- *"Which KIO workers can mount `smb://`?"* — needs `Plugin` plus a `IMPLEMENTS` relation to a `Service`.
- *"Which commits touched this class?"* — needs `Commit` plus `CHANGED_BY`. Both exist already; the ingest does not yet populate them.
- *"What did this bug report cause?"* — needs `BugReport`, `Symptom`, `RootCause`, `Fix` and the relations between them. The types exist; v0.1 wires them up.

If you need a new entity type, add it to `ENTITY_TYPES` and write a minimal extractor for it before adding any new relation. The reverse order leaves orphaned edges in the graph.

## Exercises

1. Re-read `Entity.__post_init__` in [../src/ontology/schema.py](../src/ontology/schema.py) and explain why the lab refuses to accept unknown entity types at construction time rather than at graph-build time.
2. Trace a `Q_PROPERTY` from `kfilesearcher.h` to the eventual `Property` node. Which edge connects it to its owning class? (Hint: look for `DECLARES` in the extractor.)
3. Pick one of `DbusService`, `Plugin`, `BugReport`, `Commit`. Sketch what an entity of that type would look like and which reader you would need to populate it. Where would you add the relation set?
4. Run a small Python REPL: load `artifacts/ontology/mini_repo_entities.jsonl`, count entities per type, and confirm the counts match the worked example above.
5. The mini repo extractor stores `is_qobject` as a string property on a `CppClass`. Argue for or against promoting it to a relation `IMPLEMENTS --> Type(QObject)`. What query would change?

## Further reading

- *Designing Data-Intensive Applications* by Martin Kleppmann, chapter 2, on property graphs and triple stores.
- *Semantic Web for the Working Ontologist* by Allemang, Hendler, and Gandon — particularly chapters 3 and 4 on RDF and OWL.
- The Wikidata data model documentation for a real-world example of a controlled-vocabulary ontology.
- The Schema.org documentation as a smaller, more pragmatic example.
- The Qt `QObject` documentation for the model that informs the `Signal`/`Slot`/`Property` triplet.
- The KDE `develop.kde.org` page on D-Bus introspection for the IPC half of the ontology.
- Cypher / Gremlin query primers (any tutorial) — the lab does not use them today, but they shape the design of the named queries in [../src/graph/queries.py](../src/graph/queries.py).
