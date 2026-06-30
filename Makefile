PYTHON := .venv/bin/python

.PHONY: scheduler run test

scheduler:
	$(PYTHON) -m src.book_ti.scheduler

run:
	$(PYTHON) run.py

test:
	$(PYTHON) -m pytest -q
