# 05 — Tokenizer strategy

A tokenizer converts text into integers a model can predict. For small models in narrow domains, the tokenizer is one of the highest-leverage knobs you have. This chapter explains what tokenizers do, why vocab matters for KDE specifically, what the lab measures in [../src/tokenizer/analyze_tokens.py](../src/tokenizer/analyze_tokens.py), and the strict discipline we use to decide whether to change anything.

## What a tokenizer does

In the simplest framing:

```
text ----encode---->  list[int]
[int] ----decode---->  text
```

The mapping is fixed before training. The number of tokens per input controls how much information the model sees per forward pass, how long generation takes, and indirectly how easy it is for the model to remember a concept end-to-end versus stitch it together from many pieces.

Two intuitions to carry through:

1. **Each token is a fixed cost.** A 4 K context model that wastes half of its tokens on splitting `KFilePlacesModel` into `K`, `File`, `Places`, `Model` does *not* see 4 K worth of KDE concepts. Compression matters.
2. **Tokens are also units of memory.** The model learns embeddings per token. If `KFileItemAction` is always tokenized the same way, the model can learn an embedding for the multi-token chunk; if it sometimes splits as `K-File-Item-Action` and sometimes as `KFile-Item-Action`, that learning is fragmented.

## The two big families

### BPE — Byte-Pair Encoding

Start with characters, repeatedly merge the most frequent adjacent pair. The vocabulary is a learned set of subwords. BPE handles unseen tokens by falling back to subword pieces. GPT-2/3/4, LLaMA, Mistral, Qwen — all BPE-based with various byte-level twists. For KDE-style PascalCase identifiers, BPE usually picks up common prefixes (`KConfig`, `KIO`, `KFile`) once they appear often enough in the training corpus.

### SentencePiece (Unigram / BPE on raw text)

A reimplementation that treats text as raw bytes, supports both Unigram and BPE training, and is the default in many multilingual models (T5, mT5, NLLB, ALBERT). The Unigram variant produces probabilistic tokenizations and works well for languages with no whitespace; for English-heavy code text the difference is small. KDE in practice is well-served by either.

For a small KDE-specialised model you have three realistic choices for the *base* tokenizer:

1. **Reuse the base model's tokenizer unchanged.**
2. **Extend it** with a handful of special tokens for the worst KDE offenders (`KConfigGroup`, `qmlRegisterType`, `org.kde.KWin`).
3. **Train a fresh tokenizer** on a KDE corpus (and re-init the embedding matrix). Expensive — done only for substantial wins.

The lab's discipline: do not move to option 2 or 3 unless the tokenizer report shows meaningful compression wins relative to a fresh BPE tokenizer trained on the canonical term list.

## The offline fallback in this lab

The lab is *recipes only*. It must run without downloading anything. That includes tokenizers — popular ones live behind HuggingFace registries and require either a download or a local cache. So [../src/tokenizer/analyze_tokens.py](../src/tokenizer/analyze_tokens.py) ships:

- A canonical KDE term list (`KDE_TERMS`) and a canonical KDE phrase list (`KDE_PHRASES`).
- A `WhitespaceFallbackTokenizer` that splits on whitespace, CamelCase, snake_case, dot-namespace, and a small set of C++ punctuation.
- An `analyze(tokenizer=None)` entry point that uses any HuggingFace tokenizer you pass in, falling back to the whitespace splitter otherwise.

The fallback is not pretending to be competitive. It exists so the pipeline can produce a token-cost report on any machine, anywhere, with no network. You can swap in a real tokenizer for any of the seven base models the project plans to support (Qwen-small, SmolLM, TinyLlama, Gemma-small, plus other compatible local SLMs) without touching the rest of the pipeline.

## The canonical term list

The list in [../src/tokenizer/analyze_tokens.py](../src/tokenizer/analyze_tokens.py) is curated. It includes:

- Framework classes: `KFilePlacesModel`, `KDirLister`, `KIO::Job`, `KIO::StatJob`, `KConfigGroup`, `KSharedConfig`, `KStandardDirs`.
- Qt types: `QFileSystemModel`, `QStandardPaths`, `QString`, `QStringList`.
- Qt macros: `Q_OBJECT`, `Q_PROPERTY`, `Q_SIGNALS`, `Q_SLOTS`.
- QML/registration: `qmlRegisterType`, `qCDebug`, `qCWarning`.
- D-Bus names: `org.kde.KWin`, `org.kde.plasmashell`, `org.kde.minisearch`.
- Runtime binaries: `kded6`, `plasmashell`, `kwin_wayland`, `kwin_x11`, `Baloo`.
- CMake idioms: `kcoreaddons_add_plugin`, `ecm_setup_version`, `find_package`, `target_link_libraries`.

The phrase list includes invocations the model needs to produce cleanly:

- `connect(sender, &Sender::signal, receiver, &Receiver::slot)`
- `journalctl --user -u plasma-plasmashell`
- `qdbus org.kde.minisearch /minisearch searchPath /home query`
- `ctest --output-on-failure -R minisearch`
- `qmlRegisterType<KFileSearcher>("org.kde.minisearch", 1, 0, "KFileSearcher")`

Those phrases are exactly the kind of output the tool-use templates in [../src/dataset/qa_generator.py](../src/dataset/qa_generator.py) generate. If the tokenizer butchers them, training has to compensate.

## The report shape

`analyze` returns a `TokenCostReport`:

```
TokenCostReport(
    tokenizer_name="whitespace-fallback",
    terms=[
        TermCost(term="KFilePlacesModel", chars=16, tokens=4, compression=4.0),
        ...
    ],
    phrases=[ ... ],
)
```

`compression` is `chars / tokens` — higher is better. Run the pipeline and open `artifacts/tokenizer_reports/fallback_token_cost.json`. The `summary` block carries `mean_compression`, `mean_tokens_per_term`, `worst_terms`, `best_terms`.

A few realistic numbers (your run may differ slightly):

- The whitespace fallback typically scores around 2.5 chars-per-token on the term list and a little higher on the phrases. That is a baseline, not a goal.
- A real BPE tokenizer on similar text usually scores 3.0 to 4.5. Extending it with KDE special tokens can push specific terms to 8+ (one token apiece).

The `worst_terms` helper at the bottom of [../src/tokenizer/analyze_tokens.py](../src/tokenizer/analyze_tokens.py) shows the five lowest-compression items. Those are your shortlist for special-token additions.

## Tokenizer extension vs. tokenizer training

When the report says the base tokenizer fragments key KDE concepts, you have two paths:

### Extend

Add special tokens to the existing tokenizer. With HuggingFace's `tokenizers` library this is `tokenizer.add_tokens(["KFilePlacesModel", "KConfigGroup", ...])` followed by `model.resize_token_embeddings(len(tokenizer))`. Pros: cheap, surgical, no need to retrain the tokenizer from scratch. Cons: the new tokens start with random embeddings; you need either embedding warm-up or a few hundred steps of light SFT to teach the model what they mean. Watch for *tokenizer-resize bugs* — see chapter [11_failure_modes.md](11_failure_modes.md).

### Train

Train a fresh tokenizer on a KDE corpus. Pros: optimal compression on KDE text. Cons: incompatible with the base model's pretrained embeddings — you have to re-initialise embeddings and at least the input projection, which is full-finetune territory and not LoRA-friendly.

For an SLM lab, extension is almost always the right answer. Train only when the *worst_terms* are pervasive across your dataset and the wins compound.

## The strict rule

> Do not change the tokenizer unless the report shows meaningful compression wins on the canonical term list, *and* the term list reflects your actual dataset distribution.

The first half is obvious. The second half is the trap: it is easy to optimise for the canonical KDE term list and then discover that 70% of your dataset is C++ structural noise (`#include`, `const`, `&`, namespace boilerplate) that the existing tokenizer already handles fine. Sample a hundred records from `artifacts/datasets/mini_repo_sft_v0.jsonl` (and the larger v0.1 dataset, once it exists), tokenize them, and compare distributions.

## A concrete workflow

```
[1] Run the pipeline once. Open artifacts/tokenizer_reports/fallback_token_cost.json.
[2] Note the worst 5 terms and the worst 5 phrases.
[3] Load the actual base-model tokenizer (e.g. Qwen, SmolLM, TinyLlama) in a notebook.
[4] Re-run analyze(tokenizer=loaded_tokenizer). Save the new report.
[5] Compute the delta. If at least 5 of the 10 worst terms are still under
    compression 3.0, consider adding them as special tokens.
[6] Add them, resize embeddings, and run a tiny SFT to make sure the model
    actually learns the new tokens. The eval suite is the safety net.
```

## Failure modes specific to tokenizers

- **Token leakage.** If the new special token contains a substring that already exists in the vocab (e.g. adding `KFile` when `K` and `File` already merge), you can get conflicting tokenizations. Solve by sorting your additions by length-descending and adding them as a single batch.
- **Embedding init bug.** After `resize_token_embeddings`, the new rows are random. Saving without initialising them, then resuming training, can produce wildly different gradients than the original. Initialise from the mean of the original embeddings as a safe baseline.
- **Pre-tokenizer disagreement.** If you trained the base tokenizer with byte-level pre-tokenization and you add an `org.kde.KWin` token without that prefix, the encoder may never reach the token. Always test `tokenizer.encode("org.kde.KWin")` after adding.

Chapter [11_failure_modes.md](11_failure_modes.md) covers these and a few more, with detection metrics.

## How the dataset uses the report

[../src/dataset/qa_generator.py](../src/dataset/qa_generator.py) does not (yet) read the report — but in v0.1 it will. The plan: when the report shows a worst-compressed phrase, the dataset generator emits an extra example that uses the phrase verbatim and an explanatory completion. That way the model gets dense, in-context exposure to the costly chunk and learns to predict it efficiently even if the tokenizer still splits it.

## Exercises

1. Run `python examples/run_mini_repo_pipeline.py` and open the tokenizer report. List the five worst-compressed terms and the five worst-compressed phrases.
2. Add five new terms relevant to your favourite KDE component (e.g. `KItemModels`, `KIO::CopyJob`, `org.kde.dolphin`) to `KDE_TERMS`. Re-run. Did the mean compression go up or down?
3. Load a real tokenizer in a notebook (`from transformers import AutoTokenizer`). Pass it to `analyze(tokenizer=...)`. Compute the delta against the fallback. Which terms move the most?
4. Pick one of the canonical phrases. Run `tokenizer.encode(phrase)` and print the decoded tokens. Identify the worst boundary (the place the tokenizer fragments most awkwardly). Propose a single special-token addition that would help.
5. Sketch the policy you would use to decide whether to extend the tokenizer for your v0.1 model. Include a quantitative threshold (e.g. "if 5+ of the 10 worst terms have compression < 3.0").

## Further reading

- "Neural Machine Translation of Rare Words with Subword Units" (Sennrich, Haddow, Birch, 2015) — the original BPE paper.
- "SentencePiece: A simple and language independent subword tokenizer" (Kudo, Richardson, 2018).
- "Tokenization is more than compression" — search arXiv for recent surveys; pick one from the last 18 months.
- The HuggingFace `tokenizers` library documentation, particularly the *pre-tokenizers* and *trainers* pages.
- The Qwen, SmolLM, TinyLlama, and Gemma model cards on HuggingFace — each documents its tokenizer family and vocab size.
- Andrej Karpathy's "Let's build the GPT tokenizer" video for a hands-on walk through BPE training.
- The `tiktoken` library for a fast BPE implementation you can use to cross-check compression numbers.
