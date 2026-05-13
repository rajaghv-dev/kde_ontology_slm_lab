"""`kde-lab eval` — grade the RAG baseline (or future models) against the eval set."""
from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("eval", help="Grade a model's answers against the hand-authored eval set.")
    @click.option("--model-id", "model_id", default="rag-baseline", show_default=True,
                  help="In v0 only 'rag-baseline' is wired up (no learned model needed).")
    @click.option("--repo", "repo_name", default="mini_kde_repo", show_default=True,
                  help="Which graph to use for retrieval (artifacts/graphs/<repo>.json).")
    def eval_cmd(model_id: str, repo_name: str) -> None:
        import json

        import networkx as nx

        from src.common.logging import get_logger
        from src.common.paths import EVAL_DIR, GRAPHS_DIR, ensure_dirs
        from src.dataset.jsonl_writer import write_jsonl
        from src.eval.answer_grader import grade
        from src.eval.eval_set_builder import mini_repo_eval_set
        from src.eval.report import aggregate, save as save_report
        from src.rag.answer_with_evidence import answer

        log = get_logger("cli.eval")
        ensure_dirs()

        if model_id != "rag-baseline":
            raise click.ClickException(
                f"model id {model_id!r} not wired in v0. Only 'rag-baseline' is supported; "
                "real model eval ships with the training extras."
            )

        graph_path = GRAPHS_DIR / f"{repo_name}.json"
        if not graph_path.exists():
            raise click.ClickException(
                f"no graph at {graph_path}; run `kde-lab ingest --repo {repo_name}` first."
            )

        with graph_path.open("r", encoding="utf-8") as f:
            blob = json.load(f)
        g: nx.MultiDiGraph = nx.MultiDiGraph()
        for n in blob.get("nodes", []):
            nid = n["id"]
            attrs = {k: v for k, v in n.items() if k != "id"}
            g.add_node(nid, **attrs)
        for e in blob.get("edges", []):
            src, dst = e["src"], e["dst"]
            attrs = {k: v for k, v in e.items() if k not in {"src", "dst"}}
            g.add_edge(src, dst, key=attrs.get("rel"), **attrs)

        items = mini_repo_eval_set()
        grades = []
        answers_out = []
        for item in items:
            a = answer(g, item["question"], k=6)
            grades.append(grade(a.text, item))
            answers_out.append({
                "id": item["id"], "question": item["question"],
                "answer": a.text, "evidence_refs": a.evidence_refs,
            })

        rep_data = aggregate(grades)
        write_jsonl(EVAL_DIR / f"{repo_name}_answers.jsonl", answers_out)
        jp, mp = save_report(rep_data, EVAL_DIR, name=f"{repo_name}_eval")

        n_pass = sum(1 for r in grades if r.passed)
        click.echo(f"model                : {model_id}")
        click.echo(f"items                : {len(items)}")
        click.echo(f"pass rate            : {rep_data['overall_pass_rate']:.2%}  "
                   f"({n_pass} / {len(grades)})")
        click.echo(f"mean recall          : {rep_data['overall_mean_recall']:.2%}")
        click.echo(f"json report          : {jp}")
        click.echo(f"markdown report      : {mp}")
        log.info(f"eval done for model={model_id} repo={repo_name}")
