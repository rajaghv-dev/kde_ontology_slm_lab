# Repo Inventory

_Generated: 2026-05-16. Source of truth: git log + file system._

---

## Repo purpose

`kde_ontology_slm_lab` is a hands-on learning lab that turns KDE desktop repositories
into a structured knowledge graph (ontology + NetworkX graph), then uses that graph
to build tokenizers, SFT datasets, RAG pipelines, and eventually small-language-model
adapters (LoRA) capable of answering KDE architecture and debugging questions.

The OCT framework (Observability, Controllability, Traceability) is the organising
principle: every module must advance at least one of the three.

Baseline measured on mini repo (v0.0.1, 2026-05-13):
- 64 tests passing
- 12 files ingested
- ~30 entities / ~40 relations extracted
- RAG eval pass rate: 66.67% (4/6)

---

## Languages and frameworks detected

| Language / tech   | Role                                           |
|-------------------|------------------------------------------------|
| Python 3.10+      | All application code                           |
| C++ (synthetic)   | `examples/mini_kde_repo/` fixture only         |
| QML (synthetic)   | `examples/mini_kde_repo/` fixture only         |
| CMake (synthetic) | `examples/mini_kde_repo/` fixture only         |
| YAML              | All configs under `configs/`                   |
| JSONL             | Dataset / eval / artifact serialisation        |
| Markdown          | All documentation                              |
| Bash              | Helper scripts under `scripts/`                |
| Dockerfile        | Observability stack only (`observability/`)    |

Core Python libs: `networkx`, `numpy`, `pyyaml`, `click`, `tqdm`, `rich`.

Optional extras (declared in `pyproject.toml`):
- `[tokenizer]` — `tokenizers`, `transformers`
- `[train]` — `torch`, `peft`, `trl`, `accelerate`, `datasets`, `bitsandbytes`
- `[rdf]` — `rdflib`
- `[viz]` — `matplotlib`, `graphviz`
- `[obs]` — `prometheus-client`
- `[dev]` — `pytest`, `ruff`

---

## Main entry points

| Entry point                            | How to invoke                          |
|----------------------------------------|----------------------------------------|
| `kde-lab` CLI                          | `kde-lab --help` (after `pip install -e .`) |
| `kde-lab info`                         | Prints paths, config keys, enabled repos |
| `kde-lab pipeline`                     | Delegates to `examples/run_mini_repo_pipeline.py` |
| `examples/run_mini_repo_pipeline.py`   | `python examples/run_mini_repo_pipeline.py` |
| `examples/run_rag_answer_demo.py`      | RAG answer standalone demo              |
| `examples/run_dataset_generation.py`   | Dataset generation standalone           |
| `examples/run_reasoning_eval.py`       | Eval standalone                         |
| `examples/run_tokenizer_analysis.py`   | Tokenizer analysis standalone           |
| `examples/run_training_dry_run.py`     | Training dry-run (no GPU needed)        |
| `examples/run_real_kde_repo_ingest.py` | Real KDE repo ingest (requires clone)   |

CLI subcommands registered in `src/cli/main.py`:
`ingest`, `graph`, `tokenizer`, `dataset`, `train`, `eval`

---

## Build system

| Tool         | File              | Purpose                                   |
|--------------|-------------------|-------------------------------------------|
| setuptools   | `pyproject.toml`  | Package build, entry-scripts, extras      |
| Make         | `Makefile`        | `install`, `vertical-slice`, `test`, `clean` |
| Bash scripts | `scripts/`        | Dev setup, training launchers, export     |

Package name: `kde-ontology-slm-lab` (v0.0.1)
Console script: `kde-lab` → `src.cli.main:main`

---

## Runtime dependencies

Minimum (vertical slice, no GPU):
```
networkx>=3.0  numpy>=1.26  pyyaml>=6.0  click>=8.1  tqdm>=4.66  rich>=13.0
```
(`requirements.txt` mirrors these; `numpy` is declared in `pyproject.toml` but absent
from `requirements.txt` — minor gap.)

---

## Test framework

| Item               | Detail                              |
|--------------------|-------------------------------------|
| Framework          | pytest 8+                           |
| Test directory     | `tests/`                            |
| Run command        | `pytest -q` or `make test`          |
| Current result     | **64 passed, 0 failed, 8 warnings** |
| Warning cause      | `prometheus_client` not installed (expected for dev) |
| Coverage tooling   | Not configured                      |

Test files (14 modules):
`test_context_builder`, `test_dataset_jsonl_schema`, `test_eval_smoke`,
`test_graph_build`, `test_hybrid_search`, `test_imports`, `test_mini_repo_ingest`,
`test_observability`, `test_ontology_schema`, `test_rag_answer_with_evidence`,
`test_tokenizer_analysis`, `test_traceability`, `test_train_router`,
`test_vector_store`

---

## CI/CD workflows

**None.** The `.github/` directory does not exist.
No GitHub Actions workflows, issue templates, PR templates, or dependabot config.

---

## Documentation files

Under `docs/` (15 files, ~3 000 lines total):

| File                                      | Topic                                  |
|-------------------------------------------|----------------------------------------|
| `00_big_picture.md`                       | Lab overview, OCT framework            |
| `01_kde_architecture_map.md`              | KDE system layers                      |
| `02_repo_understanding_pipeline.md`       | Ingest pipeline design                 |
| `03_kde_ontology_design.md`               | Ontology schema rationale              |
| `04_graph_schema.md`                      | Graph node/edge schema                 |
| `05_tokenizer_strategy.md`                | Tokenizer analysis strategy            |
| `06_dataset_generation_strategy.md`       | SFT dataset generation                 |
| `07_training_recipes.md`                  | LoRA, Unsloth, PEFT, GRPO recipes      |
| `08_debug_reasoning_eval.md`              | Evaluation design                      |
| `09_colab_guide.md`                       | Google Colab usage                     |
| `10_local_training_guide.md`              | Local GPU training                     |
| `11_failure_modes.md`                     | Known failure modes                    |
| `12_privacy_and_license_notes.md`         | Privacy + license policy               |
| `13_observability_with_grafana_prometheus.md` | Observability stack                |
| `14_paper_outline.md`                     | Research paper outline                 |
| `progress_log.md`                         | Dated development milestones           |

Also: `README.md`, `CHANGELOG.md`, `TODO.md`, `observability/README.md`,
`examples/mini_kde_repo/README.md`.

---

## Public APIs / CLIs / services

| Surface                 | Type        | Status       |
|-------------------------|-------------|--------------|
| `kde-lab` CLI           | CLI         | Working      |
| `src.common.*`          | Python API  | Stable       |
| `src.ontology.*`        | Python API  | Stable       |
| `src.graph.*`           | Python API  | Stable       |
| `src.repo_ingest.*`     | Python API  | Stable       |
| `src.dataset.*`         | Python API  | Stable       |
| `src.rag.answer_with_evidence` | Python API | Working (no LLM) |
| `src.rag.graph_retriever`      | Python API | Working      |
| `src.rag.embeddings`           | Python API | Working (offline fallback) |
| `src.rag.vector_store`         | Python API | Working      |
| `src.rag.hybrid_search`        | Python API | Working      |
| `src.eval.*`            | Python API  | Working      |
| `src.tokenizer.*`       | Python API  | Working      |
| `src.traceability.*`    | Python API  | Working      |
| `src.training.*`        | Python API  | **Scaffold** (no weights) |
| `src.observability.*`   | Python API  | Working (JSONL fallback) |
| Prometheus endpoint     | HTTP        | Scaffolded (opt-in, `[obs]`) |
| Grafana + Loki + Tempo  | Docker      | Scaffolded (`observability/docker-compose.yml`) |

---

## Configuration files

| File                        | Purpose                                    |
|-----------------------------|--------------------------------------------|
| `configs/repos.yaml`        | KDE repo declarations + enabled flags      |
| `configs/models.yaml`       | Seven base model declarations              |
| `configs/tokenizer.yaml`    | Tokenizer analysis settings                |
| `configs/ontology.yaml`     | Ontology extractor settings                |
| `configs/dataset.yaml`      | Dataset generator flags                    |
| `configs/training.yaml`     | Training hyperparameters                   |
| `configs/eval.yaml`         | Eval benchmark declarations                |
| `pyproject.toml`            | Package + tool config                      |
| `observability/prometheus/prometheus.yml` | Prometheus scrape config    |
| `observability/loki/loki-config.yml`      | Loki config                  |
| `observability/tempo/tempo.yml`           | Tempo config                 |

---

## Examples and demos

| Script                                 | Status   | Requires            |
|----------------------------------------|----------|---------------------|
| `examples/run_mini_repo_pipeline.py`   | Working  | base deps           |
| `examples/run_rag_answer_demo.py`      | Working  | base deps           |
| `examples/run_dataset_generation.py`   | Working  | base deps           |
| `examples/run_reasoning_eval.py`       | Working  | base deps           |
| `examples/run_tokenizer_analysis.py`   | Working  | base deps           |
| `examples/run_training_dry_run.py`     | Working  | base deps           |
| `examples/run_real_kde_repo_ingest.py` | Working* | real KDE clone      |
| Notebooks (`notebooks/`)               | Scaffolded | various extras    |

10 Jupyter notebooks exist but are not validated (scaffolded in v0).

---

## Deployment artifacts

Output paths (auto-created by `src.common.paths.ensure_dirs()`):

| Path                           | Content                                |
|--------------------------------|----------------------------------------|
| `artifacts/graphs/`            | JSON + GraphML graph exports           |
| `artifacts/ontology/`          | Entity JSONL dumps                     |
| `artifacts/tokenizer_reports/` | Token cost JSON reports                |
| `artifacts/datasets/`          | SFT JSONL examples                     |
| `artifacts/eval_reports/`      | Eval JSON + Markdown reports           |
| `artifacts/logs/`              | Pipeline JSONL logs                    |
| `artifacts/metrics/`           | Observability metrics JSONL            |
| `artifacts/plots/`             | Matplotlib plots (when viz extras installed) |

All artifact dirs are git-ignored (`.gitkeep` placeholders keep the dirs).

---

## Observability / logging / metrics / tracing

| Mechanism               | Implementation                                      |
|-------------------------|-----------------------------------------------------|
| Structured logging      | `src/observability/logger.py` (JSONL to `artifacts/logs/`) |
| Metrics                 | `src/observability/metrics.py` (JSONL + optional Prometheus) |
| Traces                  | `src/observability/traces.py` (JSONL spans)         |
| Reports                 | `src/observability/report.py` (roll-up summaries)   |
| Prometheus stack        | `observability/` Docker Compose (opt-in)            |
| Grafana dashboards      | `observability/grafana/` (scaffolded)               |
| Loki log aggregation    | `observability/loki/` (scaffolded)                  |
| Tempo tracing           | `observability/tempo/` (scaffolded)                 |

Fallback: all observability works without `prometheus_client` via JSONL files.

---

## Security-sensitive files

| File / pattern          | Risk                                          |
|-------------------------|-----------------------------------------------|
| `configs/*.yaml`        | Low — no secrets; contain only paths + flags  |
| `.gitignore`            | Covers `models/`, `checkpoints/`, `*.safetensors` |
| `observability/`        | Docker ports exposed; no auth in dev stack    |
| No `.env` / `.env.example` | Repo has no env-var-based secrets mechanism |

No hardcoded secrets detected. No tokens, API keys, or private URLs found.

---

## Known gaps (Phase 0)

| Gap                                    | Severity |
|----------------------------------------|----------|
| No `.github/` directory (no CI/CD)     | High     |
| No `CONTRIBUTING.md`                   | Medium   |
| No `AGENTS.md`                         | Medium   |
| `numpy` missing from `requirements.txt` | Low     |
| No `SECURITY.md`                       | Low      |
| No coverage configuration              | Low      |
| Branch is `master`, GitHub default is `main` | Low |
| No remote configured                   | Info     |
| 10 notebooks scaffolded but not validated | Medium |
| Training modules are stubs (no weights) | Known/documented |

---

## Initial git state

```
Branch  : master
Remote  : (none configured)
Status  : clean (nothing to commit)
Commits : 2 (501879d → 6809daf)
```
