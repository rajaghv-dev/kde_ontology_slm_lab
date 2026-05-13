"""Aggregate GradeResults into a JSON + Markdown report."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from src.eval.answer_grader import GradeResult


def aggregate(results: list[GradeResult]) -> dict:
    by_cat: dict[str, list[GradeResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    overall_pass = sum(1 for r in results if r.passed) / max(1, len(results))
    overall_recall = mean(r.mention_recall for r in results) if results else 0.0
    per_cat = {
        cat: {
            "n": len(rs),
            "pass_rate": sum(1 for r in rs if r.passed) / len(rs),
            "mean_recall": mean(r.mention_recall for r in rs),
            "forbidden_hits": sum(1 for r in rs if r.forbidden_hit),
        }
        for cat, rs in by_cat.items()
    }
    return {
        "n": len(results),
        "overall_pass_rate": overall_pass,
        "overall_mean_recall": overall_recall,
        "per_category": per_cat,
    }


def to_markdown(report: dict) -> str:
    lines = ["# Eval report", "",
             f"- N: **{report['n']}**",
             f"- Overall pass rate: **{report['overall_pass_rate']:.2%}**",
             f"- Overall mean recall: **{report['overall_mean_recall']:.2%}**",
             "", "| Category | N | Pass rate | Mean recall | Forbidden hits |",
             "|---|---|---|---|---|"]
    for cat, m in sorted(report["per_category"].items()):
        lines.append(f"| {cat} | {m['n']} | {m['pass_rate']:.2%} | "
                     f"{m['mean_recall']:.2%} | {m['forbidden_hits']} |")
    return "\n".join(lines) + "\n"


def save(report: dict, out_dir: Path, name: str = "report") -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jp = out_dir / f"{name}.json"
    mp = out_dir / f"{name}.md"
    with jp.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with mp.open("w", encoding="utf-8") as f:
        f.write(to_markdown(report))
    return jp, mp
