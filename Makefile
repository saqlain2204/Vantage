.PHONY: help setup install test lint lint-fix typecheck format coverage

# Override with: make setup PYTHON=python3.11
PYTHON ?= python

help:
	@echo "Vantage — available targets:"
	@echo ""
	@echo "  setup      Create a virtual environment and install all dependencies"
	@echo "  install    Install the package in editable mode"
	@echo "  test       Run the test suite with pytest"
	@echo "  lint       Run ruff and mypy"
	@echo "  lint-fix   Auto-fix ruff lint errors"
	@echo "  typecheck  Run mypy only"
	@echo "  format     Auto-format source with ruff"
	@echo "  coverage   Run tests and produce an HTML coverage report"

setup:
	$(PYTHON) -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

install:
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy src/vantage

lint-fix:
	$(PYTHON) -m ruff check --fix .

typecheck:
	$(PYTHON) -m pip install types-PyYAML
	$(PYTHON) -m mypy src/vantage

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check . --fix

coverage:
	$(PYTHON) -m pytest --cov=vantage --cov-report=html --cov-report=term-missing -q

