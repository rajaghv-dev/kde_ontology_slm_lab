# kde_ontology_slm_lab

A hands-on learning lab for understanding KDE repositories as **layered desktop systems** — and then building tokenizers, ontologies, datasets, and small-language-model adapters that can answer real KDE architecture and debugging questions.

This is a sibling/spiritual successor to `kde-slm` but reframed as a **learning lab**: smaller, more opinionated, with a single end-to-end runnable demo from day one.

## What makes this repo different from kde-slm

| | kde-slm | kde_ontology_slm_lab |
|---|---|---|
| Focus | Train 7 base models on real KDE | Learn the *whole stack* — repo → ontology → graph → tokenizer → dataset → SLM → eval |
| First run | Requires real KDE sources | **Runs offline** on a synthetic mini KDE repo bundled in `examples/mini_kde_repo/` |
| Reasoning frame | Implicit | Explicit **OCT framework**: Observability, Controllability, Traceability |
| KDE as | A source codebase | A **living desktop system**: signals/slots, D-Bus, KConfig, plugins, logs, bug reports, commits |
| Observability | Optional | First-class — Prometheus + Grafana + Loki + Tempo stack, plus no-install JSONL/CSV fallback |
| Training | 4 stages × 7 bases | Adapter-routed multi-stage with task classifier (architecture / debug / nav / tool-use / patch) |
| RAG | One implementation | Five compared: vector / graph / hybrid / SFT-only / SFT+retrieval |

## The OCT framework

Every module in this repo is designed around three questions:

1. **Observability** — What can we see? (Files, classes, QML items, D-Bus names, logs, config keys, CMake targets, tests, bug reports, commits, stack traces.)
2. **Controllability** — What can we influence? (Build flags, test selection, logging categories, config keys, environment variables, plugins, service restart, command-line tools, D-Bus calls.)
3. **Traceability** — How do we connect cause to effect? (User symptom → log event → service → D-Bus call → QML component → C++ class → function → config key → commit → test → fix.)

If a module does not advance at least one of these three, it does not belong here.

## What you can ask the trained model

Concrete target questions (the eval benchmarks measure exactly these):

- Why is Dolphin slow when opening a folder?
- Which KDE component owns file indexing?
- How does KIO connect to Dolphin?
- How does KWin handle window effects?
- Where is a setting stored?
- Which D-Bus service should be called?
- What code path is involved in a crash?
- Which logs should I inspect?
- Which class emits this signal?
- Which QML component maps to which C++ backend?
- What changed between two commits?
- Which test should be added?
- What is the likely root cause?
- What is the minimal safe fix?

## Quickstart (offline, no downloads)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python examples/run_mini_repo_pipeline.py
```

That one command runs the **complete vertical slice** end-to-end on the synthetic mini KDE repo bundled in `examples/mini_kde_repo/`: scanner → ontology extraction → graph build → traceability query → tokenizer report → SFT dataset → RAG answer with evidence → minimal eval. It writes artifacts under `artifacts/` and prints a Markdown summary.

## Operating modes

The repo runs in four modes:

1. **Local simulation** (default) — uses the bundled mini repo. No external dependencies.
2. **Real KDE repo** — point `configs/repos.yaml` at one or more local KDE clones. No network.
3. **Colab** — for tokenizer analysis, dataset formatting, and small-GPU LoRA demos.
4. **Training workstation** — local GPU. Unsloth / HF / PEFT.

## Recipes only — no auto-downloads

Same policy as kde-slm: this repo ships **code, configs, and a synthetic fixture**. It does not auto-download model weights, datasets, or KDE source. Any network access is opt-in via an explicit CLI flag. See `docs/12_privacy_and_license_notes.md`.

## Repo layout

See `docs/00_big_picture.md` for the conceptual map and the per-directory `README.md` files for details.

## Status

Early lab. The vertical slice is runnable end-to-end on the mini repo. Most advanced features (full training, adapter routing, observability stack) are scaffolded with working stubs. See `TODO.md` and `CHANGELOG.md`.

## License

Code: MIT. Generated datasets respect the upstream KDE source licenses (LGPL/GPL primarily). See `docs/12_privacy_and_license_notes.md`.
