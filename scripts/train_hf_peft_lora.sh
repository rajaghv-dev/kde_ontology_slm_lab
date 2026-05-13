#!/usr/bin/env bash
# Launch (or dry-run) an HF + TRL + PEFT LoRA SFT.
# DRY_RUN=0 to actually train (requires GPU + `pip install -e .[train]`).
set -euo pipefail

CONFIG="${CONFIG:-configs/training.yaml}"
DRY_RUN="${DRY_RUN:-1}"

ARGS=(--config "${CONFIG}")
if [ "${DRY_RUN}" = "1" ]; then
    ARGS+=(--dry-run)
    echo "[train] DRY_RUN=1 — printing resolved config only. Set DRY_RUN=0 to launch."
else
    echo "[train] DRY_RUN=0 — launching real training."
fi

python -m src.training.hf_peft_sft "${ARGS[@]}"
