include .env
export

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help

DOCKER_USER ?= $(shell docker info 2>/dev/null | grep Username | awk '{print $$2}')
IMAGE_TAG ?= latest

.PHONY: help install clean trello dust sync test build-script build-mcp push-script push-mcp

help:
	@echo "Available targets:"
	@echo "  install       Create virtual environment and install dependencies"
	@echo "  clean         Remove the virtual environment"
	@echo "  trello        Run the Trello client  (pass ARGS=\"<subcommand> [params]\")"
	@echo "  dust          Run the Dust client    (pass ARGS=\"<subcommand> [params]\")"
	@echo "  sync          Run the sync use case  (pass ARGS=\"<space_id> <ds_id> 'Board'\")"
	@echo "  test          Run all integration tests"
	@echo "  build-script  Build the synchronize-trello-to-dust Docker image"
	@echo "  build-mcp     Build the MCP server Docker image"
	@echo "  push-script   Tag and push synchronize-trello-to-dust to Docker Hub (IMAGE_TAG=<tag>)"
	@echo "  push-mcp      Tag and push dust-sync-mcp to Docker Hub         (IMAGE_TAG=<tag>)"

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

build-script:
	docker build -f build/Dockerfile -t synchronize-trello-to-dust .

build-mcp:
	docker build -f build/Dockerfile.mcp -t dust-sync-mcp .

push-script: build-script
	docker tag synchronize-trello-to-dust $(DOCKER_USER)/synchronize-trello-to-dust:$(IMAGE_TAG)
	docker push $(DOCKER_USER)/synchronize-trello-to-dust:$(IMAGE_TAG)

push-mcp: build-mcp
	docker tag dust-sync-mcp $(DOCKER_USER)/dust-sync-mcp:$(IMAGE_TAG)
	docker push $(DOCKER_USER)/dust-sync-mcp:$(IMAGE_TAG)

clean:
	rm -rf $(VENV)
