# Tooling Gaps

_Generated: 2026-05-16_

This document records which developer tools are declared, available, or missing for the `kde_ontology_slm_lab` project. It is produced in support of the refactor plan in `docs/refactor-plan.md`.

---

## How to re-check availability

Run the following in an activated venv (`source .venv/bin/activate` after `scripts/setup_dev.sh`):

```bash
python3 -m ruff --version
python3 -m pytest --version
python3 -m mypy --version
pyrefly --version || python3 -m pyrefly --version
```

---

## Tool inventory

| Tool | Expected use | Declared in project? | Evidence of availability | Alternative if absent |
|---|---|---|---|---|
| `ruff` | Linting and import-order enforcement | Yes — `pyproject.toml [dev]` extra; `[tool.ruff]` config present | `pip install -e ".[dev]"` installs it; `python3 -m ruff check src/` runs clean or near-clean | No replacement needed — ruff is the declared linter |
| `pytest` | Test runner (64 tests, all passing) | Yes — `pyproject.toml [dev]` extra; `[tool.pytest.ini_options]` config present | Test suite passes per commit `6809daf`; `python3 -m pytest tests/ -q` is the standard invocation | No replacement needed — pytest is the declared test runner |
| `mypy` | Static type checking | Not declared anywhere in `pyproject.toml` | Not installed by default; no `mypy.ini` or `[tool.mypy]` config | `pyrefly` (Meta's Rust-based checker) as an alternative; or add `mypy` to `[dev]` |
| `pyrefly` | Alternative static type checker (Meta / Rust-based) | Not declared in `pyproject.toml` | Not expected to be installed; no config file present | `mypy>=1.11` is the more widely supported alternative |
| `graphify` | Graph visualisation (e.g. Gephi CLI export) | Not applicable | Not expected — the lab uses `networkx` + GraphML export for graph visualisation; Gephi is a GUI tool | `networkx` + `graphviz` (optional dep declared in `[viz]`) |
| CodeQL | Security / code-quality scanning | Not applicable | Not expected — no `.github/workflows/` directory exists; CodeQL is a GitHub Actions feature | Ruff's `B` (bugbear) rules cover the most common bug classes without CodeQL |
| Memgraph | Graph database backend | Not applicable | Not expected — the lab's graph layer is intentionally `networkx`-only in v0 | The `rdf` optional group (`rdflib>=7.0`) and the stretch goal of Neo4j are the declared upgrade paths |
| `sentence-transformers` | Semantic embedding for `SentenceTransformersEmbedder` | Not declared in `pyproject.toml` | Not expected to be installed in the default venv | `HashingEmbedder` (the offline default, always available); add `sentence-transformers>=2.7` to a new `[rag-semantic]` optional group |
| `prometheus_client` | Prometheus metrics endpoint (opt-in) | Declared in `[obs]` optional group (`prometheus-client>=0.20`) | Not installed by default; lazy-imported with a graceful fallback to JSONL | JSONL sink (`artifacts/metrics/run-*.jsonl`) — fully functional without this |
| `opentelemetry` | OTLP trace export to Grafana Tempo | Not declared in `pyproject.toml` | Not installed; lazy-imported in `src/observability/traces.py` with a no-op fallback | JSONL trace sink (`artifacts/logs/traces-*.jsonl`) — fully functional without this |
| `docker` / `docker compose` | Bring up the observability stack | Not a Python dep; system tool | Not checked — requires Docker Desktop or Docker Engine on the host | JSONL sinks for metrics, logs, and traces work without any Docker stack |
| `llama.cpp` (`llama-quantize`, `convert_hf_to_gguf.py`) | GGUF export via `src/training/export_gguf.py` | Not a Python dep; external binary | Not expected — `export_gguf.py` detects absence and prints manual commands; `--dry-run` is always safe | Print-and-exit pattern already implemented; no alternative needed for the lab |
| `torch` / `bitsandbytes` / `peft` / `trl` | Actual LoRA training | Declared in `[train]` optional group | Not installed in the base venv; all training scripts support `--dry-run` | Dry-run mode is the CI-safe alternative; real training requires a GPU host with `pip install -e ".[train]"` |
| `tokenizers` / `transformers` | HF tokenizer analysis | Declared in `[tokenizer]` optional group | Not installed by default; `src/tokenizer/analyze_tokens.py` uses an offline character-level fallback | `HashingEmbedder` / char-level fallback is always available; no blocking gap |
| `unsloth` | Fast LoRA SFT via Triton kernels | Not declared in `pyproject.toml` | Not expected — `src/training/unsloth_sft.py` lazy-imports it and prints an actionable error if missing | `hf_peft_sft.py` is the declared fallback; both paths support `--dry-run` |
| `rdflib` | RDF/OWL export of the graph | Declared in `[rdf]` optional group | Not installed by default; no code currently uses it (stretch goal) | NetworkX JSON + GraphML export is the v0 production path |
| `matplotlib` / `graphviz` | Graph and metric visualisation | Declared in `[viz]` optional group | Not installed by default; no current code calls them | Console output + JSONL files are the no-viz alternative |

---

## Summary

### What is confirmed available (installed by `pip install -e ".[dev]"`)

- `ruff` — linter; configured in `pyproject.toml`; no suppressions except two documented `noqa`/`type: ignore` cases noted in the refactor plan.
- `pytest` — test runner; 64 tests passing.
- All base dependencies: `networkx`, `numpy`, `pyyaml`, `click`, `tqdm`, `rich`.

### What is missing and blocks developer workflow

1. **`numpy` absent from `requirements.txt`** — the file is a minimal install shortcut and omits numpy, causing import failures for the RAG modules when installed via `pip install -r requirements.txt` instead of `pip install -e .`. Add `numpy>=1.26` to `requirements.txt`. (Tracked as P2 in the refactor plan.)

2. **`mypy` / `pyrefly` not installed** — there is no static type checking in the developer workflow. Two `type: ignore` suppressions in `src/common/logging.py` and `src/rag/embeddings.py` exist because the return types are not correctly annotated. Neither mypy nor pyrefly is declared as a dev dependency. (Tracked as P3 in the refactor plan; fixing the annotations makes adding a type checker straightforward.)

3. **`sentence-transformers` undeclared** — a learner who instantiates `SentenceTransformersEmbedder` will get a `ModuleNotFoundError` with no pip install hint in `pyproject.toml`. (Tracked as P8 in the refactor plan.)

### What is intentionally absent (lab policy)

- `unsloth` — upstream install is platform-specific; the lab ships the recipe, not the dependency.
- `llama.cpp` — external binary; the lab prints equivalent shell commands instead.
- `torch` / GPU stack — only installed on a GPU host; all training scripts are safe in `--dry-run` mode without torch.
- Memgraph / Neo4j — stretch goal; explicitly out of scope for v0.
- CodeQL — would require `.github/workflows/` and GitHub Actions; CI itself does not yet exist.

### What is scaffolded but not wired to code

- `docker compose` stack (`observability/docker-compose.yml`) — files are present and correct; bringing up the stack is opt-in.
- `prometheus_client` and `opentelemetry` — lazy-imported; gracefully degraded to JSONL without them.

---

## Recommended installs for next phase

After `pip install -e ".[dev]"` (which is the current baseline), install these in order of priority:

```bash
# Priority 1: static type checking (enables removing the two type: ignore suppressions)
pip install mypy>=1.11

# Priority 2: semantic RAG (enables SentenceTransformersEmbedder)
# Requires network to download model weights; only install when you intend to use it.
pip install sentence-transformers>=2.7

# Priority 3: observability stack (enables Prometheus endpoint; Docker still required for the full stack)
pip install -e ".[obs]"

# Priority 4: full training stack (requires a GPU; installs torch + peft + trl + bitsandbytes)
pip install -e ".[train]"
```

To run the complete observability stack (Prometheus + Grafana + Loki + Tempo):

```bash
# Requires Docker Engine or Docker Desktop
docker compose -f observability/docker-compose.yml up -d
```

To use Unsloth (faster training on supported GPU families):

```bash
# Platform-specific; follow https://github.com/unslothai/unsloth#installation
pip install unsloth
```
