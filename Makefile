.PHONY: install dev test lint typecheck format check clean dashboard

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest --cov=aedm --cov-report=term-missing

lint:
	ruff check src/ tests/

typecheck:
	mypy src/aedm/ --ignore-missing-imports

format:
	ruff format src/ tests/

check: lint typecheck test

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

dashboard:
	streamlit run src/aedm/dashboard/app.py

analyze-sample:
	aedm analyze --input data/sample/acme_corp_roles.csv --output report/
