"""End-to-end vertical slice for kde_ontology_slm_lab.

What this script does, in order:

1. Scans the synthetic mini KDE repo.
2. Runs the per-format readers (C++, QML, CMake, D-Bus, KConfig, desktop, log).
3. Extracts ontology entities + relations.
4. Builds a NetworkX graph and saves JSON + GraphML.
5. Runs a traceability query against an embedded symptom.
6. Runs a tokenizer token-cost analysis (offline fallback by default).
7. Generates an SFT JSONL dataset from the graph.
8. Produces a RAG answer with cited evidence for each eval question.
9. Grades the answers and writes a JSON + Markdown eval report.

Run it:
    python examples/run_mini_repo_pipeline.py

Output goes to ``artifacts/`` and a short summary is printed to stdout.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the repo importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.ids import trace_id
from src.common.logging import get_logger
from src.common.paths import (
    DATASETS_OUT_DIR,
    EVAL_DIR,
    GRAPHS_DIR,
    MINI_REPO,
    ONTOLOGY_DIR,
    TOKENIZER_DIR,
    ensure_dirs,
)
from src.dataset.jsonl_writer import write_jsonl
from src.dataset.qa_generator import generate as generate_sft
from src.eval.answer_grader import grade
from src.eval.eval_set_builder import mini_repo_eval_set
from src.eval.report import aggregate, save as save_report
from src.graph.builder import build_graph, save_graphml, save_json
from src.ontology.extractor import (
    ExtractionBundle,
    from_cmake,
    from_cpp,
    from_dbus,
    from_desktop,
    from_kconfig,
    from_log,
    from_qml,
)
from src.ontology.schema import Entity
from src.rag.answer_with_evidence import answer
from src.repo_ingest.cmake_reader import read_cmake
from src.repo_ingest.cpp_reader import read_cpp
from src.repo_ingest.dbus_reader import read_dbus
from src.repo_ingest.desktop_file_reader import read_desktop
from src.repo_ingest.kconfig_reader import read_kconfig
from src.repo_ingest.log_reader import read_log
from src.repo_ingest.qml_reader import read_qml
from src.repo_ingest.scanner import scan
from src.tokenizer.analyze_tokens import analyze, save_report as save_tokenizer_report
from src.common.ids import make_id


def main() -> int:
    ensure_dirs()
    log = get_logger("pipeline")
    tid = trace_id()
    log.info(f"trace={tid} starting end-to-end pipeline against {MINI_REPO}")

    if not MINI_REPO.exists():
        log.error(f"mini repo not found at {MINI_REPO}")
        return 1

    # 1. scan
    report = scan(MINI_REPO)
    log.info(f"trace={tid} scanned {len(report.files)} files")

    # 2-3. ingest + extract
    bundle = ExtractionBundle()
    repo_id = bundle.add_entity(Entity(
        id=make_id("Repository", MINI_REPO.name),
        type="Repository", name=MINI_REPO.name,
        source_path=str(MINI_REPO),
    ))

    for sf in report.by_kind("cmake"):
        from_cmake(bundle, read_cmake(sf.path), repo_id)
    for sf in report.by_kind("cpp_header") + report.by_kind("cpp_source"):
        from_cpp(bundle, read_cpp(sf.path))
    for sf in report.by_kind("qml"):
        from_qml(bundle, read_qml(sf.path))
    for sf in report.by_kind("dbus"):
        from_dbus(bundle, read_dbus(sf.path))
    for sf in report.by_kind("kconfig"):
        from_kconfig(bundle, read_kconfig(sf.path))
    for sf in report.by_kind("desktop"):
        from_desktop(bundle, read_desktop(sf.path))
    for sf in report.by_kind("log"):
        from_log(bundle, read_log(sf.path))

    log.info(f"trace={tid} extracted {len(bundle.entities)} entities, "
             f"{len(bundle.relations)} relations")

    # 4. graph
    g = build_graph(bundle)
    json_path = save_json(g, GRAPHS_DIR / "mini_repo.json")
    graphml_path = save_graphml(g, GRAPHS_DIR / "mini_repo.graphml")
    log.info(f"trace={tid} graph saved: {json_path.name}, {graphml_path.name}")

    # 5. traceability sanity print
    from src.traceability.symptom_to_code import trace as trace_query
    tr = trace_query(g, "MiniSearch is slow when opening folders with many files", k=4)
    log.info(f"trace={tid} traceability evidence count = {len(tr.evidence)}")

    # 6. tokenizer
    rep = analyze()
    tok_path = save_tokenizer_report(rep, TOKENIZER_DIR / "fallback_token_cost.json")
    log.info(f"trace={tid} tokenizer report at {tok_path.name}, "
             f"mean compression = {rep.summary()['mean_compression']:.2f}")

    # 7. SFT dataset
    sft = generate_sft(g)
    sft_path = DATASETS_OUT_DIR / "mini_repo_sft_v0.jsonl"
    n_written = write_jsonl(sft_path, sft)
    log.info(f"trace={tid} wrote {n_written} SFT examples to {sft_path.name}")

    # 8-9. RAG + eval
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
    write_jsonl(EVAL_DIR / "mini_repo_answers.jsonl", answers_out)
    jp, mp = save_report(rep_data, EVAL_DIR, name="mini_repo_eval")
    log.info(f"trace={tid} eval pass rate = {rep_data['overall_pass_rate']:.2%}, "
             f"report at {jp.name} and {mp.name}")

    # Bundle ontology dump for the docs notebooks and for `kde-lab graph --repo mini_kde_repo`
    onto_path = ONTOLOGY_DIR / "mini_repo_entities.jsonl"
    write_jsonl(onto_path, [e.__dict__ for e in bundle.entities.values()])
    rel_path = ONTOLOGY_DIR / "mini_repo_relations.jsonl"
    write_jsonl(rel_path, [r.__dict__ for r in bundle.relations])
    log.info(f"trace={tid} ontology dump at {onto_path.name}")

    print()
    print("=" * 60)
    print("kde_ontology_slm_lab — vertical slice complete")
    print("=" * 60)
    print(f"trace_id           : {tid}")
    print(f"files scanned      : {len(report.files)}")
    print(f"entities           : {len(bundle.entities)}")
    print(f"relations          : {len(bundle.relations)}")
    print(f"graph              : {json_path}")
    print(f"sft jsonl          : {sft_path}  ({n_written} examples)")
    print(f"tokenizer report   : {tok_path}")
    print(f"eval pass rate     : {rep_data['overall_pass_rate']:.2%} "
          f"({sum(1 for r in grades if r.passed)} / {len(grades)})")
    print(f"eval report        : {mp}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
