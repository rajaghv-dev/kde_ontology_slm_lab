"""Resolve a LoRA training profile from ``configs/training.yaml``.

The YAML uses a *defaults + profiles* shape (see the file's own header for
why). This module turns that shape into a single flat ``LoRAConfig`` object
that downstream scripts can hand directly to ``peft.LoraConfig`` /
``trl.SFTConfig`` without re-parsing.

Resolution order (matches the YAML's contract):

    1. start with the top-level keys ("defaults")
    2. look up ``profile:`` in the ``profiles:`` map
    3. deep-merge that profile over the defaults

There is no implicit network access here; this is pure config plumbing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.common.config import deep_merge, load_yaml


@dataclass
class LoRAConfig:
    """A resolved LoRA recipe. Field names mirror the YAML keys so a learner
    can grep from one to the other without translation.
    """
    profile: str = "local_8gb"
    model_key: str = "qwen_small"
    dataset_path: str = "artifacts/datasets/mini_repo_sft_v0.jsonl"
    output_dir: str = "artifacts/training_runs/v0_qwen_sft"
    max_seq_length: int = 2048
    load_in_4bit: bool = True
    adapter_name: str = "kde_adapter_v0"
    packing: bool = False
    train_on_responses_only: bool = True

    # nested dicts: kept as plain dicts so we don't lose forward-compatible keys
    lora: dict[str, Any] = field(default_factory=lambda: {
        "r": 16, "alpha": 32, "dropout": 0.05, "target_modules": "all-linear",
    })
    optim: dict[str, Any] = field(default_factory=lambda: {
        "learning_rate": 2.0e-4, "batch_size": 1,
        "gradient_accumulation_steps": 16, "num_train_epochs": 3,
        "warmup_steps": 50, "weight_decay": 0.01,
        "lr_scheduler_type": "cosine", "logging_steps": 10,
        "eval_steps": 100, "save_steps": 200, "seed": 42,
    })

    # ----------------------------------------------------------------- loaders
    @classmethod
    def from_yaml(cls, path: Path | str, profile_override: str | None = None,
                  model_key_override: str | None = None) -> "LoRAConfig":
        """Load + resolve the active profile, returning a flat ``LoRAConfig``.

        ``profile_override`` and ``model_key_override`` mirror the CLI flags so
        an experimentation script can swap profiles without editing YAML.
        """
        raw = load_yaml(Path(path))
        defaults = {k: v for k, v in raw.items() if k != "profiles"}
        profiles = raw.get("profiles", {}) or {}

        profile = profile_override or defaults.get("profile", "local_8gb")
        overlay = profiles.get(profile, {}) or {}
        resolved = deep_merge(defaults, overlay)

        # Apply overrides last so they always win.
        resolved["profile"] = profile
        if model_key_override:
            resolved["model_key"] = model_key_override

        return cls(
            profile=resolved.get("profile", "local_8gb"),
            model_key=resolved.get("model_key", "qwen_small"),
            dataset_path=resolved.get("dataset_path", ""),
            output_dir=resolved.get("output_dir", ""),
            max_seq_length=int(resolved.get("max_seq_length", 2048)),
            load_in_4bit=bool(resolved.get("load_in_4bit", True)),
            adapter_name=resolved.get("adapter_name", "kde_adapter_v0"),
            packing=bool(resolved.get("packing", False)),
            train_on_responses_only=bool(resolved.get("train_on_responses_only", True)),
            lora=dict(resolved.get("lora", {}) or {}),
            optim=dict(resolved.get("optim", {}) or {}),
        )

    # -------------------------------------------------------------- materialise
    def merged(self) -> dict[str, Any]:
        """Return the fully resolved config as a flat dict.

        The shape is friendly to ``peft.LoraConfig(**cfg.merged()["lora"])``
        and ``transformers.TrainingArguments(**cfg.merged()["optim"])``; we
        do not actually call those here (lazy-import policy).
        """
        return {
            "profile": self.profile,
            "model_key": self.model_key,
            "dataset_path": self.dataset_path,
            "output_dir": self.output_dir,
            "max_seq_length": self.max_seq_length,
            "load_in_4bit": self.load_in_4bit,
            "adapter_name": self.adapter_name,
            "packing": self.packing,
            "train_on_responses_only": self.train_on_responses_only,
            "lora": dict(self.lora),
            "optim": dict(self.optim),
        }
