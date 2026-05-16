# Security Audit

**Date:** 2026-05-16
**Scope:** Static review of source files, configurations, shell scripts, Docker
compose, and dependency declarations. No dynamic analysis or network scanning
was performed.

**Verdict: no blocking issues found.** All findings are low-severity
hardening recommendations appropriate for a research/learning lab that will be
published as a public repository.

---

## 1. Hardcoded secrets

**Finding: none.**

Every config file was inspected:

| File | Finding |
|------|---------|
| `configs/models.yaml` | Uses `CHANGE_ME` placeholders — no real HF tokens or paths |
| `configs/training.yaml` | Local relative paths only |
| `configs/dataset.yaml` | `artifacts/` relative paths only |
| `configs/repos.yaml` | `../kde/…` stubs, all `enabled: false` |
| `configs/eval.yaml` | No credentials |
| `configs/ontology.yaml` | No credentials |
| `src/` (all Python) | No `os.environ` reads for tokens; no hardcoded API keys |
| `scripts/*.sh` | No tokens or passwords; use env-var overrides with safe defaults |

**Recommendation:** Before adding real HF tokens or credentials in future,
store them as GitHub Actions secrets and inject via `${{ secrets.HF_TOKEN }}`.
Never commit `.env` files. Add `*.env` and `.env*` to `.gitignore` now as
a preventive measure.

---

## 2. `.gitignore` coverage

**Current coverage:**

| Category | Covered? |
|----------|----------|
| Python bytecode (`__pycache__`, `*.pyc`) | Yes |
| Editable install artifacts (`*.egg-info`) | Yes |
| Virtual environment (`.venv`) | Yes |
| Test / lint caches | Yes |
| Generated artifact directories | Yes |
| Model weights (`.safetensors`, `.gguf`, `.bin`) | Yes |
| `models/`, `checkpoints/` | Yes |
| OS / editor noise (`.DS_Store`, `.idea/`, `.vscode/`) | Yes |

**Gaps to address:**

1. **Environment files** — `.env`, `.env.*` are not excluded. If a learner
   adds a `.env` for `HF_TOKEN` or similar, it could be committed accidentally.

   ```gitignore
   # Secrets / environment files
   .env
   .env.*
   *.env
   ```

2. **Notebook checkpoints** — `.ipynb_checkpoints/` directories are generated
   by Jupyter and can contain stale cell outputs.

   ```gitignore
   .ipynb_checkpoints/
   ```

3. **`dist/` and `build/`** — created by `python -m build`. Not currently
   produced but worth blocking preemptively.

   ```gitignore
   dist/
   build/
   ```

4. **`*.pt` (PyTorch checkpoint files)** — `.bin` is covered but `.pt` is not.
   Some HuggingFace pipelines emit `.pt` checkpoints.

   ```gitignore
   *.pt
   ```

5. **`logs/` at repo root** — any ad-hoc logging outside `artifacts/logs/`
   would not be caught.

---

## 3. Docker / observability stack

File reviewed: `observability/docker-compose.yml`

### 3a. Grafana default credentials

**Finding (low severity):** Grafana is configured with
`GF_SECURITY_ADMIN_USER=admin` / `GF_SECURITY_ADMIN_PASSWORD=admin` baked into
the compose file. These are the upstream defaults; they are well-known and
intentionally left for a local-only learning lab.

**Risk:** None for a laptop/WSL2 setup where ports are not exposed to a network.
Becomes a risk if the stack is ever deployed on a shared host or with
`--network=host` on a reachable machine.

**Recommendation:** Document explicitly in `observability/README.md` that these
credentials must be changed before any non-local deployment. Consider
parameterising via an `.env` file (which would itself be gitignored):

```yaml
# docker-compose.yml
environment:
  - GF_SECURITY_ADMIN_USER=${GF_ADMIN_USER:-admin}
  - GF_SECURITY_ADMIN_PASSWORD=${GF_ADMIN_PASSWORD:-admin}
```

### 3b. Exposed ports

All service ports are bound to `0.0.0.0` (Docker default):

| Service | Port | Accessible from |
|---------|------|-----------------|
| Prometheus | 9090 | All interfaces |
| Grafana | 3000 | All interfaces |
| Loki | 3100 | All interfaces |
| Tempo HTTP | 3200 | All interfaces |
| Tempo OTLP/gRPC | 4317 | All interfaces |

**Risk:** On a laptop/WSL2, Docker binds to the WSL2 virtual NIC which is
not reachable from the wider LAN by default. On a real Linux host with a
public IP, all five ports would be reachable without a firewall rule.

**Recommendation (localhost-only binding):** For local labs, bind to loopback
to prevent unintended exposure:

```yaml
ports:
  - "127.0.0.1:9090:9090"   # Prometheus
  - "127.0.0.1:3000:3000"   # Grafana
  - "127.0.0.1:3100:3100"   # Loki
  - "127.0.0.1:3200:3200"   # Tempo HTTP
  - "127.0.0.1:4317:4317"   # Tempo OTLP
```

### 3c. Prometheus `--web.enable-lifecycle`

**Finding (informational):** The `--web.enable-lifecycle` flag enables the
`/-/reload` and `/-/quit` HTTP endpoints. On an exposed Prometheus instance
this allows unauthenticated config reload. On a local setup this is
harmless. Mitigated by the localhost binding recommendation above.

### 3d. Image pinning

All images use exact version tags (e.g. `prom/prometheus:v2.55.1`,
`grafana/grafana:11.3.0`). This is good practice for reproducibility and
prevents silent supply-chain drift. Dependabot's `docker` ecosystem can be
added to `.github/dependabot.yml` to receive version bump PRs.

---

## 4. Dependency risk

Reviewed: `pyproject.toml`

### 4a. Version bounds

All core dependencies use `>=` lower bounds with no upper cap. This is
standard for a library/lab but means `pip install` will always pull the
latest compatible release, which could introduce breaking changes.

| Package | Bound | Notes |
|---------|-------|-------|
| `networkx` | `>=3.0` | Stable API; low risk |
| `numpy` | `>=1.26` | NumPy 2.x changed some APIs — tests cover this |
| `pyyaml` | `>=6.0` | `yaml.safe_load` used throughout — correct |
| `click` | `>=8.1` | Stable |
| `tqdm`, `rich` | `>=4.66`, `>=13.0` | Stable |
| `pytest` | `>=8.0` | Test-only; no runtime risk |
| `ruff` | `>=0.6` | Lint-only; no runtime risk |

**Training extras** (`torch>=2.4`, `peft>=0.13`, `trl>=0.11`, etc.) are
opt-in and not installed in CI — this is correct policy.

### 4b. `bitsandbytes` platform guard

```toml
"bitsandbytes>=0.43; sys_platform == 'linux'"
```

The `sys_platform` marker correctly prevents installation on macOS/Windows
where `bitsandbytes` either does not build or has limited support. Good.

### 4c. No known CVEs at audit time

No packages in the `[dev]` or core dependency set have known high/critical
CVEs at audit date (2026-05-16). Dependabot weekly updates (see
`github-readiness.md`) will surface future issues automatically.

---

## 5. Shell script safety

All five scripts were reviewed: `setup_dev.sh`, `train_hf_peft_lora.sh`,
`run_eval.sh`, `export_model.sh`, `create_sample_dataset.sh`.

**Positive findings:**

- All scripts use `set -euo pipefail` — fails immediately on error, unbound
  variables, and pipe failures.
- No `eval`, `exec`, or dynamic command construction from user-supplied input.
- No `curl | bash` or similar supply-chain anti-patterns.
- All configurable values come from environment variables with safe defaults
  (`VAR="${VAR:-default}"`), never from positional arguments that could be
  manipulated.
- `shellcheck disable=SC1090` is used narrowly and correctly in `setup_dev.sh`
  for the `source` call whose path is dynamic by design.
- No use of `rm -rf` on unchecked variables (no `rm -rf "$SOME_VAR"` pattern
  where `$SOME_VAR` could be empty or `/`).

**Minor observations:**

1. `create_sample_dataset.sh` runs `mkdir -p "$(dirname "${OUT}")"`. If `OUT`
   were set to a path starting with `/` (e.g. `/etc/passwd`), the `dirname`
   call would expand to a root system path. This is not a practical risk
   because `OUT` defaults to a relative path inside `artifacts/` and the
   script never runs with elevated privileges, but for hygiene consider
   validating that `OUT` starts with `artifacts/` or is relative.

2. `train_hf_peft_lora.sh` and `export_model.sh` invoke Python modules
   directly via `python -m`. If a malicious package shadows `src.training.*`
   in the installed environment, it would run. This is a general Python
   packaging concern, not specific to these scripts; the editable install
   (`pip install -e .`) makes `src` authoritative.

---

## 6. Config loading safety

File reviewed: `src/common/config.py`

```python
data = yaml.safe_load(f) or {}
```

**Finding: no issues.**

- `yaml.safe_load` is used — not `yaml.load` with a `Loader=None` or
  `Loader=yaml.FullLoader`. This prevents arbitrary Python object
  deserialisation from malicious YAML files.
- The return value is validated to be a `dict` before use; a top-level YAML
  list or scalar raises `ValueError` explicitly.
- The function returns an empty dict for missing files rather than raising,
  which is intentional for the lab's "sensible defaults" policy.

**Recommendation (minor):** Consider adding a maximum file size check or
a `yaml.CSafeLoader` for performance on large YAML files, though neither is
a security concern in practice.

---

## 7. Path traversal in scanner

File reviewed: `src/repo_ingest/scanner.py`

The `scan()` function uses `Path.rglob("*")` starting from a caller-supplied
`repo_root`. This means:

- If `repo_root` is `Path("/")`, the entire filesystem would be walked.
- If `repo_root` is `Path("../")`, files outside the project directory would
  be read.

**Current mitigations already present:**

- The scanner skips any path component that starts with `.` (hides `.git`,
  `.venv`, etc.).
- `repos.yaml` marks all real KDE repo entries as `enabled: false` by default.
- The mini-repo path (`examples/mini_kde_repo`) is relative and resolved via
  `src/common/paths.py`, which anchors it to the project root.

**Residual risk (low):** A user who adds an entry to `repos.yaml` pointing
`path:` at an absolute system directory (e.g. `/etc`) and sets `enabled: true`
would cause the scanner to walk that directory. The scanner only reads files
for classification (no write operations) and only produces a `ScanReport`
object, so the worst-case outcome is reading unexpected files.

**Recommendation:** In `scan()`, add a guard that resolves `repo_root` to an
absolute path and validates it is within an allowlist of expected prefixes
(e.g. the project root or a user-configured base directory):

```python
def scan(repo_root: Path, *, project_root: Path | None = None) -> ScanReport:
    repo_root = repo_root.resolve()
    if project_root is not None:
        project_root = project_root.resolve()
        if not str(repo_root).startswith(str(project_root)):
            raise ValueError(
                f"repo_root {repo_root} is outside project_root {project_root}"
            )
    ...
```

This is a defence-in-depth measure rather than a fix for an active exploit.

---

## Summary table

| Area | Severity | Action required |
|------|----------|-----------------|
| Hardcoded secrets | None | No action needed |
| `.gitignore` gaps | Low | Add `.env*`, `.ipynb_checkpoints/`, `dist/`, `build/`, `*.pt` |
| Grafana default password | Low | Document; parameterise via `.env` for non-local use |
| Docker port binding | Low | Bind to `127.0.0.1` for extra safety on shared hosts |
| Prometheus lifecycle endpoint | Informational | Mitigated by loopback binding |
| Dependency bounds | Informational | Dependabot will track updates |
| Shell script `mkdir -p` | Informational | Consider path prefix validation |
| Scanner path traversal | Low | Add project-root boundary check |
| Config YAML loading | None | `safe_load` used correctly |
