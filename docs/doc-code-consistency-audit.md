# Documentation vs Code Consistency Audit

_Generated: 2026-05-16. Updated: 2026-05-16 (post-fix pass)._

| # | Area | Documentation claim | Repo reality | Evidence | Severity | Required fix | Status |
|---|---|---|---|---|---|---|---|
| 1 | README.md quickstart | `pip install -e .` (no `[dev]` extras) | `pyproject.toml` dev extras include pytest and ruff, which are needed to run tests. `scripts/setup_dev.sh` and `docs/09_colab_guide.md` both correctly use `pip install -e ".[dev]"`. | README.md:52; scripts/setup_dev.sh:21; docs/09_colab_guide.md:33 | High | Change README.md line 52 to `pip install -e ".[dev]"` to match every other install instruction in the repo. | **FIXED** |
| 2 | docs/07_training_recipes.md — CLI plan | `kde-lab train --profile local_16gb --adapter architecture --base qwen-small` is described as the v0.1 user interface | `kde-lab train` accepts only `--profile` and `--model-key`; there is no `--adapter` or `--base` flag. The command as written will fail. | docs/07_training_recipes.md:157; src/cli/train_cmd.py:28-32 | High | Update the CLI plan to match actual flags: `kde-lab train --profile local_16gb --model-key qwen_small`; note `--adapter` and `--base` are not implemented. | **FIXED** |
| 3 | docs/13_observability_with_grafana_prometheus.md — container count | "The four services and what each is for" (Prometheus, Grafana, Loki, Tempo) | docker-compose.yml defines **five** services: Prometheus, Grafana, Loki, Promtail, and Tempo. `observability/README.md` correctly says "five containers". | docs/13_observability_with_grafana_prometheus.md:48; observability/docker-compose.yml:19-88; observability/README.md:37 | Medium | Change "The four services" to "The five services" and add Promtail to the list. | **FIXED** |
| 4 | docs/13_observability_with_grafana_prometheus.md — Loki log statement | `{job="kde-lab"} \| json \| trace_id="abcdef1234"` (job label = `kde-lab`) | promtail-config.yml sets `job: kde_lab` (underscore, not hyphen). `observability/README.md` example uses `{job="kde_lab"}`. | docs/13_observability_with_grafana_prometheus.md:213; observability/loki/promtail-config.yml:23; observability/README.md:76 | Medium | Change the example query in doc 13 from `job="kde-lab"` to `job="kde_lab"`. | **FIXED** |
| 5 | docs/13_observability_with_grafana_prometheus.md — Mode A JSONL fallback files | Claims three named artifacts: `artifacts/metrics/pipeline_run.jsonl`, `artifacts/metrics/entity_counts.csv`, and `artifacts/metrics/eval_history.csv` | The observability module writes only `artifacts/metrics/run-<trace_id>.jsonl` (one file per run, not named `pipeline_run.jsonl`) and `artifacts/logs/run-<trace_id>.jsonl`. No `entity_counts.csv` or `eval_history.csv` is ever written by any code in `src/`. | docs/13_observability_with_grafana_prometheus.md:19-21; src/observability/metrics.py:92; src/observability/logger.py:74 | High | Correct the artifact paths to `artifacts/metrics/run-<trace_id>.jsonl` (per-run metrics) and `artifacts/logs/run-<trace_id>.jsonl` (structured log). Remove the CSV files or add them to `scripts/metrics_summary.py` once that script is implemented. | **FIXED** |
| 6 | docs/13_observability_with_grafana_prometheus.md — `src/common/logging.py` emits JSON lines | "The lab's logger in `../src/common/logging.py` emits JSON lines that Loki ingests via a `promtail` container." | `src/common/logging.py` uses Python's `logging.StreamHandler` with a plain-text format (`%(asctime)s %(levelname)-5s %(name)s %(message)s`). JSON emission happens in `src/observability/logger.py` (the separate `get_obs_logger`), not in `src/common/logging.py`. Doc 13 line 208 itself acknowledges this: "The log format is plain text in v0". | docs/13_observability_with_grafana_prometheus.md:52; src/common/logging.py:19-23; src/observability/logger.py:65 | Medium | Fix line 52: change "The lab's logger in `../src/common/logging.py`" to "The observability logger in `../src/observability/logger.py`". | **FIXED** |
| 7 | observability/README.md — exporter module path | `python -m observability.exporters.kde_metrics_exporter` (bare `observability` top-level package) | There is no `__init__.py` at `observability/` — only at `observability/exporters/`. The package is installed as `src.*` via `[tool.setuptools.packages.find] where=["."] include=["src*"]`. The correct importable path is `src.observability.*`; `observability.exporters.*` would require running from inside the `observability/` directory or a separate install. | observability/README.md:55,118,119; pyproject.toml:54-56; observability/exporters/__init__.py:1 | High | Change the three `python -m observability.exporters.*` commands to either `python -m src.observability.exporters.*` (matching the installed package) or add an `__init__.py` at `observability/` and adjust `pyproject.toml` accordingly. | **PARTIALLY FIXED** — `python -m observability.*` syntax replaced with direct script invocation (`python observability/exporters/kde_metrics_exporter.py`), which works when run from the repo root. Module-path form not adopted. |
| 8 | docs/10_local_training_guide.md — training script invocation | `scripts/train_unsloth_lora.sh --base /path/... --dataset ... --adapter-out ... --profile ... --task-type ...` | `train_unsloth_lora.sh` accepts only `CONFIG` and `DRY_RUN` environment variables and passes `--config` and `--dry-run` to `python -m src.training.unsloth_sft`. The `--base`, `--dataset`, `--adapter-out`, `--profile`, and `--task-type` flags do not exist on the shell script. | docs/10_local_training_guide.md:88-94; scripts/train_unsloth_lora.sh:9-17 | High | Replace the invocation example to show `CONFIG=configs/training.yaml DRY_RUN=0 bash scripts/train_unsloth_lora.sh` and mention that profile/model/dataset overrides are done by editing `configs/training.yaml` or via env var. | **FIXED** |
| 9 | docs/09_colab_guide.md — step 10 eval runner | `python -m src.eval.eval_runner` | `src/eval/` contains `answer_grader.py`, `eval_set_builder.py`, and `report.py` — there is no `eval_runner.py`. The step is already marked "(when v0.1 lands the runner)" but the module path would fail if tried. | docs/09_colab_guide.md:188; src/eval/ listing | Medium | Either note the exact module that currently exists (`src.eval.report`) or mark the command as `(not yet implemented — see src/eval/report.py for the existing CLI)`. | **OPEN** |
| 10 | docs/00_big_picture.md — cross-reference label mismatch | "Chapter [09_debug_reasoning_eval.md](08_debug_reasoning_eval.md) (file `08_debug_reasoning_eval.md`)" | The chapter number in the link text says 09 but the link target and parenthetical both say `08`. The actual file is `docs/08_debug_reasoning_eval.md`. The chapter number in the link anchor is wrong. | docs/00_big_picture.md:88 | Low | Change "Chapter [09_debug_reasoning_eval.md]" to "Chapter [08_debug_reasoning_eval.md]" to match the actual file name. | **OPEN** |
| 11 | docs/07_training_recipes.md — configs/training.yaml described as "planned" / future schema | "The plan is for `configs/training.yaml` to look approximately like: …" with `base_models`, `adapters`, and per-adapter sub-keys | `configs/training.yaml` already exists and has a different schema: a single top-level profile with `lora:`, `optim:`, `profiles:` (five profiles). It has no `base_models:` list, no per-adapter sections. The framing as "planned/approximate" is outdated. | docs/07_training_recipes.md:118-156; configs/training.yaml:1-101 | Medium | Update the YAML snippet to reflect the actual schema, or note that the illustrated schema is aspirational v0.2+ and link to the current `configs/training.yaml` for what is live. | **OPEN** |
| 12 | docs/07_training_recipes.md — profile batch sizes | colab_t4: batch 4, local_8gb: batch 4, local_16gb: batch 8, local_24gb: batch 16, local_48gb: batch 32 | Actual `configs/training.yaml`: baseline `batch_size: 1`; `local_16gb` overrides to 2; `local_24gb` overrides to 4; `local_48gb` overrides to 8; `colab_t4` leaves at 1. All documented values are 4–8× larger than the real config. | docs/07_training_recipes.md:145-149; configs/training.yaml:40,81-99 | Medium | Update the YAML example to match the real profile values (or explicitly label the snippet as "example starting point"). | **OPEN** |
| 13 | docs/07_training_recipes.md & docs/10_local_training_guide.md — merge_adapter.py described as "in flight" | "`src/training/merge_adapter.py` (in flight) folds a LoRA into the base weights." | `src/training/merge_adapter.py` exists and has a complete docstring with usage instructions (`python -m src.training.merge_adapter …`). | docs/07_training_recipes.md:205; docs/10_local_training_guide.md:114; src/training/merge_adapter.py:1-20 | Low | Remove "(in flight)" — the file is present. | **OPEN** |
| 14 | docs/07_training_recipes.md & docs/10_local_training_guide.md — training scripts described as "in flight" | `train_unsloth_lora.sh` and `train_hf_peft_lora.sh` described as "(in flight)" | Both shell scripts exist in `scripts/`. They delegate to `python -m src.training.unsloth_sft` and `python -m src.training.hf_peft_sft` and implement the dry-run path. | docs/07_training_recipes.md:196; docs/10_local_training_guide.md:85; scripts/train_unsloth_lora.sh; scripts/train_hf_peft_lora.sh | Low | Remove "(in flight)" where the scripts are referenced. Keep the note that a real training run requires the `[train]` extras and a GPU. | **OPEN** |
| 15 | docs/09_colab_guide.md — placeholder GitHub URL | `!git clone https://github.com/your-org/kde_ontology_slm_lab.git` | The repo's actual remote URL was not auto-detected but the string `your-org` is a template placeholder that will fail for a reader who copies the command verbatim. | docs/09_colab_guide.md:29 | Low | Replace `your-org` with the real GitHub organization/user once the repo is pushed, or note it explicitly as a placeholder the reader must fill in. | **OPEN** |
| 16 | observability/README.md — prometheus_client install instruction | `pip install prometheus_client` (bare package name) | The package is in `pyproject.toml`'s `[obs]` extra as `prometheus-client>=0.20`. The canonical install is `pip install -e ".[obs]"`. | observability/README.md:54; pyproject.toml:39-41 | Low | Change to `pip install -e ".[obs]"` so users get the version-pinned install path from pyproject.toml. | **OPEN** |
| 17 | docs/00_big_picture.md — exercises reference non-standard module path | Exercise 2: "trace it by hand: from question text, through `src/rag/graph_retriever.py`, into `src/traceability/symptom_to_code.py`, ending at … `artifacts/ontology/mini_repo_entities.jsonl`." | Both source files exist. `artifacts/ontology/mini_repo_entities.jsonl` is a generated artifact that only exists after a pipeline run — the exercise must be done after step 1. This is implicit, not wrong, but could mislead a reader who has not run the pipeline. | docs/00_big_picture.md:131; src/rag/graph_retriever.py; src/traceability/symptom_to_code.py | Low | Add a note to exercise 2 that `artifacts/ontology/mini_repo_entities.jsonl` is created by step 1 (run the pipeline first). | **OPEN** |

## Critical issues

None identified. No command causes data loss, security exposure, or deployment failure.

## High issues

### H1 — README quickstart `pip install -e .` missing `[dev]` extras (README.md:52)

**STATUS: FIXED** — README.md line 52 now reads `pip install -e ".[dev]"`.

Every other install instruction in the repo — `scripts/setup_dev.sh`, `docs/09_colab_guide.md`, `Makefile` — uses `pip install -e ".[dev]"`. The bare `pip install -e .` in the README quickstart installs without pytest or ruff. A user who follows the quickstart literally and then runs `pytest -q` will hit `ModuleNotFoundError: No module named 'pytest'`.

### H2 — `kde-lab train` CLI flags do not match documented invocation (docs/07_training_recipes.md:157)

**STATUS: FIXED** — docs/07_training_recipes.md:157 now reads: "The current `kde-lab train` CLI accepts `--profile` and `--model-key` and prints the resolved training recipe as a dry-run. The full planned interface (`--adapter`, `--base`, and a real training loop) is a v0.1 target; see `TODO.md`."

The doc previously presented `kde-lab train --profile local_16gb --adapter architecture --base qwen-small` as the v0.1 user interface. The actual command in `src/cli/train_cmd.py` only accepts `--profile` and `--model-key`. Passing `--adapter` or `--base` raises a click `UsageError`.

### H3 — JSONL fallback artifact paths are wrong (docs/13_observability_with_grafana_prometheus.md:19-21)

**STATUS: FIXED** — Doc 13 Mode A section now correctly lists:
- `artifacts/metrics/run-<trace_id>.jsonl`
- `artifacts/logs/run-<trace_id>.jsonl`
- `artifacts/eval_reports/<name>.md`

No CSV files are mentioned. A note is added that a `scripts/metrics_summary.py` reader is planned.

### H4 — `python -m observability.exporters.*` module path is wrong (observability/README.md:55,118,119)

**STATUS: PARTIALLY FIXED** — The `python -m observability.*` invocation syntax has been replaced with direct script invocation: `python observability/exporters/kde_metrics_exporter.py --port 9101`. This works from the repo root without a package install. The fully correct alternative (`python -m src.observability.exporters.*`) was not adopted, but the broken `python -m observability.*` form is gone.

`observability/` has no top-level `__init__.py` and is not registered as a Python package in `pyproject.toml`. The installed packages are under `src.*`. Calling `python -m observability.exporters.kde_metrics_exporter` from the repo root will raise `ModuleNotFoundError`.

### H5 — Training script invocation shape does not match actual script (docs/10_local_training_guide.md:88-94)

**STATUS: FIXED** — docs/10_local_training_guide.md:88-94 now shows the correct env-var-driven form:
```bash
CONFIG=configs/training.yaml DRY_RUN=1 bash scripts/train_unsloth_lora.sh
CONFIG=configs/training.yaml DRY_RUN=0 bash scripts/train_unsloth_lora.sh
```

## Medium issues

### M1 — Doc 13 says "four services"; docker-compose.yml has five (docs/13_observability_with_grafana_prometheus.md:48)

**STATUS: FIXED** — "The five services and what each is for" with Promtail listed as the fourth entry.

### M2 — Loki `job` label mismatch between docs (docs/13_observability_with_grafana_prometheus.md:213)

**STATUS: FIXED** — Doc 13 example query now uses `{job="kde_lab"}` (underscore), matching promtail-config.yml and observability/README.md.

### M3 — `src/common/logging.py` incorrectly attributed as JSON emitter (docs/13_observability_with_grafana_prometheus.md:52)

**STATUS: FIXED** — The Promtail service description now reads: "The JSON lines are emitted by `src.observability.logger.get_obs_logger` in `../src/observability/logger.py`."

### M4 — eval_runner module referenced but does not exist (docs/09_colab_guide.md:188)

**STATUS: OPEN** — `python -m src.eval.eval_runner` is still cited. The module does not exist. `src/eval/` contains `answer_grader`, `eval_set_builder`, and `report`. The step hedge "(when v0.1 lands)" is present but the module path remains incorrect.

### M5 — configs/training.yaml described as "planned" but ships with a different real schema (docs/07_training_recipes.md:3,118-156)

**STATUS: OPEN** — Doc 07 still frames the YAML as aspirational and shows a `base_models:` / per-`adapters:` schema. The real file has `lora:`, `optim:`, and `profiles:` with batch sizes 4–8× smaller than documented.

## Low issues

### L1 — Cross-reference typo in docs/00_big_picture.md:88

**STATUS: OPEN** — "Chapter [09_debug_reasoning_eval.md](08_debug_reasoning_eval.md)" link text still says `09`.

### L2 — merge_adapter.py and training scripts described as "in flight" but already exist

**STATUS: OPEN** — `src/training/merge_adapter.py`, `scripts/train_unsloth_lora.sh`, and `scripts/train_hf_peft_lora.sh` all present. "(in flight)" labels not yet removed.

### L3 — Placeholder GitHub URL in docs/09_colab_guide.md:29

**STATUS: OPEN** — `https://github.com/your-org/kde_ontology_slm_lab.git` pending real org/user name after first push.

### L4 — `pip install prometheus_client` in observability/README.md:54 should be `pip install -e ".[obs]"`

**STATUS: OPEN** — Still uses bare `pip install prometheus_client`.

## Summary

| Severity | Count | Fixed | Partially Fixed | Open |
|---|---|---|---|---|
| Critical | 0 | — | — | — |
| High | 5 | 4 (H1, H2, H3, H5) | 1 (H4) | 0 |
| Medium | 5 | 3 (M1, M2, M3) | 0 | 2 (M4, M5) |
| Low | 4 | 0 | 0 | 4 (L1–L4) |
| **Total** | **14** | **7** | **1** | **6** |

The most user-blocking issues are now resolved:

1. ~~**README quickstart** installs without `[dev]`~~ — **FIXED**
2. ~~**`kde-lab train` CLI flags** documented don't exist~~ — **FIXED**
3. ~~**Observability fallback file paths** in doc 13 don't match what the code writes~~ — **FIXED**
4. **`python -m observability.exporters.*`** replaced with direct script invocation — **PARTIALLY FIXED**
5. ~~**Training script invocation** shows flags the shell scripts don't accept~~ — **FIXED**

Remaining open items are cosmetic mismatches (stale "in flight" labels, placeholder URL, non-existent eval_runner module path) or aspirational schema descriptions that require a larger doc rewrite.

---

## Resolution log

### Fixes applied in session 1 (initial refactor)

- `README.md` line 52: `pip install -e .` → `pip install -e ".[dev]"` (H1)

### Fixes applied in session 2 (doc-fix pass)

- `docs/07_training_recipes.md:157`: replaced `--adapter`/`--base` CLI example with correct `--profile`/`--model-key` description and v0.1 roadmap note (H2)
- `docs/13_observability_with_grafana_prometheus.md:19-21`: replaced three wrong artifact paths (`pipeline_run.jsonl`, `entity_counts.csv`, `eval_history.csv`) with the two real per-run JSONL paths (H3)
- `docs/13_observability_with_grafana_prometheus.md:47`: "The four services" → "The five services"; added Promtail entry (M1)
- `docs/13_observability_with_grafana_prometheus.md:213`: `job="kde-lab"` → `job="kde_lab"` (M2)
- `docs/13_observability_with_grafana_prometheus.md:52`: corrected JSON log attribution from `src/common/logging.py` to `src/observability/logger.get_obs_logger` (M3)
- `observability/README.md:55,118,119`: replaced `python -m observability.exporters.*` with direct `python observability/exporters/*.py` invocations (H4 — partial)
- `docs/10_local_training_guide.md:88-94`: replaced flag-based script invocation with correct `CONFIG=... DRY_RUN=... bash scripts/train_unsloth_lora.sh` pattern (H5)
