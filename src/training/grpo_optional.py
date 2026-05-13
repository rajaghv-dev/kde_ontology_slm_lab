"""GRPO with verifiable, KDE-ontology-grounded rewards.

ADVANCED / OPTIONAL
-------------------
This module is **not** part of the v0 vertical slice. GRPO (Group Relative
Policy Optimisation, the DeepSeek-R1 family) needs:

* A working SFT adapter (otherwise the policy explores garbage).
* A *verifiable* reward signal — preferably one that does not need a judge LM.
* Wall-clock budget to run hundreds of rollouts per gradient step.

We provide GRPO here mainly so a learner can read a complete, runnable
scaffold and see how a "verifiable reward" is structured for a domain-
specific task like KDE Q&A. **Do not pick this path until your SFT model
already beats the RAG baseline on the eval set.**

The reward
----------
``kde_ontology_reward(prompts, completions, **kwargs)`` returns one float per
completion in ``[0, 1]``:

* +1.0 base if the completion mentions at least one *real* KDE entity name
  (one that appears in ``artifacts/ontology/<repo>_entities.jsonl``).
* +0.2 bonus per additional real entity (saturates at 1.0).
* 0.0 if the completion mentions only hallucinated KDE-looking names
  (those starting with K/Q + capital but not in the ontology).

That gives the optimiser a verifiable, file-grounded signal without
needing an LM judge.

``--dry-run`` prints the resolved config and a sample reward score.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from src.common.logging import get_logger
from src.common.paths import ONTOLOGY_DIR
from src.training.lora_config import LoRAConfig


# Token regex: pick up CamelCase identifiers and dotted KDE-style names.
_ENTITY_TOKEN = re.compile(r"[A-Z][A-Za-z0-9_]+(?:::[A-Za-z0-9_]+)*|[a-z][a-z0-9]*(?:\.[a-z0-9]+)+")
# Anything that "looks like" a KDE class is K/Q + Capital letter + tail.
_KDE_LOOKING = re.compile(r"^(?:K|Q|KIO|KConfig)[A-Z][A-Za-z0-9_]*$")


def _load_entity_names(jsonl_path: Path) -> set[str]:
    """Return the set of entity names from an ontology JSONL dump.

    The pipeline writes that file at
    ``artifacts/ontology/<repo>_entities.jsonl`` (see
    ``examples/run_mini_repo_pipeline.py``). If it does not exist yet, we
    return an empty set — the reward then defaults to 0 for everything, which
    is the safe answer for "we have no oracle".
    """
    if not jsonl_path.exists():
        return set()
    out: set[str] = set()
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = rec.get("name") or rec.get("qualified_name")
            if name:
                out.add(name)
    return out


def _score_completion(text: str, real_names: set[str]) -> float:
    """One completion -> reward in [0, 1].

    Pure function; trivially unit-testable. We deliberately do *not* punish
    completions that cite no entity at all — that's just a low signal, not a
    hallucination.
    """
    tokens = set(_ENTITY_TOKEN.findall(text))
    real_hits = {t for t in tokens if t in real_names}
    if not real_hits:
        # Did the model invent KDE-looking names? Penalty by zero reward.
        return 0.0
    reward = 1.0 + 0.2 * (len(real_hits) - 1)
    # Hallucinated KDE-looking names cancel some of the reward.
    hallucinations = {t for t in tokens
                      if _KDE_LOOKING.match(t) and t not in real_names}
    reward -= 0.2 * len(hallucinations)
    return max(0.0, min(1.0, reward))


def kde_ontology_reward(prompts: list[str], completions: list[str],
                        entities_path: Path | None = None,
                        **kwargs) -> list[float]:  # noqa: ARG001 - kwargs for TRL API
    """Return one reward in [0, 1] per ``(prompt, completion)`` pair.

    Signature matches ``trl.GRPOTrainer``'s expected callback shape.
    """
    path = entities_path or (ONTOLOGY_DIR / "mini_repo_entities.jsonl")
    real_names = _load_entity_names(path)
    return [_score_completion(c, real_names) for c in completions]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GRPO with KDE-ontology rewards (advanced).")
    p.add_argument("--config", default="configs/training.yaml")
    p.add_argument("--profile", default=None)
    p.add_argument("--model-key", default=None)
    p.add_argument("--entities", default=None,
                   help="Path to the ontology entities JSONL (defaults to the mini-repo dump).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print resolved config + a sample reward; do not load weights.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log = get_logger("training.grpo")

    cfg = LoRAConfig.from_yaml(Path(args.config),
                               profile_override=args.profile,
                               model_key_override=args.model_key)
    entities_path = Path(args.entities) if args.entities else (ONTOLOGY_DIR / "mini_repo_entities.jsonl")
    n_entities = len(_load_entity_names(entities_path))

    if args.dry_run:
        log.info(f"dry-run: profile={cfg.profile} model_key={cfg.model_key} "
                 f"entities={n_entities} from {entities_path}")
        print(json.dumps(cfg.merged(), indent=2, sort_keys=True))
        sample = "KFileSearcher emits resultsReady and reads MaxResults from KConfig."
        score = kde_ontology_reward(["q"], [sample], entities_path=entities_path)[0]
        print(f"\nsample completion: {sample!r}")
        print(f"sample reward    : {score:.3f}")
        return 0

    # --- Heavy imports, lazy ----------------------------------------------
    try:
        from datasets import load_dataset  # noqa: F401
        from trl import GRPOConfig, GRPOTrainer
    except ImportError as e:  # pragma: no cover - GPU-only path
        log.error(f"GRPO needs trl>=0.11 with GRPO support: {e}")
        return 2

    # NOTE: This scaffold intentionally stops short of wiring a full training
    # loop. GRPO setup involves picking a base policy (your SFT adapter),
    # configuring rollouts, and managing KL with a frozen reference model —
    # all of which require a real model on a real GPU. A learner promoting
    # this from scaffold to runner should fill in the GRPOConfig + dataset
    # plumbing below, then call ``GRPOTrainer(model, reward_funcs=[kde_ontology_reward], ...).train()``.
    log.warning("GRPO live run is not wired in v0; this is an intentional scaffold. "
                "Use --dry-run to validate the reward function.")
    _ = (GRPOConfig, GRPOTrainer)  # silence unused-import in scaffolds
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
