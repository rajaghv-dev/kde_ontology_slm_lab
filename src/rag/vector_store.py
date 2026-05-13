"""An in-memory cosine-similarity vector index over numpy arrays.

Why not FAISS / Chroma in v0?
-----------------------------
The lab's corpus is tiny — a single mini KDE repo has ~150 entities. A
linear-scan cosine search over a (N, D) numpy matrix is well under a
millisecond at that scale, and it has *zero* dependencies beyond numpy.

FAISS adds a 100+ MB binary, Chroma adds a sqlite layer + onnxruntime, and
neither makes the lab's experiments faster at this corpus size. When a
learner graduates to a real KDE checkout (10k+ entities), swapping this
module for FAISS is the next obvious upgrade — and the public interface
here (``add`` / ``query`` / ``save`` / ``load``) is exactly what FAISS
exposes too, so the swap is local.

Persistence is via ``numpy.savez_compressed``: vectors as one array, ids +
payloads as a JSON sidecar embedded in the same archive. Re-loading is
zero-copy where possible.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class VectorStore:
    """An exact-cosine in-memory index. Use for corpora up to ~10k vectors.

    Vectors should be L2-normalised when added (the default embedders in
    ``src.rag.embeddings`` already do this). If they are not, the resulting
    scores are *dot products*, not true cosines.
    """
    dim: int
    ids: list[str] = field(default_factory=list)
    payloads: list[dict] = field(default_factory=list)
    _matrix: np.ndarray | None = None  # shape (N, dim), float32

    # ----------------------------------------------------------------- add
    def add(self, id_: str, vector: np.ndarray, payload: dict | None = None) -> None:
        """Append one vector. Vectors must have length ``self.dim``."""
        v = np.asarray(vector, dtype=np.float32).reshape(-1)
        if v.shape[0] != self.dim:
            raise ValueError(f"vector dim {v.shape[0]} != index dim {self.dim}")
        self.ids.append(id_)
        self.payloads.append(dict(payload or {}))
        if self._matrix is None:
            self._matrix = v[np.newaxis, :].copy()
        else:
            self._matrix = np.vstack([self._matrix, v[np.newaxis, :]])

    def add_many(self, ids: list[str], vectors: np.ndarray,
                 payloads: list[dict] | None = None) -> None:
        """Bulk insert — much faster than calling ``add`` in a loop."""
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(f"expected (N, {self.dim}) matrix; got {vectors.shape}")
        if len(ids) != vectors.shape[0]:
            raise ValueError("ids and vectors must have the same length")
        pls = payloads or [{} for _ in ids]
        self.ids.extend(ids)
        self.payloads.extend([dict(p) for p in pls])
        if self._matrix is None:
            self._matrix = vectors.astype(np.float32, copy=True)
        else:
            self._matrix = np.vstack([self._matrix, vectors.astype(np.float32, copy=False)])

    # --------------------------------------------------------------- query
    def query(self, vector: np.ndarray, k: int = 5) -> list[tuple[str, float, dict]]:
        """Return the top-``k`` (id, score, payload) triples by cosine.

        If the index is empty we return ``[]``. We do *not* raise on
        empty — that lets callers like ``hybrid_search`` treat the vector
        leg as "no contribution" without try/except.
        """
        if self._matrix is None or self._matrix.shape[0] == 0:
            return []
        q = np.asarray(vector, dtype=np.float32).reshape(-1)
        if q.shape[0] != self.dim:
            raise ValueError(f"query dim {q.shape[0]} != index dim {self.dim}")
        scores = self._matrix @ q  # (N,) — exact dot product
        # Argsort descending; ``k`` may exceed N, that's fine.
        k = min(k, scores.shape[0])
        top = np.argpartition(-scores, kth=k - 1)[:k] if k > 1 else np.array([int(np.argmax(scores))])
        top = top[np.argsort(-scores[top])]
        return [(self.ids[i], float(scores[i]), dict(self.payloads[i])) for i in top.tolist()]

    # ------------------------------------------------------------ persist
    def save(self, path: Path | str) -> Path:
        """Persist the index as a single ``.npz`` archive."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        meta = {"dim": self.dim, "ids": self.ids, "payloads": self.payloads}
        np.savez_compressed(
            p,
            matrix=(self._matrix if self._matrix is not None
                    else np.zeros((0, self.dim), dtype=np.float32)),
            meta=np.array(json.dumps(meta), dtype=object),
        )
        return p

    @classmethod
    def load(cls, path: Path | str) -> "VectorStore":
        """Re-create a VectorStore previously written by :meth:`save`."""
        p = Path(path)
        with np.load(p, allow_pickle=True) as data:
            meta_blob = data["meta"]
            meta_str = str(meta_blob.item() if meta_blob.shape == () else meta_blob)
            meta: dict[str, Any] = json.loads(meta_str)
            matrix = np.asarray(data["matrix"], dtype=np.float32)
        store = cls(dim=int(meta["dim"]),
                    ids=list(meta.get("ids", [])),
                    payloads=[dict(x) for x in meta.get("payloads", [])])
        store._matrix = matrix if matrix.size else None
        return store

    # ------------------------------------------------------------- helpers
    def __len__(self) -> int:
        return len(self.ids)
