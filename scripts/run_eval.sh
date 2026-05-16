#!/usr/bin/env bash
# Grade the RAG baseline against the eval set.
#
# v0 only supports model-id=rag-baseline; learned-model eval ships once
# the [train] extras are installed and a real checkpoint exists.
#
# Prerequisites:
#   kde-lab ingest --repo mini_kde_repo   (or `kde-lab pipeline`) must have
#   already run so that artifacts/graphs/mini_kde_repo.json exists.
#
# Usage:
#   bash scripts/run_eval.sh
#   REPO=my_repo MODEL_ID=rag-baseline bash scripts/run_eval.sh
set -euo pipefail

REPO="${REPO:-mini_kde_repo}"
MODEL_ID="${MODEL_ID:-rag-baseline}"

# kde-lab eval --repo <name> --model-id <id>
kde-lab eval --repo "${REPO}" --model-id "${MODEL_ID}"
