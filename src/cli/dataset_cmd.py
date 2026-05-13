"""`kde-lab dataset` — generate the SFT JSONL from the persisted graph."""
from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("dataset", help="Generate the SFT JSONL by running the qa_generator over the graph.")
    @click.option("--n", "limit", default=None, type=int,
                  help="Optional cap on the number of records written.")
    @click.option("--out", "out_path", default=None,
                  help="Override the JSONL output path (default: artifacts/datasets/<repo>_sft_v0.jsonl).")
    @click.option("--repo", "repo_name", default="mini_kde_repo", show_default=True,
                  help="Which graph (in artifacts/graphs/) to read.")
    def dataset(limit: int | None, out_path: str | None, repo_name: str) -> None:
        import json
        from pathlib import Path

        import networkx as nx

        from src.common.logging import get_logger
        from src.common.paths import DATASETS_OUT_DIR, GRAPHS_DIR, ensure_dirs
        from src.dataset.jsonl_writer import write_jsonl
        from src.dataset.qa_generator import generate as generate_sft

        log = get_logger("cli.dataset")
        ensure_dirs()

        graph_path = GRAPHS_DIR / f"{repo_name}.json"
        if not graph_path.exists():
            raise click.ClickException(
                f"no graph at {graph_path}; run `kde-lab ingest --repo {repo_name}` "
                "or `kde-lab graph` first."
            )

        with graph_path.open("r", encoding="utf-8") as f:
            blob = json.load(f)

        # Rebuild a minimal MultiDiGraph from the JSON dump. We keep this
        # local so the dataset command does not need to reach for the
        # ontology layer.
        g: nx.MultiDiGraph = nx.MultiDiGraph()
        for n in blob.get("nodes", []):
            nid = n["id"]
            attrs = {k: v for k, v in n.items() if k != "id"}
            g.add_node(nid, **attrs)
        for e in blob.get("edges", []):
            src = e["src"]
            dst = e["dst"]
            attrs = {k: v for k, v in e.items() if k not in {"src", "dst"}}
            g.add_edge(src, dst, key=attrs.get("rel"), **attrs)

        log.info(f"loaded graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
        records = generate_sft(g)
        if limit is not None:
            records = records[:limit]

        if out_path:
            out = Path(out_path)
        else:
            out = DATASETS_OUT_DIR / f"{repo_name}_sft_v0.jsonl"

        n_written = write_jsonl(out, records)
        click.echo(f"records written      : {n_written}")
        click.echo(f"dataset jsonl        : {out}")
