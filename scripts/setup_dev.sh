#!/usr/bin/env bash
# Create a venv (if missing) and install the lab in editable mode with [dev] extras.
#
# We deliberately do NOT install [train] here. Training pulls torch + bitsandbytes
# + peft + trl which together weigh hundreds of MB and only matter once a learner
# is ready to actually launch a fine-tune. The lab's policy is "recipes only, no
# auto-downloads".
#
# Usage:
#   bash scripts/setup_dev.sh            # normal interactive setup
#   CI=1 bash scripts/setup_dev.sh       # skip venv creation (GitHub Actions)
#   VENV_DIR=my_venv bash scripts/setup_dev.sh
set -euo pipefail

# ── helpers ──────────────────────────────────────────────────────────────────
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
red()    { printf '\033[0;31m%s\033[0m\n' "$*" >&2; }

# ── Python version guard ──────────────────────────────────────────────────────
PY_CMD="${PYTHON:-python3}"

if ! command -v "${PY_CMD}" >/dev/null 2>&1; then
    red "[setup] '${PY_CMD}' not found. Install Python >= 3.10 first."
    exit 1
fi

PY_VERSION="$("${PY_CMD}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="${PY_VERSION%%.*}"
PY_MINOR="${PY_VERSION#*.}"

if [ "${PY_MAJOR}" -lt 3 ] || { [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -lt 10 ]; }; then
    red "[setup] Python ${PY_VERSION} detected — need >= 3.10. Aborting."
    exit 1
fi

yellow "[setup] Python ${PY_VERSION} — OK"

# ── CI mode: skip venv ────────────────────────────────────────────────────────
# Set CI=1 (GitHub Actions sets this automatically) to skip venv creation.
# The caller (Actions runner / tox / nox) manages the interpreter itself.
CI="${CI:-0}"

if [ "${CI}" = "1" ]; then
    yellow "[setup] CI mode — skipping venv creation, installing into active environment"
    "${PY_CMD}" -m pip install --upgrade pip --quiet
    "${PY_CMD}" -m pip install -e ".[dev]" --quiet
else
    VENV_DIR="${VENV_DIR:-.venv}"

    if [ ! -d "${VENV_DIR}" ]; then
        yellow "[setup] creating venv at ${VENV_DIR}"
        "${PY_CMD}" -m venv "${VENV_DIR}"
    else
        yellow "[setup] reusing existing venv at ${VENV_DIR}"
    fi

    # shellcheck disable=SC1090
    source "${VENV_DIR}/bin/activate"

    python -m pip install --upgrade pip --quiet
    pip install -e ".[dev]" --quiet
fi

# ── smoke-test the CLI ────────────────────────────────────────────────────────
yellow "[setup] verifying CLI …"
kde-lab info

# ── success banner ────────────────────────────────────────────────────────────
echo
green "╔══════════════════════════════════════════════════════════╗"
green "║  kde_ontology_slm_lab dev environment ready              ║"
green "╚══════════════════════════════════════════════════════════╝"
echo

if [ "${CI}" != "1" ]; then
    echo "  source ${VENV_DIR}/bin/activate"
fi
echo "  kde-lab pipeline                          # end-to-end mini-repo slice"
echo "  pytest tests/ -q                          # run all tests"
echo "  bash scripts/create_sample_dataset.sh     # generate a small SFT JSONL"
echo "  bash scripts/run_eval.sh                  # grade the RAG baseline"
echo "  bash scripts/train_hf_peft_lora.sh        # dry-run an HF/PEFT training plan"
echo
