# 09 — Colab guide

Google Colab is the cheapest path to a working LoRA fine-tune. A free T4 with 16 GB is enough to run every CPU stage in this lab and a small SFT demo for the v0.1 adapters. This chapter walks the no-cost (CPU-only) path, the T4 GPU path, what to copy from the repo, what to skip, and the storage gotchas that bite first-time Colab users. The lab's recipes-only policy applies: nothing here downloads anything automatically; you do every download explicitly.

## What works on Colab

The seven understanding stages — scan, read, extract, build, trace, tokenize, dataset — run on the Colab CPU runtime in under a minute. You do not need a GPU to:

- ingest the mini repo or any real repo,
- run the ontology extractor,
- build the graph,
- run traceability queries,
- analyze tokenizers (with the offline fallback or any loaded HuggingFace tokenizer),
- generate the SFT JSONL,
- grade the v0 RAG baseline.

You need a GPU to:

- run LoRA / QLoRA SFT on a small base model (Stage 2 of chapter [07_training_recipes.md](07_training_recipes.md)),
- run DPO (Stage 5),
- generate at length with the trained model.

## CPU-only path

The cheapest path is the one to learn on. With a CPU runtime:

```python
# Step 1. Clone the repo (no model downloads).
!git clone https://github.com/your-org/kde_ontology_slm_lab.git
%cd kde_ontology_slm_lab

# Step 2. Install. The dev extras pull in pytest, ruff, and the lab's own deps.
!pip install -e ".[dev]"

# Step 3. Run the vertical slice.
!python examples/run_mini_repo_pipeline.py

# Step 4. Inspect artifacts.
!ls artifacts/
```

That is the complete CPU-only flow. The pipeline writes to `artifacts/` relative to the Colab working directory, which sits in the ephemeral VM filesystem.

Open the artifacts in the notebook:

```python
import json
from pathlib import Path
graph = json.loads(Path("artifacts/graphs/mini_repo.json").read_text())
print(len(graph["nodes"]), "nodes,", len(graph["edges"]), "edges")
```

A reasonable second step is to read the v0 eval report and the tokenizer report:

```python
print(Path("artifacts/eval_reports/mini_repo_eval.md").read_text())
print(Path("artifacts/tokenizer_reports/fallback_token_cost.json").read_text())
```

## T4 GPU path

Switch the runtime to **T4 GPU** under *Runtime > Change runtime type*. Confirm with `!nvidia-smi`. You should see one T4 with ~15 360 MiB.

Add the training dependencies (these are not part of the v0 pipeline so the lab does not auto-install them):

```python
!pip install -q transformers peft accelerate bitsandbytes trl datasets
```

Or, if you want the fast path:

```python
!pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

Note: those installs trigger network access. Do them explicitly; the v0 pipeline does not.

Now download the base model **manually** with your own credentials:

```python
from huggingface_hub import login
login(token="<your token>")    # only if the model is gated
from transformers import AutoTokenizer, AutoModelForCausalLM
base = "<org/model-name>"      # e.g. a small Qwen / SmolLM / TinyLlama / Gemma-small variant
tok = AutoTokenizer.from_pretrained(base)
mdl = AutoModelForCausalLM.from_pretrained(base, torch_dtype="auto")
```

Wrap that in your dataset:

```python
from datasets import load_dataset
ds = load_dataset("json", data_files="artifacts/datasets/mini_repo_sft_v0.jsonl")["train"]
```

The lab's SFT helper script (`scripts/train_unsloth_lora.sh`, in flight) shows the exact arguments for `trl.SFTTrainer` or Unsloth's wrapper. The key recipes for Colab T4:

- Use QLoRA (`load_in_4bit=True`) for anything over ~1 B params.
- Set `per_device_train_batch_size=2`, `gradient_accumulation_steps=4` (effective batch 8).
- `max_seq_length=1024` is a sweet spot.
- Set `bf16=False, fp16=True` on T4 — bf16 is slow on Volta/Turing cards.
- 2 epochs over the mini-repo dataset (~50 records) takes a few minutes.

This is a *demo*, not a real training run — the mini-repo dataset is too small to teach anything robust. The point of running it on Colab is to verify that the toolchain works end-to-end before you scale up to a real KDE ingest.

## What to copy from the repo

Everything under [../src/](../src/), [../examples/](../examples/), [../configs/](../configs/), and [../scripts/](../scripts/). The `git clone` step covers it. You do not need to copy [../artifacts/](../artifacts/) — those are generated.

You probably do not need [../docs/](../docs/) on Colab unless you want to read them in-notebook.

## What to skip

- [../observability/](../observability/) — the full Docker stack is irrelevant on Colab. The no-install fallback under `observability/exporters/` works because it just writes JSONL/CSV. Skip the Docker piece.
- Heavy notebooks under [../notebooks/](../notebooks/) — open the ones that are about CPU-only analysis (tokenizer, ontology, graph). Skip training notebooks unless you are on GPU.
- The `local_*` profile configs in `configs/training.yaml`. Use `colab_t4`.

## Storage gotchas

Three traps to know about:

### 1. The VM filesystem is ephemeral

When the runtime disconnects, `/content` is wiped. If you spent two hours training a model and forgot to save it, it is gone.

**Mitigation:** save adapters and reports to Google Drive. Mount it once at the top of your notebook:

```python
from google.colab import drive
drive.mount('/content/drive')
ADAPTER_DIR = "/content/drive/MyDrive/kde-lab/adapters"
!mkdir -p {ADAPTER_DIR}
```

Then point your training script's `output_dir` at `ADAPTER_DIR`.

### 2. Disk is small

T4 runtimes have ~70 GB of disk; CPU runtimes have ~100 GB. Caching a 7 B base model eats ~14 GB before you train anything. If you intend to compare multiple base models in one session, you will fill the disk.

**Mitigation:** delete the model cache between runs (`!rm -rf ~/.cache/huggingface/hub`) and download only the model you need this session.

### 3. Bandwidth is metered

Free Colab runtimes do not have unlimited bandwidth. Downloading a 7 B base model can take 20+ minutes and may time out.

**Mitigation:** snapshot the base model to Drive once and load from there:

```python
mdl.save_pretrained("/content/drive/MyDrive/kde-lab/base-snapshots/<model-name>")
tok.save_pretrained("/content/drive/MyDrive/kde-lab/base-snapshots/<model-name>")
```

Subsequent sessions load from Drive instead of HuggingFace.

## Downloading artifacts back to your machine

After a Colab session, you usually want the adapter and the eval reports locally.

```python
from google.colab import files
import shutil
shutil.make_archive("kde-lab-adapter", "zip", "/content/drive/MyDrive/kde-lab/adapters")
files.download("kde-lab-adapter.zip")
```

Or if everything fits under 1 GB and you do not use Drive:

```python
shutil.make_archive("kde-lab-artifacts", "zip", "artifacts")
files.download("kde-lab-artifacts.zip")
```

## A reproducible session shape

A pattern that works:

```
[1] Mount Drive.
[2] Clone repo.
[3] pip install -e ".[dev]".
[4] python examples/run_mini_repo_pipeline.py  (CPU work — confirms toolchain.)
[5] Switch runtime to T4. Mount Drive again.
[6] pip install training extras.
[7] Load base from Drive snapshot (or first-time download to Drive).
[8] Run scripts/train_unsloth_lora.sh (Stage 2 of training).
[9] Save adapter to Drive.
[10] Run python -m src.eval.eval_runner (when v0.1 lands the runner).
[11] Download eval report and adapter zip.
```

Saving each step to Drive keeps you from re-doing work when the runtime disconnects.

## Recipes-only stays in effect on Colab

The lab's policy is the same on Colab: no auto-downloads from the pipeline itself. The pipeline runs `python examples/run_mini_repo_pipeline.py` and writes only to local disk. Any model or tokenizer download is your explicit `huggingface_hub` call, your explicit `from_pretrained`. The `configs/repos.yaml` machinery for ingesting real KDE source is also explicit; the pipeline does not phone home.

That makes Colab safe for trying things — you cannot accidentally download a 30 GB model because some inner module decided to.

## Exercises

1. Open a free Colab runtime (CPU). Run steps 1–4 of the CPU-only path. Confirm the eval pass rate matches what you get locally.
2. Switch to T4. Run `!nvidia-smi`. Note the available memory. Decide which compute profile in chapter 07 best matches.
3. Pick one small base model. Snapshot it to your Drive. Confirm a subsequent runtime can `from_pretrained` straight from Drive without network.
4. Add a cell that prints the tokenizer report's `summary` field for both the offline fallback and the snapshotted base tokenizer. Compute the compression delta on the canonical phrases.
5. Sketch a Colab "session contract" — three or four lines describing exactly what the user must save to Drive before disconnecting to make the next session resumable.

## Further reading

- Google Colab's documentation pages, particularly *Runtime types*, *Storage*, and *Saving and loading data*.
- The HuggingFace `transformers` "Quick tour" page for `from_pretrained` patterns.
- The Unsloth GitHub README for the Colab notebooks they maintain.
- The `bitsandbytes` documentation on `load_in_4bit`.
- The TRL library's `SFTTrainer` reference page.
- "Practical Recommendations for QLoRA Fine-Tuning" — search HuggingFace blog.
- The Kaggle notebooks for KDE / Qt / GTK code corpora (search Kaggle for "Qt source") — they show how others have approached limited-bandwidth dataset prep.
