# Interfaces

This document covers every public interface in `kde_ontology_slm_lab` that
a learner, contributor, or calling code is expected to use directly. Interfaces
are organised by layer, from the CLI down to individual module functions.

---

## CLI — `kde-lab`

Entry point: `src.cli.main:main` (registered as `kde-lab` in `pyproject.toml`).

All subcommands are registered lazily: heavy imports (networkx, readers,
extractor) happen only when the subcommand is actually invoked, so
`kde-lab --help` and `kde-lab info` are fast.

### `kde-lab info`

**Purpose**: Diagnostic. Print Python version, canonical paths, and a
one-line summary of what each config file enables. Loads only YAML; imports
nothing heavy.

**Input**: None.

**Output**: Human-readable text to stdout showing:
- Python version and platform
- `REPO_ROOT`, `CONFIGS`, `ARTIFACTS`, `DATASETS`, `MINI_REPO` paths
- For each of 7 config files: whether it exists and its top-level keys
- Enabled repos, declared models, active dataset generators, eval benchmarks

**Side effects**: None. Read-only.

**Error behavior**: If a config file is malformed YAML (top-level is not a
mapping), `load_yaml` raises `ValueError`.

**Tests**: `tests/test_imports.py` (smoke import).

**Documentation status**: Docstring in `src/cli/main.py`.

---

### `kde-lab pipeline`

**Purpose**: Run the complete 9-stage vertical slice on the mini repo. Delegates
to `examples/run_mini_repo_pipeline.py:main()`.

**Input**: None.

**Output**: Artifact files in `artifacts/`; summary banner to stdout.

**Side effects**: Creates/overwrites files under `artifacts/graphs/`,
`artifacts/ontology/`, `artifacts/tokenizer_reports/`, `artifacts/datasets/`,
`artifacts/eval_reports/`, `artifacts/logs/`.

**Error behavior**: Returns exit code 1 if `MINI_REPO` does not exist.

**Tests**: `tests/test_mini_repo_ingest.py`, `tests/test_eval_smoke.py`.

**Documentation status**: Module docstring in `run_mini_repo_pipeline.py`.

---

### `kde-lab ingest`

**Purpose**: Scan a repo declared in `configs/repos.yaml`, run all per-format
readers, extract ontology entities and relations, build the graph, and persist
all artifacts.

**Input**:

| Option | Default | Description |
|---|---|---|
| `--repo` | `mini_kde_repo` | Name key in `configs/repos.yaml`; must be `enabled: true` |

**Output** (stdout):
```
entities written     : <N>  (<path>)
relations written    : <N>  (<path>)
graph json           : <path>
graph graphml        : <path>
```

**Side effects**:
- `artifacts/ontology/<repo>_entities.jsonl`
- `artifacts/ontology/<repo>_relations.jsonl`
- `artifacts/graphs/<repo>.json`
- `artifacts/graphs/<repo>.graphml`

**Error behavior**: `ClickException` if repo name is not found in config, if
`enabled: false`, or if the resolved path does not exist.

**Tests**: `tests/test_mini_repo_ingest.py`.

**Documentation status**: Module docstring in `src/cli/ingest_cmd.py`.

---

### `kde-lab graph`

**Purpose**: Rebuild the NetworkX graph from previously persisted ontology JSONL
files and re-export JSON + GraphML. Useful when the graph build logic changes
without re-running the readers.

**Input**:

| Option | Default | Description |
|---|---|---|
| `--repo` | `mini_kde_repo` | Reads `artifacts/ontology/<repo>_entities.jsonl` |
| `--out` | None | Override JSON output path; GraphML sibling is derived |

**Output** (stdout):
```
nodes                : <N>
edges                : <N>
graph json           : <path>
graph graphml        : <path>
```

**Side effects**: Writes JSON and GraphML graph files.

**Error behavior**: `ClickException` if the entities JSONL file does not exist
(message: "run `kde-lab ingest` first"). `ValueError` from `Entity.__init__`
if a stored record contains an unknown entity type.

**Tests**: `tests/test_graph_build.py`.

**Documentation status**: Module docstring in `src/cli/graph_cmd.py`.

---

### `kde-lab tokenizer`

**Purpose**: Run the offline token-cost analyser over the canonical KDE term
list and print the five worst-tokenised terms.

**Input**:

| Option | Default | Description |
|---|---|---|
| `--report-path` | None | Override JSON report path (priority: flag > config > default) |

**Output** (stdout):
```
tokenizer            : <name>
mean compression     : <float> chars/token
mean tokens per term : <float>
report               : <path>

worst 5 terms (lowest chars/token):
  - '<term>'   tokens=<N>  chars=<N>  compression=<float>
  ...
```

**Side effects**: Writes `artifacts/tokenizer_reports/v0.json` (or the
overridden path).

**Error behavior**: No hard errors; uses `WhitespaceFallbackTokenizer` when no
HF tokenizer is available.

**Tests**: `tests/test_tokenizer_analysis.py`.

**Documentation status**: Module docstring in `src/cli/tokenizer_cmd.py`.

---

### `kde-lab dataset`

**Purpose**: Generate an SFT JSONL dataset by running the QA template engine
over a persisted graph.

**Input**:

| Option | Default | Description |
|---|---|---|
| `--repo` | `mini_kde_repo` | Reads `artifacts/graphs/<repo>.json` |
| `--n` | None | Optional cap on output records |
| `--out` | None | Override JSONL output path |

**Output** (stdout):
```
records written      : <N>
dataset jsonl        : <path>
```

**Side effects**: Writes `artifacts/datasets/<repo>_sft_v0.jsonl`.

**Error behavior**: `ClickException` if graph JSON does not exist (message:
"run `kde-lab ingest` or `kde-lab graph` first").

**Tests**: `tests/test_dataset_jsonl_schema.py`.

**Documentation status**: Module docstring in `src/cli/dataset_cmd.py`.

---

### `kde-lab eval`

**Purpose**: Grade RAG-baseline answers against the hand-authored eval set and
write JSON + Markdown reports.

**Input**:

| Option | Default | Description |
|---|---|---|
| `--model-id` | `rag-baseline` | Only `rag-baseline` is wired in v0 |
| `--repo` | `mini_kde_repo` | Reads `artifacts/graphs/<repo>.json` |

**Output** (stdout):
```
model                : <id>
items                : <N>
pass rate            : <pct>  (<n> / <total>)
mean recall          : <pct>
json report          : <path>
markdown report      : <path>
```

**Side effects**: Writes `artifacts/eval_reports/<repo>_answers.jsonl`,
`<repo>_eval.json`, `<repo>_eval.md`.

**Error behavior**: `ClickException` if `model_id != "rag-baseline"`, or if
graph JSON does not exist.

**Tests**: `tests/test_eval_smoke.py`.

**Documentation status**: Module docstring in `src/cli/eval_cmd.py`.

---

### `kde-lab train`

**Purpose**: Dry-run only. Resolve the training recipe from `configs/training.yaml`
and `configs/models.yaml`, print it as JSON, and exit. Does not launch training.

**Input**:

| Option | Default | Description |
|---|---|---|
| `--profile` | from config | Override `profile:` key (e.g. `colab_t4`, `local_24gb`) |
| `--model-key` | from config | Override `model_key:` (must be a key in `models.yaml`) |

**Output**: JSON dump of the resolved recipe to stdout.

**Side effects**: None (logs one INFO line).

**Error behavior**: None beyond YAML parse errors; always exits 0 in v0.

**Tests**: No dedicated test (train cmd is a stub).

**Documentation status**: Module docstring in `src/cli/train_cmd.py` explains
why a placeholder.

---

## `src.ontology.schema`

### `ENTITY_TYPES` / `RELATION_TYPES`

**Type**: `frozenset[str]`

**Purpose**: Single source of truth for all valid entity and relation type
strings. Every `Entity` and `Relation` constructor validates against these sets.

**ENTITY_TYPES** (30 members):
`Repository`, `Module`, `BuildTarget`, `SourceFile`, `HeaderFile`, `CppClass`,
`Function`, `Method`, `Signal`, `Slot`, `QmlFile`, `QmlComponent`, `Property`,
`DbusService`, `DbusInterface`, `DbusMethod`, `DbusSignal`, `ConfigFile`,
`ConfigGroup`, `ConfigKey`, `Plugin`, `DesktopFile`, `Service`, `LogCategory`,
`LogEvent`, `TestCase`, `BugReport`, `Commit`, `Symptom`, `RootCause`, `Fix`,
`EvaluationQuestion`, `DatasetExample`.

**RELATION_TYPES** (25 members):
`CONTAINS`, `BUILDS`, `DEFINES`, `DECLARES`, `CALLS`, `EMITS`, `CONNECTS_TO`,
`HANDLES`, `IMPLEMENTS`, `EXPOSES_DBUS`, `CALLS_DBUS`, `READS_CONFIG`,
`WRITES_CONFIG`, `LOADS_PLUGIN`, `REGISTERS_SERVICE`, `LOGS_TO`, `TESTED_BY`,
`CHANGED_BY`, `FIXES`, `CAUSES`, `OBSERVED_IN`, `RELATED_TO`, `ANSWERED_BY`,
`SUPPORTED_BY_EVIDENCE`.

---

### `Entity`

**Purpose**: A typed node in the knowledge graph.

```python
@dataclass
class Entity:
    id: str               # globally unique; use src.common.ids.make_id()
    type: str             # must be in ENTITY_TYPES
    name: str             # short display name
    qualified_name: str   # defaults to name if omitted
    properties: dict[str, str]  # free key-value metadata
    source_path: str      # file path string (not a Path object)
    source_line: int      # 0 if unknown
```

**Error behavior**: `__post_init__` raises `ValueError` for unknown `type`.
Sets `qualified_name = name` if `qualified_name` is empty.

**Tests**: `tests/test_ontology_schema.py`.

---

### `Relation`

**Purpose**: A typed directed edge between two `Entity` ids.

```python
@dataclass
class Relation:
    src: str              # source entity id
    rel: str              # must be in RELATION_TYPES
    dst: str              # destination entity id
    properties: dict[str, str]  # free key-value metadata
```

**Error behavior**: `__post_init__` raises `ValueError` for unknown `rel`.

**Tests**: `tests/test_ontology_schema.py`.

---

## `src.graph.builder`

### `build_graph(bundle: ExtractionBundle) -> nx.MultiDiGraph`

**Purpose**: Convert an `ExtractionBundle` into a NetworkX `MultiDiGraph`.

**Input**: `ExtractionBundle` with `.entities` (dict) and `.relations` (list).

**Output**: `nx.MultiDiGraph` where:
- Node attributes: `type`, `name`, `qualified_name`, `source_path`,
  `source_line`, plus `prop_<key>` for each item in `entity.properties`.
- Edge key: the relation type string (e.g. `"EMITS"`).
- Edge attributes: `rel` (the relation type), plus `prop_<key>` for each item
  in `relation.properties`.

**Side effects**: None.

**Error behavior**: Edges whose `src` or `dst` id is not in the node set are
silently dropped.

**Tests**: `tests/test_graph_build.py`.

---

### `save_json(g: nx.MultiDiGraph, path: Path) -> Path`

**Purpose**: Serialise the graph to a JSON file.

**Output format**:
```json
{
  "nodes": [{"id": "...", "type": "...", "name": "...", ...}],
  "edges": [{"src": "...", "dst": "...", "rel": "...", ...}]
}
```

**Side effects**: Creates parent directories; writes/overwrites the file.

**Returns**: The `path` argument (for chaining/logging).

---

### `save_graphml(g: nx.MultiDiGraph, path: Path) -> Path`

**Purpose**: Serialise the graph to GraphML format via `networkx.write_graphml`.

**Side effects**: Creates parent directories; writes/overwrites the file.

**Returns**: The `path` argument.

---

## `src.graph.queries`

All functions are pure: no side effects, graph is never mutated.

### `nodes_of_type(g, type_: str) -> list[str]`

Return all node ids whose `type` attribute equals `type_`.

---

### `out_edges_by_rel(g, node: str, rel: str) -> list[tuple[str, str]]`

Return `(node, dst)` pairs for all outgoing edges from `node` with edge key
`rel`.

---

### `neighbors_by_rel(g, node: str, rel: str) -> list[str]`

Return the destination node ids of all outgoing edges from `node` with edge
key `rel`.

---

### `signals_emitted_by(g, class_node: str) -> list[str]`

Return Signal node ids that `class_node` reaches via `EMITS` edges.

---

### `config_keys_read_by(g, class_node: str) -> list[str]`

Return ConfigKey node ids reachable from `class_node` via `READS_CONFIG`.

---

### `log_categories_of(g, class_node: str) -> list[str]`

Return LogCategory node ids reachable from `class_node` via `LOGS_TO`.

---

### `dbus_methods_of(g, iface_node: str) -> list[str]`

Return DbusMethod node ids (only nodes whose `type == "DbusMethod"`) reachable
from `iface_node` via `EXPOSES_DBUS`.

---

### `qml_backend_for(g, qml_component_node: str) -> list[str]`

Return CppClass node ids reachable from `qml_component_node` via `CONNECTS_TO`.
The filter `type == "CppClass"` is applied.

---

### `find_by_name(g, name: str, types: Iterable[str] | None = None) -> list[str]`

Case-insensitive substring search over `name` and `qualified_name` node
attributes. If `types` is given, only nodes of those types are returned.

**Tests**: `tests/test_graph_build.py`.

---

## `src.rag.graph_retriever`

### `retrieve(g: nx.MultiDiGraph, query: str, k: int = 5) -> Retrieval`

**Purpose**: Produce ranked evidence for a natural-language query by routing
through `src.traceability.symptom_to_code.trace`.

**Input**:
- `g`: a built knowledge graph.
- `query`: natural-language question or symptom description.
- `k`: maximum number of evidence items to return.

**Output**: `Retrieval(query=str, items=list[EvidenceItem])` where each
`EvidenceItem` has fields:
- `entity_id: str`
- `type: str`
- `name: str`
- `source_path: str`
- `source_line: int`
- `confidence: float` — 0.8 for direct name-match seeds; decays 0.15 per hop
- `reason: str` — human-readable explanation
- `relation: str` — edge type that connected this item, or `""` for seeds

**Side effects**: None.

**Error behavior**: Returns `Retrieval` with `items=[]` if no seed terms match
the graph. Does not raise.

**Tests**: `tests/test_rag_answer_with_evidence.py`, `tests/test_traceability.py`.

**Documentation status**: Module docstring in `src/rag/graph_retriever.py`.

---

## `src.rag.answer_with_evidence`

### `answer(g: nx.MultiDiGraph, query: str, k: int = 5) -> Answer`

**Purpose**: Generate a deterministic markdown answer to `query`, citing
evidence from the graph. No LLM is invoked. This is the v0 baseline the
fine-tuned model is expected to beat on the eval suite.

**Input**:
- `g`: a built knowledge graph.
- `query`: natural-language question.
- `k`: number of evidence items passed to the retriever.

**Output**: `Answer(query=str, text=str, evidence_refs=list[dict])` where each
evidence ref is:
```python
{
    "file": str,
    "line": int,
    "symbol": str,
    "relation": str,   # edge type or "seed"
    "confidence": float,
}
```

The `text` field is a markdown string organised as:
```
Answer to: <query>
Likely components: <names>
Logs to watch: `<cats>`
Config keys involved: `<keys>`
D-Bus methods of interest: <methods>

Evidence:
[1] <type> `<name>` — <file>:<line> (rel=<rel>, conf=<float>)
...
```

If retrieval is empty, `text` is a polite refusal message and `evidence_refs`
is `[]`.

**Side effects**: None.

**Error behavior**: Does not raise; returns a refusal `Answer` on empty
retrieval.

**Tests**: `tests/test_rag_answer_with_evidence.py`.

**Documentation status**: Module docstring explains the v0 vs fine-tune
distinction.

---

## `src.eval.answer_grader`

### `grade(answer_text: str, item: dict) -> GradeResult`

**Purpose**: Programmatic substring-recall grader. No LLM. Checks whether all
required substrings appear in the answer and no forbidden substrings appear.

**Input**:
- `answer_text`: the full answer string to check.
- `item`: an eval set record with optional keys:
  - `"id"` (str): identifier for the result.
  - `"category"` (str): task category label.
  - `"must_mention"` (list[str]): all must appear (case-insensitive) for pass.
  - `"must_not_mention"` (list[str]): any appearance causes fail.

**Output**: `GradeResult`:

```python
@dataclass
class GradeResult:
    item_id: str
    category: str
    mention_recall: float   # hits / len(must_mention); 1.0 if must_mention is empty
    forbidden_hit: bool     # True if any must_not_mention substring is present
    passed: bool            # mention_recall == 1.0 and not forbidden_hit
```

**Side effects**: None.

**Error behavior**: Does not raise. If `must_mention` is missing or empty,
`mention_recall` is 1.0.

**Tests**: `tests/test_eval_smoke.py`.

**Documentation status**: Module docstring in `src/eval/answer_grader.py`.

---

## `src.training.train_router`

### `route(query: str) -> str`

**Purpose**: Map a query string to one of seven adapter names using ordered
regex rules. Deterministic: first matching rule wins.

**Input**: `query` — any string; empty/whitespace returns `"architecture"`.

**Output**: One of:
```
"patch_review" | "debugging" | "qml_cpp" | "dbus_config" |
"tool_use" | "code_navigation" | "architecture"
```

Rule priority (highest first):
1. `patch_review` — diff/patch/review/regression keywords
2. `debugging` — crash/freeze/hang/leak/slow/why keywords
3. `qml_cpp` — qml/Q_PROPERTY/qmlRegisterType keywords
4. `dbus_config` — dbus/kconfig/desktop/configkey keywords
5. `tool_use` — journalctl/ctest/gdb/strace keywords
6. `code_navigation` — "where is", "which class", emit/defines keywords
7. `architecture` — design/component/overview/how keywords (also the fallback)

**Side effects**: None.

**Error behavior**: Never raises. Falls through to `"architecture"` if no rule
matches.

**Tests**: `tests/test_train_router.py`.

---

### `explain(query: str) -> dict`

**Purpose**: Diagnostic helper that returns which rule fired and which token
matched.

**Output**:
```python
{
    "adapter": str,
    "matched": str | None,   # the matched regex group, or None for fallback
    "rule_index": int,       # index in _RULES, or -1 for fallback
}
```

**Side effects**: None.

**Tests**: `tests/test_train_router.py`.

---

## Configuration YAML schema

### `configs/repos.yaml`

**Top-level key**: `repos` — list of repo entries.

Each entry:

```yaml
- name: <str>              # short id; used by --repo flag
  path: <str>              # absolute or relative to REPO_ROOT
  enabled: <bool>          # must be true for kde-lab ingest to proceed
  include_globs:           # list of glob patterns passed to the scanner
    - "**/*.cpp"
    ...
  exclude_globs:           # patterns always skipped
    - "**/.git/**"
    ...
  license: <str>           # informational; e.g. "synthetic" or "LGPL-2.1-or-later"
```

Only `mini_kde_repo` is `enabled: true` by default.

---

### `configs/models.yaml`

**Top-level key**: `models` — mapping of model keys to model entries.

Each entry:

```yaml
<model_key>:
  base_model: <str>           # HuggingFace model id or absolute local path
  family: <str>               # qwen | smol | llama | gemma | phi | custom
  train_method: <str>         # lora | full
  max_seq_length: <int>       # context window for truncation
  tokenizer_extend: <bool>    # whether to extend the tokenizer vocab
  availability_check: <bool>  # whether to verify weights before training
  notes: <str>                # free-text guidance for the learner
```

All `base_model` values use `CHANGE_ME` placeholders in the shipped config.

---

### `configs/training.yaml`

**Top-level structure** (defaults; profiles override via deep-merge):

```yaml
profile: <str>             # key in profiles: map; CLI --profile overrides
model_key: <str>           # key in configs/models.yaml; CLI --model-key overrides
dataset_path: <str>        # path to SFT JSONL
output_dir: <str>          # adapter checkpoint output directory
max_seq_length: <int>
load_in_4bit: <bool>

lora:
  r: <int>                 # LoRA rank; typical: 8/16/32/64
  alpha: <int>             # scaling = alpha / r; keep ~2*r
  dropout: <float>
  target_modules: <str>    # "all-linear" or comma-separated module names

optim:
  learning_rate: <float>
  batch_size: <int>        # per-device
  gradient_accumulation_steps: <int>
  num_train_epochs: <int>
  warmup_steps: <int>
  weight_decay: <float>
  lr_scheduler_type: <str>
  logging_steps: <int>
  eval_steps: <int>
  save_steps: <int>
  seed: <int>

packing: <bool>
train_on_responses_only: <bool>
adapter_name: <str>

profiles:
  <profile_name>:           # partial override; deep-merged over top-level
    ...
```

Shipped profiles: `colab_t4`, `local_8gb` (empty / uses defaults),
`local_16gb`, `local_24gb`, `local_48gb`.

---

### `configs/tokenizer.yaml`

Consumed by `kde-lab tokenizer`. Relevant key:

```yaml
analyze:
  report_path: <str>   # optional; relative to REPO_ROOT
```

---

### `configs/dataset.yaml`

Consumed by `kde-lab info` (summary) and future dataset generation.

```yaml
generators:
  <generator_name>: <bool>   # true to enable
```

---

### `configs/eval.yaml`

Consumed by `kde-lab info` (summary) and `kde-lab eval`.

```yaml
benchmarks:
  - <benchmark_name>
```

---

### `configs/ontology.yaml`

Informational in v0. Not yet consumed by any runtime code.

---

## `src.common.config.load_yaml`

### `load_yaml(path: Path, default: dict | None = None) -> dict`

**Purpose**: Load a YAML mapping from `path`. Returns `default` (or `{}`) when
the file is absent. Raises `ValueError` if the file exists but its top-level is
not a mapping.

**Side effects**: None beyond file reads.

---

## `src.common.paths`

**Purpose**: Single source of truth for all canonical filesystem paths.

| Name | Value |
|---|---|
| `REPO_ROOT` | Directory containing `pyproject.toml` |
| `MINI_REPO` | `REPO_ROOT/examples/mini_kde_repo` |
| `ARTIFACTS` | `REPO_ROOT/artifacts` |
| `DATASETS` | `REPO_ROOT/datasets` |
| `CONFIGS` | `REPO_ROOT/configs` |
| `GRAPHS_DIR` | `ARTIFACTS/graphs` |
| `ONTOLOGY_DIR` | `ARTIFACTS/ontology` |
| `TOKENIZER_DIR` | `ARTIFACTS/tokenizer_reports` |
| `DATASETS_OUT_DIR` | `ARTIFACTS/datasets` |
| `EVAL_DIR` | `ARTIFACTS/eval_reports` |
| `LOGS_DIR` | `ARTIFACTS/logs` |
| `PLOTS_DIR` | `ARTIFACTS/plots` |

### `ensure_dirs() -> None`

Create all artifact subdirectories if they do not exist. Idempotent.

---

## `src.observability.metrics`

### Counter / Gauge / Histogram

```python
from src.observability.metrics import counter, gauge, histogram, time_block

c = counter("my_metric", labels={"component": "scanner"})
c.inc(1.0)

g = gauge("graph_node_count", labels={"repo": "mini_kde_repo"})
g.set(142.0)

h = histogram("ingest_duration_seconds")
h.observe(0.031)

with time_block("rag_latency", labels={"task_type": "debugging"}) as h:
    ...  # h.observe(elapsed) called automatically on exit
```

Allowed label keys: `repo`, `component`, `task_type`, `split`,
`model_family`, `adapter_name`.

Forbidden label keys (raise `ValueError`): `file_path`, `symbol_id`,
`trace_id`, `question_id`, `dataset_example_id`.

All observations are always written to
`artifacts/metrics/run-<trace_id>.jsonl`. Prometheus mirroring is optional
and silent when `prometheus-client` is not installed.

**Tests**: `tests/test_observability.py`.

---

## `src.observability.traces`

### `span(name: str, labels: dict[str, str] | None = None)`

Context manager. Opens a named span; appends a JSONL record to
`artifacts/logs/traces-<trace_id>.jsonl` on exit. Yields the `Span` object.

```python
from src.observability.traces import span

with span("graph.build", labels={"repo": "mini_kde_repo"}) as s:
    g = build_graph(bundle)
    # s.trace_id, s.span_id, s.parent_id available here
```

Span record schema:
```json
{
  "trace_id": "...",
  "span_id": "...",
  "parent_id": "...",
  "name": "...",
  "start_ns": 1234567890000,
  "end_ns":   1234567891000,
  "labels": {}
}
```

OTLP emission is automatic if `opentelemetry` is installed.

**Tests**: `tests/test_observability.py`.
