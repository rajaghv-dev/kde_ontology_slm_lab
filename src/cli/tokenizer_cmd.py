"""`kde-lab tokenizer` — run the token-cost analyzer and surface the worst terms."""
from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("tokenizer", help="Run the offline tokenizer analyzer; print the 5 worst terms.")
    @click.option("--report-path", "report_path", default=None,
                  help="Override the JSON report path (default from configs/tokenizer.yaml).")
    def tokenizer(report_path: str | None) -> None:
        from pathlib import Path

        from src.common.config import load_yaml
        from src.common.logging import get_logger
        from src.common.paths import CONFIGS, REPO_ROOT, TOKENIZER_DIR, ensure_dirs
        from src.tokenizer.analyze_tokens import analyze, save_report, worst_terms

        log = get_logger("cli.tokenizer")
        ensure_dirs()

        cfg = load_yaml(CONFIGS / "tokenizer.yaml")
        analyze_cfg = cfg.get("analyze", {}) or {}

        # Resolve where the report should land. CLI flag > config > default.
        if report_path:
            out = Path(report_path)
        elif analyze_cfg.get("report_path"):
            rp = Path(analyze_cfg["report_path"])
            out = rp if rp.is_absolute() else REPO_ROOT / rp
        else:
            out = TOKENIZER_DIR / "v0.json"

        log.info("running offline-fallback tokenizer analyzer")
        rep = analyze()                 # uses KDE_TERMS / KDE_PHRASES from analyze_tokens.py
        saved = save_report(rep, out)

        summary = rep.summary()
        click.echo(f"tokenizer            : {rep.tokenizer_name}")
        click.echo(f"mean compression     : {summary.get('mean_compression', 0):.2f} chars/token")
        click.echo(f"mean tokens per term : {summary.get('mean_tokens_per_term', 0):.2f}")
        click.echo(f"report               : {saved}")
        click.echo("")
        click.echo("worst 5 terms (lowest chars/token):")
        for tc in worst_terms(rep, n=5):
            click.echo(f"  - {tc.term!r:50s}  tokens={tc.tokens:3d}  "
                       f"chars={tc.chars:3d}  compression={tc.compression:.2f}")
