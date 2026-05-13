#!/usr/bin/env bash
# Create a venv (if missing) and install the lab in editable mode with [dev] extras.
#
# We deliberately do NOT install [train] here. Training pulls torch + bitsandbytes
# + peft + trl which together weigh hundreds of MB and only matter once a learner
# is ready to actually launch a fine-tune. The lab's policy is "recipes only, no
# auto-downloads".
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"

if [ ! -d "${VENV_DIR}" ]; then
    echo "[setup] creating venv at ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
pip install -e ".[dev]"

echo
echo "[setup] dev environment ready in ${VENV_DIR}"
echo
echo "Next steps:"
echo "  source ${VENV_DIR}/bin/activate"
echo "  kde-lab info"
echo "  kde-lab pipeline                 # run the end-to-end mini-repo slice"
echo "  pytest tests/ -q                 # run all tests"
echo "  bash scripts/create_sample_dataset.sh    # generate a small SFT JSONL"
echo "  bash scripts/train_hf_peft_lora.sh       # dry-run an HF/PEFT training plan"
