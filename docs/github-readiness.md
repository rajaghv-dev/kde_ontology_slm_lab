# GitHub Readiness Checklist

This document describes what is needed to make `kde_ontology_slm_lab` fully
ready for public or collaborative hosting on GitHub.

---

## Current state

| Item | Status |
|------|--------|
| `.github/workflows/` | Created — `validate.yml` added |
| Issue templates | Missing |
| Pull request template | Missing |
| Dependabot config | Missing |
| CODEOWNERS | Missing |
| Code scanning (CodeQL) | Missing |
| Branch name (`master` vs `main`) | Needs decision — see below |
| Remote configured | None — push target not yet set |

---

## Branch naming: `master` vs `main`

The local default branch is `master`. GitHub's default since October 2020 is
`main`. This is purely cosmetic but matters for:

- The CI workflow's branch filter (currently `"**"` — catches both).
- GitHub repository settings after first push (`Settings > Branches > Default branch`).
- Any badge URLs or documentation links that hardcode a branch name.

**Recommendation:** rename before the first push to avoid a redirect chain:

```bash
git branch -m master main
```

Then set the default branch to `main` in `Settings > Branches` after pushing.

---

## Recommended CI workflow

A minimal `validate.yml` has been created at `.github/workflows/validate.yml`.
It runs on every push and pull request across Python 3.10, 3.11, and 3.12:

1. Checkout the repository.
2. Set up the requested Python version.
3. Cache pip using `pyproject.toml` as the cache key.
4. Install `pip install -e ".[dev]"` (core + pytest + ruff, **no** training deps).
5. `ruff check src/` — lint.
6. `pytest -q` — 64-test suite.

Training dependencies (`torch`, `peft`, `trl`, etc.) are intentionally excluded
because they add hundreds of MB and require a GPU-capable runner.

---

## Missing: pull request template

Create `.github/pull_request_template.md`:

```markdown
## Summary

<!-- What does this PR do? One paragraph. -->

## Changes

- 

## Testing

- [ ] `pytest -q` passes locally
- [ ] `ruff check src/` passes locally
- [ ] New tests added for new behaviour (if applicable)

## Checklist

- [ ] No model weights, API keys, or personal paths committed
- [ ] CHANGELOG updated (if user-visible change)
- [ ] Docs updated (if behaviour changes)
```

---

## Missing: issue templates

Create `.github/ISSUE_TEMPLATE/` with the following files.

**`.github/ISSUE_TEMPLATE/bug_report.yml`**

```yaml
name: Bug Report
description: Something is broken or behaves unexpectedly.
labels: ["bug"]
body:
  - type: textarea
    id: description
    attributes:
      label: What happened?
      description: Clear description of the bug.
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      placeholder: |
        1. Run `kde-lab pipeline`
        2. See error ...
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behaviour
    validations:
      required: true
  - type: input
    id: python
    attributes:
      label: Python version
      placeholder: "3.11"
    validations:
      required: true
  - type: input
    id: os
    attributes:
      label: Operating system
      placeholder: "Ubuntu 24.04 / WSL2"
    validations:
      required: true
```

**`.github/ISSUE_TEMPLATE/feature_request.yml`**

```yaml
name: Feature Request
description: Propose a new capability or improvement.
labels: ["enhancement"]
body:
  - type: textarea
    id: motivation
    attributes:
      label: Motivation
      description: What problem does this solve?
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
    validations:
      required: true
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
```

**`.github/ISSUE_TEMPLATE/docs.yml`**

```yaml
name: Documentation Issue
description: Something in the docs is wrong, missing, or unclear.
labels: ["documentation"]
body:
  - type: input
    id: location
    attributes:
      label: Location
      placeholder: "docs/07_training_recipes.md, section X"
    validations:
      required: true
  - type: textarea
    id: issue
    attributes:
      label: What is wrong or missing?
    validations:
      required: true
  - type: textarea
    id: suggestion
    attributes:
      label: Suggested fix (optional)
```

---

## Missing: Dependabot

Create `.github/dependabot.yml` to receive automated dependency update PRs:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      dev-deps:
        patterns: ["pytest*", "ruff*"]

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

Grouping dev deps avoids a flood of single-package PRs. Training deps (`torch`,
`peft`, etc.) are optional and heavy; consider adding them to an ignore list if
Dependabot updates them too aggressively.

---

## Missing: CODEOWNERS

Create `CODEOWNERS` (at the repo root or under `.github/`):

```
# Default owner for all files
*                   @your-github-username

# CI / tooling
.github/            @your-github-username
pyproject.toml      @your-github-username

# Core pipeline
src/                @your-github-username
configs/            @your-github-username
```

Replace `@your-github-username` with the actual GitHub handle before pushing.
CODEOWNERS has no effect without at least one collaborator or branch protection
rule that requires a review.

---

## Missing: code scanning (CodeQL)

Add `.github/workflows/codeql.yml` to enable GitHub's static analysis:

```yaml
name: CodeQL

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "30 4 * * 1"   # weekly on Monday

permissions:
  contents: read
  security-events: write

jobs:
  analyze:
    name: Analyze (Python)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3
```

This is free for public repositories. For private repos it requires GitHub
Advanced Security.

---

## Recommended first-push sequence

```bash
# 1. Rename branch
git branch -m master main

# 2. Create GitHub repo (do NOT initialise with README/gitignore)
gh repo create kde_ontology_slm_lab --public --source=. --remote=origin

# 3. Push
git push -u origin main

# 4. Set default branch
gh api repos/{owner}/kde_ontology_slm_lab \
  --method PATCH --field default_branch=main

# 5. Enable branch protection (optional but recommended)
gh api repos/{owner}/kde_ontology_slm_lab/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["lint + test (Python 3.11)"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews=null \
  --field restrictions=null
```
