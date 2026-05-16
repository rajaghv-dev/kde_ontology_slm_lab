# 07 — Training recipes

This is where the dataset becomes a model. The lab uses *adapter-routed multi-stage SFT*: instead of one monolithic fine-tune, you train a handful of small LoRA adapters, each specialising in one task type, plus a tiny router that picks the right adapter at inference. This chapter explains the five stages, the seven adapters, the configs (planned at `configs/training.yaml`), and the five compute profiles you can target.

## Why adapters at all

A KDE-specialised SLM has to be good at very different kinds of questions:

- Architecture explanation (*"which class emits resultsReady?"*).
- Debug triage (*"why is search slow?"*).
- Code navigation (*"where is MaxResults stored?"*).
- Tool use (*"how do I call this with qdbus?"*).
- Patch review (*"is this diff a safe fix?"*).
- QML <-> C++ bridging (*"what backs this QML component?"*).
- D-Bus and config exploration (*"what does the interface expose?"*).

A single dense model trained on all of these gets pulled in too many directions: tool-use answers leak structural reasoning, debug answers turn into D-Bus call traces, and so on. With seven small adapters you get clean, separable behaviours and the option to swap any one of them out without retraining the rest. LoRA adapters are tiny (a few MB), so the total package stays well under a hundred MB.

The router is a small classifier — a sentence-embedding model plus a logistic head, or even a tiny BERT — that maps an input question to one of the seven task types.

```
question
   |
   v
+---------+
|  router |   (~10M params, ~80 KB on disk)
+---------+
   |
   v selected task_type
   |
   v
+-------------------------+
|   base SLM + adapter_K  |
+-------------------------+
   |
   v
answer
```

For a v0.1 deployment you can also short-circuit the router and call any adapter directly via CLI.

## The five training stages

Each stage targets a specific deficit. Skipping a stage produces a recognisable failure mode (chapter [11_failure_modes.md](11_failure_modes.md)).

### Stage 1 — CPT skip (continued pretraining)

For a *small* model, full continued pretraining on KDE source is usually not worth the compute. The base model already knows English, C++, QML syntax, and a fair amount of public KDE source (it was likely in pretraining). The lab explicitly skips CPT in v0.1; if the eval suite later shows a vocabulary gap (e.g. KDE-specific identifiers never seen at pretraining time), you can revisit.

### Stage 2 — SFT for KDE vocabulary

The first real fine-tune. Mix all six templates from chapter 06 in a single dataset. Goal: teach the model the *KDE flavour* — to use class names verbatim, to cite evidence, to refuse politely when the graph does not back the claim. Use the `architecture_qa`, `code_navigation`, and `debugging` task types.

Typical settings:

- LoRA rank 8 or 16, alpha 16, dropout 0.05.
- Learning rate 1e-4 (for LoRA), 5e-5 (full FT).
- Batch size 4 to 16 depending on profile.
- 2 to 4 epochs over the SFT split.

Save the adapter as `architecture_adapter`.

### Stage 3 — Tool-use SFT

A separate fine-tune, starting from the *base* model again (not on top of stage 2). Train on the `tool_use` task type plus the function-calling extension planned for v0.1. The model learns to produce well-formed `qdbus`, `journalctl`, `ctest`, `ripgrep`, and `git blame` invocations.

The reason for resetting from base: tool-use answers have a very different style from architecture answers (terse, structured, one command per line). Co-training pulls the model toward a muddled hybrid; separating the adapters keeps each style clean. Save as `tool_use_adapter`.

### Stage 4 — Debug reasoning SFT

Again from base. Train on the `debugging` task type plus the symptom-to-component traces produced by [../src/traceability/symptom_to_code.py](../src/traceability/symptom_to_code.py). The output style here is multi-step: *"likely components ... logs to watch ... config keys involved ... evidence ..."*. The v0 RAG renderer in [../src/rag/answer_with_evidence.py](../src/rag/answer_with_evidence.py) is the template the model should learn to reproduce.

Save as `debug_adapter`.

### Stage 5 — Preference tuning

DPO or ORPO over preference triples (`prompt`, `chosen`, `rejected`). The dataset comes from chapter 06's `negative_examples` plus a small amount of human-curated preference data. Goal: teach the model to prefer evidence-grounded answers over plausible-but-unsupported ones, and to refuse cleanly rather than confabulate.

DPO settings to start with:

- beta = 0.1 (the standard).
- Watch KL between the SFT model and the DPO model carefully — KL collapse is the failure mode in chapter [11_failure_modes.md](11_failure_modes.md).
- 1 epoch typically suffices.

GRPO is on the optional / stretch list — it works but adds another two failure modes the lab does not yet have the budget to monitor.

## The seven adapters

Each adapter is a separate LoRA. The list lives (eventually) in `configs/training.yaml`:

| Adapter            | Task type(s)                     | Trained in stage | Notes                                              |
|--------------------|----------------------------------|------------------|----------------------------------------------------|
| `architecture`     | `architecture_qa`                | 2                | Class/signal/property reasoning.                   |
| `debugging`        | `debugging`                      | 4                | Symptom -> components -> logs.                     |
| `code_navigation`  | `code_navigation`                | 2                | Where-is-this-stored questions.                    |
| `tool_use`         | `tool_use`                       | 3                | qdbus, journalctl, ctest invocations.              |
| `patch_review`     | (v0.1)                           | 5                | Reads a diff, classifies risk, suggests tests.     |
| `qml_cpp`          | `code_navigation` (subset)       | 2                | QML -> C++ backend bridging.                       |
| `dbus_config`      | `tool_use` (subset)              | 3                | D-Bus exploration and KConfig lookup.              |

For v0.1 several of these collapse into the same adapter — that is fine. The architectural distinction matters at the router level even if two adapters share weights initially.

## The router

The router is the smallest piece. A `sentence-transformers/all-MiniLM-L6-v2` embedding plus a logistic regression head trained on the `task_type` field of the SFT dataset is more than enough. Inputs are short (the user question alone), classes are few (7), and the training data is exactly the v0 dataset — `(instruction, task_type)` pairs.

You evaluate the router on its own:

```
accuracy@1   : >0.95 on the held-out eval set
confusion    : matrix of (actual, predicted) task_types
```

If the router falls below ~0.9, it becomes the single biggest source of error. Train it with cross-validation and watch for the obvious confusions (e.g. `code_navigation` <-> `architecture_qa`).

## Configs

The plan is for `configs/training.yaml` to look approximately like:

```yaml
base_models:
  - name: qwen-small        # path/to/local/snapshot
    family: qwen
  - name: smollm
    family: smollm
  - name: tinyllama
    family: tinyllama
  - name: gemma-small
    family: gemma
  # plus three more small / community models, all local snapshots

adapters:
  architecture:
    target_modules: [q_proj, k_proj, v_proj, o_proj]
    r: 16
    alpha: 16
    dropout: 0.05
    lr: 1e-4
    epochs: 3
  tool_use: { ... }
  debugging: { ... }
  ...

profiles:
  colab_t4:    {batch_size: 4,  max_seq_len: 1024, precision: bf16}
  local_8gb:   {batch_size: 4,  max_seq_len: 1024, precision: 4bit_qlora}
  local_16gb:  {batch_size: 8,  max_seq_len: 2048, precision: bf16}
  local_24gb:  {batch_size: 16, max_seq_len: 4096, precision: bf16}
  local_48gb:  {batch_size: 32, max_seq_len: 4096, precision: bf16}

preference:
  algorithm: dpo
  beta: 0.1
  epochs: 1
```

The current `kde-lab train` CLI accepts `--profile` and `--model-key` and prints the resolved training recipe as a dry-run. The full planned interface (`--adapter`, `--base`, and a real training loop) is a v0.1 target; see `TODO.md`.

## Compute profiles

Five profiles, listed roughly in increasing capability:

### `colab_t4` (free Colab)

- 1x T4 16 GB.
- Use QLoRA (4-bit base) or LoRA on a bf16 small model under 1.5 B params.
- Max seq len 1024.
- Expect 30–90 minutes per adapter stage.

### `local_8gb`

- 1x small consumer GPU (e.g. RTX 3060 8 GB, T4, RTX 4060).
- QLoRA mandatory for anything beyond ~1 B params.
- Max seq len 1024.

### `local_16gb`

- 1x mid-range workstation card.
- LoRA on bf16 base up to ~3 B params, or QLoRA up to ~7 B.
- Max seq len 2048.

### `local_24gb`

- 1x RTX 3090/4090 or A5000-class.
- LoRA on bf16 7 B; QLoRA on 13 B.
- Max seq len 4096.

### `local_48gb`

- 2x 24 GB or 1x 48 GB.
- LoRA on bf16 13 B; QLoRA on 30+ B if you want to play.
- Max seq len 4096 with room for full sequences.

## Unsloth vs. HF/PEFT

[../scripts/train_unsloth_lora.sh](../scripts/train_unsloth_lora.sh) and [../scripts/train_hf_peft_lora.sh](../scripts/train_hf_peft_lora.sh) (in flight) wrap the two paths.

- **Unsloth** is fastest, especially on consumer GPUs. It rewrites attention and MLP kernels for LoRA/QLoRA workloads. Recommended on the `colab_t4`, `local_8gb`, and `local_16gb` profiles.
- **HF + PEFT** is more flexible: works on any architecture, supports tricks Unsloth has not implemented yet (e.g. specific adapter merging tactics). Use it on `local_24gb` and above when you care more about compatibility than raw speed.

The recipe is the same on both: load base, attach LoRA, train, save adapter, (optionally) merge.

## When to merge adapters

`src/training/merge_adapter.py` (in flight) folds a LoRA into the base weights. Do this when:

- You are exporting to GGUF for `llama.cpp` and want a single file.
- You are shipping to an environment that does not support PEFT loading.
- You have *one* adapter you trust and you no longer want the router overhead.

Do *not* do this when:

- You expect to retrain or swap adapters frequently.
- You have multiple adapters that need to coexist (the router-based deployment).

## What the eval suite watches

Every stage produces a fresh eval run; chapter [08_debug_reasoning_eval.md](08_debug_reasoning_eval.md) lists the suites and metrics. The most important loops:

- **After stage 2:** architecture_qa pass rate must climb from baseline; hallucination rate must not climb.
- **After stage 3:** tool-use command safety must be >0.99 (no destructive commands generated unprompted).
- **After stage 4:** debug evidence precision/recall must climb without dropping IDK correctness.
- **After stage 5:** preference-tuned model must not collapse — KL between SFT and DPO model stays bounded; refusal rate on out-of-graph questions must be ~1.0.

## Exercises

1. Read [../src/dataset/qa_generator.py](../src/dataset/qa_generator.py) and identify which template feeds which stage. Note any task type that is currently underrepresented.
2. Sketch the training command for stage 2 on the `colab_t4` profile, including base-model path and adapter output dir. Save it as a shell command you can paste into Colab.
3. Design the router training set: dump the JSONL, project `(instruction, task_type)` pairs, and pick a held-out 10% by `metadata.component`. What accuracy would you accept?
4. The plan calls for seven adapters. Argue for collapsing two of them in v0.1 if your compute budget is tight. Which two? Why?
5. Draft a one-page run sheet for stage 5 (preference tuning) including the metrics you would watch in real time to abort if DPO collapses.

## Further reading

- *LoRA: Low-Rank Adaptation of Large Language Models* (Hu et al., 2021).
- *QLoRA: Efficient Finetuning of Quantized LLMs* (Dettmers et al., 2023).
- *DPO: Direct Preference Optimization* (Rafailov et al., 2023).
- *ORPO* (Hong et al., 2024) — the simpler "no reference model" preference tuning approach.
- The Unsloth project README on GitHub for the fast-path recipes.
- HuggingFace PEFT documentation, particularly the `LoraConfig` and `PeftModel` pages.
- *State of GPT* talk by Andrej Karpathy for the overall pipeline framing.
- The TRL library documentation for `SFTTrainer` and `DPOTrainer`.
