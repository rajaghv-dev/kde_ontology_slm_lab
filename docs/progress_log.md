# Progress log

A running, dated log of milestones for `kde_ontology_slm_lab`. The point is not to be exhaustive — the git log is exhaustive — but to leave a trail a future learner (or a future you) can read end-to-end to understand how the project actually evolved.

Format: one entry per dated milestone, plus short "planned" entries for items still on the road map in [../TODO.md](../TODO.md). Keep entries factual; opinions go in the chapter docs.

---

## 2026-05-13 — Day 1: vertical slice committed

The lab's first runnable day. Everything below is observable from the v0.0.1 commit.

**What landed:**

- Repo scaffold: `src/`, `examples/`, `tests/`, `configs/`, `docs/`, `notebooks/`, `observability/`, `scripts/`, `artifacts/`.
- Synthetic mini KDE repo under [../examples/mini_kde_repo/](../examples/mini_kde_repo/): C++, QML, CMake, D-Bus, KConfig, desktop file, test, and a log file with the `minisearch.backend` category.
- Seven per-format readers under [../src/repo_ingest/](../src/repo_ingest/): scanner, CMake, C++, QML, D-Bus, KConfig, desktop, log.
- Ontology in [../src/ontology/schema.py](../src/ontology/schema.py): 32 entity types, 24 relation types, with the construction-time validation rule.
- Graph builder in [../src/graph/builder.py](../src/graph/builder.py) with JSON and GraphML export.
- Ten named graph queries in [../src/graph/queries.py](../src/graph/queries.py).
- Traceability path in [../src/traceability/symptom_to_code.py](../src/traceability/symptom_to_code.py) (seed-and-expand, 3-hop default).
- Tokenizer analyzer in [../src/tokenizer/analyze_tokens.py](../src/tokenizer/analyze_tokens.py) with the offline `WhitespaceFallbackTokenizer` and the canonical KDE term + phrase lists.
- SFT dataset generator in [../src/dataset/qa_generator.py](../src/dataset/qa_generator.py) with six template families.
- RAG renderer in [../src/rag/answer_with_evidence.py](../src/rag/answer_with_evidence.py) that cites evidence inline.
- Eval set + grader + report in [../src/eval/](../src/eval/).
- End-to-end pipeline in [../examples/run_mini_repo_pipeline.py](../examples/run_mini_repo_pipeline.py).
- Smoke tests for every layer: imports, ingest, ontology, graph, dataset, eval, tokenizer, traceability, RAG.
- The 15 learning chapters under [docs/](.) — this log included.

**Measured baselines (mini repo, v0):**

- Tests: 26 passing.
- Files ingested: 12 (mini repo).
- Entities extracted: ~30 (single run, exact number printed by the pipeline).
- Relations: ~40.
- Tokenizer mean compression on the canonical term list (whitespace fallback): ~2.5 chars/token.
- RAG eval pass rate: 66.67% (4 of 6 items).

**Known to be missing:**

- Trained models — none yet. Today's "answers" are deterministic Markdown from [../src/rag/answer_with_evidence.py](../src/rag/answer_with_evidence.py).
- Real KDE ingest — supported in principle (just point `configs/repos.yaml` at a clone) but not exercised in CI.
- The observability Docker stack — files scaffolded but not booted.
- Adapter routing — designed in chapter 07; no code yet.

The number to beat is 66.67%. Every later milestone should report against it.

---

## 2026-05-14 (planned) — Documentation cycle complete

**Goal:** all 15 learning chapters under [docs/](.) reviewed end-to-end, with cross-links validated and exercises tested by a fresh reader.

**Checklist:**

- [ ] Every chapter renders cleanly in plain Markdown (no broken links, no missing code paths).
- [ ] Cross-links between chapters resolve.
- [ ] Each chapter has 3-5 exercises and 3-7 further-reading items.
- [ ] A new contributor can read 00-04 and run the pipeline without external help.

---

## 2026-05-20 (planned) — Notebooks online

**Goal:** the 10 Jupyter notebooks under [../notebooks/](../notebooks/) load `artifacts/` artifacts and produce the figures listed in chapter [14_paper_outline.md](14_paper_outline.md).

**Tracked artifacts:**

- `notebooks/02_ontology_visual.ipynb` -> `artifacts/plots/ontology_tree.png`
- `notebooks/03_graph_snapshot.ipynb` -> `artifacts/plots/graph_topology.png`
- `notebooks/05_tokenizer_analysis.ipynb` -> `artifacts/plots/tokenizer_compression.png`
- `notebooks/06_dataset_inspection.ipynb` -> `artifacts/plots/dataset_distribution.png`

---

## 2026-05-27 (planned) — Configs filled out

**Goal:** all seven configs in [../configs/](../configs/) populated and validated.

**Sections:**

- `configs/repos.yaml` — points at the mini repo by default; documents the shape for real KDE clones.
- `configs/models.yaml` — the seven base models (Qwen-small, SmolLM, TinyLlama, Gemma-small, plus three more compatible SLMs) with local snapshot paths.
- `configs/tokenizer.yaml` — extension rules per base.
- `configs/ontology.yaml` — overrides for the entity/relation set (kept empty in v0.1; placeholder).
- `configs/dataset.yaml` — per-template flags, split policy.
- `configs/training.yaml` — adapters, profiles, hyperparameters (per chapter 07).
- `configs/eval.yaml` — the 10 suites and per-suite settings.

**Acceptance:** `python -m kde_lab config validate` (planned CLI) reports zero errors.

---

## 2026-06-10 (planned) — Observability stack up

**Goal:** the full Docker stack at [../observability/](../observability/) boots and Grafana renders the seven planned dashboards.

**Acceptance:** `docker compose up -d` plus one pipeline run produces visible time series in `kde_ingest_files_total`, `kde_ontology_entities_total`, `kde_eval_pass_rate`.

---

## 2026-06-25 (planned) — First trained adapter

**Goal:** the architecture adapter (Stage 2 of chapter 07) trained on the mini repo and a small slice of real KDE source. Eval pass rate measured against the v0 baseline.

**Tracked artifacts:**

- `artifacts/training_runs/architecture_v0.1/` — adapter + training args + model card.
- `artifacts/eval_reports/architecture_v0.1.md` — pass rate per category.

**Acceptance:** pass rate beats 66.67% on the v0 eval, and pass rate on the hallucination-resistance suite exceeds 0.90.

---

## 2026-07-15 (planned) — All seven adapters + router

**Goal:** all seven adapters from chapter 07 trained, plus the small router classifier, plus a unified inference path that selects the right adapter per question.

**Acceptance:** the router achieves > 0.95 accuracy on the held-out eval; the routed inference pass rate beats every single adapter's pass rate on its category.

---

## 2026-08-01 (planned) — Real-repo ingest

**Goal:** ingest the KIO + KConfig + Dolphin slice of `invent.kde.org` (locally cloned). The pipeline runs end-to-end; the dataset grows ~100x; the eval suite is expanded to cover real questions.

**Tracked artifacts:**

- `artifacts/graphs/kde_kio_kconfig_dolphin.json` (and .graphml).
- `artifacts/datasets/kde_kio_kconfig_dolphin_sft_v0.2.jsonl`.
- `artifacts/eval_reports/kde_kio_kconfig_dolphin_v0.2.md`.

**Acceptance:** the v0.2 dataset passes every quality rule in chapter 06; the v0.2 eval is reproducible from the configs.

---

## 2026-09-01 (planned) — v0.2 release

**Goal:** the lab is presentable as a workshop demo or a paper companion. The CHANGELOG records what shipped; the docs are stable.

**Items expected to be done:**

- Adapter routing.
- Full observability stack.
- Real-repo ingest.
- The 10 eval suites populated.
- The paper outline in chapter 14 turned into a draft.

The list of "will not do" items in [../TODO.md](../TODO.md) stays out of scope.

---

## How to update this log

When a milestone lands:

1. Add a new dated entry above the planned ones.
2. Quote the actual measured numbers (test count, pass rate, dataset size).
3. List what is observable from that commit alone.
4. List what is still missing.
5. Promote one of the planned entries (or delete it if it was wrong) so the next milestone is always within reach.

The log is a learner's reading order. Keep it readable.
