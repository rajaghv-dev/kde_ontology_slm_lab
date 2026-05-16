# Contributing

## Philosophy

`kde_ontology_slm_lab` is a learning lab built around the OCT (Ontology-Context-Training)
framework. The guiding rule is **recipes only, no auto-downloads**: every heavy dependency
(torch, bitsandbytes, llama.cpp) is opt-in. The `[dev]` extras stay lightweight so
`kde-lab info` boots in under a second.

## Dev environment

```bash
bash scripts/setup_dev.sh        # creates .venv and installs [dev] extras
source .venv/bin/activate
kde-lab info                     # smoke-test
```

For GitHub Actions the runner sets `CI=1` automatically, which tells the script to skip
venv creation and install into the active environment.

## Running tests

```bash
pytest -q                        # all tests (configured in pyproject.toml)
pytest tests/test_graph.py -q    # single module
```

## Running the full pipeline

```bash
make vertical-slice              # ingest -> graph -> dataset -> eval
kde-lab pipeline                 # same thing via the CLI
```

## Code style

- Formatter / linter: **ruff** (`ruff check . && ruff format .`)
- Line length: 100 characters
- Type annotations on all public functions
- Heavy imports (networkx, torch, transformers) must live **inside** the command handler
  function, not at module top-level, so `kde-lab --help` stays fast.

## Adding a new file-format reader

1. Create `src/repo_ingest/<format>_reader.py` implementing `read(path) -> list[Entity]`.
2. Register it in `src/repo_ingest/scanner.py` under the appropriate file-extension key.
3. Add at least one test in `tests/test_<format>_reader.py`.
4. Update `docs/architecture.md` with the new reader.

## Pull request guidelines

- Keep PRs small and focused — one logical change per PR.
- Update docs (docstrings, `docs/`, config comments) alongside code changes.
- All tests must pass; ruff must report no errors.
- PR title format: `<type>: <short description>` — e.g. `feat: add json_reader`,
  `fix: handle empty graph in qa_generator`, `docs: document export_model.sh`.

## Branch naming

```
feat/<short-name>
fix/<short-name>
docs/<short-name>
chore/<short-name>
```

## Commit message style

```
<type>: <imperative summary under 72 chars>

Optional body explaining the why, not the what.
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.

## License

MIT. No CLA required.
