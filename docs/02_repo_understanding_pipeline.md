# 02 — Repo understanding pipeline

Reading a KDE repository the way a compiler reads source code does not get you to traceability. You also need every cross-cutting concern: which D-Bus name a binary registers, which KConfig keys it reads, which log category it writes to. This chapter walks the seven steps that turn a repo on disk into a knowledge graph, using the mini repo as the worked example.

The complete pipeline is the runnable script [../examples/run_mini_repo_pipeline.py](../examples/run_mini_repo_pipeline.py). Open it in another tab. The chapter mirrors its order.

## The seven steps

```
[1] scan         (src/repo_ingest/scanner.py)
[2] read         (src/repo_ingest/*_reader.py)
[3] extract      (src/ontology/extractor.py)
[4] graph        (src/graph/builder.py)
[5] trace        (src/traceability/symptom_to_code.py)
[6] tokenize     (src/tokenizer/analyze_tokens.py)
[7] dataset      (src/dataset/qa_generator.py)
```

Steps 8 and 9 — RAG and eval — live in the eval pipeline and are covered in chapter [08_debug_reasoning_eval.md](08_debug_reasoning_eval.md). Steps 1 through 7 are the *understanding* layer; they have to be solid before training is meaningful.

## Step 1: scan

The scanner walks the repo root recursively and classifies every file it recognises. The classification is intentionally narrow: the v0 lab knows about CMake, C++ source/header, QML, D-Bus XML, KConfig XML, `.desktop` files, and `.log` files.

```
KIND_BY_EXT = {
    ".cpp": "cpp_source",
    ".cc":  "cpp_source",
    ".cxx": "cpp_source",
    ".h":   "cpp_header",
    ".hpp": "cpp_header",
    ".qml": "qml",
    ".kcfg": "kconfig",
    ".desktop": "desktop",
    ".xml": "xml",
    ".cmake": "cmake_module",
    ".md":  "markdown",
    ".log": "log",
}
```

Two specialisations matter:

- `CMakeLists.txt` is classified as `cmake` by filename, not extension.
- `.xml` files inside a directory named `dbus/` are reclassified as `dbus` (this is the `DBUS_HINT_DIR` rule in [../src/repo_ingest/scanner.py](../src/repo_ingest/scanner.py)).

Dotfiles and dot-directories are skipped. The output is a `ScanReport` with a list of `ScannedFile(path, kind, rel_path)`.

For the mini repo the scan finds:

- 1 root `CMakeLists.txt` (top-level fixture build),
- 4 C++ files (header and source for `KFileSearcher` and `KFileSearchBackend`) plus `main.cpp` and the test source,
- 1 QML file (`SearchView.qml`),
- 1 D-Bus XML (`org.kde.minisearch.xml`),
- 1 KConfig XML (`minisearch.kcfg`),
- 1 desktop file (`minisearch.desktop`),
- 1 log file (`minisearch.log`),
- 1 `tests/CMakeLists.txt`, 1 README.

That is roughly twelve recognised files, which is enough material to populate every entity type covered in this chapter.

## Step 2: per-format readers

Each kind has its own reader. They are small on purpose: every one fits on a single screen and uses only regular expressions. They do not parse — they *spot* the shapes the ontology needs.

### `cpp_reader.py`

[../src/repo_ingest/cpp_reader.py](../src/repo_ingest/cpp_reader.py) extracts:

- `class Foo : public Bar {` declarations,
- `Q_OBJECT` presence,
- `Q_PROPERTY(Type name READ ...)` properties,
- `Q_SIGNALS:` / `signals:` blocks and the function names inside them,
- `public Q_SLOTS:` / `private slots:` blocks,
- `Q_LOGGING_CATEGORY(VAR, "name.dot.path")`,
- `readEntry("Key", ...)` calls,
- `#include <Header>` lines.

The output is a `CppReadResult` with `findings`, `declared_classes`, and `implemented_classes`. The last field is the key to the *cross-file linking* trick: when a `.cpp` file does not contain `class X { ... }` but does contain `void X::foo()`, we capture `X` as an *implemented* class so the extractor can link the methods, signals, and slots to a `CppClass` entity even when the declaration sat in a separate header.

### `qml_reader.py`

[../src/repo_ingest/qml_reader.py](../src/repo_ingest/qml_reader.py) pulls the `import` lines, the root component, and any used Capitalised types. It filters out a small set of built-ins like `ApplicationWindow`, `Column`, `Row`, `Text`, `Label`, `ListView` so the only `used_types` that escape are real C++ backed types. In the mini repo, that yields `KFileSearcher` as the one significant used type.

### `cmake_reader.py`

[../src/repo_ingest/cmake_reader.py](../src/repo_ingest/cmake_reader.py) finds `project(...)`, `add_executable(...)`, `add_library(...)`, `target_link_libraries(...)`, and `add_subdirectory(...)`. Sources passed to `add_executable` and `add_library` become `SourceFile` and `HeaderFile` entities the ontology can hang relations on.

### `dbus_reader.py`, `kconfig_reader.py`, `desktop_file_reader.py`, `log_reader.py`

Each parses the corresponding XML / INI / log format. They are all variants of "open the file, walk the elements or lines, return a dataclass". The log reader emits a `LogEvent` per matching line; the others emit interfaces, groups, entries, or desktop fields.

## Step 3: extract — turn reader output into ontology

The extractor lives in [../src/ontology/extractor.py](../src/ontology/extractor.py). Each `from_<format>` function takes a reader result and an `ExtractionBundle` and grows it with `Entity` and `Relation` records.

The two patterns that come up repeatedly:

1. **Deterministic ids.** Every `Entity.id` is `kde:<entity_type>:<sha1(qualified_name.lower())[:8]>` (see [../src/common/ids.py](../src/common/ids.py)). That means the same class produces the same id from the header reader and the source reader, even if they run in different orders. The extractor exploits this to add edges that point at ids it has not yet created — the graph builder fills them in later.

2. **Owner resolution.** Inside `from_cpp`, the extractor tracks `last_class_id` as it walks findings. Signals and slots attach to that class. When the source file has no `class X {` block but does have `X::foo()` definitions, the extractor synthesises an `implicit_class_id` from `implemented_classes[0]` so the findings still have an owner.

For the mini repo, after extraction you have entities like:

```
kde:Repository:<hash>           name=mini_kde_repo
kde:Module:<hash>               name=mini_search   (from CMake project())
kde:CppClass:<hash>             name=KFileSearcher
kde:Signal:<hash>               name=resultsReady       (EMITS edge from class)
kde:Signal:<hash>               name=searchFailed
kde:Signal:<hash>               name=currentPathChanged
kde:Signal:<hash>               name=maxResultsChanged
kde:Slot:<hash>                 name=searchPath
kde:Slot:<hash>                 name=cancel
kde:Property:<hash>             name=currentPath
kde:Property:<hash>             name=maxResults
kde:ConfigKey:<hash>            name=MaxResults
kde:ConfigKey:<hash>            name=IncludeHidden
kde:LogCategory:<hash>          name=minisearch.backend
kde:DbusInterface:<hash>        name=org.kde.minisearch
kde:DbusMethod:<hash>           name=searchPath, name=cancel, ...
kde:QmlComponent:<hash>         name=ApplicationWindow (root) or KFileSearcher
kde:DesktopFile:<hash>          name=MiniSearch
```

(The hashes are stable but elided here.) The extractor also dumps everything as JSONL to `artifacts/ontology/mini_repo_entities.jsonl` so the notebooks and the docs have something to inspect.

## Step 4: build the graph

Step 4 is [../src/graph/builder.py](../src/graph/builder.py). It folds the `ExtractionBundle` into a `networkx.MultiDiGraph`. Two design choices to keep in mind:

- **Multi-edges are allowed.** Two `CppClass` nodes can have both a `DEFINES` and a `RELATED_TO` edge between them. NetworkX's `MultiDiGraph` keys them on `rel`.
- **Dangling relations are dropped.** If a relation points at an id that does not exist, the builder silently drops it. The lab prefers a clean graph over noisy edges; chapter [11_failure_modes.md](11_failure_modes.md) discusses when that becomes a bug.

The graph is saved as both JSON (`artifacts/graphs/mini_repo.json`) and GraphML (`artifacts/graphs/mini_repo.graphml`). The JSON is for notebooks; the GraphML is for Gephi or yEd if you want to look at the graph visually.

## Step 5: traceability sanity check

Before tokenizing or generating data, the pipeline runs a real traceability query as a smoke test. The script asks:

```
MiniSearch is slow when opening folders with many files
```

`src/traceability/symptom_to_code.py` extracts seed terms (`MiniSearch`, `slow`, `folder`, `file`), matches them against entity names with `find_by_name`, and does a breadth-first expansion along the high-signal relations (`EMITS`, `READS_CONFIG`, `LOGS_TO`, `EXPOSES_DBUS`, `CONNECTS_TO`, `TESTED_BY`, `DEFINES`, `CONTAINS`, `BUILDS`).

The smoke output prints how many evidence items came back. On v0 you should see at least 4 — typically the `KFileSearcher` class, its `minisearch.backend` log category, the `MaxResults` config key, and one of the source files. If you get zero, the readers and the extractor are out of sync and the rest of the pipeline cannot help.

## Step 6: tokenizer report

Tokenization is the cheap step that decides whether KDE terms are expensive or cheap for the model to predict. [../src/tokenizer/analyze_tokens.py](../src/tokenizer/analyze_tokens.py) defines a canonical list of KDE terms (`KFilePlacesModel`, `qmlRegisterType`, `org.kde.minisearch`, ...) and a canonical list of phrases (`connect(...)`, `journalctl --user -u plasma-plasmashell`, ...). The analyzer reports `chars/tokens` compression per term and writes the result to `artifacts/tokenizer_reports/fallback_token_cost.json`.

Run the script and look at the lowest-compression rows. Those are the terms where the model is paying many tokens per concept; they are candidates for special-token addition or tokenizer-train decisions in chapter [05_tokenizer_strategy.md](05_tokenizer_strategy.md).

## Step 7: dataset generation

Finally, [../src/dataset/qa_generator.py](../src/dataset/qa_generator.py) walks the graph and emits an SFT JSONL dataset to `artifacts/datasets/mini_repo_sft_v0.jsonl`. Each record is evidence-grounded: every `output` is justified by a list of `evidence` entries pointing at the entities (file, line, symbol) that support it. We never generate a fact that the graph cannot back up.

The templates are listed at the bottom of `qa_generator.py`:

- `template_signal_emission` — *"Which signals does X emit?"*
- `template_config_keys` — *"Which KConfig keys does X read?"*
- `template_qml_backend` — *"Which C++ class is QML component Y backed by?"*
- `template_log_to_component` — *"When debugging X, which log category to enable?"*
- `template_dbus_methods` — *"Which D-Bus methods does interface Z expose?"*
- `template_refusal` — *"What signal does the imaginary KFooBarMaker emit?"* (the model must say it does not see one)

Chapter [06_dataset_generation_strategy.md](06_dataset_generation_strategy.md) covers the schema and the "I don't know" discipline.

## One concrete trace, end-to-end

To pin all of this down, follow the slot `KFileSearcher::cancel` from source to dataset:

```
[1] scan      kfilesearcher.h, kfilesearcher.cpp           kind=cpp_header|cpp_source
[2] cpp_reader.read_cpp("kfilesearcher.h")
    findings  CppFinding(kind="class", name="KFileSearcher", line=12)
    findings  CppFinding(kind="slot",  name="cancel",        line=30)
[3] from_cpp(bundle, result)
    Entity    id=kde:CppClass:<hash>  name=KFileSearcher
    Entity    id=kde:Slot:<hash>      name=cancel
    Relation  KFileSearcher --HANDLES--> cancel
[4] build_graph(bundle)
    Node      kde:CppClass:<hash>  type=CppClass  name=KFileSearcher
    Node      kde:Slot:<hash>      type=Slot      name=cancel
    Edge      (KFileSearcher, cancel, key="HANDLES")
[5] trace("MiniSearch is slow ...")
    Seed terms include "MiniSearch", which fuzzily matches "KFileSearcher" by substring.
    The slot `cancel` shows up as 1-hop neighbour via HANDLES.
[6] tokenize  KFileSearcher  =>  ["k", "file", "searcher"]  (whitespace-fallback)
[7] dataset_template_log_to_component
    instruction: "When debugging KFileSearcher, which log category should I enable to see runtime traces?"
    evidence:    [{file=...kfilesearcher.h, symbol=KFileSearcher},
                  {file=..., symbol=minisearch.backend}]
```

That same trace is what the eval expects the model to produce when asked the question. If the trace breaks anywhere — wrong file ingested, wrong reader regex, missing extractor branch — the eval drops a point and you have a concrete pointer to which step needs fixing.

## Exercises

1. Run `python examples/run_mini_repo_pipeline.py` and confirm the seven artifacts in `artifacts/` correspond to the seven steps. Identify which artifact lets you debug each step in isolation.
2. Open [../examples/mini_kde_repo/src/kfilesearchbackend.h](../examples/mini_kde_repo/src/kfilesearchbackend.h) and list every shape `cpp_reader.py` should pick up. Compare with `result.findings` if you run the reader directly in a Python REPL.
3. Add a deliberate typo to a `Q_SIGNALS:` block (e.g. `Q_SIGNAL:` without the S). Re-run the pipeline; the eval pass rate should drop. Identify which test in `tests/` catches the regression.
4. Drop a fictional `MiniSearch.log` line such as `2026-05-13T11:00:00.000 ERROR minisearch.backend index database corrupt`. Re-run and check that the new `LogEvent` shows up in the graph JSON.
5. Sketch one more reader you would add for v0.1 (Doxygen, kernel-style API headers, AppStream metadata, or systemd `.service` files). Which entity types does it justify? Does the ontology already support them?

## Further reading

- The `networkx` documentation for `MultiDiGraph` and graph I/O.
- The Tree-sitter project — when v0.1 swaps the regex C++ reader for a real parser, this is the candidate.
- Python's `xml.etree.ElementTree` documentation for the D-Bus and KConfig parsers.
- The KDE `develop.kde.org` tutorial on creating a KCM module (good context for what the KConfig layer actually does).
- The `qmlRegisterType` reference in the Qt documentation, which explains the C++/QML id we map in `from_qml`.
- *Crafting Interpreters* by Robert Nystrom for the discipline of cheap, regex-shaped readers before you reach for a parser.
