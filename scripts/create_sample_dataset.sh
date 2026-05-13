#!/usr/bin/env bash
# Generate a small SFT JSONL by running the dataset CLI against the saved
# mini-repo graph. Cap the record count so the file fits on a chapter slide.
set -euo pipefail

OUT="${OUT:-artifacts/datasets/sample.jsonl}"
N="${N:-50}"

mkdir -p "$(dirname "${OUT}")"

python -m src.cli.main dataset --n "${N}" --out "${OUT}"

echo
echo "[dataset] wrote sample dataset to ${OUT}"
if command -v wc >/dev/null 2>&1; then
    echo "[dataset] lines: $(wc -l < "${OUT}")"
fi
