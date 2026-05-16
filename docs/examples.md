# Examples

_Generated: 2026-05-16. All examples validated against the current repo._

---

## Overview

All examples live in `examples/`. They each add the repo root to `sys.path` via
`sys.path.insert(0, ...)`, so they run without needing `pip install -e .` — though
installing is still recommended for IDE support.

**Prerequisite for most examples:**
```bash
python examples/run_mini_repo_pipeline.py   # builds artifacts/graphs/mini_repo.json
```

---

## `run_mini_repo_pipeline.py` — End-to-end vertical slice

### Purpose
Runs all 9 pipeline stages in one command: scan → ingest → ontology → graph →
traceability → tokenizer → dataset → RAG → eval. This is the repo's primary demo.

### Command
```bash
python examples/run_mini_repo_pipeline.py
```
Or via Makefile: `make vertical-slice`
Or via CLI: `kde-lab pipeline`

### Expected output
```
kde_ontology_slm_lab — vertical slice complete
============================================================
trace_id           : <hex>
files scanned      : 15
entities           : 78
relations          : 77
graph              : artifacts/graphs/mini_repo.json
sft jsonl          : artifacts/datasets/mini_repo_sft_v0.jsonl  (7 examples)
tokenizer report   : artifacts/tokenizer_reports/fallback_token_cost.json
eval pass rate     : 66.67% (4 / 6)
eval report        : artifacts/eval_reports/mini_repo_eval.md
============================================================
```

### Files generated
- `artifacts/graphs/mini_repo.json` — NetworkX graph as JSON
- `artifacts/graphs/mini_repo.graphml` — GraphML export
- `artifacts/ontology/mini_repo_entities.jsonl` — entity dump for `kde-lab graph`
- `artifacts/ontology/mini_repo_relations.jsonl` — relation dump for `kde-lab graph`
- `artifacts/tokenizer_reports/fallback_token_cost.json`
- `artifacts/datasets/mini_repo_sft_v0.jsonl` — 7 SFT QA pairs
- `artifacts/eval_reports/mini_repo_eval.json` + `.md`
- `artifacts/logs/run-<trace_id>.jsonl` — structured log

### What it teaches
The full OCT pipeline: how 7 file formats become a graph, how the graph powers
RAG answers, how answers are graded without an LLM.

### Current status
**Working.** 66.67% eval pass rate is the baseline to beat.

---

## `run_rag_answer_demo.py` — Interactive RAG query

### Purpose
Query the saved graph interactively with any question. Shows how graph retrieval
turns keyword matching into cited evidence.

### Command
```bash
# One-shot
python examples/run_rag_answer_demo.py --query "Which signals does KFileSearcher emit?"

# Interactive (prompts on stdin)
python examples/run_rag_answer_demo.py

# Different repo graph
python examples/run_rag_answer_demo.py --repo mini_repo --k 10
```

### Expected output (for the signals query)
```
Evidence:
[1] CppClass `KFileSearcher` — src/kfilesearcher.h:12 (rel=seed, conf=0.80)
...
[7] Signal `currentPathChanged` — src/kfilesearcher.h:32 (rel=EMITS, conf=0.60)
[8] Signal `maxResultsChanged` — src/kfilesearcher.h:32 (rel=EMITS, conf=0.60)
[9] Signal `resultsReady` — src/kfilesearcher.h:32 (rel=EMITS, conf=0.60)
[10] Signal `searchFailed` — src/kfilesearcher.h:32 (rel=EMITS, conf=0.60)
```

### Files used
- `artifacts/graphs/mini_repo.json` (input — run pipeline first)

### What it teaches
How `src.rag.graph_retriever.retrieve` walks the graph, confidence decay, evidence
citation format.

### Current status
**Working.**

---

## `run_dataset_generation.py` — SFT dataset generation

### Purpose
Generate the SFT JSONL dataset from a pre-built graph. Useful for tweaking
`src/dataset/qa_generator.py` without re-running the full pipeline.

### Command
```bash
python examples/run_dataset_generation.py
python examples/run_dataset_generation.py --repo mini_repo --n 3
python examples/run_dataset_generation.py --out /tmp/my_dataset.jsonl
```

### Expected output
```
records written      : 7
dataset jsonl        : artifacts/datasets/mini_repo_sft_v0.jsonl
```

### Files generated
- `artifacts/datasets/mini_repo_sft_v0.jsonl`

### What it teaches
The 6 SFT template families in `qa_generator.py`, how graph nodes become
instruction/response pairs.

### Current status
**Working.**

---

## `run_reasoning_eval.py` — Eval baseline run

### Purpose
Grade the RAG baseline against the 6-item hand-authored eval set. Thin wrapper
around `kde-lab eval`.

### Command
```bash
python examples/run_reasoning_eval.py
python examples/run_reasoning_eval.py --repo mini_repo
```

### Expected output
```
items              : 6
pass rate          : 66.67%  (4 / 6)
mean recall        : 66.67%
json report        : artifacts/eval_reports/mini_repo_eval.json
markdown report    : artifacts/eval_reports/mini_repo_eval.md
```

### Files generated
- `artifacts/eval_reports/mini_repo_eval.json`
- `artifacts/eval_reports/mini_repo_eval.md`

### What it teaches
How `answer_grader.grade` works (mention recall + forbidden strings), the 66.67%
baseline, how to extend the eval set in `src/eval/eval_set_builder.py`.

### Current status
**Working.**

---

## `run_tokenizer_analysis.py` — Token cost analysis

### Purpose
Show how KDE-specific terms tokenize under the offline character-level fallback.
Identifies which terms would benefit from tokenizer extension.

### Command
```bash
python examples/run_tokenizer_analysis.py
```

### Expected output (excerpt)
```
Worst-compressing terms (chars per token, lower is worse):
  - Q_PROPERTY     10 chars / 9 tok = 1.11
  - Q_SIGNALS       9 chars / 8 tok = 1.12
  - Q_OBJECT        8 chars / 7 tok = 1.14
```

### Files generated
- `artifacts/tokenizer_reports/fallback_token_cost.json`
- `artifacts/tokenizer_reports/offline_tokenizer_report.json`

### What it teaches
Why tokenizer extension matters for KDE terms, the `WhitespaceFallbackTokenizer`
design, the compression ratio metric.

### Current status
**Working.**

---

## `run_training_dry_run.py` — Training recipe preview

### Purpose
Print the fully resolved training config that would be used if `[train]` extras
and model weights were available. Does not launch training.

### Command
```bash
python examples/run_training_dry_run.py
# or with profile override:
python examples/run_training_dry_run.py --profile colab_t4
```

### Expected output (excerpt)
```json
{
  "output_dir": "artifacts/training_runs/v0_qwen_sft",
  "packing": false,
  "profile": "local_8gb",
  ...
}
Dry run complete. Re-run without --dry-run to launch training ...
```

### Files used
- `configs/training.yaml`
- `configs/models.yaml`

### What it teaches
Profile resolution (defaults + overlay), the LoRA config schema, what a training
launch would configure.

### Current status
**Working (dry-run only).**

---

## `run_real_kde_repo_ingest.py` — Real KDE repo ingest

### Purpose
Ingest one or more real KDE repos (e.g. `kio`, `kconfig`, `dolphin`) from a local
clone. Mirrors what `kde-lab ingest` does but prints each step for learners.

### Command
```bash
# First: clone a real KDE repo and point configs/repos.yaml at it
python examples/run_real_kde_repo_ingest.py --repo kio
```

### Prerequisites
1. Clone the repo: `git clone https://invent.kde.org/frameworks/kio`
2. Edit `configs/repos.yaml`: set `path: /path/to/kio` and `enabled: true`
3. Run the script

### Current status
**Working but requires external setup** — no real KDE clones are bundled.
The `mini_kde_repo` is the only out-of-the-box target.

---

## Mini KDE repo fixture

The synthetic KDE repo at `examples/mini_kde_repo/` contains all file types
the pipeline handles:

| File | Type | What it exercises |
|---|---|---|
| `src/kfilesearcher.h` | C++ header | signals, slots, Q_PROPERTY, KConfig read |
| `src/kfilesearcher.cpp` | C++ source | class implementation |
| `src/kfilesearchbackend.h/cpp` | C++ | backend class |
| `qml/SearchView.qml` | QML | `import org.kde.minisearch`, `KFileSearcher` binding |
| `dbus/org.kde.minisearch.xml` | D-Bus XML | `searchPath`, `cancel`, `currentPath` methods + signals |
| `kconfig/minisearch.kcfg` | KConfigXT | `MaxResults`, `IncludeHidden`, `DefaultPath` |
| `desktop/minisearch.desktop` | Desktop entry | `DBusActivatable=true` |
| `logs/minisearch.log` | Log file | `minisearch.backend` category, hot-path marker |
| `tests/tst_kfilesearcher.cpp` | C++ test | unit test |
| `CMakeLists.txt` | CMake | build targets |
