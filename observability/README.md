# Observability stack

This directory ships **two** observability backends for the lab. You pick which
one you want based on how much infrastructure you feel like running.

> Why a stack at all? The lab is built around the OCT framework
> (Observability / Control / Traceability). Every pipeline stage emits a
> structured event so a learner can later answer *what happened, in what
> order, with what inputs, and why*. This works whether you stop at JSONL on
> disk or all the way up to Grafana dashboards.

## Mode 1 - No-install (default)

This mode is always on. You do not need Docker, Prometheus, or Grafana.

* `src.observability.metrics.counter / gauge / histogram` write to
  `artifacts/metrics/run-<trace_id>.jsonl`.
* `src.observability.logger.get_obs_logger` writes both human-readable lines
  to stderr and JSON lines to `artifacts/logs/run-<trace_id>.jsonl`.
* `src.observability.traces.span` writes span records to
  `artifacts/logs/traces-<trace_id>.jsonl`.
* `python -m src.observability.report` rolls all of the above into a
  Markdown report at `artifacts/eval_reports/observability_report.md`.

When to use it: notebooks, CI smoke tests, quick experimentation, anywhere
you cannot or will not run Docker.

## Mode 2 - Local docker-compose (opt-in)

When you want flame graphs and real dashboards, run:

```bash
cd observability
docker compose up -d
```

This brings up five containers:

| Service     | Port | Role                                                  |
|-------------|------|-------------------------------------------------------|
| Prometheus  | 9090 | Scrapes the lab's metrics exporter on host :9101.     |
| Grafana     | 3000 | Auto-provisioned dashboards + datasources.            |
| Loki        | 3100 | Aggregates `artifacts/logs/*.jsonl`.                  |
| Promtail    | -    | Sidecar that tails the JSONL files into Loki.         |
| Tempo       | 3200 | Receives OTLP traces on `:4317`.                      |

Grafana login is `admin` / `admin`. The dashboards live under the *KDE Lab*
folder and are loaded read-only from `observability/grafana/dashboards/`.

### Bringing it up

```bash
# from the repo root
pip install prometheus_client    # if you want metrics exposed
python -m observability.exporters.kde_metrics_exporter --port 9101 &
docker compose -f observability/docker-compose.yml up -d
```

Open <http://localhost:3000> and look for the *KDE Lab* dashboards folder.

### Tearing it down

```bash
docker compose -f observability/docker-compose.yml down
# optional: also drop the persistent volumes
docker compose -f observability/docker-compose.yml down -v
```

## How log shipping works

Promtail (`loki/promtail-config.yml`) tails everything under
`artifacts/logs/*.jsonl`, parses each line as JSON, and promotes `level` and
`logger` to Loki labels. Open Grafana -> Explore -> Loki and try:

```
{job="kde_lab", level="ERROR"}
```

## How trace shipping works

If you `pip install opentelemetry-sdk opentelemetry-exporter-otlp` and point
OTEL to `localhost:4317`, the `span()` context manager will also emit OTLP
spans into Tempo. With the default deps, only the JSONL spans on disk are
written; Tempo will simply have no traces.

## Dashboards shipped

| File                                          | Focus                                                |
|-----------------------------------------------|------------------------------------------------------|
| `kde_repo_understanding_overview.json`        | Files scanned, symbols, entities, scan rate.         |
| `kde_ontology_graph.json`                     | Graph node/edge counts, top entity types.            |
| `kde_tokenizer_report.json`                   | Tokens-per-term, compression ratio per model.        |
| `kde_dataset_quality.json`                    | Example counts, evidence coverage, task mix.         |
| `kde_training_run.json`                       | Loss curve, latency, per-adapter view.               |
| `kde_eval_debug_reasoning.json`               | Component accuracy, hallucination, safety.           |
| `kde_rag_vs_finetune_comparison.json`         | vector vs graph vs hybrid head-to-head.              |

## Alert rules shipped

| File                                | Alert                            | Severity |
|-------------------------------------|----------------------------------|----------|
| `prometheus/rules/kde_ingest_rules.yml`   | KdeIngestTooSlow            | warning  |
| `prometheus/rules/kde_dataset_rules.yml`  | KdeDatasetEvidenceCoverageLow | warning |
| `prometheus/rules/kde_training_rules.yml` | KdeTrainingLossStuck        | warning  |
| `prometheus/rules/kde_eval_rules.yml`     | KdeHallucinationRateHigh    | warning  |
| `prometheus/rules/kde_eval_rules.yml`     | KdeEvalAccuracyDropped      | warning  |

Alertmanager is intentionally not configured -- this is a learning lab and
shouting at you while you tune adapters is the wrong default. The block is
stubbed in `prometheus/prometheus.yml` if you want to wire one up.

## Smoke-testing without the pipeline

You can prime the JSONL sinks with fake data so Grafana panels light up
before you ever run `examples/run_mini_repo_pipeline.py`:

```bash
python -m observability.exporters.kde_log_generator
python -m observability.exporters.kde_trace_generator
```
