"""The whitespace fallback tokenizer should run offline and report a
reasonable compression ratio on the canonical KDE term list.
"""
from src.tokenizer.analyze_tokens import KDE_TERMS, analyze, worst_terms


def test_analyze_runs_offline():
    rep = analyze()
    assert rep.tokenizer_name == "whitespace-fallback"
    assert len(rep.terms) == len(KDE_TERMS)
    summary = rep.summary()
    assert summary["mean_compression"] > 0


def test_worst_terms_sorted_ascending():
    rep = analyze()
    worst = worst_terms(rep, n=3)
    assert len(worst) == 3
    assert worst[0].compression <= worst[-1].compression
