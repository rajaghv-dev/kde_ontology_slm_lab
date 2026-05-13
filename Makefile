.PHONY: help install vertical-slice test clean

help:
	@echo "Targets:"
	@echo "  install         Install in editable mode with dev extras"
	@echo "  vertical-slice  Run the end-to-end mini-repo pipeline"
	@echo "  test            Run smoke tests"
	@echo "  clean           Remove generated artifacts"

install:
	pip install -e ".[dev]"

vertical-slice:
	python examples/run_mini_repo_pipeline.py

test:
	pytest -q

clean:
	rm -rf artifacts/graphs/* artifacts/ontology/* artifacts/tokenizer_reports/* \
	       artifacts/datasets/* artifacts/eval_reports/* artifacts/logs/* artifacts/plots/* \
	       __pycache__ src/**/__pycache__ tests/__pycache__
