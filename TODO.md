# TODO

Tracked outside of issue tracker for the v0 lab. Each item rolls up into the milestone commits in `CHANGELOG.md`.

## Done in v0
- [x] Vertical slice: mini repo → ingest → ontology → graph → traceability → tokenizer report → dataset → RAG → eval → smoke tests.

## Next (v0.1, in flight)
- [ ] Fill out remaining learning chapters in `docs/` (00–14).
- [ ] Complete the 10 Jupyter notebooks in `notebooks/`.
- [ ] Configs in `configs/` for all seven sections (repos / models / tokenizer / ontology / dataset / training / eval).
- [ ] Observability stack under `observability/` — Prometheus rules, Grafana dashboards, Loki, Tempo, docker-compose, exporters.
- [ ] Training recipes under `src/training/` — Unsloth + HF/PEFT SFT, DPO, optional GRPO, merge_adapter, export_gguf, train router.
- [ ] Advanced RAG: `src/rag/embeddings.py`, `vector_store.py`, `hybrid_search.py`.
- [ ] CLI: `src/cli/` subcommands wired through `kde-lab ingest|graph|tokenizer|dataset|train|eval`.

## Optional / stretch
- [ ] Neo4j and RDF/OWL exporters for the graph.
- [ ] Tree-sitter or libclang upgrade for the C++ reader.
- [ ] Real-repo ingestion against a small slice of `invent.kde.org` (KIO + KConfig + Dolphin core).
- [ ] Multi-turn debugging dialogue support.
- [ ] Function-calling / tool-use SFT data (ripgrep, qdbus, journalctl, ctest, git blame).
- [ ] Adapter-routing inference server.

## Will NOT do
- [ ] Production-grade CI.
- [ ] Auto-download of model weights or datasets.
- [ ] Kubernetes / microservices.
- [ ] Training that requires GPUs in CI.
