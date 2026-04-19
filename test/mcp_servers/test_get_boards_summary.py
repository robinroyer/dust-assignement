"""Integration tests for the get_boards_summary MCP tool.

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


def test_returns_counts_for_found_board(pm):
    board = pm.seed_board("Software Engineering", description="Eng team board")
    todo = pm.seed_list(board.id, "To Do")
    done = pm.seed_list(board.id, "Done")
    pm.seed_card(todo.id, board.id, "Fix login bug")
    pm.seed_card(todo.id, board.id, "Add dark mode")
    pm.seed_card(done.id, board.id, "Setup CI")

    result = server_module.get_boards_summary(["Software Engineering"])

    assert result["skipped"] == []
    assert len(result["boards"]) == 1
    b = result["boards"][0]
    assert b.name == "Software Engineering"
    assert b.description == "Eng team board"
    assert b.list_count == 2
    assert b.card_count == 3


def test_unknown_board_goes_to_skipped(pm):
    result = server_module.get_boards_summary(["Unknown Board"])

    assert result["boards"] == []
    assert result["skipped"] == ["Unknown Board"]


def test_mix_of_found_and_skipped(pm):
    board = pm.seed_board("Product")
    lst = pm.seed_list(board.id, "Backlog")
    pm.seed_card(lst.id, board.id, "Feature X")

    result = server_module.get_boards_summary(["Product", "Missing Board"])

    assert len(result["boards"]) == 1
    assert result["boards"][0].name == "Product"
    assert result["skipped"] == ["Missing Board"]


def test_empty_board_has_zero_counts(pm):
    pm.seed_board("Sales")

    result = server_module.get_boards_summary(["Sales"])

    assert result["skipped"] == []
    b = result["boards"][0]
    assert b.list_count == 0
    assert b.card_count == 0


def test_multiple_boards_aggregated_independently(pm):
    b1 = pm.seed_board("Sales")
    lst1 = pm.seed_list(b1.id, "Active")
    pm.seed_card(lst1.id, b1.id, "Deal A")

    b2 = pm.seed_board("Engineering")
    lst2 = pm.seed_list(b2.id, "Sprint")
    pm.seed_card(lst2.id, b2.id, "Task 1")
    pm.seed_card(lst2.id, b2.id, "Task 2")

    result = server_module.get_boards_summary(["Sales", "Engineering"])

    by_name = {b.name: b for b in result["boards"]}
    assert by_name["Sales"].card_count == 1
    assert by_name["Engineering"].list_count == 1
    assert by_name["Engineering"].card_count == 2
    assert result["skipped"] == []
