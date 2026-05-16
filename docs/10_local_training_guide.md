# 10 — Local training guide

When you outgrow Colab you train locally. This chapter covers the five hardware profiles, the Unsloth vs. HuggingFace+PEFT tradeoff, the LoRA / QLoRA / full-finetune decision matrix, how to use the two training scripts at [../scripts/](../scripts/), and when to merge adapters versus ship them separately. It assumes you have read chapter [07_training_recipes.md](07_training_recipes.md); this one is the practical companion.

## The five hardware profiles

Repeating from chapter 07, with concrete recipes per profile.

### `colab_t4` — 1x T4 16 GB

- For first-time training and toolchain debugging.
- QLoRA mandatory for anything ~1.5 B params or above.
- See chapter [09_colab_guide.md](09_colab_guide.md) for the Colab-specific bits.

### `local_8gb` — 1x consumer GPU 8 GB

- Examples: RTX 3060 8 GB, RTX 4060, T4 in a workstation.
- QLoRA mandatory for >1 B params.
- Reduce `max_seq_len` to 1024.
- Useful as a *sanity* environment — you confirm the pipeline works, then move to a bigger machine for the real run.

### `local_16gb` — 1x mid-range GPU 16 GB

- RTX 4080 (16 GB), RTX A4000, V100 16 GB.
- LoRA on bf16 base up to ~3 B params.
- QLoRA on bf16 base up to ~7 B params.
- `max_seq_len` 2048.

### `local_24gb` — 1x high-end GPU 24 GB

- RTX 3090, RTX 4090, A5000, A6000 cut down.
- LoRA on bf16 7 B is the sweet spot.
- QLoRA on 13 B is comfortable.
- `max_seq_len` 4096.
- This is the workstation tier where most KDE-SLM work should live for v0.1.

### `local_48gb` — 1x A6000 / dual 24 GB

- LoRA on bf16 13 B.
- QLoRA on 30+ B for experiments.
- Full fine-tune on small models (1–3 B) becomes feasible if you really need it.

## Unsloth vs. HF/PEFT — the tradeoff

| Dimension              | Unsloth                                | HF + PEFT                                  |
|------------------------|----------------------------------------|--------------------------------------------|
| Speed (small GPU)      | 2x–5x faster                           | Baseline                                   |
| Memory                 | Lower (~30%)                           | Standard                                   |
| Model coverage         | Targeted (Llama / Mistral / Gemma / Qwen / Phi / SmolLM family) | Almost any architecture                    |
| Custom modifications   | Harder (kernels are bespoke)           | Easier — plain PyTorch underneath          |
| Adapter merging        | Built-in `model.save_pretrained_merged`| `peft.PeftModel.merge_and_unload()`        |
| Quantisation paths     | 4-bit + bf16 well supported            | 4-bit (bitsandbytes), 8-bit, GPTQ via plugins |
| Debugging              | Slightly harder when kernels misfire   | Easier — stack traces land in vanilla code |

Rule of thumb:

- **Speed-first, supported architecture, you do not need custom tricks** -> Unsloth.
- **Architecture not on Unsloth's list, or you need custom forward-pass tweaks** -> HF + PEFT.
- **Production export to GGUF or ONNX** -> either works; HF + PEFT is more battle-tested.

For the seven base models the lab targets (Qwen-small, SmolLM, TinyLlama, Gemma-small, plus three additional compatible SLMs you select), Unsloth covers all of them at the time of writing.

## LoRA vs. QLoRA vs. full finetune

| Approach   | What it touches                                                         | When to use                                    |
|------------|--------------------------------------------------------------------------|------------------------------------------------|
| LoRA       | Trains low-rank deltas on attention and MLP projections; base stays bf16/fp16 in VRAM. | The default. Best quality per GB.              |
| QLoRA      | Base is loaded 4-bit (NF4 quant); LoRA deltas in bf16. Saves ~70% VRAM.  | When the base model would otherwise OOM.       |
| Full FT    | Updates all base weights. Need bf16 + Adam state -> ~5x base size in VRAM. | Only when LoRA quality is provably insufficient. |

For an adapter-routed lab, full finetune is almost always the wrong tool. The whole point of the architecture is small, swappable LoRA modules.

A practical decision tree:

```
Will the base model fit in VRAM with bf16 weights + optimiser + activations?
  Yes -> LoRA
  No  -> Will it fit with 4-bit base?
           Yes -> QLoRA
           No  -> Smaller base model, or smaller batch / shorter seq, then retry
```

## Using the two training scripts

[../scripts/train_unsloth_lora.sh](../scripts/train_unsloth_lora.sh) and [../scripts/train_hf_peft_lora.sh](../scripts/train_hf_peft_lora.sh) (in flight as of v0; see [../TODO.md](../TODO.md)) wrap the two paths. The intended invocations:

```bash
# Dry-run (default — prints resolved config, no GPU needed)
CONFIG=configs/training.yaml DRY_RUN=1 bash scripts/train_unsloth_lora.sh

# Real training (requires GPU and [train] extras)
CONFIG=configs/training.yaml DRY_RUN=0 bash scripts/train_unsloth_lora.sh
```

The scripts are configured via `configs/training.yaml` directly — `max_seq_len`, `batch_size`, `precision`, `lr`, `epochs`, and `target_modules` are all set there. Under the hood the Unsloth variant calls `FastLanguageModel.from_pretrained` + `FastLanguageModel.get_peft_model`.

The HF/PEFT counterpart uses the same env-var pattern and the same `configs/training.yaml`, but drives training via `AutoModelForCausalLM` + `peft.LoraConfig` + `trl.SFTTrainer`:

```bash
# Dry-run
CONFIG=configs/training.yaml DRY_RUN=1 bash scripts/train_hf_peft_lora.sh

# Real training
CONFIG=configs/training.yaml DRY_RUN=0 bash scripts/train_hf_peft_lora.sh
```

Outputs land under `artifacts/training_runs/<adapter_name>/`:

```
adapter_model.safetensors
adapter_config.json
README.md            (auto-generated, includes data card link)
training_args.json
tokenizer_config.json (if changed)
```

A `kde-lab train` CLI subcommand is planned (TODO) that wraps both scripts behind a unified flag set.

## When to merge adapters

`src/training/merge_adapter.py` (in flight) folds a LoRA into the base. The script:

1. Loads base in bf16.
2. Loads the LoRA from the adapter directory.
3. Calls `peft_model.merge_and_unload()`.
4. Saves the merged model.

Merge when:

- You are exporting to **GGUF** for `llama.cpp` / Ollama distribution. Only merged models export cleanly.
- You are shipping to an inference environment that does not support PEFT loading.
- You are publishing a model card and want one self-contained snapshot.

Do *not* merge when:

- You will retrain or swap adapters often. Merging discards the LoRA's compactness.
- You run a router-based deployment. Each adapter stays separate so the router can select.
- You expect to combine multiple adapters at inference (a stretch goal mentioned in chapter 07's footnotes).

## A safe defaults block for v0.1

If you want a starting point you can override:

```yaml
profile: local_24gb
base: <path-to-local-snapshot>      # never auto-downloaded by the lab
quantisation: bf16                  # use 4bit_qlora on local_8gb or smaller
lora:
  r: 16
  alpha: 16
  dropout: 0.05
  target_modules: [q_proj, k_proj, v_proj, o_proj]
optim:
  lr: 1e-4
  warmup_ratio: 0.03
  weight_decay: 0.01
schedule:
  epochs: 3
  per_device_train_batch_size: 8
  gradient_accumulation_steps: 1
  max_seq_len: 4096
mixed_precision: bf16
gradient_checkpointing: true
seed: 42
```

Note `seed: 42` — every learning lab should write its seed down so the runs reproduce.

## Reproducibility checklist

Before you call a run "done":

- [ ] Base model snapshot hash recorded in `metadata.json`.
- [ ] Dataset JSONL hash recorded.
- [ ] Tokenizer hash recorded (file checksum of `tokenizer.json` or `tokenizer.model`).
- [ ] Training args fully serialised to JSON.
- [ ] Eval pass rate per category, plus the full report.
- [ ] Git commit hash of the lab repo.
- [ ] System info: GPU model, CUDA version, driver version.

That eight-item list is the difference between a model card and a model. Both [../scripts/](../scripts/) entries will write the first seven items automatically once v0.1 lands.

## Common failures (specific to local training)

- **OOM at step 0:** mismatch between profile and actual base size. Try the next smaller profile or QLoRA.
- **Loss going to zero too fast:** LR too high or dataset too small (memorisation). Drop LR to 5e-5, add more data, increase weight decay.
- **NaN loss with bf16:** rare but happens on Turing cards. Switch to fp16, or use `bitsandbytes` with the safer optimiser path.
- **Generated text reverts to base style:** you accidentally trained only on `input`, not `output`. Re-check the SFT trainer's `dataset_text_field` and the formatting function.

Chapter [11_failure_modes.md](11_failure_modes.md) covers the deeper failure modes (forgetting, KL collapse, evidence drift). The four above are the ones you hit in the first thirty minutes.

## Exercises

1. Identify your profile. Run `nvidia-smi` and consult the table.
2. Pick a base model. Save its snapshot under `models/<name>/` so the training script reads from local disk only.
3. Estimate the bf16 VRAM footprint of base weights + optimiser + 4096-token activations. Decide whether you need QLoRA.
4. Sketch a minimal `train_hf_peft_lora.py` that loads the SFT JSONL, attaches a LoRA, and trains for one epoch. Compare its arg surface to the planned shell script.
5. After a run, write the eight-item reproducibility block by hand. Identify which item is the most error-prone to record automatically.

## Further reading

- The Unsloth GitHub README and the `unsloth-cli` examples folder.
- The HuggingFace PEFT documentation, particularly `LoraConfig` and `prepare_model_for_kbit_training`.
- *QLoRA: Efficient Finetuning of Quantized LLMs* (Dettmers et al., 2023).
- *LoRA Land* by Predibase for a survey of LoRA quality vs. cost.
- The HuggingFace blog post "A guide to using QLoRA in production".
- The `bitsandbytes` README for 8-bit and 4-bit quantisation details.
- The `llama.cpp` documentation on GGUF conversion if you plan to ship merged models for local inference.
