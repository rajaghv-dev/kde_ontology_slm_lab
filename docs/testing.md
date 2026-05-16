# Testing

---

## Test types

The suite uses four broad test styles, all run through pytest with no special plugins required:

| Style | Description | Examples |
|---|---|---|
| **Import smoke** | Verify every public module imports without side effects | `test_imports.py` |
| **Unit** | Isolated tests of a single function or class with no external I/O | `test_ontology_schema.py`, `test_train_router.py`, `test_vector_store.py`, `test_context_builder.py`, `test_tokenizer_analysis.py` |
| **Integration** | Multiple subsystems wired together, driven from the bundled mini repo fixture | `test_mini_repo_ingest.py`, `test_graph_build.py`, `test_rag_answer_with_evidence.py`, `test_hybrid_search.py`, `test_dataset_jsonl_schema.py`, `test_traceability.py` |
| **End-to-end smoke** | Full pipeline from graph to graded eval result | `test_eval_smoke.py` |
| **Observability** | State-redirected module tests using `monkeypatch` and `tmp_path` | `test_observability.py` |

All tests run **completely offline** — no model downloads, no network access, no GPU required.

---

## How to run all tests

```bash
# Preferred: uses pytest.ini_options in pyproject.toml (addopts = "-q", testpaths = ["tests"])
pytest

# Equivalent explicit form
python3 -m pytest tests/ -q

# Via make
make test
```

---

## How to run specific test modules

```bash
# Single module
pytest tests/test_imports.py -v

# Single test function
pytest tests/test_graph_build.py::test_kfilesearcher_emits_resultsReady -v

# All observability tests
pytest tests/test_observability.py -v

# Everything except the slow end-to-end smoke
pytest tests/ --ignore=tests/test_eval_smoke.py -q

# Run only unit tests (by keyword)
pytest -k "schema or router or vector_store or tokenizer or context_builder" -v
```

---

## Test data

All tests use a **synthetic mini KDE repository** bundled at `examples/mini_kde_repo/`. This fixture is self-contained and intentionally small. Its path is resolved via `src.common.paths.MINI_REPO`.

The mini repo contains one realistic file of each supported format:

| Format | File path (relative to `mini_kde_repo/`) | What it exercises |
|---|---|---|
| C++ header | `src/kfilesearcher.h` | QObject class, signals, slots, Q_PROPERTY |
| C++ source | `src/kfilesearcher.cpp` | Config key reads, backend class |
| QML | `qml/SearchView.qml` | Component tree, C++ type usage |
| CMake | `CMakeLists.txt` | Project name, build targets |
| D-Bus XML | `dbus/org.kde.minisearch.xml` | Interface name, methods |
| KConfig | `kconfig/minisearch.kcfg` | Config entries (e.g. `MaxResults`) |
| .desktop | `desktop/minisearch.desktop` | App name, D-Bus activatable flag |
| Log file | `logs/minisearch.log` | Log categories (e.g. `minisearch.backend`) |

No real KDE source code, model weights, or network resources are needed to run any test.

---

## What is tested

### `test_imports.py` — module import health (1 test)

- Every public module under `src/` imports cleanly in a single test (`test_imports_clean`).
- Covers: `src.common.*`, `src.repo_ingest.*` (7 readers + scanner), `src.ontology.*`, `src.graph.*`, `src.traceability.*`, `src.tokenizer.*`, `src.dataset.*`, `src.rag.*`, `src.eval.*`.

### `test_mini_repo_ingest.py` — file readers (7 tests)

- `test_scan_finds_all_kinds`: scanner detects all 8 file kinds (cmake, cpp_source, cpp_header, qml, dbus, kconfig, desktop, log).
- `test_cpp_reader_finds_class_and_signals`: C++ reader reports `is_qobject = True` and finds signals `resultsReady`, `searchFailed`, `currentPathChanged`.
- `test_qml_reader_links_to_cpp_type`: QML reader identifies root component `ApplicationWindow` and used C++ type `KFileSearcher`.
- `test_cmake_reader_finds_target`: CMake reader finds project `MiniSearch` and target `minisearch`.
- `test_dbus_reader_finds_methods`: D-Bus reader finds interface methods `searchPath` and `cancel`.
- `test_kconfig_reader_finds_max_results`: KConfig reader finds entry `MaxResults`.
- `test_desktop_reader`: Desktop reader finds app name `MiniSearch` and `dbus_activatable = True`.
- `test_log_reader_finds_backend_category`: Log reader finds category `minisearch.backend`.

### `test_graph_build.py` — graph construction and queries (3 tests)

- `test_kfilesearcher_emits_resultsReady`: Builds the full graph from the mini repo; asserts `KFileSearcher` node exists and the `EMITS` edge to `resultsReady` signal is present.
- `test_kfilesearcher_reads_max_results`: Asserts `READS_CONFIG` edge from `KFileSearcher` to `MaxResults` config key.
- `test_backend_logs_to_minisearch_backend_category`: Asserts `LOGS_TO` edge from `KFileSearchBackend` to `minisearch.backend` log category.

### `test_ontology_schema.py` — schema validation (6 tests)

- Known entity types (e.g. `CppClass`) are accepted; unknown types raise `ValueError`.
- Known relation types (e.g. `EMITS`) are accepted; unknown relations raise `ValueError`.
- Core KDE concepts present in `ENTITY_TYPES`: `CppClass`, `Signal`, `Slot`, `QmlComponent`, `DbusInterface`, `DbusMethod`, `ConfigKey`, `LogCategory`, `Symptom`.
- Core relations present in `RELATION_TYPES`: `EMITS`, `HANDLES`, `READS_CONFIG`, `EXPOSES_DBUS`, `LOGS_TO`, `CONNECTS_TO`, `DEFINES`.

### `test_rag_answer_with_evidence.py` — RAG answer quality (2 tests)

- `test_in_domain_query_carries_evidence`: For "Which signals does KFileSearcher emit?", the answer must have non-empty `evidence_refs` and mention `KFileSearcher` in the text.
- `test_off_topic_query_falls_back_cleanly`: For "what is the weather on mars", either no evidence refs or the text does not hallucinate a KDE class name.

### `test_context_builder.py` — context window management (5 tests)

- `test_estimate_tokens_basic`: Token estimator returns 0 for empty string, positive for non-empty, and scales with length.
- `test_build_context_is_deterministic`: Same evidence list produces identical context string across multiple calls; citation indices `[1]`, `[2]`, ... are stable.
- `test_build_context_respects_budget`: With 20 evidence items and a 40-token budget, fewer than 20 items are cited and the total stays within budget.
- `test_build_context_zero_budget_returns_empty`: Budget of 0 returns empty string.
- `test_build_context_blocks_match_string_version`: `build_context_blocks` and `build_context` agree on which items are included and total token count.

### `test_dataset_jsonl_schema.py` — SFT record shape (2 tests)

- `test_examples_have_required_shape`: Every generated record has the required top-level keys (`id`, `task_type`, `instruction`, `input`, `output`, `evidence`, `negative_examples`, `metadata`), an allowed `task_type`, and evidence items with the required keys.
- `test_examples_are_unique`: No two records share the same `(instruction, output)` pair.

### `test_eval_smoke.py` — end-to-end eval pipeline (1 test)

- `test_pipeline_evaluates_end_to_end`: Builds graph, runs `mini_repo_eval_set()`, answers all questions via `answer()`, grades each, aggregates; asserts `n == len(items)` and `overall_pass_rate > 0.0`.

### `test_hybrid_search.py` — hybrid retrieval (4 tests)

- `test_in_domain_query_returns_graph_hits`: "Which signals does KFileSearcher emit?" returns at least one hit whose name mentions `KFileSearcher`.
- `test_vector_contributes_when_graph_misses_paraphrase`: A paraphrased query returns hits, each with at least one source leg (`graph` or `vector`).
- `test_sources_are_attributed_when_both_legs_hit`: At least one hit is attributed to the `graph` leg for an exact-name query.
- `test_empty_vector_store_still_returns_graph_hits`: With an empty vector store, the graph leg still fires and all hits have `sources == {"graph"}`.

### `test_observability.py` — no-install observability stack (11 tests)

All tests use a `monkeypatch`/`tmp_path` fixture (`obs`) that reloads observability modules and redirects JSONL output to a temporary directory. Prometheus client is not required.

- `test_counter_inc_writes_jsonl`: Counter increments write correctly-shaped JSONL rows.
- `test_counter_rejects_negative`: Negative increment raises `ValueError`.
- `test_gauge_set_inc_dec`: Gauge set/inc/dec write rows with correct values.
- `test_histogram_observes`: Histogram observation writes correct metric name and value.
- `test_forbidden_labels_raise`: Labels `file_path` and `trace_id` raise `ValueError` with message "forbidden".
- `test_unknown_labels_raise`: Unknown label keys raise `ValueError` with message "unknown".
- `test_time_block_records_positive_duration`: `time_block` context manager measures real elapsed time.
- `test_jsonl_is_valid_json_per_line`: Every line in the JSONL output parses as valid JSON.
- `test_span_nesting`: Parent/child spans are linked via `parent_id`; both have `end_ns >= start_ns`.
- `test_report_rolls_up`: `build_report()` creates a Markdown file containing metric summaries and span names.
- `test_start_http_server_is_safe_without_prom`: Calling `start_http_server(port=0)` does not raise even if `prometheus_client` is absent.

### `test_tokenizer_analysis.py` — offline tokenizer (2 tests)

- `test_analyze_runs_offline`: Analysis uses `tokenizer_name = "whitespace-fallback"`, covers all KDE terms, and reports `mean_compression > 0`.
- `test_worst_terms_sorted_ascending`: `worst_terms(n=3)` returns exactly 3 results sorted by compression ascending.

### `test_traceability.py` — symptom-to-code trace (1 test)

- `test_slow_folder_symptom_finds_backend`: Tracing "MiniSearch is slow when opening folders with many files" against the full graph returns evidence containing `KFileSearcher` or `KFileSearchBackend` and exposes the `minisearch.backend` log category.

### `test_train_router.py` — task router (11 tests)

- `test_returns_one_of_the_seven_adapters`: `route()` always returns a value in `ADAPTERS`.
- `test_architecture_default_fallback`: Empty or whitespace-only query routes to `"architecture"`.
- `test_architecture_explicit`, `test_debugging_route`, `test_code_navigation_route`, `test_tool_use_route`, `test_patch_review_route`, `test_qml_cpp_route`, `test_dbus_config_route`: Keyword-bearing queries route to the correct adapter.
- `test_route_is_deterministic`: Same query always returns the same adapter.
- `test_explain_returns_match_metadata`: `explain()` returns adapter name, matched pattern, and rule index for a matched query.
- `test_explain_fallback_has_no_match`: `explain("")` returns `matched = None` and adapter `"architecture"`.

### `test_vector_store.py` — in-memory vector store (6 tests)

- `test_add_and_query_returns_self`: Adding one vector and querying with it returns itself with cosine score ≈ 1.
- `test_query_orders_by_similarity`: Results are ordered by cosine similarity descending.
- `test_query_handles_empty_store`: Empty store returns `[]` without error.
- `test_add_many_bulk_insert`: `add_many()` inserts multiple vectors; `len(store)` is correct.
- `test_dim_mismatch_raises`: Adding a vector of wrong dimension raises `ValueError`.
- `test_save_and_load_roundtrip`: Store saved to `.npz` and reloaded preserves dimension, count, and query results.

---

## What is NOT tested (gaps)

| Gap | Reason / notes |
|---|---|
| Real KDE repository ingestion | No real KDE source is bundled; tests use the synthetic mini repo only |
| `src.cli.*` CLI commands | The CLI subcommands (`ingest`, `graph`, `tokenizer`, `dataset`, `train`, `eval`) have no dedicated tests; only the router logic is unit-tested |
| `kde-lab info` and `kde-lab pipeline` CLI paths | No integration test invokes the CLI as a subprocess |
| LoRA / QLoRA training loop | Requires `torch`, `peft`, `trl`; not installable without GPU/heavy extras |
| `src.dataset.qa_generator` task type coverage | Tests verify shape and uniqueness but not that all six `task_type` values are generated |
| Eval grader accuracy | `test_eval_smoke.py` asserts `pass_rate > 0` but does not assert a minimum threshold |
| Multi-repo / multi-bundle graph merging | Only single-bundle graphs are tested |
| RDF/OWL export (`rdf` extra) | No tests exist for the optional RDF serialization path |
| Visualization (`viz` extra) | No tests for matplotlib/graphviz outputs |
| Prometheus HTTP metrics server | Only the no-install fallback path is tested; `prometheus_client` integration is untested |
| Notebook code (`notebooks/`) | Notebooks are not executed as part of the test suite |
| `conftest.py` isolation | The root `conftest.py` only adds `sys.path`; there are no session-level fixtures for expensive setup (graph build is repeated per test module) |
| Windows / macOS CI | No platform matrix is configured |

---

## Known warnings

The following warnings are expected and harmless:

| Warning | Source | Reason |
|---|---|---|
| `importlib.reload` on observability modules | `test_observability.py` `obs` fixture | Intentional: reloads modules to reset global state and redirect file paths to `tmp_path`. May emit `ResourceWarning` about unclosed files on some Python versions. |
| `DeprecationWarning` from networkx | `src.graph.builder` | NetworkX 3.x occasionally warns about internal API usage; not project code. |
| No `__init__.py` in `tests/` subdirs | pytest collection | `tests/__init__.py` exists; pytest collects all test files normally. |

---

## CI validation (currently: none)

No CI pipeline (GitHub Actions, GitLab CI, etc.) is configured at this time.

**To add minimal CI**, create `.github/workflows/test.yml`:

```yaml
name: test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: python3 -m ruff check src/
      - run: pytest -q
```

This would validate the full test suite on Python 3.10, 3.11, and 3.12 on every push and pull request, taking approximately 60–90 seconds per matrix entry (no GPU required).
