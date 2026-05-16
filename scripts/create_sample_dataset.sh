#!/usr/bin/env bash
# Generate a small SFT JSONL by running the dataset CLI against the saved
# mini-repo graph. Cap the record count so the file fits on a chapter slide.
#
# Prerequisites:
#   kde-lab ingest --repo mini_kde_repo   (or `kde-lab pipeline`) must have
#   already run so that artifacts/graphs/mini_kde_repo.json exists.
#
# Usage:
#   bash scripts/create_sample_dataset.sh
#   N=100 OUT=artifacts/datasets/custom.jsonl bash scripts/create_sample_dataset.sh
set -euo pipefail

OUT="${OUT:-artifacts/datasets/sample.jsonl}"
N="${N:-50}"
REPO="${REPO:-mini_kde_repo}"

mkdir -p "$(dirname "${OUT}")"

# kde-lab dataset --repo <name> [--n <limit>] [--out <path>]
kde-lab dataset --repo "${REPO}" --n "${N}" --out "${OUT}"

echo
echo "[dataset] wrote sample dataset to ${OUT}"
if command -v wc >/dev/null 2>&1; then
    echo "[dataset] lines: $(wc -l < "${OUT}")"
fi
