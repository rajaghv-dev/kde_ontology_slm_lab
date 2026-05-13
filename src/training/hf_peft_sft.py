"""Supervised fine-tuning via Hugging Face ``transformers`` + ``trl`` + ``peft``.

Why this path exists
--------------------
The HF stack is the broadest-supported way to do LoRA SFT on a small model.
It works on every architecture the lab targets (Qwen, SmolLM, TinyLlama,
Gemma, Phi). Unsloth (see ``unsloth_sft.py``) is faster on 4-bit but more
brittle across families; this script is the reliable baseline.

Order of operations
-------------------
1. Resolve ``configs/training.yaml`` into a flat :class:`LoRAConfig`.
2. (heavy import) Load tokenizer + base model, optionally in 4-bit.
3. Build ``peft.LoraConfig`` from the resolved ``lora`` block.
4. Build ``trl.SFTConfig`` from the resolved ``optim`` block.
5. Stream the JSONL dataset (one record per line; fields: ``instruction``,
   ``output``, optional ``input``).
6. ``trl.SFTTrainer.train()``, then ``model.save_pretrained(output_dir)``.

``--dry-run`` skips steps 2-6: it just prints the resolved config. This is
how the lab's CI exercises the script without GPUs or weights.

Run it:

    python -m src.training.hf_peft_sft --config configs/training.yaml --dry-run
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.common.logging import get_logger
from src.training.lora_config import LoRAConfig


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LoRA SFT via HF + TRL + PEFT.")
    p.add_argument("--config", default="configs/training.yaml",
                   help="Path to the training YAML.")
    p.add_argument("--profile", default=None,
                   help="Override `profile:` from the YAML (e.g. colab_t4).")
    p.add_argument("--model-key", default=None,
                   help="Override `model_key:` from the YAML.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the resolved config and exit. Does NOT load weights or data.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log = get_logger("training.hf_peft_sft")

    cfg = LoRAConfig.from_yaml(Path(args.config),
                               profile_override=args.profile,
                               model_key_override=args.model_key)
    resolved = cfg.merged()

    if args.dry_run:
        log.info(f"dry-run: profile={cfg.profile} model_key={cfg.model_key}")
        print(json.dumps(resolved, indent=2, sort_keys=True))
        print()
        print("Dry run complete. Re-run without --dry-run to launch training "
              "(requires the [train] extra and a real base_model id).")
        return 0

    # --- Heavy imports, lazy on purpose ------------------------------------
    try:
        import torch  # noqa: F401
        from datasets import load_dataset
        from peft import LoraConfig
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
        from trl import SFTConfig, SFTTrainer
    except ImportError as e:  # pragma: no cover - exercised only on a GPU host
        log.error(f"missing training extras: {e}. Install with `pip install -e .[train]`.")
        return 2

    # Resolve the actual HF model id from configs/models.yaml.
    from src.common.config import load_yaml
    from src.common.paths import CONFIGS
    models = load_yaml(CONFIGS / "models.yaml").get("models", {}) or {}
    entry = models.get(cfg.model_key, {})
    base_model = entry.get("base_model", "")
    if not base_model or "CHANGE_ME" in base_model:
        log.error(f"models.yaml entry for {cfg.model_key!r} is unset ({base_model!r}). "
                  "Pin a real HF id before training.")
        return 3

    # 1. tokenizer + base model
    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = None
    if cfg.load_in_4bit:
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype="bfloat16",
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        base_model, quantization_config=bnb, device_map="auto",
    )

    # 2. LoRA + SFT configs
    lora_cfg = LoraConfig(
        r=int(cfg.lora.get("r", 16)),
        lora_alpha=int(cfg.lora.get("alpha", 32)),
        lora_dropout=float(cfg.lora.get("dropout", 0.05)),
        target_modules=cfg.lora.get("target_modules", "all-linear"),
        task_type="CAUSAL_LM",
    )
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

    # 3. dataset (JSONL with instruction/input/output)
    ds = load_dataset("json", data_files=cfg.dataset_path, split="train")

    def fmt(rec: dict) -> dict:
        instruction = rec.get("instruction", "")
        extra = rec.get("input", "") or ""
        prompt = instruction + ("\n\n" + extra if extra else "")
        return {"text": f"{prompt}\n\n{rec.get('output', '')}"}

    ds = ds.map(fmt, remove_columns=[c for c in ds.column_names if c != "text"])

    # 4. train + save
    trainer = SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=ds,
                         peft_config=lora_cfg, args=sft_cfg)
    trainer.train()
    trainer.save_model(cfg.output_dir)
    log.info(f"adapter saved to {cfg.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
