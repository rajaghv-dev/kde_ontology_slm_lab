# TODO

Tracked outside of issue tracker for the v0 lab. Each item rolls up into the milestone commits in `CHANGELOG.md`.

## Done in v0
- [x] Vertical slice: mini repo → ingest → ontology → graph → traceability → tokenizer report → dataset → RAG → eval → smoke tests.

## Done in v0.1
- [x] `kde-lab` CLI fully wired (ingest, graph, tokenizer, dataset, train, eval).
- [x] Training recipe scripts (`train_unsloth_lora.sh`, `train_hf_peft_lora.sh`).
- [x] Observability stack scaffolded.
- [x] Advanced RAG (`embeddings`, `vector_store`, `hybrid_search`).
- [x] Fill out remaining learning chapters in `docs/` (00–14).
- [x] Configs in `configs/` for all seven sections (repos / models / tokenizer / ontology / dataset / training / eval).

## Next (v0.2)
- [ ] Boot observability Docker stack end-to-end and validate dashboards.
- [ ] Complete 10 Jupyter notebooks (currently scaffolded).
- [ ] Add `sentence-transformers` to `[obs]` or new `[embed]` extra in pyproject.toml.
- [ ] Add `opentelemetry-sdk` to pyproject.toml optional extras.
- [ ] Add mypy to `[dev]` extras and run type checking in CI.
- [ ] Implement real training loop in `src/training/` (requires GPU + weights).
- [ ] Fix `from_desktop` self-loop in `src/ontology/extractor.py` (cosmetic).
- [ ] Real KDE repo ingestion against a small invent.kde.org slice.

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
