lint:
	ruff check lm
	ruff format --check lm
	mypy lm

fmt:
	ruff format lm
	ruff check --fix lm
	ruff format lm

install:
	cp lm $(HOME)/.local/bin/lm
