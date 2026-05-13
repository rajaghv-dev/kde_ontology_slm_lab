"""Round-trip tests for the in-memory cosine vector store.

These tests use synthetic vectors so they pass with no model downloads.
"""
from __future__ import annotations

import numpy as np

from src.rag.vector_store import VectorStore


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def test_add_and_query_returns_self():
    store = VectorStore(dim=4)
    v = _unit(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))
    store.add("a", v, {"name": "alpha"})
    hits = store.query(v, k=1)
    assert hits[0][0] == "a"
    assert hits[0][2]["name"] == "alpha"
    assert hits[0][1] > 0.99  # cosine ~= 1


def test_query_orders_by_similarity():
    store = VectorStore(dim=3)
    store.add("close", _unit(np.array([1.0, 0.1, 0.0])), {})
    store.add("far",   _unit(np.array([0.0, 0.0, 1.0])), {})
    store.add("mid",   _unit(np.array([0.7, 0.7, 0.0])), {})
    hits = store.query(_unit(np.array([1.0, 0.0, 0.0])), k=3)
    # "close" should rank above "mid" which ranks above "far".
    ids = [h[0] for h in hits]
    assert ids[0] == "close"
    assert ids.index("mid") < ids.index("far")


def test_query_handles_empty_store():
    store = VectorStore(dim=3)
    out = store.query(np.array([1.0, 0.0, 0.0]), k=5)
    assert out == []


def test_add_many_bulk_insert():
    store = VectorStore(dim=2)
    mat = np.stack([_unit(np.array([1.0, 0.0])),
                    _unit(np.array([0.0, 1.0])),
                    _unit(np.array([1.0, 1.0]))]).astype(np.float32)
    store.add_many(["x", "y", "z"], mat, [{"n": "x"}, {"n": "y"}, {"n": "z"}])
    assert len(store) == 3


def test_dim_mismatch_raises():
    store = VectorStore(dim=4)
    try:
        store.add("bad", np.zeros(3, dtype=np.float32))
    except ValueError:
        return
    raise AssertionError("expected ValueError on dim mismatch")


def test_save_and_load_roundtrip(tmp_path):
    store = VectorStore(dim=3)
    store.add("a", _unit(np.array([1.0, 0.0, 0.0])), {"name": "alpha"})
    store.add("b", _unit(np.array([0.0, 1.0, 0.0])), {"name": "beta"})
    p = store.save(tmp_path / "store.npz")
    assert p.exists()

    loaded = VectorStore.load(p)
    assert loaded.dim == 3
    assert len(loaded) == 2

    hits = loaded.query(_unit(np.array([1.0, 0.0, 0.0])), k=1)
    assert hits[0][0] == "a"
    assert hits[0][2]["name"] == "alpha"
