"""Fold a LoRA adapter back into its base model weights.

Why merge
---------
* **No PEFT at inference**: a merged checkpoint is a plain HF model. Anything
  that loads ``AutoModelForCausalLM.from_pretrained`` will work — vLLM, TGI,
  llama.cpp's ``convert_hf_to_gguf.py``, MLX, you name it.
* **One model, one path**: makes downstream packaging (GGUF, ONNX) simpler.

Cost
----
* **Disk**: you now store the *full* base-size weights (e.g. ~1 GB for a 0.5B
  fp16 model) on top of the original base. The LoRA adapter is typically
  10-50 MB; the merged file is the size of the base.
* **Quantisation interaction**: merging a LoRA into a 4-bit base requires
  first up-casting the base to fp16/bf16, then re-quantising downstream
  (e.g. via ``export_gguf``). The merge step itself runs in fp16.

Run:
    python -m src.training.merge_adapter \
        --base Qwen/Qwen2.5-0.5B-Instruct \
        --adapter artifacts/training_runs/v0_qwen_sft \
        --out artifacts/training_runs/v0_qwen_merged
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.common.logging import get_logger


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge a PEFT LoRA adapter into its base model.")
    p.add_argument("--base", default=None,
                   help="HF id or local path of the base model. If omitted, read from configs/models.yaml.")
    p.add_argument("--adapter", default="artifacts/training_runs/v0_qwen_sft",
                   help="Directory containing the saved PEFT adapter.")
    p.add_argument("--out", default="artifacts/training_runs/v0_qwen_merged",
                   help="Output directory for the merged HF model.")
    p.add_argument("--config", default="configs/training.yaml",
                   help="Training YAML used only to look up the default base model.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print resolved paths and exit; do not load weights.")
    return p.parse_args(argv)


def _resolve_base(config_path: Path, override: str | None) -> str:
    if override:
        return override
    from src.common.config import load_yaml
    from src.common.paths import CONFIGS
    cfg = load_yaml(config_path)
    model_key = cfg.get("model_key", "qwen_small")
    models = load_yaml(CONFIGS / "models.yaml").get("models", {}) or {}
    return models.get(model_key, {}).get("base_model", "")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log = get_logger("training.merge_adapter")

    base = _resolve_base(Path(args.config), args.base)
    adapter = Path(args.adapter)
    out = Path(args.out)

    plan = {
        "base_model": base,
        "adapter_dir": str(adapter),
        "out_dir": str(out),
    }
    log.info(f"merge plan: {plan}")

    if args.dry_run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        print("\nDry run only. To actually merge, install [train] extras and re-run without --dry-run.")
        return 0

    if not base or "CHANGE_ME" in base:
        log.error(f"base model is unset ({base!r}). Pin a real HF id in configs/models.yaml first.")
        return 2

    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:  # pragma: no cover
        log.error(f"missing extras: {e}. Install with `pip install -e .[train]`.")
        return 3

    log.info(f"loading base {base}")
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype="auto")
    tokenizer = AutoTokenizer.from_pretrained(base, use_fast=True)

    log.info(f"loading adapter from {adapter}")
    model = PeftModel.from_pretrained(model, str(adapter))

    log.info("merging and unloading adapter")
    merged = model.merge_and_unload()

    out.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(out)
    tokenizer.save_pretrained(out)
    log.info(f"merged model written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
