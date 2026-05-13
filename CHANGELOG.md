# Changelog

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
