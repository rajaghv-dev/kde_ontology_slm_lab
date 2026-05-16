#!/usr/bin/env bash
# Two-step export: LoRA merge -> GGUF quantise.
#
# DRY-RUN BY DEFAULT — no real weights are touched until you opt in.
#
# This script is a documented stub. Real export requires:
#   1. pip install -e .[train]          (adds peft + transformers)
#   2. A trained LoRA adapter checkpoint in ADAPTER (run scripts/train_hf_peft_lora.sh first)
#   3. A real base_model id in configs/models.yaml (replace the CHANGE_ME placeholder)
#   4. llama.cpp's convert_hf_to_gguf.py on PATH, or set --llamacpp to its directory
#
# Environment variables (all optional, shown with defaults):
#   ADAPTER        path to the LoRA adapter dir   (artifacts/training_runs/v0_qwen_sft)
#   MERGED_OUT     path for merged HF weights      (artifacts/training_runs/v0_qwen_merged)
#   GGUF_OUT       path for the output GGUF file   (artifacts/exports/v0_qwen.Q4_K_M.gguf)
#   QUANT          quantisation type               (Q4_K_M)
#   DRY_RUN_MERGE  1 = skip merge, 0 = do merge   (1)
#   DRY_RUN_GGUF   1 = skip gguf,  0 = do gguf    (1)
#
# Usage:
#   bash scripts/export_model.sh                            # dry-run both steps
#   DRY_RUN_MERGE=0 bash scripts/export_model.sh            # real merge, dry gguf
#   DRY_RUN_MERGE=0 DRY_RUN_GGUF=0 bash scripts/export_model.sh  # full export
set -euo pipefail

ADAPTER="${ADAPTER:-artifacts/training_runs/v0_qwen_sft}"
MERGED_OUT="${MERGED_OUT:-artifacts/training_runs/v0_qwen_merged}"
GGUF_OUT="${GGUF_OUT:-artifacts/exports/v0_qwen.Q4_K_M.gguf}"
QUANT="${QUANT:-Q4_K_M}"

DRY_RUN_MERGE="${DRY_RUN_MERGE:-1}"
DRY_RUN_GGUF="${DRY_RUN_GGUF:-1}"

mkdir -p "$(dirname "${GGUF_OUT}")"

MERGE_ARGS=(--adapter "${ADAPTER}" --out "${MERGED_OUT}")
if [ "${DRY_RUN_MERGE}" = "1" ]; then
    MERGE_ARGS+=(--dry-run)
fi

GGUF_ARGS=(--hf-dir "${MERGED_OUT}" --out "${GGUF_OUT}" --quant "${QUANT}")
if [ "${DRY_RUN_GGUF}" = "1" ]; then
    GGUF_ARGS+=(--dry-run)
fi

echo "[export] step 1/2 — merge_adapter (dry_run=${DRY_RUN_MERGE})"
python -m src.training.merge_adapter "${MERGE_ARGS[@]}"

echo "[export] step 2/2 — export_gguf  (dry_run=${DRY_RUN_GGUF})"
python -m src.training.export_gguf "${GGUF_ARGS[@]}"

echo
echo "[export] done."
if [ "${DRY_RUN_MERGE}" = "1" ] || [ "${DRY_RUN_GGUF}" = "1" ]; then
    echo "[export] one or both steps ran in dry-run mode."
    echo "[export] set DRY_RUN_MERGE=0 and/or DRY_RUN_GGUF=0 to actually export."
fi
