# 00 — The big picture

This lab teaches you how to turn a desktop operating system into something a small language model can reason about. The desktop in question is KDE; the model is a tiny one you can fine-tune on a single GPU; the contract between them is an explicit ontology and a graph that holds every fact the model is allowed to claim.

If you only read one chapter, read this one. Everything else is a deeper pass over what we sketch here.

## Why KDE-as-a-system, not KDE-as-source

A common first instinct is to point a code-trained model at the KDE source tree and hope it can answer questions like *"why is Dolphin slow when I open this folder?"* It cannot, and it will lie politely while failing.

The reason is that a running KDE desktop is not just C++. It is:

- C++ classes wired together with Qt signals and slots,
- QML views that bind to those C++ classes via `qmlRegisterType`,
- D-Bus services that other processes call into,
- KConfig keys that change runtime behaviour from outside the binary,
- `QLoggingCategory` channels you can enable to inspect what is happening,
- desktop files that wire applications into the menu and session,
- plugins loaded at runtime that the static call graph never sees,
- and bug reports, commits, and tests describing past failures.

A code-only model sees the C++ and misses everything else. The model in this lab sees all of it — through a single graph that links every layer to every other layer.

## The OCT framework

Three questions structure the entire repo:

1. **Observability** — *what can we see?* Files, classes, QML items, D-Bus names, log categories, config keys, CMake targets, tests, commits, stack traces.
2. **Controllability** — *what can we change?* Build flags, test selection, logging rules, config keys, environment variables, plugins, service restarts, command-line tools, D-Bus calls.
3. **Traceability** — *how do we connect cause to effect?* A user symptom flows back through a log event, a service, a D-Bus call, a QML component, a C++ class, a function, a config key, a commit, a test, and a fix.

Every module either records something observable, exposes something controllable, or threads a trace through both. If a module fails all three checks, it does not belong in this lab. Chapter [13_observability_with_grafana_prometheus.md](13_observability_with_grafana_prometheus.md) shows how the same triad shapes the optional Prometheus + Grafana stack.

## The lab as a vertical slice

Most KDE-on-LLM projects pile horizontally: build a giant ingester, then a giant tokenizer, then a giant training script, and only at the end discover that none of them fit together. We do the opposite. From day one the lab runs a complete vertical slice on a synthetic mini repo:

```
mini repo  --->  ingest  --->  ontology  --->  graph  --->  traceability
                                                                   |
                                                                   v
                              eval  <---  RAG  <---  dataset  <---  tokenizer
```

That is seven stages, end-to-end, in a single command:

```
python examples/run_mini_repo_pipeline.py
```

The script lives at [../examples/run_mini_repo_pipeline.py](../examples/run_mini_repo_pipeline.py). It runs offline, writes its artifacts under [../artifacts/](../artifacts/), and prints a Markdown summary. On the v0 mini repo it grades a tiny RAG eval at roughly 66.67% pass rate. That number is the baseline we want every later change to beat.

## The mini repo

The fixture at [../examples/mini_kde_repo/](../examples/mini_kde_repo/) is a deliberately minimal KDE-style project called `MiniSearch`. It exists so the seven-stage pipeline has something concrete to chew on without downloading anything. The pieces:

- `src/kfilesearcher.h` and `.cpp` — a `KFileSearcher` `QObject` with three signals (`resultsReady`, `searchFailed`, `currentPathChanged`), two slots (`searchPath`, `cancel`), two Q_PROPERTY entries, and a `readEntry("MaxResults", ...)` call into KConfig.
- `src/kfilesearchbackend.h` and `.cpp` — a backend `QObject` that owns the scan thread.
- `qml/SearchView.qml` — imports `org.kde.minisearch 1.0` and instantiates a `KFileSearcher`.
- `dbus/org.kde.minisearch.xml` — D-Bus introspection XML exposing `searchPath`, `cancel`, `currentPath`, plus signals.
- `kconfig/minisearch.kcfg` — defines `MaxResults`, `IncludeHidden`, `DefaultPath`, `ThumbnailEnabled`.
- `desktop/minisearch.desktop` — `DBusActivatable=true`, the usual desktop fields.
- `logs/minisearch.log` — runtime trace lines under the `minisearch.backend` category, one of which says *"backend.scanDirectory hot"*.
- `tests/tst_kfilesearcher.cpp` — a unit test.

The mini repo is fictional but representative. It exercises every reader, every ontology entity type that v0 cares about, and every traceability path the eval suite measures.

## What you can ask the trained model

The eval suite in [../src/eval/eval_set_builder.py](../src/eval/eval_set_builder.py) lists the v0 questions, all of which the model and the RAG answerer must learn to answer well:

- *Which signals does `KFileSearcher` emit?*
- *Which KConfig key controls the maximum number of results?*
- *When MiniSearch is slow, which log category should I enable?*
- *Which C++ class is the `SearchView` QML component backed by?*
- *Which D-Bus methods does `org.kde.minisearch` expose?*
- *What signal does the imaginary `KFooBarMaker` emit?* (the model must refuse)

Once you scale this up to real KDE source, the questions become:

- Why is Dolphin slow when opening a folder?
- Which KDE component owns file indexing?
- How does KIO connect to Dolphin?
- Where is a given setting stored?
- Which D-Bus service should be called?
- Which logs should I inspect?

Chapter [09_debug_reasoning_eval.md](08_debug_reasoning_eval.md) (file `08_debug_reasoning_eval.md`) shows what a passing answer looks like for each.

## The seven-stage pipeline, mapped to chapters

```
[1] ingest     -> 02_repo_understanding_pipeline.md
[2] ontology   -> 03_kde_ontology_design.md
[3] graph      -> 04_graph_schema.md
[4] tokenizer  -> 05_tokenizer_strategy.md
[5] dataset    -> 06_dataset_generation_strategy.md
[6] training   -> 07_training_recipes.md
[7] RAG + eval -> 08_debug_reasoning_eval.md
```

Surrounding those seven you will find:

- [01_kde_architecture_map.md](01_kde_architecture_map.md) — the KDE platform itself, so the ontology has somewhere real to point at.
- [09_colab_guide.md](09_colab_guide.md) and [10_local_training_guide.md](10_local_training_guide.md) — how to actually run the training stages.
- [11_failure_modes.md](11_failure_modes.md) — the things that will go wrong, and the metric that tells you.
- [12_privacy_and_license_notes.md](12_privacy_and_license_notes.md) — KDE licensing and the redaction discipline.
- [13_observability_with_grafana_prometheus.md](13_observability_with_grafana_prometheus.md) — the optional metrics stack.
- [14_paper_outline.md](14_paper_outline.md) — the paper that could come out of this work.
- [progress_log.md](progress_log.md) — the dated trail of what shipped when.

## Five RAG modes, one eval

The lab compares five strategies for connecting a small model to KDE knowledge:

1. **Vector-only** — pure embedding retrieval over chunked source.
2. **Graph-only** — the v0 retriever, which walks the ontology graph.
3. **Hybrid** — vector candidates re-ranked by graph proximity.
4. **SFT-only** — fine-tuned model, no retrieval at inference.
5. **SFT + retrieval** — fine-tuned model with hybrid retrieval at inference.

Each is graded by the same suite in [../src/eval/](../src/eval/). The point is not to crown a winner once but to keep the comparison live as the lab grows.

## Recipes only, no auto-downloads

The repo ships code, configs, and a synthetic fixture. It does not auto-download model weights, datasets, or KDE source — see [../README.md](../README.md) and [12_privacy_and_license_notes.md](12_privacy_and_license_notes.md). Any network access is opt-in and explicit. That keeps the lab cheap, reproducible, and safe to run in CI.

## Exercises

1. Run `python examples/run_mini_repo_pipeline.py` and open every file it writes under `artifacts/`. Identify which artifact corresponds to each of the seven stages above.
2. Pick one question from the eval suite and trace it by hand: from question text, through `src/rag/graph_retriever.py`, into `src/traceability/symptom_to_code.py`, ending at the matching `Entity` ids in `artifacts/ontology/mini_repo_entities.jsonl`.
3. Re-read the OCT triad and label each module under `src/` with O, C, T, or some combination. Where do you find gaps?
4. Imagine adding a new symptom — *"thumbnails sometimes never render"*. Which mini repo files would you have to extend before the eval set could grade a passing answer?
5. Sketch a five-line summary of why this lab uses an explicit ontology rather than relying on a large pretrained model's implicit one. Compare with your sketch after chapter 03.

## Further reading

- The KDE architecture overview at `develop.kde.org` (search "KDE Frameworks tier system" and "Plasma architecture").
- *Programming with Qt 6* by Daniel Eckert (any recent edition) for signals, slots, properties, and `QObject` lifecycle.
- *Designing Data-Intensive Applications* by Martin Kleppmann, chapter 2 ("Data models and query languages"), for the property-graph perspective behind the ontology.
- *Retrieval-Augmented Generation for Large Language Models: A Survey* — search arXiv; pick the most recent revision.
- The `networkx` `MultiDiGraph` documentation for the concrete graph model used in [../src/graph/builder.py](../src/graph/builder.py).
- The `tokenizers` library documentation for the BPE / WordPiece / Unigram families covered in chapter 05.
- The CHANGELOG and TODO at [../CHANGELOG.md](../CHANGELOG.md) and [../TODO.md](../TODO.md) for what shipped and what is coming next.
