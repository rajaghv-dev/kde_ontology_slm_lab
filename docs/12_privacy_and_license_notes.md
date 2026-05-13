# 12 — Privacy, licensing, and safety

A KDE-specialised language model trained on KDE source has to respect the licenses KDE source carries, and a debugging-oriented model that ingests logs has to respect the privacy of whoever produced those logs. This chapter covers the legal frame, the redaction rules, the data and model cards, and the "do not train secrets into the model" guarantee that drives every dataset filter.

If you take only one thing away: this lab ships *recipes*, not *data*. The synthetic mini repo is the lab's only embedded source. Anything else — real KDE source, your local logs, your bug reports — you provide explicitly, and you control how it gets processed.

## KDE licensing in one paragraph

The KDE Frameworks libraries are primarily **LGPL-2.1-or-later** (some are **LGPL-3.0-or-later** or **MIT** for individual files; a few are **BSD-3-Clause**). Plasma is mostly **GPL-2.0-or-later** and **GPL-3.0-or-later**. KIO is **LGPL-2.0-or-later** with some files **LGPL-2.1-or-later**. Many applications (Dolphin, Konsole, Kate) are **GPL-2.0-or-later**. Tests and examples often pick up **BSD-2-Clause** or **MIT**. The SPDX-License-Identifier header at the top of each KDE file is the authoritative source per file.

The relevant practical implication for a language model: text from a GPL-licensed file is GPL-licensed text. Memorising it into a model and reproducing it verbatim is a copy. Reproducing it with the SPDX line stripped is still a copy. That matters in two places:

1. **The dataset.** Records that quote KDE source must keep enough of the citation to allow attribution; the `evidence` list with file path and line numbers is exactly that.
2. **The model output.** A model that emits multi-line verbatim KDE code without attribution makes the user's downstream copy unattributed. Chapter [11_failure_modes.md](11_failure_modes.md)'s memorisation detection is the relevant safeguard.

## What you can train without a copyright fight

Three buckets of source you can use with high confidence:

1. **Synthetic.** The mini repo under [../examples/mini_kde_repo/](../examples/mini_kde_repo/) is licensed `LGPL-2.1-or-later` and authored for this lab. Use it freely.
2. **Public KDE source the user has cloned.** They opt in by configuring `configs/repos.yaml` to point at a local clone. The lab does not download it.
3. **Generated text grounded in graph facts.** The QA pairs in `artifacts/datasets/mini_repo_sft_v0.jsonl` are *about* KDE source but do not contain verbatim source. They are derivative facts (e.g. *"KFileSearcher emits resultsReady"*) with file/line evidence pointers.

What you should *not* drop straight into training without filtering:

1. **Bug reports and forum threads.** They mix factual content with usernames, emails, machine names, IPs, and sometimes credentials.
2. **Local logs.** A `~/.local/share/...` log can include filesystem paths that reveal your username, project names, and sometimes content.
3. **Email archives.** kde-devel and kde-core-devel archives are public but full of names, addresses, and personal context.

## The redaction rules

Before any text reaches training, it passes a redactor. The lab's redaction rules — to be implemented as `src/dataset/redact.py` in v0.1 — are:

| Class           | Pattern (regex sketch)                       | Replacement              |
|-----------------|-----------------------------------------------|--------------------------|
| Username paths  | `/home/[^/\s]+/`                              | `/home/<user>/`          |
| Email addresses | `[\w.+-]+@[\w-]+\.[\w.-]+`                    | `<email>`                |
| GitHub-style tokens | `gh[pousr]_[A-Za-z0-9]{36,}`              | `<token>`                |
| Generic API keys | `[A-Za-z0-9_-]{32,}` (with context filter)   | `<key>`                  |
| Machine names   | hostname capture from log prefixes            | `<host>`                 |
| IP addresses    | `\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b`      | `<ip>`                   |
| Absolute Windows paths | `C:\\[^\s]+`                           | `C:\\<path>`             |
| Author tags     | "Author: name <email>" lines in commit msgs   | `Author: <author>`       |

Each rule is applied to every input field (`instruction`, `input`, `output`, every `evidence.symbol`). Records that fail the redaction (e.g. still contain `@` after redaction) are dropped, not patched, so a buggy regex cannot silently leak.

The redactor runs *after* the QA generator but *before* the JSONL writer. Adding a redactor pass means every regression check has to use the redacted records, including the mini-repo eval set — even though the mini repo is synthetic and has nothing to redact, the rule applies uniformly.

## Data cards and model cards

Every dataset and every model the lab produces should ship with a card.

### Data card

A short Markdown that answers:

- What is this dataset?
- Where did the source text come from? (Mini repo, real KDE clone, generated.)
- What licenses apply to the source?
- What redactions were applied?
- What is the split policy?
- What is the schema?
- What are the known limitations?

`datasets/data_cards/` is the directory; one Markdown per dataset.

### Model card

A short Markdown that answers:

- What is this model?
- What base model? What snapshot hash?
- What dataset(s) did it train on? Link to data cards.
- What hyperparameters?
- What evals did it pass?
- What is it for?
- What is it *not* for?
- What is the license?

`artifacts/training_runs/<name>/README.md` is the location; the training scripts in [../scripts/](../scripts/) generate the boilerplate.

## Separating public KDE data from private data

If you run the lab on your workstation, you might mix three classes of source:

1. **Public KDE clones** — fine to train on (license permitting).
2. **Your local logs** — your data; you decide.
3. **Internal patches or proprietary downstream forks** — must not enter the public model.

The lab's discipline:

- `configs/repos.yaml` distinguishes `public:` repos (entries get `metadata.license` from the clone) from `private:` repos (entries get `metadata.confidential=true`).
- The dataset writer refuses to emit records with `metadata.confidential=true` into a publicly distributable dataset directory. They land under `datasets/private/` instead.
- The model card includes a `trained_on:` list that explicitly enumerates which data classes the run touched.

That gives you the option to train two models — a public KDE-SLM and an internal *KDE + downstream* SLM — without one accidentally bleeding into the other.

## "Do not train secrets into the model"

A secret in the dataset is a secret in the weights, and the model will eventually surface it. The standard counterexamples (GitHub Copilot reproducing AWS keys, language models repeating ChatGPT prompt leaks) are not edge cases — they are the default outcome.

The lab's guarantee, enforced by the dataset filter:

> No record is written to a training JSONL if it contains a pattern matching any of the redaction-rule classes that survived the redactor.

Concretely:

```python
# pseudo-code for the v0.1 filter
def safe_record(rec: dict) -> bool:
    blob = json.dumps(rec)
    for pat in REDACTION_PATTERNS:
        if pat.search(blob):
            return False
    return True
```

A record that contains an unredacted email is *dropped*, not redacted post-hoc. The reason: a regex miss in the redactor would otherwise leak; dropping forces the redactor to be correct.

That is paranoid by design. The corollary is that the dataset shrinks visibly when you add new redaction rules. That is fine; correctness over volume.

## What the lab still cannot guarantee

Three things are out of scope for v0.1:

1. **Memorisation detection at the model level.** Once you have a trained model, checking that it cannot reproduce a given input verbatim is an active research area. The lab's `evaluation` suite includes only basic prompts; deeper membership-inference is v0.2.
2. **Differential-privacy training.** DP-SGD is expensive and degrades small-model quality more than large-model quality. The lab does not adopt it; the redaction discipline is the substitute.
3. **Cross-tenant isolation.** If you train one model on data from two independent owners, you cannot guarantee one owner cannot infer the other's data. Do not co-mingle data classes unless you have explicit consent for both.

Calling these out keeps the threat model honest. The lab is not a panacea; it is a careful pipeline.

## A quick safety checklist before publishing a model

Before pushing a model anywhere public:

- [ ] Data card committed, with redaction rules listed.
- [ ] Model card committed, with `trained_on:` list.
- [ ] Dataset JSONL passes `safe_record` for every line (CI assertion).
- [ ] Memorisation smoke test: 20 prompts that probe for username paths, emails, and known KDE bug-report quotes; the model produces no exact matches.
- [ ] Eval pass rate on hallucination-resistance suite >= 0.95.
- [ ] License of base model checked; redistribution allowed.
- [ ] License of dataset (LGPL/GPL derivative or your own license) declared on the model card.

If any item fails, the model stays internal until it does not.

## Exercises

1. Open three random log lines from [../examples/mini_kde_repo/logs/minisearch.log](../examples/mini_kde_repo/logs/minisearch.log). Identify what the redactor would change. (The fixture has been pre-redacted; would your rules change anything?)
2. Sketch `src/dataset/redact.py` with five rules. Include the unit-test cases that would catch a regression in each.
3. Write a 5-bullet data card for the v0 SFT dataset.
4. Pick one downstream license scenario: you fork a KIO file under LGPL-2.1, add internal changes, and want to train on the modified file. What does your model card say? Can you distribute the model?
5. Draft a one-paragraph statement for users explaining that the model may surface KDE source patterns and how to attribute them when reusing model output.

## Further reading

- The KDE Licensing Policy at `community.kde.org/Policies/Licensing_Policy`.
- The SPDX License List at `spdx.org/licenses`.
- *Extracting Training Data from Large Language Models* (Carlini et al., 2021) — the canonical memorisation paper.
- *Membership Inference Attacks Against Machine Learning Models* (Shokri et al., 2017).
- The HuggingFace "Model Card" guidelines.
- The "Data Sheets for Datasets" paper (Gebru et al., 2018).
- The GDPR overview pages at `gdpr.eu` for the privacy frame, even outside the EU it is a useful checklist.
