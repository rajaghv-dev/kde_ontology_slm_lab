"""Export a merged HF checkpoint to a quantised GGUF for llama.cpp / Ollama.

This script is a thin wrapper around two tools from the llama.cpp repo:

* ``convert_hf_to_gguf.py``  — converts HF format to .gguf
* ``llama-quantize``         — quantises a fp16 .gguf to e.g. Q4_K_M

If those tools are not found on ``PATH`` (and ``--llamacpp`` is not given),
we print the equivalent manual commands and exit 0. The lab's policy is
"recipes only, no auto-downloads" — we do not git-clone llama.cpp for you.

Quantisation defaults
---------------------
* ``Q4_K_M`` is the modern sweet spot for small models on CPU/edge: ~30% of
  fp16 size, ~1-2% perplexity hit. ``Q5_K_M`` is the next step up if RAM
  allows. ``Q8_0`` is essentially lossless but ~50% of fp16.

Run:
    python -m src.training.export_gguf \
        --hf-dir artifacts/training_runs/v0_qwen_merged \
        --out artifacts/exports/v0_qwen.Q4_K_M.gguf
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from src.common.logging import get_logger


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert + quantise a merged HF model to GGUF.")
    p.add_argument("--hf-dir", default="artifacts/training_runs/v0_qwen_merged",
                   help="Directory containing the merged HF model (output of merge_adapter).")
    p.add_argument("--out", default="artifacts/exports/v0_qwen.Q4_K_M.gguf",
                   help="Destination path for the quantised .gguf file.")
    p.add_argument("--quant", default="Q4_K_M",
                   help="llama-quantize type. Q4_K_M is the modern default.")
    p.add_argument("--llamacpp", default=None,
                   help="Path to a llama.cpp checkout. Used to find convert_hf_to_gguf.py.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the commands that would run and exit 0.")
    return p.parse_args(argv)


def _find_convert_script(llamacpp_dir: str | None) -> Path | None:
    if llamacpp_dir:
        cand = Path(llamacpp_dir) / "convert_hf_to_gguf.py"
        return cand if cand.exists() else None
    found = shutil.which("convert_hf_to_gguf.py")
    return Path(found) if found else None


def _find_quantize() -> str | None:
    # Modern binary is `llama-quantize`; older builds shipped `quantize`.
    return shutil.which("llama-quantize") or shutil.which("quantize")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log = get_logger("training.export_gguf")

    hf_dir = Path(args.hf_dir)
    out = Path(args.out)
    fp16_gguf = out.with_suffix(".fp16.gguf")

    convert = _find_convert_script(args.llamacpp)
    quantize = _find_quantize()

    cmds = [
        ["python", str(convert) if convert else "convert_hf_to_gguf.py",
         str(hf_dir), "--outfile", str(fp16_gguf), "--outtype", "f16"],
        [quantize or "llama-quantize", str(fp16_gguf), str(out), args.quant],
    ]

    if args.dry_run or not convert or not quantize:
        if not convert or not quantize:
            log.warning("llama.cpp tools not found on PATH; printing manual commands.")
        print("# 1. Clone llama.cpp once:")
        print("#    git clone https://github.com/ggerganov/llama.cpp && cd llama.cpp && make")
        print("# 2. Convert HF -> fp16 gguf:")
        print("   " + " ".join(cmds[0]))
        print("# 3. Quantise fp16 gguf -> " + args.quant + ":")
        print("   " + " ".join(cmds[1]))
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    log.info(f"converting {hf_dir} -> {fp16_gguf}")
    subprocess.run(cmds[0], check=True)
    log.info(f"quantising -> {out} ({args.quant})")
    subprocess.run(cmds[1], check=True)
    log.info(f"export complete: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
