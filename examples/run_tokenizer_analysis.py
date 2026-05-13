"""Run a KDE-term token-cost analysis with the offline fallback tokenizer.

A learner reads this script to see, in one screen, what
``src.tokenizer.analyze_tokens.analyze`` produces. The output report lands
in ``artifacts/tokenizer_reports/`` and is also surfaced to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.logging import get_logger
from src.common.paths import TOKENIZER_DIR, ensure_dirs
from src.tokenizer.analyze_tokens import analyze, save_report, worst_terms


def main() -> int:
    ensure_dirs()
    log = get_logger("examples.tokenizer_analysis")

    rep = analyze()
    out = save_report(rep, TOKENIZER_DIR / "offline_tokenizer_report.json")
    summary = rep.summary()
    worst = worst_terms(rep, n=5)

    log.info(f"wrote tokenizer report to {out}")
    print(json.dumps({"summary": summary, "report_path": str(out)}, indent=2))
    print("\nWorst-compressing terms (chars per token, lower is worse):")
    for tc in worst:
        print(f"  - {tc.term:<48s}  {tc.chars:>3d} chars / {tc.tokens:>3d} tok  "
              f"= {tc.compression:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
