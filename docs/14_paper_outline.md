# 14 — Paper outline

This lab is shaped like a paper waiting to be written. If you actually write one — for a workshop, a tech report, or a chapter in a thesis — this outline is the skeleton. It tracks the choices made in the lab and points at the figures the notebooks and the eval reports already (or will) produce. Treat it as a checklist for "does the work say something useful".

## Working title

> **From source to symptom: an ontology-first small-language-model lab for KDE debugging**

Alternates:

- *KDE as a system, not a codebase: training small language models for desktop debugging*
- *Adapter-routed small models for layered desktop platforms*
- *Evidence-grounded fine-tuning of small language models on KDE*

The "from source to symptom" framing tracks the seven-stage pipeline and the OCT lens.

## Abstract sketch

> Modern desktop platforms like KDE are layered systems: C++ classes, QML views, D-Bus services, KConfig keys, log categories, plugins, and tests interact at runtime in ways that source-only models cannot follow. We present a learning-oriented lab, `kde_ontology_slm_lab`, that turns a KDE repository into a typed knowledge graph (32 entity types, 24 relation types) and uses that graph to generate an evidence-grounded SFT dataset for small language models. We compare five retrieval/training modes (vector-only, graph-only, hybrid, SFT-only, SFT+retrieval) and a seven-adapter routing scheme. The lab ships a runnable vertical slice on a synthetic mini repo, an Observability-Controllability-Traceability (OCT) framing, and ten evaluation suites targeting architecture, code navigation, debug triage, evidence citation, tool-use correctness, hallucination resistance, uncertainty handling, patch plan quality, test suggestion quality, and repo-version robustness. We report baseline results on the mini repo (66.67% pass rate at v0) and outline the path to a public benchmark on a small slice of real KDE source.

## Section outline

### 1. Motivation

- Why training a code-LLM on KDE source alone is not enough.
- The layered-system view: signals/slots, D-Bus, KConfig, QML, logs, plugins, desktop files.
- The cost of hallucinated APIs in a debugging context.
- The case for small models with explicit knowledge graphs (cheap to deploy, easy to audit).

### 2. The OCT framework

- Three questions: what can we see, what can we change, how do we link cause to effect.
- How OCT structures the lab's modules.
- Comparison with related framings: SE4ML, system-level observability literature.

### 3. KDE platform mapped to an ontology

- The KDE Frameworks tier system in one diagram.
- The 32 entity types and 24 relations (table).
- Why directed multi-graph (`networkx.MultiDiGraph`).
- The cross-file linking trick (header / source split) and its impact on dataset coverage.

### 4. Repo understanding pipeline

- Seven stages with code references to the lab's modules.
- Per-format readers (CMake, C++, QML, D-Bus, KConfig, desktop, log).
- The traceability query and its role as a graph-quality smoke test.
- One worked trace from source line to dataset record.

### 5. Tokenizer analysis

- Why vocab matters for small models.
- The offline fallback (with a fairness disclaimer).
- The canonical KDE term and phrase lists.
- A compression delta table across base-model tokenizers.

### 6. Dataset construction

- The JSONL schema with `evidence`, `negative_examples`, `metadata`.
- Six template families.
- The seven quality rules.
- The "I don't know from evidence" discipline.
- Split policy (by repo, component, time — not random).

### 7. Adapter-routed training

- The five stages.
- The seven adapters.
- The router (small classifier).
- The five compute profiles.
- LoRA vs. QLoRA vs. full FT decision matrix.

### 8. Five RAG / training modes compared

- Vector-only, graph-only, hybrid, SFT-only, SFT+retrieval.
- Pass rate per category for each mode.
- Latency and memory comparisons.

### 9. Evaluation

- The 10 suites.
- The grader's design and its limits.
- Programmatic grading vs. LLM-judge.
- Detailed results on the mini repo and on a real KDE slice (v0.1).

### 10. Failure modes

- Catastrophic forgetting, KL collapse, evidence drift, hallucinated APIs.
- The detection signals and the fixes.
- A short taxonomy of "soft" failures we did not see and how we know.

### 11. Privacy, licensing, and safety

- KDE licensing in one paragraph.
- Redaction rules.
- Data and model card discipline.
- The "no secrets in the weights" guarantee.

### 12. Observability infrastructure

- The two modes (no-install vs. full stack).
- Prometheus metrics, label discipline, Grafana dashboards.
- The role of trace ids in pipeline debugging.

### 13. Related work

- Code-only training (CodeGen, StarCoder, Replit, Code Llama family).
- Knowledge-graph-augmented LLMs (e.g. Atlas, GraphRAG-style approaches).
- Retrieval-augmented small models (RAG surveys).
- Open-source desktop tooling (`compdb`, `clang-index`, `cscope`).
- KDE bug-report classification work (where it exists).

### 14. Future work

- Function-calling / tool-use SFT for `qdbus`, `journalctl`, `ctest`, `ripgrep`, `git blame`.
- Real-repo ingestion against KIO + KConfig + Dolphin core.
- Adapter-routing inference server.
- Multi-turn debugging dialogue.
- Neo4j + RDF/OWL exporters.
- Tree-sitter / libclang C++ reader upgrade.

### 15. Conclusion

The contribution is not a model — it is a *recipe* for producing models with verifiable, auditable knowledge of a specific desktop platform. The lab's value is the discipline (ontology-first, evidence-on-every-claim, ten-suite eval, OCT lens) rather than any single trained checkpoint.

## Key claims the lab is designed to support

If the paper has to defend a thesis, these are the load-bearing claims:

1. **An explicit, domain-specific ontology improves answer faithfulness for small models in narrow domains.** Tested by comparing graph-only and hybrid retrieval against vector-only.
2. **Evidence-grounded SFT reduces hallucination rate by an order of magnitude relative to a raw code-text SFT.** Tested by the hallucination-resistance suite.
3. **Adapter routing produces cleaner per-task outputs than a single monolithic SFT.** Tested by per-category pass rate.
4. **Tokenizer extension helps disproportionately in low-resource SLM regimes.** Tested by per-term compression delta and downstream eval.
5. **A vertical-slice methodology accelerates lab progress relative to the "build all of ingest before any of training" approach.** Tested anecdotally (paper time-to-first-result) and by tracking the dated milestones in [progress_log.md](progress_log.md).

Claims 1–4 are quantitative; claim 5 is methodological and lives mostly in the discussion section.

## Where the figures come from

| Figure                                | Source                                          |
|---------------------------------------|--------------------------------------------------|
| OCT triad diagram                     | Hand-drawn, in `docs/00_big_picture.md`         |
| KDE layered stack                     | Hand-drawn, in `docs/01_kde_architecture_map.md`|
| Seven-stage pipeline diagram          | Hand-drawn, in `docs/02_repo_understanding_pipeline.md` |
| Ontology entity-type tree             | Generated from [../src/ontology/schema.py](../src/ontology/schema.py) by `notebooks/02_ontology_visual.ipynb` (planned) |
| Graph topology snapshot               | Generated from `artifacts/graphs/mini_repo.json` by `notebooks/03_graph_snapshot.ipynb` (planned) |
| Tokenizer compression bar chart       | Generated from `artifacts/tokenizer_reports/fallback_token_cost.json` by `notebooks/05_tokenizer_analysis.ipynb` (planned) |
| Dataset task-type distribution        | Generated from `artifacts/datasets/mini_repo_sft_v0.jsonl` by `notebooks/06_dataset_inspection.ipynb` (planned) |
| Eval pass-rate-per-category table     | `artifacts/eval_reports/mini_repo_eval.md`      |
| Training loss curves                  | Captured by exporters into Prometheus / Grafana |
| Failure-mode taxonomy diagram         | Hand-drawn, in `docs/11_failure_modes.md`       |

The notebooks under [../notebooks/](../notebooks/) are scheduled for v0.1 — see [../TODO.md](../TODO.md). Once they exist, each one produces its figure as a deterministic PNG / SVG in `artifacts/plots/`.

## What the paper should not claim

- *A state-of-the-art KDE assistant.* The lab is a methodology and a baseline, not a competition entry.
- *Generalisation to non-KDE desktop platforms.* GNOME / Cinnamon / XFCE have similar shapes but the lab does not test them.
- *Industrial robustness.* The C++ reader is regex-based. Tree-sitter / libclang is a v0.2 stretch.

Stating the limits is what separates a useful paper from a hyped one.

## Exercises

1. Pick one section above and draft its three figures in pencil. Identify which artifact (or notebook) you need to produce each.
2. For claim 2 (evidence-grounded SFT reduces hallucination), describe the experiment design: control, treatment, metrics, statistical test.
3. Search the most recent year of arXiv for "graph RAG small model code". Sketch a related-work paragraph that situates this lab against the top three results.
4. Write the abstract by yourself, in 120 words or fewer. Compare with the sketch above.
5. Identify which of the five compute profiles your reader is likely to have. Frame the paper's results so that profile is the centre of gravity.

## Further reading

- *How to write a good systems paper* (Mark Allman, ACM CCR) — useful regardless of venue.
- *The Researcher's Bible* by Bundy, MacQueen, et al.
- Recent USENIX ATC, OSDI, EuroSys papers on systems + ML — for the "infra + measurement" flavour this lab matches.
- Recent EMNLP / ACL papers on knowledge-graph-augmented LLMs.
- The Bloomberg Code Llama and Replit Code papers for code-LLM evaluation patterns.
- The KDE Akademy talks for a year-over-year pulse on what the community is asking for.
- *The Elements of Style* (Strunk & White) for the rewriting pass. Always.
