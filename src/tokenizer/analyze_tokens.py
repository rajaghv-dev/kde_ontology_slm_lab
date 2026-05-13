"""Tokenizer analysis with an offline fallback.

The lab is meant to run without downloading anything. So this module:

1. Defines a *canonical KDE term list* (see ``KDE_TERMS`` and ``KDE_PHRASES``)
   that the analyzer always measures.
2. Provides a ``WhitespaceFallbackTokenizer`` that does CamelCase / snake_case /
   dot-namespace splitting in pure Python. It is not a great tokenizer but it
   produces a meaningful baseline.
3. If a Hugging Face tokenizer is provided (by name *and* available locally,
   or as a loaded object), it is used instead.

A token-cost report counts tokens per term and computes a compression ratio
versus the raw character count. The report is consumed by:
- the dataset generator (to decide whether to add a token sentinel)
- the documentation (chapter 05_tokenizer_strategy.md)
- the optional notebook (notebooks/05_tokenizer_analysis.ipynb)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


# --- Canonical term list ---------------------------------------------------
KDE_TERMS: list[str] = [
    "KFilePlacesModel", "KDirLister", "KIO::Job", "KIO::StatJob",
    "KConfigGroup", "KSharedConfig", "KConfigXT", "KStandardDirs",
    "QFileSystemModel", "QStandardPaths", "QString", "QStringList",
    "Q_OBJECT", "Q_PROPERTY", "Q_SIGNALS", "Q_SLOTS",
    "qmlRegisterType", "qCDebug", "qCWarning",
    "org.kde.KWin", "org.kde.plasmashell", "org.kde.minisearch",
    "kded6", "plasmashell", "kwin_wayland", "kwin_x11", "Baloo",
    "kcoreaddons_add_plugin", "ecm_setup_version",
    "CMakeLists.txt", "find_package", "target_link_libraries",
]

KDE_PHRASES: list[str] = [
    "connect(sender, &Sender::signal, receiver, &Receiver::slot)",
    "journalctl --user -u plasma-plasmashell",
    "qdbus org.kde.minisearch /minisearch searchPath /home query",
    "ctest --output-on-failure -R minisearch",
    "qmlRegisterType<KFileSearcher>(\"org.kde.minisearch\", 1, 0, \"KFileSearcher\")",
]

CAMEL_SPLIT = re.compile(r"(?<!^)(?=[A-Z])")
TOKENISH = re.compile(r"[A-Za-z][A-Za-z0-9]*|[<>:.()\"&,;=/-]")


class TokenizerLike(Protocol):
    def encode(self, text: str) -> list[int]: ...
    def __len__(self) -> int: ...


@dataclass
class WhitespaceFallbackTokenizer:
    """Reasonable offline baseline that splits on whitespace, CamelCase, snake_case,
    dot, and a handful of C++ punctuation. Returns ints by mapping each piece
    to a stable integer derived from hashing.
    """
    name: str = "whitespace-fallback"
    vocab: dict[str, int] = field(default_factory=dict)

    def _split(self, text: str) -> list[str]:
        out: list[str] = []
        for chunk in text.split():
            for piece in TOKENISH.findall(chunk):
                # split CamelCase
                for sub in CAMEL_SPLIT.split(piece):
                    if "_" in sub:
                        out.extend(s for s in sub.split("_") if s)
                    elif "." in sub:
                        out.extend(s for s in sub.split(".") if s)
                    elif sub:
                        out.append(sub.lower())
        return out

    def encode(self, text: str) -> list[int]:
        pieces = self._split(text)
        ids: list[int] = []
        for p in pieces:
            if p not in self.vocab:
                self.vocab[p] = len(self.vocab) + 1
            ids.append(self.vocab[p])
        return ids

    def __len__(self) -> int:
        return len(self.vocab)


# --- Report shape ----------------------------------------------------------

@dataclass
class TermCost:
    term: str
    chars: int
    tokens: int
    compression: float  # chars / tokens, higher is better

    @classmethod
    def from_text(cls, term: str, ids: list[int]) -> "TermCost":
        chars = len(term)
        toks = max(1, len(ids))
        return cls(term=term, chars=chars, tokens=toks, compression=chars / toks)


@dataclass
class TokenCostReport:
    tokenizer_name: str
    terms: list[TermCost] = field(default_factory=list)
    phrases: list[TermCost] = field(default_factory=list)

    def summary(self) -> dict[str, float]:
        all_items = self.terms + self.phrases
        if not all_items:
            return {"mean_compression": 0.0, "mean_tokens_per_term": 0.0}
        return {
            "mean_compression": sum(t.compression for t in all_items) / len(all_items),
            "mean_tokens_per_term": sum(t.tokens for t in all_items) / len(all_items),
            "worst_terms": min(t.compression for t in all_items),
            "best_terms": max(t.compression for t in all_items),
        }

    def to_json(self) -> dict:
        return {
            "tokenizer": self.tokenizer_name,
            "summary": self.summary(),
            "terms": [t.__dict__ for t in self.terms],
            "phrases": [t.__dict__ for t in self.phrases],
        }


def analyze(tokenizer: TokenizerLike | None = None,
            terms: list[str] | None = None,
            phrases: list[str] | None = None) -> TokenCostReport:
    tok = tokenizer or WhitespaceFallbackTokenizer()
    name = getattr(tok, "name", tok.__class__.__name__)
    rep = TokenCostReport(tokenizer_name=name)
    for t in (terms if terms is not None else KDE_TERMS):
        ids = tok.encode(t)
        rep.terms.append(TermCost.from_text(t, ids))
    for p in (phrases if phrases is not None else KDE_PHRASES):
        ids = tok.encode(p)
        rep.phrases.append(TermCost.from_text(p, ids))
    return rep


def save_report(rep: TokenCostReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rep.to_json(), f, indent=2)
    return path


def worst_terms(rep: TokenCostReport, n: int = 5) -> list[TermCost]:
    return sorted(rep.terms + rep.phrases, key=lambda t: t.compression)[:n]
