"""Make sure every public module imports cleanly. This is the cheapest
regression test in the lab and the one most likely to catch a silly bug.
"""

def test_imports_clean():
    import src.common.config           # noqa: F401
    import src.common.ids              # noqa: F401
    import src.common.logging          # noqa: F401
    import src.common.paths            # noqa: F401
    import src.repo_ingest.scanner     # noqa: F401
    import src.repo_ingest.cpp_reader  # noqa: F401
    import src.repo_ingest.qml_reader  # noqa: F401
    import src.repo_ingest.cmake_reader  # noqa: F401
    import src.repo_ingest.dbus_reader   # noqa: F401
    import src.repo_ingest.kconfig_reader  # noqa: F401
    import src.repo_ingest.desktop_file_reader  # noqa: F401
    import src.repo_ingest.log_reader  # noqa: F401
    import src.ontology.schema         # noqa: F401
    import src.ontology.extractor      # noqa: F401
    import src.graph.builder           # noqa: F401
    import src.graph.queries           # noqa: F401
    import src.traceability.symptom_to_code  # noqa: F401
    import src.tokenizer.analyze_tokens  # noqa: F401
    import src.dataset.qa_generator    # noqa: F401
    import src.dataset.jsonl_writer    # noqa: F401
    import src.rag.graph_retriever     # noqa: F401
    import src.rag.answer_with_evidence  # noqa: F401
    import src.eval.eval_set_builder   # noqa: F401
    import src.eval.answer_grader      # noqa: F401
    import src.eval.report             # noqa: F401
