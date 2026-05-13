"""Grade an answer against an eval item.

The grader returns a structured record so the report module can roll it up
into category-level metrics.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GradeResult:
    item_id: str
    category: str
    mention_recall: float    # fraction of must_mention substrings present
    forbidden_hit: bool      # True if any must_not_mention substring is present
    passed: bool             # mention_recall == 1.0 and not forbidden_hit


def grade(answer_text: str, item: dict) -> GradeResult:
    text = answer_text.lower()
    must = item.get("must_mention", []) or []
    must_not = item.get("must_not_mention", []) or []
    hits = sum(1 for m in must if m.lower() in text)
    recall = hits / len(must) if must else 1.0
    forbidden = any(m.lower() in text for m in must_not)
    passed = recall >= 1.0 and not forbidden
    return GradeResult(
        item_id=item["id"], category=item.get("category", "?"),
        mention_recall=recall, forbidden_hit=forbidden, passed=passed,
    )
