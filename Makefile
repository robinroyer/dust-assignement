include .env
export

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help

.PHONY: help install clean trello

help:
	@echo "Available targets:"
	@echo "  install  Create virtual environment and install dependencies"
	@echo "  clean    Remove the virtual environment"
	@echo "  trello   Run the Trello client (pass ARGS=\"<subcommand> [params]\")"

install:
	@python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Virtual environment ready. Activate with: source $(VENV)/bin/activate"

trello:
	$(PYTHON) src/project-management/trello_client.py $(ARGS)

clean:
	rm -rf $(VENV)
