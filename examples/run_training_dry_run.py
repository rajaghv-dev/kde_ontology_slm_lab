"""Show what a training launch would do, without launching anything.

This wraps ``src.training.hf_peft_sft`` in ``--dry-run`` mode. It is the
recommended first thing a learner runs after editing ``configs/training.yaml``
or ``configs/models.yaml``: it prints the fully resolved recipe and exits.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.training.hf_peft_sft import main as sft_main


def main(argv: list[str] | None = None) -> int:
    extra = list(argv) if argv is not None else sys.argv[1:]
    if "--dry-run" not in extra:
        extra.append("--dry-run")
    return sft_main(extra)


if __name__ == "__main__":
    raise SystemExit(main())
