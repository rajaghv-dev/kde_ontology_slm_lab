"""Format retrieved evidence into a prompt-ready context string.

Contract
--------
* **Deterministic**: same evidence list in -> same string out. No timestamps,
  no random tie-breaking.
* **Budgeted**: caller passes ``max_tokens``; we never exceed it.
* **Citation-ready**: each entry is prefixed with ``[i]`` so the downstream
  model can refer to it.

Token estimation
----------------
We do not need a real tokenizer here; the goal is a *soft* budget so we
don't blow past a model's context window. Counting whitespace tokens with
a small upward bias is good enough — typical subword tokenizers produce
1.2-1.5 tokens per whitespace token on technical English. We use 1.3x.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

_WS_TOK = re.compile(r"\S+")
_TOKEN_FUDGE = 1.3  # whitespace tokens -> subword tokens (rough English)


def estimate_tokens(text: str) -> int:
    """Cheap upper-ish bound on subword-token count.

    Pure function, deterministic. Empty / whitespace strings count as 0.
    """
    if not text:
        return 0
    return int(len(_WS_TOK.findall(text)) * _TOKEN_FUDGE) + 1


@dataclass
class ContextBlock:
    """One piece of evidence as the prompt will see it."""
    rank: int          # 1-based position in the context
    text: str          # the rendered line(s) for this evidence
    tokens: int        # estimated token cost


def _render_evidence(rank: int, ev: Mapping) -> str:
    """Render one evidence dict as a single citation line.

    The exact shape of ``ev`` matches what ``src.rag.answer_with_evidence`` and
    ``src.rag.hybrid_search`` produce, but we accept any mapping with at
    least a ``name`` or ``symbol`` field.
    """
    name = ev.get("name") or ev.get("symbol") or ev.get("id") or "<unknown>"
    type_ = ev.get("type", "")
    file_ = ev.get("file", "")
    line = ev.get("line", 0)
    rel = ev.get("relation", "")
    conf = ev.get("confidence", None)

    loc = f"{file_}:{line}" if file_ else "<no-source>"
    parts = [f"[{rank}] "]
    if type_:
        parts.append(f"{type_} ")
    parts.append(f"`{name}`")
    parts.append(f" - {loc}")
    if rel:
        parts.append(f" (rel={rel}")
        if conf is not None:
            parts.append(f", conf={float(conf):.2f}")
        parts.append(")")
    elif conf is not None:
        parts.append(f" (conf={float(conf):.2f})")
    return "".join(parts)


def build_context(
    evidence: Iterable[Mapping],
    max_tokens: int = 512,
    header: str = "Evidence:",
) -> str:
    """Produce a budgeted, deterministic context string.

    Evidence items are appended in iteration order. As soon as adding the
    next item would exceed ``max_tokens``, we stop. We never truncate
    inside a citation — that would break the ``[i]`` referencing contract.
    """
    if max_tokens <= 0:
        return ""

    lines: list[str] = [header]
    used = estimate_tokens(header)

    for i, ev in enumerate(evidence, start=1):
        line = _render_evidence(i, ev)
        cost = estimate_tokens(line)
        if used + cost > max_tokens:
            break
        lines.append(line)
        used += cost

    return "\n".join(lines)


def build_context_blocks(
    evidence: Iterable[Mapping],
    max_tokens: int = 512,
    header: str = "Evidence:",
) -> list[ContextBlock]:
    """Same budgeted selection, but returns structured blocks instead of a string.

    Handy for tests that want to assert on per-block token cost without
    re-parsing the string. The ``header`` argument participates in the
    budget exactly the same way it does in :func:`build_context`, so the
    two helpers agree on how many evidence items fit.
    """
    out: list[ContextBlock] = []
    used = estimate_tokens(header) if header else 0
    for i, ev in enumerate(evidence, start=1):
        line = _render_evidence(i, ev)
        cost = estimate_tokens(line)
        if used + cost > max_tokens:
            break
        out.append(ContextBlock(rank=i, text=line, tokens=cost))
        used += cost
    return out
