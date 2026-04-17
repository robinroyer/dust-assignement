VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help

.PHONY: help install clean

help:
	@echo "Available targets:"
	@echo "  install  Create virtual environment and install dependencies"
	@echo "  clean    Remove the virtual environment"

install: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate
	@echo "Virtual environment ready. Activate with: source $(VENV)/bin/activate"

clean:
	rm -rf $(VENV)
