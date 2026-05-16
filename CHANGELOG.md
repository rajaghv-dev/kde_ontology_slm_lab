# Changelog

## [0.0.2] — refactor, documentation alignment, CI

### Fixed
- `run_mini_repo_pipeline.py` was not writing `mini_repo_relations.jsonl`, causing
  `kde-lab graph` to silently load 0 edges. Now writes both entities and relations.
- README quickstart used `pip install -e .` (missing `[dev]` — pytest fails without it).
- `requirements.txt` was missing `numpy>=1.26` (required by RAG modules).
- `kde-lab graph` now warns explicitly when relations JSONL is absent.

### Refactored
- `deep_merge()` moved to `src/common/config.py`; removed duplicates from
  `src/cli/train_cmd.py` and `src/training/lora_config.py`.

### Added
- `AGENTS.md` — agent-friendly operational guide.
- `CONTRIBUTING.md` and `SECURITY.md`.
- `tests/test_cli_smoke.py` — smoke tests for all CLI subcommands.
- `.github/workflows/validate.yml` — Python 3.10/3.11/3.12 matrix CI.
- 16 documentation files under `docs/`: inventory, audits, architecture (with
  Mermaid diagram), interface reference (849 lines), setup validation, testing
  guide, examples guide, observability guide, refactor plan, tooling gaps,
  agent handoff, GitHub readiness, security audit, and PR summary.
- `reports/final-validation-report.md`.

### Documentation fixed
- `docs/13_observability_with_grafana_prometheus.md`: corrected artifact paths
  (JSONL per run, not CSV), "four services" → "five services" (Promtail added),
  fixed JSON logger attribution.
- `observability/README.md`: fixed module invocation paths (direct script, not
  `python -m observability.*`).
- `docs/07_training_recipes.md`: corrected CLI interface description to match
  current `--profile`/`--model-key` flags.
- `docs/10_local_training_guide.md`: replaced flag-based script invocation with
  correct env-var pattern (`CONFIG=... DRY_RUN=1 bash scripts/train_unsloth_lora.sh`).

## [0.0.1] — initial vertical slice

### Added
- Repo structure following the planned layout.
- Synthetic mini KDE repo fixture under `examples/mini_kde_repo/` (C++, QML, CMake, D-Bus, KConfig, desktop file, test, log).
- `src/repo_ingest/` — scanner + readers for CMake, C++, QML, D-Bus, KConfig, desktop files.
- `src/ontology/` — entity + relation schema, extractor.
- `src/graph/` — NetworkX-backed graph builder + queries + JSON/GraphML export.
- `src/traceability/` — symptom-to-code-path query.
- `src/tokenizer/` — token-cost analyzer with offline character-level fallback.
- `src/dataset/` — QA generator + JSONL writer producing evidence-grounded SFT examples.
- `src/rag/` — graph retriever + answer-with-evidence renderer.
- `src/eval/` — evaluation set builder + grader + report.
- `examples/run_mini_repo_pipeline.py` — end-to-end vertical slice.
- Smoke tests for every layer.
- Configs scaffolding under `configs/`.
- Initial docs under `docs/`.
