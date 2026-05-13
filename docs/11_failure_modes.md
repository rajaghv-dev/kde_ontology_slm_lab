# 11 — Failure modes

Every training run will go wrong eventually. The useful question is *which kind of wrong* — because each failure mode has its own detection signal and its own fix. This chapter catalogues ten common failures (and one bonus class) you will hit on a KDE SLM project, paired with the metric or test that flags each and the canonical remediation.

The list is intentionally ordered from "happens to you in the first hour" to "happens to you after six months of seemingly fine results".

## 1. Catastrophic forgetting

The model was good at general code completion before SFT. After Stage 2 it suddenly cannot produce a syntactically correct Python function. KDE answers look fine; everything else is broken.

**How to detect:** keep a small *general* eval set alongside the KDE eval (50–100 prompts from HumanEval, GSM8K, MMLU subset, plain conversation). Run both after every stage. Catastrophic forgetting shows up as a >5 percentage-point drop on the general suite while the KDE suite climbs.

**How to fix:**

- Lower the LoRA rank (8 instead of 16). Less capacity to overwrite.
- Mix 10–20% general data into every SFT stage.
- Run shorter (1 epoch, not 4). The damage usually happens in epochs 2+.
- Use a higher KL or KL-style regulariser if you are doing preference tuning.

## 2. KL collapse in DPO

You ran Stage 5 (DPO). Eval pass rate goes up by 5%. Then you generate any out-of-distribution prompt and the model is incoherent — repeats tokens, produces empty strings, or only replies in one canned phrase.

**How to detect:** measure KL divergence between the SFT model and the DPO model on a held-out prompt set. If KL exceeds ~5 nats per token on average, you are in collapse territory.

**How to fix:**

- Increase `beta` in DPO (try 0.2 or 0.3). Higher beta = stay closer to reference.
- Reduce epochs. DPO converges fast; 1 epoch is usually enough.
- Ensure your `chosen` and `rejected` are *meaningfully different*. If they are near-identical, DPO degenerates.
- Switch to ORPO, which trains the reference and policy together and dodges this class of failure.

## 3. Reward hacking in GRPO

Optional / stretch in this lab. If you do try GRPO, the model can find a degenerate output that maxes the reward function while being useless to a human. *"Evidence: [evidence] [evidence] [evidence]"* repeated forever scores well on token-level evidence-mention metrics.

**How to detect:** the model's outputs visibly degrade even as numerical reward climbs. Add a *generation quality* spot-check: 10 sample outputs per training step, eyeballed.

**How to fix:**

- Strengthen the reward function with format constraints (length, structure).
- Add a KL penalty against the SFT model.
- Lower the GRPO update step.
- Stop early. GRPO benefits taper quickly.

## 4. Evidence drift

The model used to cite the file and line that justify each claim. After three rounds of SFT, evidence pointers go stale — they reference files that no longer exist, or line numbers that have shifted.

**How to detect:** parse each generated answer's `evidence_refs`. For each ref, check that the file exists *in the current graph* and that the named symbol is at (or near) the claimed line. The evidence-citation suite in chapter [08_debug_reasoning_eval.md](08_debug_reasoning_eval.md) measures this directly.

**How to fix:**

- Regenerate the dataset against the current graph before every SFT run.
- Make `Entity.source_line` exact, not approximate, in the readers.
- When ingesting real KDE repos, pin the repo SHA the dataset was generated from. Record it in `metadata.repo_sha`.

## 5. Hallucinated APIs

The model claims that `KFileSearcher::indexBaloo()` exists. It does not. The user runs it, the build fails, the trust is gone.

**How to detect:** the hallucination-resistance suite in chapter 08 measures this. Also useful: run a regex over generated answers extracting any `::` symbol; check each against the entity name set in the graph.

**How to fix:**

- Make sure the dataset has explicit refusal examples (chapter 06, rule 3).
- Lower the SFT epoch count — overfit models confabulate more.
- At inference, run a *post-generation grounding check*: extract claimed symbols, verify each against the graph, refuse or rephrase if any fail.

## 6. Tokenizer-resize bugs

After adding KDE special tokens, the model produces gibberish until many steps of fine-tuning. Or worse, it produces gibberish *forever* because the embedding init was wrong.

**How to detect:** after every tokenizer change, run the tokenizer-cost report (chapter [05_tokenizer_strategy.md](05_tokenizer_strategy.md)) *and* a 10-prompt generation smoke test. The compression numbers should reflect the new tokens; the smoke generations should still be coherent.

**How to fix:**

- After `model.resize_token_embeddings(N)`, initialise the new rows from the mean of the existing embeddings, not from random.
- Verify the lm-head was resized too — some loaders forget.
- Run a warm-up: 100 SFT steps before any serious training.

## 7. Embedding-init bugs (related, but distinct)

You changed the base model's embedding layer (e.g. expanded vocab, swapped tokenizer) without updating the lm-head bias. The model has working knowledge in the middle layers but cannot produce the new tokens.

**How to detect:** the new tokens' generation probability is near zero across all prompts. Inspect `lm_head.weight`'s new rows; if their norm is much smaller than the existing rows, you have an init bug.

**How to fix:**

- Tie or copy the lm-head row to the embedding row at init.
- If the architecture has independent input/output embeddings, initialise both.
- Re-run a small calibration SFT.

## 8. Dataset leakage from training to eval

You hit 95% on the eval suite. Celebrations. Then you check by hand and discover several eval items appear nearly verbatim in the training set.

**How to detect:** for each eval item, compute the cosine similarity (or simple lexical overlap) between its `instruction` and every training `instruction`. If max similarity exceeds 0.95, you have leakage.

**How to fix:**

- Split by *component* and *repo* (chapter 06, rule 2). Do not split by random shuffle.
- After dataset generation, run a `leak_check.py` that asserts no exact-match or near-match instructions between splits.
- Keep the eval set hand-authored and separately stored.

## 9. Broken chat templates

You trained with a `<|user|>...<|assistant|>` template; at inference you forgot to apply the same template. The model produces garbage, or worse, ignores your instructions.

**How to detect:** generate a prompt with and without the chat template applied. If outputs differ wildly, you are using the wrong template at inference.

**How to fix:**

- Save `tokenizer.chat_template` alongside the adapter.
- At inference, always call `tokenizer.apply_chat_template(messages, tokenize=False)` before generation.
- Pin the template in the model card.

## 10. Log-only-no-code traces

The traceability path returns log categories and config keys but no code locations. The model can say *"watch the minisearch.backend logs"* but not *"look at `kfilesearchbackend.cpp` line 87"*.

**How to detect:** every passing answer should include at least one `evidence_refs` entry with a non-empty `file`. Trace items without a code anchor fail the *evidence-citation* metric.

**How to fix:**

- Re-check the extractor — `from_log` records line numbers, but is the line number being kept through to the answer?
- Make sure the dataset templates require at least one code-evidence entry for any debugging task type.
- At retrieval time, expand log-category seeds via `LOGS_TO` reverse edges to reach the owning class.

## Bonus: silent extractor regressions

The C++ regex was changed. It still matches all the mini-repo cases, but on real KDE source it misses 30% of slots because some files use `private slots:` rather than `public Q_SLOTS:`.

**How to detect:** track the *entity count per type* over time in a CSV under `artifacts/metrics/`. If `Slot` count drops 30% between commits without a corresponding code change, you have a regex regression. The observability stack (chapter [13_observability_with_grafana_prometheus.md](13_observability_with_grafana_prometheus.md)) is the long-term home for this signal.

**How to fix:**

- Pin a *snapshot count* test: a unit test that asserts each entity type's count on the mini repo. The mini repo is small enough that exact counts are stable.
- For real KDE source, assert *minimum* counts.
- Always test new regexes against a held-out fixture before merging.

## A failure-mode triage flow

When the eval drops, do not guess. Follow:

```
[1] Did entity counts change? -> extractor regression (bonus).
[2] Did dataset record counts change? -> template / quality-rule regression.
[3] Did tokenizer compression change? -> tokenizer regression (#6, #7).
[4] Did the loss curve look fine but generations are bad? -> chat template (#9) or hallucination (#5).
[5] Did KL diverge from SFT? -> DPO collapse (#2).
[6] Did the general eval drop while KDE eval climbed? -> catastrophic forgetting (#1).
[7] Did evidence precision/recall drop? -> evidence drift (#4) or log-only traces (#10).
```

Most regressions are caught in steps 1–3. The hard ones (5, 9, 10) get caught only when the eval suite includes them explicitly, which is why chapter 08 lists ten suites instead of two.

## Exercises

1. Pick three failure modes and write a one-paragraph postmortem template for each. What you would record, what you would change.
2. Add a snapshot test to `tests/test_mini_repo_ingest.py` asserting exact entity counts. Run it; perturb the C++ reader to break a regex; confirm the test fails.
3. Sketch the contents of `artifacts/metrics/entity_counts.csv` that the observability layer would write — one row per pipeline run, columns per entity type.
4. Walk through DPO collapse in your head: which two metrics, plotted side by side, would let you see it forming?
5. For a model you actually train, write the eight-item reproducibility block from chapter 10. Then ask: which of these failure modes would the block let you catch?

## Further reading

- "Catastrophic Forgetting in Connectionist Networks" (McCloskey & Cohen, 1989) — the original frame; still readable.
- *DPO* and *ORPO* papers, plus *RLHF Pitfalls* — search arXiv for recent surveys of preference-tuning failures.
- *On the dangers of stochastic parrots* — for context on hallucination.
- The HuggingFace `tokenizers` library's *Adding tokens* page, which has caveats about resize bugs.
- "Detecting Trained Language Models that Will Memorise" — papers on detecting memorisation are useful for dataset-leakage checks.
- The TRL repository's *Common pitfalls* document (in the TRL docs).
- Search Anthropic / OpenAI cookbooks for "evaluating instruction following" — useful for the broken-chat-template diagnostic.
