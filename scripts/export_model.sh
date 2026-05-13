#!/usr/bin/env bash
# Two-step export: LoRA merge -> GGUF quantise.
#
# By default both steps run as --dry-run (no weights touched). Toggle either
# step via DRY_RUN_MERGE / DRY_RUN_GGUF (set to 0 to actually run).
#
# Real merge needs `pip install -e .[train]` and a real base_model id in
# configs/models.yaml. Real GGUF needs a llama.cpp checkout on PATH (or via
# --llamacpp).
set -euo pipefail

ADAPTER="${ADAPTER:-artifacts/training_runs/v0_qwen_sft}"
MERGED_OUT="${MERGED_OUT:-artifacts/training_runs/v0_qwen_merged}"
GGUF_OUT="${GGUF_OUT:-artifacts/exports/v0_qwen.Q4_K_M.gguf}"
QUANT="${QUANT:-Q4_K_M}"

DRY_RUN_MERGE="${DRY_RUN_MERGE:-1}"
DRY_RUN_GGUF="${DRY_RUN_GGUF:-1}"

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
echo "[export] done. Set DRY_RUN_MERGE=0 and/or DRY_RUN_GGUF=0 to actually export."
