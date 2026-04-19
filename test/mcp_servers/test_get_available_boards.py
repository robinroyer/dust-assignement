"""Integration tests for the get_available_boards MCP tool.

Uses InMemoryProjectManagementTool injected via monkeypatch on _get_pm,
so no real Trello API calls are made.
"""

import os

os.environ.setdefault("MCP_AUTH_TOKEN", "test")  # must be set before settings.py is imported

import pytest

import mcp_servers.server as server_module
from project_management.in_memory import InMemoryProjectManagementTool


@pytest.fixture
def pm():
    return InMemoryProjectManagementTool()


@pytest.fixture(autouse=True)
def inject_pm(pm, monkeypatch):
    monkeypatch.setattr(server_module, "_get_pm", lambda: pm)


def test_returns_all_board_names_when_no_prefix(pm, monkeypatch):
    monkeypatch.setattr(server_module, "BOARD_PREFIX", "")
    pm.seed_board("Engineering")
    pm.seed_board("Sales")

    result = server_module.get_available_boards()

    assert set(result["boards"]) == {"Engineering", "Sales"}
    assert result["prefix"] == ""


def test_prefix_filters_boards(pm, monkeypatch):
    monkeypatch.setattr(server_module, "BOARD_PREFIX", "home-")
    pm.seed_board("home-engineering")
    pm.seed_board("home-sales")
    pm.seed_board("other-board")

    result = server_module.get_available_boards()

    assert set(result["boards"]) == {"home-engineering", "home-sales"}


def test_prefix_in_response_matches_env(pm, monkeypatch):
    monkeypatch.setattr(server_module, "BOARD_PREFIX", "acme-")
    pm.seed_board("acme-roadmap")

    result = server_module.get_available_boards()

    assert result["prefix"] == "acme-"


def test_no_boards_returns_empty_list(pm, monkeypatch):
    monkeypatch.setattr(server_module, "BOARD_PREFIX", "")

    result = server_module.get_available_boards()

    assert result["boards"] == []


def test_no_boards_match_prefix_returns_empty_list(pm, monkeypatch):
    monkeypatch.setattr(server_module, "BOARD_PREFIX", "home-")
    pm.seed_board("other-board")
    pm.seed_board("unrelated")

    result = server_module.get_available_boards()

    assert result["boards"] == []


def test_closed_boards_are_excluded(pm, monkeypatch):
    monkeypatch.setattr(server_module, "BOARD_PREFIX", "")
    open_board = pm.seed_board("Open Board")
    closed_board = pm.seed_board("Closed Board")
    pm.update_card  # ensure pm has update_card; close via internal state
    pm._boards[closed_board.id].closed = True

    result = server_module.get_available_boards()

    assert result["boards"] == ["Open Board"]


def test_prefix_is_case_sensitive(pm, monkeypatch):
    monkeypatch.setattr(server_module, "BOARD_PREFIX", "Home-")
    pm.seed_board("home-engineering")
    pm.seed_board("Home-sales")

    result = server_module.get_available_boards()

    assert result["boards"] == ["Home-sales"]
