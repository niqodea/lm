install:
	cp lm $(HOME)/.local/bin/lm

# ---

venv:
	python3.14 -m venv .venv
	.venv/bin/pip install --group dev

lint:
	ruff check lm
	ruff format --check lm
	mypy lm

test:
	pytest tests --numprocesses auto

fmt:
	ruff format lm
	ruff check --fix lm
	ruff format lm
