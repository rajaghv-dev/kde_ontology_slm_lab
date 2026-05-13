"""Pluggable embedding-model interface.

Why this exists
---------------
Vector RAG is part of the lab, but the lab must run *offline*. So the default
:class:`HashingEmbedder` produces deterministic embeddings from a feature-
hashing trick — no model download, no torch, no network. It is bad at
semantic similarity but excellent at letting a learner exercise the whole
``embed -> index -> retrieve`` pipeline before they invest in a real encoder.

When a learner *does* want real embeddings, the
:class:`SentenceTransformersEmbedder` shim lazy-imports
``sentence_transformers`` and raises a clear, actionable error if it is
not installed.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np

_WS_RE = re.compile(r"[A-Za-z0-9_]+")


class Embedder(Protocol):
    """Anything that maps text -> numpy float32 vector of fixed dimension."""

    @property
    def dim(self) -> int: ...

    def embed(self, text: str) -> np.ndarray: ...

    def embed_many(self, texts: list[str]) -> np.ndarray: ...


@dataclass
class HashingEmbedder:
    """Deterministic offline embedder via a signed feature-hashing trick.

    Algorithm (cheap, well-understood, zero deps beyond numpy):

    1. Tokenise the text on word boundaries.
    2. For each token, compute ``h = blake2b(token, digest_size=8)`` and split
       it into a *bucket index* (mod ``dim``) and a *sign* (one bit).
    3. Increment the bucket by the signed weight.
    4. L2-normalise the resulting vector so cosine similarity is well-defined.

    Why blake2b? It's in the stdlib, fast, and ``digest_size=8`` keeps the
    hash work negligible per call.
    """
    dim_: int = 256
    lowercase: bool = True

    @property
    def dim(self) -> int:
        return self.dim_

    def _tokens(self, text: str) -> list[str]:
        s = text.lower() if self.lowercase else text
        return _WS_RE.findall(s)

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim_, dtype=np.float32)
        for tok in self._tokens(text):
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            # First 4 bytes -> bucket; 5th byte's low bit -> sign.
            bucket = int.from_bytes(h[:4], "big") % self.dim_
            sign = 1.0 if (h[4] & 1) else -1.0
            vec[bucket] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0.0 and math.isfinite(norm):
            vec /= norm
        return vec

    def embed_many(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim_), dtype=np.float32)
        return np.stack([self.embed(t) for t in texts], axis=0)


class SentenceTransformersEmbedder:
    """Lazy-loaded ``sentence-transformers`` wrapper.

    We do **not** import ``sentence_transformers`` at module load — the
    library is heavy (pulls torch + transformers). The import happens on
    first ``embed()`` so the rest of the lab keeps booting fast.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None  # lazy
        self._dim: int | None = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as e:  # pragma: no cover - exercised only when installed
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install it with `pip install sentence-transformers` and rerun. "
                "If you want to stay offline, use HashingEmbedder instead."
            ) from e
        self._model = SentenceTransformer(self.model_name)
        # MiniLM-L6-v2 is 384-d; we just ask the model.
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        self._ensure_loaded()
        assert self._dim is not None
        return self._dim

    def embed(self, text: str) -> np.ndarray:  # pragma: no cover - needs network
        self._ensure_loaded()
        vec = self._model.encode([text], normalize_embeddings=True)[0]  # type: ignore[union-attr]
        return np.asarray(vec, dtype=np.float32)

    def embed_many(self, texts: list[str]) -> np.ndarray:  # pragma: no cover
        self._ensure_loaded()
        out = self._model.encode(texts, normalize_embeddings=True)  # type: ignore[union-attr]
        return np.asarray(out, dtype=np.float32)


def default_embedder() -> Embedder:
    """The lab's default. Offline, deterministic, no downloads."""
    return HashingEmbedder()
