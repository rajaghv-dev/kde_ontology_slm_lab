# AGENTS.md

## Repo purpose
`kde_ontology_slm_lab` is a hands-on learning lab: KDE desktop repositories ->
ontology + NetworkX knowledge graph -> tokenizer analysis -> SFT datasets ->
RAG pipeline -> small-language-model (LoRA) adapters. OCT framework organises
every module: Observability, Controllability, Traceability. v0.0.1 vertical
slice runs fully offline on `examples/mini_kde_repo/`.

## Safe files to edit
- `src/` — all Python modules (follow coding style below)
- `tests/` — add or update pytest tests
- `configs/*.yaml` — YAML configs (shape is documented inline)
- `examples/` — pipeline scripts and mini repo fixture
- `docs/` — Markdown chapters and progress log
- `notebooks/` — Jupyter notebooks (not yet executed)
- `scripts/` — shell helpers

## Files requiring human approval
- `pyproject.toml` — package metadata, entry points, extras
- `src/cli/main.py` — CLI entry point wiring
- `src/common/paths.py` — canonical path constants (all modules depend on this)
- `src/ontology/schema.py` — entity/relation schema (32 types, 24 relations)
- `observability/docker-compose.yml` — Docker stack
- `CHANGELOG.md`, `TODO.md`, `README.md` — project-level docs

## Build command
```
pip install -e .
```

## Test command
```
python3 -m pytest tests/ -q
```
Expected: 64 passed, 0 failed, ~8 warnings (prometheus_client not installed).

## Lint command
```
python3 -m ruff check src/
```

## Validation command
```
python examples/run_mini_repo_pipeline.py
```
Runs the full vertical slice offline; writes artifacts under `artifacts/`
and prints a Markdown summary. No GPU or network required.

## Coding style
- Python 3.10+, type annotations on all public functions
- `from __future__ import annotations` at top of every module
- Docstrings: module-level required; class and public method docstrings required
- No auto-downloads; any network access must be behind an explicit opt-in flag
- Heavy imports (torch, networkx, transformers) inside function bodies or
  lazy-registered CLI handlers — never at module top level in CLI entry points
- Path resolution only via `src.common.paths`; never `os.path` or raw strings
- Artifact output only to subdirs of `ARTIFACTS`; never to repo root or `src/`

## Refactor rules
- Do not rename public API symbols without updating all callers and tests
- Do not add new required args to existing public functions without a default
- Training modules (`src/training/`) are stubs — add code but do not remove
  the stub structure or docstrings explaining the learning rationale
- RAG advanced modules (`embeddings.py`, `vector_store.py`, `hybrid_search.py`)
  must preserve the offline fallback path

## Security rules
- No credentials, API keys, or tokens anywhere in the repo
- No auto-download of model weights or datasets
- No network calls in any `src/` module without explicit opt-in flag
- `examples/mini_kde_repo/` is synthetic fixture only — do not embed real KDE
  source or real log data

## Known risks
- `src/training/` modules are scaffolded stubs; calling them without GPU/weights
  will raise clear errors but produce no trained artifacts
- `observability/docker-compose.yml` stack is not validated; `docker compose up`
  may fail without further config
- `numpy` is in `pyproject.toml` but absent from `requirements.txt` (minor gap)
- No `.github/` directory; no CI workflows exist

## Current TODOs
- Fill out 10 Jupyter notebooks under `notebooks/`
- Complete all seven `configs/*.yaml` files
- Validate observability Docker stack
- Wire real training logic into `src/training/` stubs
- Implement advanced RAG: vector store, hybrid search, real embeddings
- Wire all CLI subcommands end-to-end

## Next recommended tasks (ordered)
1. Add GitHub Actions workflow: `pytest -q` + `ruff check src/`
2. Complete `configs/repos.yaml` and `configs/models.yaml` with real values
3. Implement `src/training/hf_peft_sft.py` SFT trainer (no GPU in CI)
4. Run and validate the observability Docker stack
5. Execute and validate all 10 notebooks
