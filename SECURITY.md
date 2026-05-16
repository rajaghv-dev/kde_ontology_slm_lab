# Security

## Reporting a vulnerability

Please email **rajaghv.dev@gmail.com** with a description of the issue.
Do not open a public GitHub issue for security reports.
Expect an acknowledgement within 48 hours.

## Supported versions

| Version | Supported |
|---------|-----------|
| v0.0.1 (main branch) | Yes |

## Policies

**No auto-downloads.**
The lab never pulls model weights, datasets, or binaries automatically. Every
download is an explicit, documented manual step. The `[train]` and `[tokenizer]`
extras must be installed by the user.

**No hardcoded secrets.**
All configs under `configs/` use `CHANGE_ME` placeholder strings. Never commit
real API keys, tokens, or passwords. Use environment variables or a local
`.env` file (which is listed in `.gitignore`).

## Known dev-stack defaults

**Grafana / Prometheus (observability stack)**
The `docker-compose.yml` in `observability/` starts Grafana with the default
`admin` / `admin` credentials. This is intentional for a local dev stack only.
Never expose these ports to a network without changing the credentials first.

**Docker port binding**
Docker services bind to `0.0.0.0` by default (all interfaces). For local-only
development prefix port mappings with `127.0.0.1:`, e.g.:

```yaml
ports:
  - "127.0.0.1:3000:3000"
```

## Dependency security

Run `pip audit` (or `pip-audit`) periodically against the installed environment.
The `[dev]` extras are intentionally minimal to reduce the attack surface.
