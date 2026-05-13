"""`kde-lab graph` — rebuild the graph from persisted ontology JSONL and re-export."""
from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("graph", help="Rebuild the graph from persisted ontology and export JSON + GraphML.")
    @click.option("--repo", "repo_name", default="mini_kde_repo", show_default=True,
                  help="Reads artifacts/ontology/<repo>_entities.jsonl and <repo>_relations.jsonl.")
    @click.option("--out", "out_path", default=None,
                  help="Optional override for the JSON output path. The .graphml sibling is derived.")
    def graph(repo_name: str, out_path: str | None) -> None:
        from pathlib import Path

        from src.common.logging import get_logger
        from src.common.paths import GRAPHS_DIR, ONTOLOGY_DIR, ensure_dirs
        from src.dataset.jsonl_writer import read_jsonl
        from src.graph.builder import build_graph, save_graphml, save_json
        from src.ontology.extractor import ExtractionBundle
        from src.ontology.schema import Entity, Relation

        log = get_logger("cli.graph")
        ensure_dirs()

        ent_path = ONTOLOGY_DIR / f"{repo_name}_entities.jsonl"
        rel_path = ONTOLOGY_DIR / f"{repo_name}_relations.jsonl"
        if not ent_path.exists():
            raise click.ClickException(
                f"no ontology dump at {ent_path}; run `kde-lab ingest --repo {repo_name}` first."
            )

        log.info(f"loading entities from {ent_path}")
        bundle = ExtractionBundle()
        for rec in read_jsonl(ent_path):
            # Entity.__init__ rejects unknown types, which is the safety we want here.
            bundle.add_entity(Entity(**rec))
        if rel_path.exists():
            for rec in read_jsonl(rel_path):
                bundle.add_relation(Relation(**rec))

        g = build_graph(bundle)

        if out_path:
            json_path = Path(out_path)
        else:
            json_path = GRAPHS_DIR / f"{repo_name}.json"
        graphml_path = json_path.with_suffix(".graphml")

        save_json(g, json_path)
        save_graphml(g, graphml_path)

        click.echo(f"nodes                : {g.number_of_nodes()}")
        click.echo(f"edges                : {g.number_of_edges()}")
        click.echo(f"graph json           : {json_path}")
        click.echo(f"graph graphml        : {graphml_path}")
