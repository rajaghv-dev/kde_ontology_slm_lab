"""`kde-lab train` — placeholder for the LoRA training loop.

Why a placeholder?
    Launching a real training run requires (a) the [train] extras
    (torch, peft, trl, bitsandbytes), (b) downloaded base-model weights,
    and (c) a GPU. The lab's policy is "recipes only, no auto-downloads",
    so we print the resolved recipe and exit. Wiring the actual loop is
    deliberate, opt-in work in src/training/.
"""
from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("train", help="Print the training recipe that would run. Does not launch training.")
    @click.option("--profile", "profile_override", default=None,
                  help="Override `profile:` from configs/training.yaml (e.g. colab_t4, local_24gb).")
    @click.option("--model-key", "model_key_override", default=None,
                  help="Override `model_key:` from configs/training.yaml.")
    def train(profile_override: str | None, model_key_override: str | None) -> None:
        import json

        from src.common.config import deep_merge, load_yaml
        from src.common.logging import get_logger
        from src.common.paths import CONFIGS

        log = get_logger("cli.train")

        cfg = load_yaml(CONFIGS / "training.yaml")
        models = load_yaml(CONFIGS / "models.yaml").get("models", {}) or {}

        profile = profile_override or cfg.get("profile", "local_8gb")
        model_key = model_key_override or cfg.get("model_key")

        profile_overlay = (cfg.get("profiles", {}) or {}).get(profile, {})
        resolved = deep_merge(
            {k: v for k, v in cfg.items() if k != "profiles"},
            profile_overlay,
        )
        resolved["profile"] = profile
        resolved["model_key"] = model_key
        resolved["resolved_model_entry"] = models.get(model_key, {})

        click.echo("kde-lab train (dry-run — no training launched in v0)")
        click.echo("-" * 60)
        click.echo(json.dumps(resolved, indent=2, sort_keys=True))
        click.echo("")
        click.echo("To actually train, install the [train] extra, supply a real "
                   "base_model id in configs/models.yaml, and implement the loop "
                   "in src/training/.")
        log.info(f"dry-run for profile={profile} model_key={model_key}")
