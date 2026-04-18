include .env
export

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help

.PHONY: help install clean trello dust sync test

help:
	@echo "Available targets:"
	@echo "  install  Create virtual environment and install dependencies"
	@echo "  clean    Remove the virtual environment"
	@echo "  trello   Run the Trello client  (pass ARGS=\"<subcommand> [params]\")"
	@echo "  dust     Run the Dust client    (pass ARGS=\"<subcommand> [params]\")"
	@echo "  sync     Run the sync use case  (pass ARGS=\"<space_id> <ds_id> 'Board'\")"
	@echo "  test     Run all integration tests"

install:
	@python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Virtual environment ready. Activate with: source $(VENV)/bin/activate"

trello:
	PYTHONPATH=src $(PYTHON) -m project_management.trello_client $(ARGS)

dust:
	PYTHONPATH=src $(PYTHON) -m data_sources.dust_client $(ARGS)

sync:
	PYTHONPATH=src $(PYTHON) -m use_cases.synchronize_trello_to_dust $(ARGS)

test:
	$(VENV)/bin/pytest test/ -v

clean:
	rm -rf $(VENV)
