# 08 — Debug reasoning evaluation

A model is only as good as its evaluation. This chapter describes the 10 eval suites the lab plans to ship, the metrics each one reports, and walks one full debugging scenario — *"Dolphin slow on folder open"* — through what a passing answer looks like. The v0 mini-repo eval is small enough that you can read every assertion in [../src/eval/eval_set_builder.py](../src/eval/eval_set_builder.py); the rest of this chapter describes the structure each new suite should follow.

## Why programmatic graders

The eval is graded by code, not by a human and not by an LLM judge. That choice is deliberate:

- **Reproducibility.** The grade is a pure function of the answer and the eval item.
- **Speed.** You can run the whole eval every commit.
- **No second model in the loop.** LLM-as-judge has known biases and turns each eval run into a long, expensive evaluation in its own right.

The trade-off is that programmatic grading is brittle: you can write a great answer that misses a `must_mention` substring and gets marked wrong. Mitigation: write `must_mention` lists that include enough plausible synonyms, and use the `category` field to spot systematic graders-too-strict bugs.

## The grader

[../src/eval/answer_grader.py](../src/eval/answer_grader.py) is short:

```python
def grade(answer_text: str, item: dict) -> GradeResult:
    text = answer_text.lower()
    must = item.get("must_mention", []) or []
    must_not = item.get("must_not_mention", []) or []
    hits = sum(1 for m in must if m.lower() in text)
    recall = hits / len(must) if must else 1.0
    forbidden = any(m.lower() in text for m in must_not)
    passed = recall >= 1.0 and not forbidden
    ...
```

So a record passes when:

1. Every `must_mention` substring appears, case-insensitive, somewhere in the answer.
2. No `must_not_mention` substring appears.

That is enough for the v0 suite and enough for most regression checks. The report module in [../src/eval/report.py](../src/eval/report.py) rolls per-item results up to per-category and overall numbers.

## The v0 mini-repo eval

[../src/eval/eval_set_builder.py](../src/eval/eval_set_builder.py) hand-authors six items:

```
eval:01:signal-emitted   architecture_qa   "Which signals does the KFileSearcher class emit?"
                                           must_mention: resultsReady, searchFailed, currentPathChanged
eval:02:config-key       code_navigation   "Which KConfig key controls the maximum number of results..."
                                           must_mention: MaxResults
eval:03:log-category     debugging         "When MiniSearch becomes slow on large folders, which log category..."
                                           must_mention: minisearch.backend
eval:04:qml-backend      code_navigation   "Which C++ class is the SearchView QML component backed by?"
                                           must_mention: KFileSearcher
eval:05:dbus-methods     tool_use          "Which D-Bus methods does org.kde.minisearch expose?"
                                           must_mention: searchPath, cancel
eval:06:refusal          refusal           "What signal does the imaginary class KFooBarMaker emit?"
                                           must_mention: do not see
                                           must_not_mention: KFooBarMaker emits
```

Six items, five categories. On the v0 RAG baseline (no fine-tuning, deterministic answerer in [../src/rag/answer_with_evidence.py](../src/rag/answer_with_evidence.py)), the pass rate is roughly **66.67% (4 of 6)** — the number to beat with every new model.

## The 10 planned eval suites

Once real KDE repos and the SLM are in the loop, the eval set has to grow. The lab plans 10 suites, each with its own item shape and grader.

### 1. Architecture understanding

*"Which class owns X?"*, *"What signal fires when Y changes?"*, *"Which slot reacts to Z?"*

- Items: programmatically generated from the graph, just like the dataset templates.
- Metric: `must_mention` recall; pass rate.
- Watch for: confusion between `Signal` and `Slot`; missing class names on multi-class answers.

### 2. Code navigation

*"Where is `MaxResults` stored?"*, *"Which file declares `KFileSearcher`?"*

- Items: per-graph generation, file paths derived from `Entity.source_path`.
- Metric: **exact file-hit rate**. The answer must include the correct file name (or its basename).

### 3. Debug triage

*"MiniSearch hangs on big folders — where do I look?"*

- Items: hand-authored from real bug reports plus generated symptoms.
- Metric: **component classification accuracy** (the answer names the right `CppClass`), plus evidence precision/recall on logs and config keys.

### 4. Evidence citation

For every answer, score whether the cited evidence list correctly supports each claim.

- Items: paired (claim, evidence_list) extracted from model output.
- Metric: **evidence precision** (fraction of cited refs that actually support the claim) and **evidence recall** (fraction of supporting refs that were cited).
- Watch for: model citing tangential evidence that *contains* the right keyword but does not justify the claim.

### 5. Tool command correctness

For tool-use answers, parse the generated command and check it against an allowlist + parameter shape.

- Items: prompts like *"how do I list D-Bus methods of org.kde.minisearch?"*.
- Metric: **command safety score** — fraction of generated commands that pass `--dry-run` or shellcheck-equivalent validation.

### 6. Hallucination resistance

Items asking about classes/keys/methods that *do not exist* in the graph.

- Metric: **hallucination rate** (1 minus refusal rate on out-of-graph items). Target: < 0.05.

### 7. Uncertainty handling

Items deliberately ambiguous or under-specified.

- Metric: **IDK correctness** — fraction of items where the answer correctly signals uncertainty or asks a clarifying question.

### 8. Patch plan quality

Items present a diff and ask *"is this safe? What would you add?"*.

- Metric: **plan score** — a small rubric (does it identify affected components, does it mention a test, does it flag risk). Programmatic via `must_mention` over plan structure.

### 9. Test suggestion quality

*"What test should be added for this slot?"*

- Metric: **test-name plausibility** — answer must include a sensible `tst_<class>_<scenario>` shape.

### 10. Repo-version robustness

Same architecture questions evaluated against two versions of the same repo.

- Metric: **delta accuracy** — pass rate on v_new minus pass rate on v_old. The model should degrade gracefully or correctly flag changes.

## The metrics, summarised

| Metric                       | Where it shows up                       | Acceptable range (v0.1)  |
|------------------------------|-----------------------------------------|--------------------------|
| Exact file-hit rate          | Code navigation                         | >= 0.80                  |
| Component classification acc | Debug triage                            | >= 0.75                  |
| Evidence precision           | Evidence citation                       | >= 0.85                  |
| Evidence recall              | Evidence citation                       | >= 0.70                  |
| Command safety score         | Tool command correctness                | >= 0.99                  |
| Hallucination rate           | Hallucination resistance                | <= 0.05                  |
| IDK correctness              | Uncertainty handling                    | >= 0.85                  |
| Answer faithfulness          | All categories                          | tracked, not gated       |

"Answer faithfulness" is the most expensive metric — it requires NLI-style entailment against the cited evidence. It is the v0.2 candidate; v0.1 uses recall + precision as proxies.

## One worked eval: "Dolphin slow on folder open"

This is the symptom-style question chapter [00_big_picture.md](00_big_picture.md) and [01_kde_architecture_map.md](01_kde_architecture_map.md) keep returning to. Imagine the eval item:

```yaml
id: eval:debug:dolphin-slow-folder
question: "Dolphin is slow when I open a folder full of photos. Where should I look?"
category: debugging
must_mention:
  - "Dolphin"
  - "KIO"
  - "Baloo"
  - "thumbnail"
  - "log"
must_not_mention:
  - "Xorg"        # likely-irrelevant red herring
  - "TCP"         # not a network problem
```

A passing answer for the trained model:

> "Dolphin loads folder contents through a KIO worker. On large or photo-heavy folders, two extra components run: the **Baloo** indexer (which may stall on a corrupt or large database) and the **thumbnail** subsystem (`KFileItemActions` plus a thumbnailer plugin per mime type). Enable the `kf.kio.workers.file`, `kf.baloo`, and `org.kde.dolphin` **log** categories with `QT_LOGGING_RULES`, then reopen the folder and look for stalls under each category. The relevant **KConfig** key is `Dolphin/PreviewSettings/MaximumSize`; lowering it skips large-image previews. Evidence: kio worker classes in `src/workers/file/file.cpp`; Baloo client in `src/baloo/...`; PreviewSettings group in `dolphin.kcfg`."

This answer:

- Mentions all five `must_mention` keywords (component classification works).
- Names specific log categories (debug triage works).
- Cites file paths (evidence citation works).
- Recommends a config key (controllability, the C in OCT).
- Avoids `Xorg` and `TCP` (no false positives).

If the model also produces a structured evidence list pointing at the cited files, evidence precision and recall both score well.

A failing answer for the same item, taken from a hypothetical broken model:

> "Dolphin uses Xorg for rendering and TCP for network folders. Try restarting it."

That answer hits 0 of the `must_mention` items, hits both forbidden terms, and would be flagged for both factual error and hallucination.

## Wiring evals into the loop

The pipeline already calls the grader on the mini repo:

```python
items = mini_repo_eval_set()
grades = []
for item in items:
    a = answer(g, item["question"], k=6)
    grades.append(grade(a.text, item))
rep_data = aggregate(grades)
save(rep_data, EVAL_DIR, name="mini_repo_eval")
```

That produces `artifacts/eval_reports/mini_repo_eval.md` and `.json`. The Markdown table looks like:

```
# Eval report
- N: 6
- Overall pass rate: 66.67%
- Overall mean recall: 88.89%

| Category         | N | Pass rate | Mean recall | Forbidden hits |
|------------------|---|-----------|-------------|----------------|
| architecture_qa  | 1 | 100.00%   | 100.00%     | 0              |
| code_navigation  | 2 | 100.00%   | 100.00%     | 0              |
| debugging        | 1 | 100.00%   | 100.00%     | 0              |
| refusal          | 1 |   0.00%   |  50.00%     | 0              |
| tool_use         | 1 |  50.00%   |  75.00%     | 0              |
```

Watch the per-category numbers more than the overall — they tell you where a regression lives.

## Exercises

1. Run the pipeline and open `artifacts/eval_reports/mini_repo_eval.md`. Identify which two items fail at the v0 baseline. What change to the RAG renderer or the dataset would fix each?
2. Add a new eval item asking about the `IncludeHidden` config key. Re-run and confirm the new row appears in the report.
3. Sketch one item for each of the 10 planned suites, with at least `question`, `category`, `must_mention`, and one example of a passing answer.
4. Re-read the grader. Propose one small extension that would catch a common false positive (e.g. requiring at least one of `must_mention` to appear in the *first* sentence of the answer).
5. Estimate the cost of an LLM-judge-augmented "answer faithfulness" metric for 100 items per commit. Decide whether the lab should adopt it now or defer.

## Further reading

- The HELM paper (Liang et al., 2022) for an end-to-end benchmark methodology.
- *MT-Bench* and *Arena Hard* — they go heavy on LLM-judge; useful to compare with the programmatic style.
- *Holistic Evaluation of Language Models* for the metric vocabulary.
- "Sufficient evidence and sound reasoning" — search for recent papers on faithful retrieval-augmented generation metrics.
- The TruthfulQA paper for the hallucination-resistance frame.
- The HumanEval / SWE-bench papers for code-grounded grading approaches.
- *Evaluation of Large Language Models: A Survey* — search arXiv.
