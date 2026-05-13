#!/usr/bin/env bash
# Grade the RAG baseline against the eval set. v0 only supports the
# rag-baseline; learned models are wired up once training extras are installed.
set -euo pipefail

REPO="${REPO:-mini_kde_repo}"
MODEL_ID="${MODEL_ID:-rag-baseline}"

python -m src.cli.main eval --repo "${REPO}" --model-id "${MODEL_ID}"
