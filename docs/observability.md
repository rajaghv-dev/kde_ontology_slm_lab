# Observability

_Generated: 2026-05-16._

---

## Overview

The lab follows the OCT framework for its own telemetry: every pipeline run is
**observable** (structured logs, metrics, traces), **controllable** (flags, env vars),
and **traceable** (every log line and metric carries a `trace_id`).

Observability works in two modes:

| Mode | Requirements | Output |
|---|---|---|
| **Fallback (default)** | No extra installs | JSONL files under `artifacts/` |
| **Full stack** | Docker + `pip install ".[obs]"` | Prometheus + Grafana + Loki + Tempo |

The fallback mode is always active. The full stack is additive.

---

## Logs

### Implementation
`src/observability/logger.py` — `get_obs_logger(name, trace=None)`

Two destinations per log call:
1. **stderr** — human-readable text (`src.common.logging` format)
2. **`artifacts/logs/run-<trace_id>.jsonl`** — one JSON object per line

### JSONL record schema
```json
{
  "ts": 1747394636.12,
  "level": "INFO",
  "logger": "pipeline",
  "message": "trace=abc123 scanned 15 files",
  "trace": "abc123"
}
```

### How to read logs
```bash
# Human-readable tail
tail -f artifacts/logs/run-*.jsonl | python3 -c "import sys,json; [print(json.loads(l)['message']) for l in sys.stdin]"

# Filter by trace id
jq 'select(.trace == "abc123")' artifacts/logs/run-abc123.jsonl

# Count by level
jq -r '.level' artifacts/logs/run-*.jsonl | sort | uniq -c
```

### Trace ID propagation
The trace ID is set once per pipeline run (via `src.common.ids.trace_id()`) and
propagated via the `KDE_OBS_TRACE_ID` environment variable. Any subprocess or
concurrent module that calls `get_obs_logger` will share the same trace ID.

---

## Metrics

### Implementation
`src/observability/metrics.py` — `Counter`, `Gauge`, `Histogram`

Two backends:
1. **JSONL** (`artifacts/metrics/`) — always active
2. **Prometheus** (`prometheus_client`) — active when `[obs]` extra is installed

### Metric types

| Class | Methods | Example use |
|---|---|---|
| `Counter` | `inc(amount, labels)` | entities extracted, eval items graded |
| `Gauge` | `set(v)`, `inc(v)`, `dec(v)` | current graph node count |
| `Histogram` | `observe(v, labels)` | pipeline stage duration |

### Label rules
- Labels must be declared at construction time
- High-cardinality labels (file paths, entity IDs) are forbidden — use fixed enums
- Negative counter increments raise `ValueError`

### JSONL metric record
```json
{"ts": 1747394636.12, "kind": "counter", "name": "entities_extracted",
 "value": 78, "labels": {"repo": "mini_kde_repo"}}
```

### Prometheus endpoint
```python
from src.observability.metrics import start_http_server
start_http_server(port=9101)   # safe no-op without prometheus_client
```
Port 9101 is scraped by the Docker Prometheus config in `observability/prometheus/`.

---

## Traces

### Implementation
`src/observability/traces.py` — `span(name, labels)` context manager

### Usage
```python
from src.observability.traces import span

with span("graph.build", labels={"repo": "mini_kde_repo"}):
    g = build_graph(bundle)
```

### Output
- **JSONL** → `artifacts/logs/traces-<trace_id>.jsonl`
- **OTLP** → Grafana Tempo on port 4317 (if `opentelemetry` is installed)

### Span JSONL record
```json
{"trace_id": "abc123", "span_id": "uuid4", "parent_span_id": null,
 "name": "graph.build", "start_time": 1.23, "end_time": 1.45,
 "duration_ms": 220, "labels": {"repo": "mini_kde_repo"}}
```

---

## Debugging

### Enable verbose logging
```bash
# Set Python log level to DEBUG before running
PYTHONPATH=. python3 -c "
import logging; logging.getLogger().setLevel(logging.DEBUG)
from examples.run_mini_repo_pipeline import main; main()
"
```

### Inspect a specific run
```bash
# Find latest run
ls -t artifacts/logs/ | head -5

# Pretty-print the JSONL log
cat artifacts/logs/run-<trace_id>.jsonl | python3 -m json.tool | less

# Show trace spans
cat artifacts/logs/traces-<trace_id>.jsonl | jq '.name, .duration_ms'
```

### Warning: prometheus_client not installed
The 8 `UserWarning` messages in the test suite are expected. They mean the
`[obs]` extra is not installed, so metrics fall back to JSONL-only mode.
This is correct for dev/CI environments.

---

## Health checks

There is no HTTP health endpoint in the default (non-Docker) mode.

In the Docker stack, Prometheus provides a health check via:
```
http://localhost:9090/-/healthy
```

Grafana: `http://localhost:3000/api/health`

---

## Audit events

Pipeline runs emit structured log lines at the start and end of each stage,
including entity counts, timing, and trace IDs. These can serve as audit
events in a regulated environment.

Example audit trail in the JSONL log:
```
{"trace": "1d8f11f1", "message": "starting end-to-end pipeline against .../mini_kde_repo"}
{"trace": "1d8f11f1", "message": "scanned 15 files"}
{"trace": "1d8f11f1", "message": "extracted 78 entities, 77 relations"}
{"trace": "1d8f11f1", "message": "eval pass rate = 66.67%"}
```

---

## Docker observability stack

### What it provides
```
Prometheus :9090   — metrics scraping (scrapes :9101 from the lab's exporter)
Grafana    :3000   — dashboards (admin/admin in dev mode)
Loki       :3100   — log aggregation (Promtail tails artifacts/logs/*.jsonl)
Tempo      :3200   — distributed traces (OTLP on :4317)
Promtail   (internal) — log shipper from artifacts/logs/
```

### How to start
```bash
docker compose -f observability/docker-compose.yml up -d

# Check status
docker compose -f observability/docker-compose.yml ps

# Stop
docker compose -f observability/docker-compose.yml down
```

### Current status
**Scaffolded — not validated.** The `docker-compose.yml` is correctly structured
with pinned image versions, but:
- The lab has never been booted against this stack
- The metrics exporter scripts (`observability/exporters/`) generate synthetic
  data, not real pipeline metrics
- The Grafana dashboards (`observability/grafana/dashboards/`) are placeholders

### Security note
The Grafana default password is `admin`/`admin`. This is intentional for a local
learning lab. **Do not expose this stack on a network interface** without changing
`GF_SECURITY_ADMIN_PASSWORD`. The `docker-compose.yml` binds to `0.0.0.0`; for
local-only use, prefix ports with `127.0.0.1:` (e.g. `127.0.0.1:3000:3000`).

---

## Gaps

| Gap | Impact | Fix |
|---|---|---|
| Docker stack not validated end-to-end | Medium | Boot it once, capture dashboard screenshots |
| Exporter scripts generate synthetic data only | Low | Wire real `src.observability.metrics` output to the exporter |
| `observability/exporters/` not importable via `python -m observability.*` | High (docs wrong) | Use `python -m src.observability.*` or add `observability/` as a package |
| No health endpoint in non-Docker mode | Low | Add a `/health` HTTP endpoint to the metrics server |
| `opentelemetry` optional dep not declared in `pyproject.toml` | Low | Add `[obs]` extras or a `[tracing]` extra |

---

## Recommended minimal improvements

1. **Fix the module import path in docs** — `observability/README.md` says
   `python -m observability.exporters.*` but that package is not registered;
   correct to `python -m src.observability.*` (see `docs/doc-code-consistency-audit.md`).

2. **Boot the Docker stack once** — run `docker compose up -d`, confirm
   Prometheus scrapes, Grafana loads, and Loki receives a log line.

3. **Wire pipeline metrics to Prometheus** — the `run_mini_repo_pipeline.py`
   already uses `src.observability.metrics`; adding a `start_http_server(9101)`
   call before the pipeline would make it scrapeable.

4. **Declare `opentelemetry-sdk` as an optional dep** — add it to
   `[project.optional-dependencies.obs]` in `pyproject.toml`.
