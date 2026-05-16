# Code Quality Audit

_Generated: 2026-05-16. Based on direct source inspection._

---

## Lint results

`ruff` is declared as a `[dev]` extra but is not installed in the system Python used for
this audit session. Lint results are inferred from source reading.

Ruff config (`pyproject.toml`): `select = ["E", "F", "I", "W", "B", "UP"]`, `ignore = ["E501"]`
Line length: 100.

Likely clean: no unused imports found by inspection, `from __future__ import annotations`
present in all modules, consistent use of type hints.

One explicit suppression found: `src/common/logging.py:29` — `# type: ignore[assignment]`
(LoggerAdapter return-type mismatch; acceptable workaround).

---

## Module structure findings

| Area | Finding | Evidence | Risk | Suggested refactor | Priority |
|---|---|---|---|---|---|
| `run_mini_repo_pipeline.py` vs `ingest_cmd` | Pipeline writes `_entities.jsonl` but NOT `_relations.jsonl`; `kde-lab graph` silently loads 0 relations | `examples/run_mini_repo_pipeline.py:~115` writes only entities; `src/cli/ingest_cmd.py:91-92` writes both | Medium — `kde-lab graph` after the pipeline produces an edge-free graph | Add `write_jsonl(rel_path, [r.__dict__ for r in bundle.relations])` to `run_mini_repo_pipeline.py` | P1 |
| `from_desktop` self-loop | `from_desktop` adds a `REGISTERS_SERVICE` edge from `did` to `did` (self-loop) | `src/ontology/extractor.py:237-238` | Low — self-loops are valid in MultiDiGraph but may confuse path queries | Store an explicit `DesktopService` entity or use a property instead | P2 |
| `src/common/logging.py` global mutable | Uses `global _CONFIGURED` — not thread-safe if modules ever parallelize | `src/common/logging.py:12, 18` | Low — current code is single-threaded | Use `logging.basicConfig(force=False)` or a module-level `_setup_once` lock | P3 |
| `graph_cmd` graceful on missing relations | `graph_cmd.py:31` checks `if rel_path.exists()` before loading relations — good pattern, but silently produces a graph with 0 edges if ingest was run via the pipeline script | `src/cli/graph_cmd.py:27-34` | Medium — silent degradation, no warning emitted | Add a `log.warning(f"no relations JSONL at {rel_path}")` | P2 |
| `src/rag/embeddings.py` hash quality | `HashingEmbedder` uses SHA-256 truncated to `dim//32` bytes → 32-bit chunks. For `dim=128` this gives 4 meaningful components from the full hash — low-entropy embedding | `src/rag/embeddings.py` | Low — documented as intentional offline stub | Fine as-is; document clearly in code (already has a comment) | P3 |
| No CLI tests | 6 CLI subcommand modules (`ingest`, `graph`, `tokenizer`, `dataset`, `train`, `eval`) have zero test coverage | `tests/` has no `test_cli*.py` | High — CLI is user-facing; bugs here are invisible | Add at minimum a `test_cli_smoke.py` that invokes `CliRunner` from Click | P1 |
| `conftest.py` uses `sys.path.insert` | `tests/conftest.py` mutates sys.path rather than relying on editable install | `tests/conftest.py` | Low — works, but may mask packaging issues | Remove once `pip install -e .` is part of CI setup | P3 |
| `src/training/*` all stubs | 7 training modules are importable but produce no real artifacts without GPU + weights | All `src/training/*.py` | Known / documented | Fine; ensure `train_router.py` is the only one tested | None |
| `src/observability/metrics.py` 272 lines | Largest file; mixes Prometheus and JSONL backends in one class hierarchy | `src/observability/metrics.py` | Low — well-structured, works | Could split `_Prom*` wrappers to a separate file, but not urgent | P3 |
| `numpy` missing from `requirements.txt` | `requirements.txt` lists base deps but omits `numpy>=1.26` which is a direct dep of `src/rag/vector_store.py`, `src/rag/hybrid_search.py`, `src/rag/embeddings.py` | `requirements.txt`; `pyproject.toml` has it | Low — `pyproject.toml` covers it; `requirements.txt` is the gap | Add `numpy>=1.26` to `requirements.txt` | P2 |

---

## Dead code / unused imports

By inspection: none found. Every import in the core modules is used. The
`# type: ignore[assignment]` in `logging.py:29` suppresses a mypy false-positive, not a real issue.

The `from src.common.ids import make_id` import appears in both `run_mini_repo_pipeline.py`
and throughout the pipeline — all used.

---

## Missing tests

Modules in `src/` with no corresponding test file:

| Module | Test file | Gap |
|---|---|---|
| `src/cli/ingest_cmd.py` | None | All CLI commands untested |
| `src/cli/graph_cmd.py` | None | ditto |
| `src/cli/tokenizer_cmd.py` | None | ditto |
| `src/cli/dataset_cmd.py` | None | ditto |
| `src/cli/train_cmd.py` | None | ditto |
| `src/cli/eval_cmd.py` | None | ditto |
| `src/cli/main.py` | None | `info` command untested |
| `src/dataset/jsonl_writer.py` (`read_jsonl`) | `test_dataset_jsonl_schema.py` tests write; `read_jsonl` is not tested | Medium |
| `src/rag/context_builder.py` | `test_context_builder.py` exists | Covered |
| `src/training/lora_config.py` | None | Stubs; low priority |
| `src/training/merge_adapter.py` | None | Stubs; low priority |
| `src/training/grpo_optional.py` | None | Stubs; low priority |
| `src/training/hf_peft_sft.py` | None | Stubs; low priority |
| `src/training/unsloth_sft.py` | None | Stubs; low priority |
| `src/training/export_gguf.py` | None | Stubs; low priority |

---

## TODOs found in code

No `TODO`, `FIXME`, `HACK`, or `XXX` comments found in `src/`. TODOs are tracked in
the top-level `TODO.md` file (by design — documented in README).

---

## Requirements consistency

`requirements.txt` (minimum runtime):
```
networkx>=3.0  pyyaml>=6.0  click>=8.1  tqdm>=4.66  rich>=13.0
```

`pyproject.toml` core dependencies:
```
networkx>=3.0  numpy>=1.26  pyyaml>=6.0  click>=8.1  tqdm>=4.66  rich>=13.0
```

**Gap:** `numpy>=1.26` is in `pyproject.toml` but absent from `requirements.txt`.
The RAG vector store and hybrid search modules both `import numpy` directly.
A user doing `pip install -r requirements.txt` (instead of `pip install -e .`) would
get an `ImportError` when running the RAG modules.

---

## Summary

The codebase is clean and well-structured for a v0 learning lab. No security issues, no
dead code, no circular imports. The main quality gaps are:

1. **P1 — Missing CLI tests:** All 6 subcommands are untested. A `CliRunner`-based smoke
   test would catch regressions immediately.
2. **P1 — Pipeline-vs-CLI artifact gap:** `run_mini_repo_pipeline.py` does not write the
   `_relations.jsonl` file that `kde-lab graph` depends on.
3. **P2 — numpy in requirements.txt:** Minor packaging inconsistency.
4. **P2 — Silent edge-free graph warning:** `graph_cmd` should warn when relations JSONL
   is absent.
5. **P2 — `from_desktop` self-loop:** Cosmetic design issue in the extractor.

---

## Top 5 priority actions

| # | Action | File | Priority |
|---|---|---|---|
| 1 | Add `write_jsonl` for relations in `run_mini_repo_pipeline.py` | `examples/run_mini_repo_pipeline.py` | P1 |
| 2 | Add `tests/test_cli_smoke.py` using Click `CliRunner` | new file | P1 |
| 3 | Add `numpy>=1.26` to `requirements.txt` | `requirements.txt` | P2 |
| 4 | Add `log.warning` in `graph_cmd` when relations JSONL is absent | `src/cli/graph_cmd.py` | P2 |
| 5 | Add CI workflow (`.github/workflows/validate.yml`) | new file | P1 (handled by Phase 9 agent) |
