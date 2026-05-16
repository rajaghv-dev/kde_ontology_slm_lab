# Refactor Plan

_Branch: `master` — Generated: 2026-05-16_

---

## Goals

1. Eliminate the single confirmed code duplication (`_deep_merge`).
2. Fix the `requirements.txt` omission of `numpy` (a runtime dep of `src/rag/embeddings.py` and `src/rag/vector_store.py`).
3. Silence the two `type: ignore` suppressions with a narrower fix or a correct type annotation.
4. Add test coverage for the CLI subcommands and the training dry-run paths that currently have zero tests.
5. Stand up a minimal `.github/workflows/` CI pipeline (lint + tests, no GPU).
6. Validate the `examples/` entry points and the `scripts/` dev-setup scripts against the current code.

---

## Non-goals

- Rewriting working modules (scanner, ontology extractor, graph builder, RAG pipeline).
- Implementing real training (GPU-gated; deliberate policy).
- Changing the public API of any module in `src/`.
- Adding external services, databases, or network dependencies.
- Production-grade CI (explicitly called out in `TODO.md` as "Will NOT do").

---

## Current problems (evidence-based)

### P1 — Code duplication: `_deep_merge`

`_deep_merge` is implemented identically in two files:

- `src/cli/train_cmd.py` (lines 15-23)
- `src/training/lora_config.py` (lines 26-37, with a comment saying it is kept local to avoid importing the CLI)

The comment in `lora_config.py` is correct that `src.training` should not import the CLI, but the fix is to move the function to `src/common/` rather than duplicate it.

### P2 — `numpy` missing from `requirements.txt`

`requirements.txt` lists only: `networkx`, `pyyaml`, `click`, `tqdm`, `rich`. It omits `numpy`, which is imported unconditionally at module load time in:

- `src/rag/embeddings.py` (top-level `import numpy as np`)
- `src/rag/vector_store.py` (top-level `import numpy as np`)
- `src/rag/hybrid_search.py` (top-level `import numpy as np`)

A fresh install via `pip install -r requirements.txt` (without `pyproject.toml`) would fail when any RAG module is imported. `numpy` is declared correctly in `pyproject.toml` dependencies.

### P3 — `type: ignore` suppressions

Two suppressions in production code suppress real typing gaps:

- `src/common/logging.py:28` — `# type: ignore[assignment]` on `LoggerAdapter` returned where `logging.Logger` is expected. Fix: annotate the return type as `logging.Logger | logging.LoggerAdapter`.
- `src/rag/embeddings.py:103` — `# type: ignore` on `from sentence_transformers import SentenceTransformer`. Fix: wrap in `TYPE_CHECKING` guard since the import only occurs at runtime inside `_ensure_loaded`.

### P4 — `noqa: F401` on intentional side-effect import

`src/training/hf_peft_sft.py:69` uses `import torch  # noqa: F401` to check torch availability as a side-effect. Fix: use `importlib.util.find_spec("torch")` or restructure the try/except so torch is used, not just imported.

### P5 — No tests for CLI subcommands

The six CLI subcommand files (`ingest_cmd.py`, `graph_cmd.py`, `tokenizer_cmd.py`, `dataset_cmd.py`, `train_cmd.py`, `eval_cmd.py`) have zero test coverage. The `kde-lab info` and `kde-lab pipeline` commands in `main.py` are also untested. The Click test runner (`click.testing.CliRunner`) allows testing these entirely offline.

### P6 — No tests for training dry-run paths

`hf_peft_sft.main(["--dry-run"])`, `unsloth_sft.main(["--dry-run"])`, `grpo_optional.main(["--dry-run"])`, `merge_adapter.main(["--dry-run"])`, and `export_gguf.main(["--dry-run"])` are untested. All of these intentionally exit early before any heavy imports, making them testable without GPU or model weights.

### P7 — No CI/CD

There is no `.github/` directory. Tests pass locally (64 tests, all green per commit message), but there is no automated check on push. Without CI, regressions on these dry-run paths and CLI paths will go undetected.

### P8 — `sentence_transformers` undeclared

`src/rag/embeddings.py:SentenceTransformersEmbedder` lazy-imports `sentence_transformers` but that package does not appear in any `pyproject.toml` optional group. A learner who follows the code path will hit an unhelpful `ModuleNotFoundError`. Fix: add `sentence-transformers` to a new `[rag-semantic]` optional group.

---

## Evidence summary

| Problem | File(s) | Evidence |
|---|---|---|
| P1 `_deep_merge` dup | `src/cli/train_cmd.py:15`, `src/training/lora_config.py:26` | Identical implementations; `lora_config.py` explains why but duplicates anyway |
| P2 numpy missing | `requirements.txt` | Omitted from file; all three RAG modules import it unconditionally |
| P3 type: ignore | `src/common/logging.py:28`, `src/rag/embeddings.py:103` | Suppressions mask fixable type mismatches |
| P4 noqa F401 | `src/training/hf_peft_sft.py:69` | Side-effect import pattern; `noqa` is the workaround |
| P5 no CLI tests | `src/cli/*.py` | No `test_cli*.py` file found in `tests/` |
| P6 no training tests | `src/training/hf_peft_sft.py` etc | No `test_hf_peft*.py` or `test_*_dryrun.py` found |
| P7 no CI | repo root | No `.github/` directory |
| P8 sentence-transformers | `src/rag/embeddings.py:103` | Not in any `pyproject.toml` group |

---

## Refactor strategy

Phases are ordered from lowest to highest risk. Each phase is independently mergeable; no phase blocks another.

- **Phase 1** fixes documentation-only alignment (zero code risk).
- **Phase 2** fixes structural issues with small, isolated code changes.
- **Phase 3** adds tests; no production code changes.
- **Phase 4** adds CI; no production code changes.
- **Phase 5** validates examples and scripts.
- **Phase 6** performs final GitHub readiness steps.

---

## Files to change

| Phase | File | Change |
|---|---|---|
| 2 | `src/common/config.py` | Add `deep_merge(base, overlay)` function |
| 2 | `src/training/lora_config.py` | Remove local `_deep_merge`; import from `src.common.config` |
| 2 | `src/cli/train_cmd.py` | Remove local `_deep_merge`; import from `src.common.config` |
| 2 | `requirements.txt` | Add `numpy>=1.26` |
| 2 | `pyproject.toml` | Add `sentence-transformers>=2.7` to a new `[rag-semantic]` optional group |
| 2 | `src/common/logging.py` | Fix `get_logger` return type annotation |
| 2 | `src/rag/embeddings.py` | Replace bare `type: ignore` with `TYPE_CHECKING` guard |
| 2 | `src/training/hf_peft_sft.py` | Replace `import torch  # noqa: F401` with `importlib.util.find_spec` |
| 3 | `tests/test_cli.py` | New: CliRunner-based tests for all 8 subcommands |
| 3 | `tests/test_training_dryrun.py` | New: dry-run tests for hf_peft_sft, unsloth_sft, grpo_optional, merge_adapter, export_gguf |
| 4 | `.github/workflows/ci.yml` | New: lint (ruff) + test (pytest) on push/PR |

---

## Files NOT to touch

- `src/repo_ingest/` — all readers work and are tested indirectly via `test_graph_build.py`
- `src/ontology/` — schema and extractor are stable; tested via graph build
- `src/graph/` — builder and queries are stable; tested via `test_graph_build.py` and `test_traceability.py`
- `src/traceability/` — tested via `test_traceability.py`
- `src/tokenizer/` — tested via pipeline
- `src/dataset/` — tested via pipeline
- `src/eval/` — tested via pipeline; grader and eval set builder are simple and correct
- `src/rag/graph_retriever.py` — delegate to traceability; correct
- `src/rag/answer_with_evidence.py` — correct; tested via pipeline
- `src/rag/context_builder.py` — has tests (`test_context_builder.py`)
- `src/rag/vector_store.py` — has tests (`test_vector_store.py`)
- `src/rag/hybrid_search.py` — has tests (`test_hybrid_search.py`)
- `src/rag/embeddings.py` — struct is correct; only the `type: ignore` needs fixing
- `src/training/lora_config.py` — logic is correct; only the `_deep_merge` dup and one import fix needed
- `src/training/train_router.py` — has full tests (`test_train_router.py`)
- `src/observability/` — has full tests (`test_observability.py`)
- `observability/docker-compose.yml` and surrounding stack files — scaffolded correctly; do not touch
- `configs/` — deliberately CHANGE_ME; do not touch model ids
- `examples/` — leave scripts in place; Phase 5 just runs them as smoke tests
- `notebooks/` — out of scope for this refactor

---

## Backward compatibility concerns

- Moving `_deep_merge` to `src/common/config.py`: no backward compat issue — it is a private function (prefixed `_`) in both current locations and not importable by external code.
- Adding `numpy` to `requirements.txt`: additive; no breakage.
- Adding `[rag-semantic]` optional group: additive; no breakage.
- Fixing `get_logger` return type: the actual runtime behavior is unchanged; only the annotation changes.
- Replacing `type: ignore` with a proper guard: runtime behavior identical; the import still happens lazily.
- CI: additive; no code changes.

---

## Test strategy

- All new tests use only the packages already declared in `[dev]` extras (`pytest`) plus the base dependencies.
- CLI tests use `click.testing.CliRunner` — no subprocess, no filesystem side effects beyond `tmp_path`.
- Training dry-run tests call `main(["--dry-run"])` and assert return code `0` and that the config JSON appears on stdout.
- No GPU, no model weights, no network required for any new test.
- Existing 64 tests must remain green throughout; each phase is validated before proceeding to the next.

---

## Rollback plan

Each phase corresponds to one or two commits. Rolling back to before any phase is a `git revert` of those commits. Because no phase changes the public API or the data formats, a rollback does not require migrating artifacts.

---

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `deep_merge` move breaks an import path | Low — it's private and only used in two files | Update both import sites in the same commit; run full test suite before merging |
| `requirements.txt` numpy pin conflicts with a learner's environment | Very low — `>=1.26` is a loose lower bound | Pin is consistent with `pyproject.toml` |
| CI fails due to platform difference (WSL2 vs. GitHub runner) | Low — tests are pure-Python, no OS-specific code | Use `ubuntu-latest` runner; the lab already targets Linux for `bitsandbytes` anyway |
| New CLI tests hit filesystem side effects | Medium — `ingest` and `graph` write artifacts | Use `tmp_path` monkeypatching for all artifact dirs, same pattern as `test_observability.py` |

---

## Phase plan

### Phase 1 — Documentation alignment (safe, no code changes)

**What:** Align `README.md`, `TODO.md`, and `docs/00_big_picture.md` with the current code state. No code is changed.

**Specific tasks:**

- `README.md` Status section: change "Most advanced features are scaffolded" to note that advanced RAG (`embeddings.py`, `vector_store.py`, `hybrid_search.py`, `context_builder.py`) is fully implemented and tested, not merely scaffolded.
- `TODO.md` v0.1 section: tick `Advanced RAG: src/rag/embeddings.py, vector_store.py, hybrid_search.py` (already done and tested in commit `6809daf`).
- `TODO.md` v0.1 section: clarify that `src/cli/` subcommands are wired but lack tests.
- `docs/00_big_picture.md` or a new `docs/progress.md`: note the current test count (64) and which modules have coverage vs. which do not.

**Files:**
- `README.md`
- `TODO.md`

**Risk:** Zero — documentation only.

---

### Phase 2 — Safe structural cleanup

**What:** Fix the five code-level problems that can be addressed with small, isolated changes.

**Specific tasks and files:**

1. **`src/common/config.py`** — Add a `deep_merge(base: dict, overlay: dict) -> dict` public function (copy the existing implementation, remove the underscore prefix so it is importable).

2. **`src/training/lora_config.py`** — Remove `_deep_merge` (lines 26-37). Replace with `from src.common.config import deep_merge`. Update the call site on line 36 accordingly.

3. **`src/cli/train_cmd.py`** — Remove `_deep_merge` (lines 15-23). Replace with `from src.common.config import deep_merge`. Update the two call sites.

4. **`requirements.txt`** — Add line `numpy>=1.26` after `networkx>=3.0`.

5. **`pyproject.toml`** — Add new optional group:
   ```toml
   [project.optional-dependencies]
   rag-semantic = [
       "sentence-transformers>=2.7",
   ]
   ```

6. **`src/common/logging.py`** — Change `get_logger` return type from `logging.Logger` to `logging.Logger | logging.LoggerAdapter`. Remove the `# type: ignore[assignment]` on line 28.

7. **`src/rag/embeddings.py`** — Wrap the `sentence_transformers` import inside `_ensure_loaded` with a `TYPE_CHECKING` guard import for the type annotation:
   ```python
   from __future__ import annotations
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from sentence_transformers import SentenceTransformer
   ```
   Remove the bare `# type: ignore` on line 103.

8. **`src/training/hf_peft_sft.py`** — Replace the `import torch  # noqa: F401` side-effect check with:
   ```python
   import importlib.util
   if importlib.util.find_spec("torch") is None:
       ...  # raise or log; avoid the noqa
   ```
   Or restructure so `torch` is actually used (e.g., `torch.__version__` in the log). Either removes the `noqa`.

**Risk:** Low. Each change is a one-to-three line edit in a single file. Run `pytest tests/ -q` after each edit to confirm no regression.

---

### Phase 3 — Test repair and addition

**What:** Add the two missing test files covering the CLI and training dry-run paths. No production code changes.

**Target: `tests/test_cli.py`** (new file)

Cover all eight Click entry points using `click.testing.CliRunner`:

- `kde-lab --help` — asserts exit code 0 and the word "kde_ontology_slm_lab" in output.
- `kde-lab info` — asserts exit code 0 and "python" in output; reads from real `configs/` (already present).
- `kde-lab pipeline` — **do not invoke** the real pipeline in CI (it writes to `artifacts/`); assert that the command is registered and that `--help` works.
- `kde-lab ingest --help` — asserts exit code 0.
- `kde-lab graph --help` — asserts exit code 0.
- `kde-lab tokenizer` — invoke with a `--report-path tmp_path/report.json`; asserts exit code 0 and that the report file exists.
- `kde-lab dataset --help` — asserts exit code 0 (the real command requires an existing graph artifact).
- `kde-lab train` (dry-run mode — it always is in v0) — asserts exit code 0 and `"dry-run"` in output.
- `kde-lab eval --help` — asserts exit code 0.

**Target: `tests/test_training_dryrun.py`** (new file)

Cover the five training scripts' `--dry-run` paths:

- `hf_peft_sft.main(["--dry-run"])` — asserts return code 0; asserts the JSON config appears on stdout.
- `unsloth_sft.main(["--dry-run"])` — same.
- `grpo_optional.main(["--dry-run"])` — same.
- `merge_adapter.main(["--dry-run"])` — same.
- `export_gguf.main(["--dry-run"])` — same; also asserts the "manual commands" note is printed.
- `lora_config.LoRAConfig.from_yaml(CONFIGS / "training.yaml")` — asserts the result is a `LoRAConfig` with the correct `profile` field.
- `qlora_config.QLoRAConfig.from_yaml(CONFIGS / "training.yaml")` — asserts the `base` field is a `LoRAConfig`.

**After Phase 3:** test count should rise from 64 to approximately 80-90.

**Risk:** Low. New files only; no existing code changes.

---

### Phase 4 — CI/CD setup

**What:** Add `.github/workflows/ci.yml` to run lint and tests on every push and pull request to `master` and `main`.

**File: `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install dev dependencies
        run: pip install -e ".[dev]"
      - name: Lint (ruff)
        run: python -m ruff check src/ --output-format=concise
      - name: Test
        run: python -m pytest tests/ -q
```

**Constraints:**
- No GPU steps (training tests all run in `--dry-run` mode).
- No network access beyond `pip install`.
- No `[train]` extras installed in CI — tests that would need torch are excluded by the `--dry-run` / `# pragma: no cover` pattern already in place.

**Risk:** Low. Adding a workflow file does not affect any existing code.

---

### Phase 5 — Examples and setup validation

**What:** Verify that the six `examples/run_*.py` scripts and the `scripts/setup_dev.sh` script work end-to-end against the current codebase. Fix any import path issues found.

**Specific checks:**

- `python examples/run_mini_repo_pipeline.py` — should exit 0; artifacts written to `artifacts/`.
- `python examples/run_advanced_rag.py` (if it exists) — invoke with `--help` or a dry-run flag.
- `scripts/setup_dev.sh` — run in a clean venv; check that `kde-lab info` succeeds after install.
- Confirm that `kde-lab pipeline` (the CLI wrapper) produces identical output to the direct script.

**Files potentially touched:** any `examples/run_*.py` that has a stale import or broken path after Phase 2 changes. Expected to be zero; the `deep_merge` rename is the only structural change and it is internal to `src.common.config` and `src.training.lora_config`.

**Risk:** Very low. Phase 5 is validation, not a code change phase. Only fix what is broken.

---

### Phase 6 — Final GitHub readiness

**What:** Prepare the repo for a public push to a remote.

**Specific tasks:**

1. Set `main` as the default branch target in `.github/workflows/ci.yml` (both `master` and `main` are already listed above; this just confirms the remote default).
2. Confirm `.gitignore` excludes `artifacts/`, `datasets/`, `models/`, `checkpoints/`, `*.gguf`, `*.safetensors` (already present).
3. Add `CONTRIBUTING.md` only if a collaborator is expected; skip otherwise (per non-goals).
4. Tag `v0.1.0` once CI is green and all phases are merged.

**Risk:** Zero — no code changes; tag and remote setup only.
