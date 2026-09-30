.PHONY: install install-dev lint format typecheck test test-unit test-integration \
        validate-config run coverage clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

typecheck:
	mypy src

test: test-unit test-integration

test-unit:
	pytest tests/unit -m unit

test-integration:
	pytest tests/integration -m integration

coverage:
	pytest --cov=meca_engine --cov-report=html tests/unit tests/integration

validate-config:
	python -m meca_engine.cli.main validate-config

run:
	python -m meca_engine.cli.main run --help

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
