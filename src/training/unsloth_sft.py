"""Supervised fine-tuning via Unsloth's ``FastLanguageModel``.

Why a learner might pick Unsloth
--------------------------------
* **Speed**: Unsloth's custom Triton kernels give a 1.5-2x throughput win
  over vanilla HF on 4-bit LoRA, and it cuts VRAM usage by ~30% by patching
  cross-entropy and rope.
* **Single API**: ``FastLanguageModel.from_pretrained(...)`` returns model +
  tokenizer with bitsandbytes 4-bit already wired up.
* **Sweet spot**: Llama, Qwen, Mistral, Gemma, Phi families on a single
  consumer GPU.

Why a learner might pick the HF/PEFT path (see ``hf_peft_sft.py``) instead
-------------------------------------------------------------------------
* **Coverage**: HF + PEFT works on essentially every model on the Hub; Unsloth
  supports a curated list.
* **Familiarity**: the HF stack is what most tutorials, papers, and bug
  reports assume.
* **Debuggability**: when the kernel-level optimisations bite back, plain
  PyTorch is easier to introspect.

Order of operations mirrors ``hf_peft_sft`` exactly so the two scripts can
be diffed side-by-side:

    1. Resolve ``configs/training.yaml`` -> :class:`LoRAConfig`.
    2. (heavy) ``FastLanguageModel.from_pretrained`` (4-bit by default).
    3. ``FastLanguageModel.get_peft_model`` from the resolved LoRA block.
    4. ``trl.SFTTrainer`` + ``trl.SFTConfig`` from the resolved optim block.
    5. Stream the JSONL dataset.
    6. ``trainer.train()`` -> save adapter.

``--dry-run`` skips steps 2-6.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.common.logging import get_logger
from src.training.lora_config import LoRAConfig


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LoRA SFT via Unsloth FastLanguageModel.")
    p.add_argument("--config", default="configs/training.yaml")
    p.add_argument("--profile", default=None)
    p.add_argument("--model-key", default=None)
    p.add_argument("--dry-run", action="store_true",
                   help="Print resolved config and exit. No weights or data are loaded.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log = get_logger("training.unsloth_sft")

    cfg = LoRAConfig.from_yaml(Path(args.config),
                               profile_override=args.profile,
                               model_key_override=args.model_key)
    resolved = cfg.merged()

    if args.dry_run:
        log.info(f"dry-run: profile={cfg.profile} model_key={cfg.model_key}")
        print(json.dumps(resolved, indent=2, sort_keys=True))
        print()
        print("Unsloth dry run complete. Real training requires the unsloth "
              "extra (`pip install unsloth`) and a GPU.")
        return 0

    # --- Heavy imports, lazy on purpose ------------------------------------
    try:
        from datasets import load_dataset
        from trl import SFTConfig, SFTTrainer
        from unsloth import FastLanguageModel
    except ImportError as e:  # pragma: no cover - exercised only on a GPU host
        log.error(f"missing extras: {e}. Install unsloth and trl to launch training.")
        return 2

    from src.common.config import load_yaml
    from src.common.paths import CONFIGS
    models = load_yaml(CONFIGS / "models.yaml").get("models", {}) or {}
    entry = models.get(cfg.model_key, {})
    base_model = entry.get("base_model", "")
    if not base_model or "CHANGE_ME" in base_model:
        log.error(f"models.yaml entry for {cfg.model_key!r} is unset.")
        return 3

    # 1. model + tokenizer in one call
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=cfg.max_seq_length,
        load_in_4bit=cfg.load_in_4bit,
    )

    # 2. attach LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=int(cfg.lora.get("r", 16)),
        lora_alpha=int(cfg.lora.get("alpha", 32)),
        lora_dropout=float(cfg.lora.get("dropout", 0.05)),
        target_modules=cfg.lora.get("target_modules", "all-linear"),
    )

    # 3. dataset
    ds = load_dataset("json", data_files=cfg.dataset_path, split="train")

    def fmt(rec: dict) -> dict:
        instruction = rec.get("instruction", "")
        extra = rec.get("input", "") or ""
        prompt = instruction + ("\n\n" + extra if extra else "")
        return {"text": f"{prompt}\n\n{rec.get('output', '')}"}

    ds = ds.map(fmt, remove_columns=[c for c in ds.column_names if c != "text"])

    # 4. SFT
    sft_cfg = SFTConfig(
        output_dir=cfg.output_dir,
        per_device_train_batch_size=int(cfg.optim.get("batch_size", 1)),
        gradient_accumulation_steps=int(cfg.optim.get("gradient_accumulation_steps", 16)),
        num_train_epochs=int(cfg.optim.get("num_train_epochs", 3)),
        learning_rate=float(cfg.optim.get("learning_rate", 2e-4)),
        warmup_steps=int(cfg.optim.get("warmup_steps", 50)),
        weight_decay=float(cfg.optim.get("weight_decay", 0.01)),
        lr_scheduler_type=cfg.optim.get("lr_scheduler_type", "cosine"),
        logging_steps=int(cfg.optim.get("logging_steps", 10)),
        save_steps=int(cfg.optim.get("save_steps", 200)),
        seed=int(cfg.optim.get("seed", 42)),
        packing=cfg.packing,
        max_seq_length=cfg.max_seq_length,
    )

    trainer = SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=ds, args=sft_cfg)
    trainer.train()
    trainer.save_model(cfg.output_dir)
    log.info(f"unsloth adapter saved to {cfg.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
