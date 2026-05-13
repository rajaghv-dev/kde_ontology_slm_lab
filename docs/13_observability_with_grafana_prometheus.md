# 13 — Observability with Grafana / Prometheus

You cannot improve what you do not measure. The lab is built around the OCT framework (Observability, Controllability, Traceability), and the *Observability* layer for the lab itself is a small metrics stack you can stand up under [../observability/](../observability/). This chapter explains the two operating modes (no-install fallback vs. full Docker stack), the Prometheus metric names, the labelling discipline that keeps cardinality sane, and the seven Grafana dashboards the lab plans to ship.

## Why an observability stack for an SLM lab

Three reasons:

1. **The pipeline is a system.** Ingest, ontology, graph, tokenizer, dataset, training, eval — each has metrics. A single CSV per run loses the over-time view (regression detection, A/B comparisons).
2. **You want to dogfood KDE's tools.** KDE itself watches Prometheus / Grafana / Loki in production. Building the lab on top of the same stack means the lab's logs and metrics behave like KDE's.
3. **Eval is a continuous metric.** Pass rate per category should be a time series, not a one-off report.

If you skip this layer, you can still run everything — the JSONL fallback is enough. But you give up the regression detection that makes the lab a *lab*.

## Mode A — no-install JSONL/CSV/Markdown fallback (default)

The default mode does not require Docker. Each pipeline run writes:

- `artifacts/metrics/pipeline_run.jsonl` — one row per stage with start/end time, counts, and any error.
- `artifacts/metrics/entity_counts.csv` — one row per run, columns per entity type.
- `artifacts/metrics/eval_history.csv` — one row per run, columns per eval category.
- `artifacts/eval_reports/<name>.md` — the human-readable Markdown report.

These are append-only. A small `scripts/metrics_summary.py` (planned) reads them and prints the last N runs as a Markdown table.

This mode is enough for solo learning and small experiments. It scales to a few hundred runs. After that you want indexes.

## Mode B — full Docker stack

The full stack lives at [../observability/](../observability/):

```
observability/
  docker-compose.yml          # the orchestration
  prometheus/                  # config + scrape rules
  grafana/                     # dashboards as JSON
  loki/                        # log aggregator
  tempo/                       # trace store
  exporters/                   # tiny Python exporters per pipeline stage
```

Bring it up with:

```
cd observability && docker compose up -d
```

The four services and what each is for:

- **Prometheus.** Scrapes counters and histograms. Stores time series. Default target: each Python exporter on `localhost:<port>`.
- **Grafana.** Reads from Prometheus, Loki, and Tempo. Renders dashboards. Default port 3000.
- **Loki.** Aggregates structured logs from the pipeline. The lab's logger in [../src/common/logging.py](../src/common/logging.py) emits JSON lines that Loki ingests via a `promtail` container.
- **Tempo.** Stores traces if you instrument with OpenTelemetry. The `trace_id` helper in [../src/common/ids.py](../src/common/ids.py) is the seed for span correlation.

The exporters under `observability/exporters/` are tiny Python servers that:

1. Import the lab's modules.
2. Run a single pipeline stage on a schedule (or on demand).
3. Update Prometheus client metrics.

That keeps the metrics close to the code rather than living in a separate scraping layer.

## Prometheus metric names

A small, opinionated set:

### Ingest

```
kde_ingest_files_total{repo, kind}            counter
kde_ingest_duration_seconds{repo, stage}       histogram
kde_ingest_errors_total{repo, kind}            counter
```

### Ontology

```
kde_ontology_entities_total{repo, entity_type} gauge   # current count, last run
kde_ontology_relations_total{repo, relation}    gauge
kde_ontology_extract_seconds{repo}              histogram
```

### Graph

```
kde_graph_nodes_total{repo}                    gauge
kde_graph_edges_total{repo}                    gauge
kde_graph_components_total{repo}               gauge    # weakly-connected components
kde_graph_build_seconds{repo}                  histogram
```

### Tokenizer

```
kde_tokenizer_compression_ratio{tokenizer}     gauge   # mean compression
kde_tokenizer_worst_term_compression{tokenizer} gauge
kde_tokenizer_terms_total{tokenizer}           gauge
```

### Dataset

```
kde_dataset_examples_total{split, task_type}   gauge
kde_dataset_with_evidence_total{split}         gauge
kde_dataset_refusal_total{split}               gauge
```

### Training

```
kde_train_steps_total{adapter, profile}        counter
kde_train_loss{adapter}                        gauge
kde_train_lr{adapter}                          gauge
kde_train_grad_norm{adapter}                   gauge
kde_train_duration_seconds{adapter}            histogram
```

### Eval

```
kde_eval_pass_rate{category, model_family}     gauge
kde_eval_mean_recall{category, model_family}   gauge
kde_eval_forbidden_hits{category, model_family} gauge
kde_eval_runs_total{model_family}              counter
```

## Safe labels vs. dangerous labels

Cardinality is the enemy of every metrics system. Prometheus is fine with thousands of time series per metric and pathological at millions. The lab's labelling rules:

| Safe labels (bounded sets) | Why                                                                   |
|----------------------------|------------------------------------------------------------------------|
| `repo`                     | A handful of repos (mini, KIO, KConfig, Dolphin, ...).                 |
| `entity_type`              | 32 types from the schema. Stable.                                      |
| `relation`                 | 24 relations. Stable.                                                  |
| `kind`                     | A handful of file kinds.                                               |
| `task_type`                | Up to ~10 task types.                                                  |
| `split`                    | `train`, `eval`, `test`. Three values.                                 |
| `model_family`             | Qwen, SmolLM, TinyLlama, Gemma, ... — handful.                        |
| `tokenizer`                | One per family.                                                        |
| `adapter`                  | Seven planned. Bounded.                                                |
| `profile`                  | Five compute profiles.                                                 |

| Dangerous labels (unbounded) | Why to avoid                                                          |
|------------------------------|------------------------------------------------------------------------|
| `file_path`                  | Tens of thousands of files. Cardinality explosion.                     |
| `symbol_id`                  | Entity ids are hashes; thousands per repo.                             |
| `commit_sha`                 | One per commit. Use as a log field, not a metric label.                |
| `eval_item_id`               | Hundreds. Use Loki / Tempo for per-item drill-down.                    |
| `user`                       | Cardinality plus a privacy concern.                                    |

Rule of thumb: if a label can take more than ~100 distinct values across the lab's lifetime, it does not belong on a Prometheus metric. Put it in a log instead.

## The seven planned Grafana dashboards

Each dashboard is a JSON under `observability/grafana/`. The set:

### 1. Pipeline overview

- Files ingested per kind, last 7 days.
- Entities per type, current snapshot vs. baseline.
- Relations per type, current snapshot vs. baseline.
- Pipeline stage durations, p50/p95/p99.

### 2. Ontology health

- Entity counts over time (line per type).
- Orphan-edge ratio (relations dropped because endpoint missing).
- Top 10 nodes by degree.

### 3. Graph topology

- Node and edge totals.
- Weakly-connected component count.
- A small histogram of degree distribution.

### 4. Tokenizer

- Compression ratio over time per tokenizer name.
- Worst-term compression over time.
- Term count over time (catches accidental list changes).

### 5. Dataset

- Records per task type.
- Records with non-empty evidence.
- Refusal records as a fraction of total.
- Split distribution.

### 6. Training

- Loss curves per adapter, with run id.
- LR schedule.
- Gradient norm.
- Step time, per profile.

### 7. Eval

- Pass rate per category, line per model family.
- Mean recall per category.
- Forbidden hits (should be zero).
- Run frequency (catches eval falling out of CI).

The seven dashboards correspond, roughly, to the seven stages of the pipeline plus the cross-cutting "ontology health" view. The naming is intentional: each dashboard maps to one chapter of these docs.

## How the lab logs

[../src/common/logging.py](../src/common/logging.py) provides `get_logger(name)` and the pipeline emits structured lines with a trace id from `trace_id()` in [../src/common/ids.py](../src/common/ids.py). The log format is plain text in v0, JSON in v0.1 once the Loki configuration is in place. Once it is JSON, Loki can index any field (e.g. `trace_id`, `stage`, `entity_count`) without falling into the cardinality trap of metric labels.

The trace ids are short (10 hex chars). One pipeline run shares one trace id across every log line; that makes log queries trivial:

```
{job="kde-lab"} | json | trace_id="abcdef1234"
```

In Tempo, a span tree per stage gives you the full per-run flame chart. With v0.1 instrumentation the chart looks like:

```
pipeline-run                  120 ms
  scan                          5 ms
  read (cpp x4)                40 ms
  read (qml x1)                 4 ms
  read (cmake x2)               6 ms
  extract                      20 ms
  graph build                  10 ms
  traceability sanity           3 ms
  tokenizer analyze             8 ms
  dataset generate             15 ms
  rag answer (per eval x6)      9 ms
```

## A short Prometheus rule example

You will want alerts. A simple rule for eval regression:

```yaml
- alert: KDEEvalPassRateDropped
  expr: kde_eval_pass_rate{category="architecture_qa"} <
        avg_over_time(kde_eval_pass_rate{category="architecture_qa"}[7d]) - 0.05
  for: 1h
  annotations:
    summary: "architecture_qa pass rate dropped > 5 pp vs 7-day baseline"
```

Build the rule once. Re-use the shape for every category.

## Exercises

1. Pick three metrics from the list above. Sketch how you would compute them from the v0 pipeline's existing artifacts. Confirm the JSONL fallback already supports all three.
2. Open the entity-counts CSV (after the v0.1 fallback writes it). Identify the smallest "missing entity" you would alert on.
3. Choose one Grafana dashboard. List the four panels it needs and the Prometheus queries (PromQL) behind each.
4. Argue for or against using `model_family` as a metric label vs. a log field. Where does the boundary sit for you?
5. Bring up the Docker stack on your workstation and confirm Prometheus scrapes a `kde_ingest_files_total` value after one pipeline run.

## Further reading

- The Prometheus documentation, particularly the *Best Practices* and *Naming* pages.
- The Grafana "Build a dashboard" tutorial.
- The Loki documentation on label cardinality (this is where you internalise the *no high-cardinality labels* rule).
- The OpenTelemetry documentation for Python.
- *Observability Engineering* by Majors, Fong-Jones, Miranda (O'Reilly) — for the broader philosophy.
- *Distributed Tracing in Practice* by Parker, Spoonhower, Mace, Sigelman.
- Prometheus's `prometheus_client` Python package documentation.
