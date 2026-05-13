"""QLoRA recipe — LoRA on top of a 4-bit-quantised frozen base model.

QLoRA = LoRA + ``bitsandbytes`` 4-bit (NF4) base. The trainable adapter is
still fp16/bf16, but the base weights stay quantised in memory. On an 8GB
GPU that is the difference between "can't load Qwen-0.5B" and "can train
3 epochs in an hour".

This module is a thin wrapper around :class:`src.training.lora_config.LoRAConfig`
that adds the ``BitsAndBytesConfig``-style fields. The values mirror the
defaults Tim Dettmers' QLoRA paper recommends and that ``bitsandbytes`` /
``transformers`` accept verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.training.lora_config import LoRAConfig


@dataclass
class QLoRAConfig:
    """LoRA hyperparameters + the 4-bit base-quantisation knobs.

    ``base`` is the standard LoRA recipe (rank, alpha, optim, etc.). The
    extra fields are exactly what you would pass to
    ``transformers.BitsAndBytesConfig``.
    """
    base: LoRAConfig
    load_in_4bit: bool = True
    bnb_4bit_compute_dtype: str = "bfloat16"   # accepted by transformers as a string
    bnb_4bit_quant_type: str = "nf4"           # "nf4" or "fp4"; nf4 is the QLoRA default
    bnb_4bit_use_double_quant: bool = True     # an extra ~0.4 bits/param of savings

    @classmethod
    def from_yaml(cls, path: Path | str,
                  profile_override: str | None = None,
                  model_key_override: str | None = None) -> "QLoRAConfig":
        base = LoRAConfig.from_yaml(path, profile_override=profile_override,
                                    model_key_override=model_key_override)
        # If the YAML explicitly turns off 4-bit, honour that. Otherwise QLoRA's
        # whole point is to keep it on.
        return cls(base=base, load_in_4bit=bool(base.load_in_4bit))

    def merged(self) -> dict[str, Any]:
        out = self.base.merged()
        out["bnb"] = {
            "load_in_4bit": self.load_in_4bit,
            "bnb_4bit_compute_dtype": self.bnb_4bit_compute_dtype,
            "bnb_4bit_quant_type": self.bnb_4bit_quant_type,
            "bnb_4bit_use_double_quant": self.bnb_4bit_use_double_quant,
        }
        return out


# A convenience factory for callers who already hold a LoRAConfig.
def from_lora(base: LoRAConfig) -> QLoRAConfig:
    """Wrap an existing LoRAConfig with the QLoRA defaults."""
    return QLoRAConfig(base=base, load_in_4bit=True)
