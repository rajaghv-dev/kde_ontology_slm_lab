"""The context builder must be deterministic and budget-respecting."""
from __future__ import annotations

from src.rag.context_builder import (
    build_context,
    build_context_blocks,
    estimate_tokens,
)


def _sample_evidence(n: int) -> list[dict]:
    return [{
        "name": f"KClass{i}",
        "type": "CppClass",
        "file": f"src/kclass{i}.cpp",
        "line": 10 + i,
        "relation": "DEFINES",
        "confidence": 0.8,
    } for i in range(n)]


def test_estimate_tokens_basic():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") > 0
    # Longer input -> more tokens.
    assert estimate_tokens("a b c d e f g h") > estimate_tokens("a b")


def test_build_context_is_deterministic():
    ev = _sample_evidence(5)
    a = build_context(ev, max_tokens=200)
    b = build_context(ev, max_tokens=200)
    assert a == b
    # And the citation indices are stable [1], [2], ...
    for i in range(1, 6):
        assert f"[{i}]" in a


def test_build_context_respects_budget():
    ev = _sample_evidence(20)
    out = build_context(ev, max_tokens=40)
    # Should have stopped well short of all 20 entries.
    cited = sum(1 for i in range(1, 21) if f"[{i}]" in out)
    assert cited < 20
    assert cited >= 1
    # Token estimate of the produced string should not exceed the budget.
    assert estimate_tokens(out) <= 40 + estimate_tokens("Evidence:")


def test_build_context_zero_budget_returns_empty():
    assert build_context(_sample_evidence(3), max_tokens=0) == ""


def test_build_context_blocks_match_string_version():
    ev = _sample_evidence(8)
    blocks = build_context_blocks(ev, max_tokens=80)
    rendered = build_context(ev, max_tokens=80)
    # Each block's rank should appear in the rendered string.
    for b in blocks:
        assert f"[{b.rank}]" in rendered
    # Token totals should not exceed the budget.
    assert sum(b.tokens for b in blocks) <= 80
