"""Integration test for the synchronize_trello_to_dust use case.

Uses InMemoryProjectManagementTool and InMemoryDataSource as test doubles,
injected via dependency-injector provider overrides on SyncContainer.
No real Trello or Dust API calls are made.
"""

from datetime import datetime

import pytest
from dependency_injector import providers

from data_sources.in_memory import InMemoryDataSource
from project_management.in_memory import InMemoryProjectManagementTool
from use_cases.synchronize_trello_to_dust import SyncContainer, SyncResult, synchronize

SPACE_ID = "space-1"
DS_ID = "ds-1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pm():
    return InMemoryProjectManagementTool()


@pytest.fixture
def ds():
    store = InMemoryDataSource()
    store.seed_data_source(SPACE_ID, DS_ID, "Trello Sync")
    return store


@pytest.fixture
def container(pm, ds):
    c = SyncContainer()
    c.project_management.override(providers.Object(pm))
    c.data_source.override(providers.Object(ds))
    c.config.from_dict({"space_id": SPACE_ID, "ds_id": DS_ID})
    yield c
    c.project_management.reset_override()
    c.data_source.reset_override()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cards_are_synced_as_documents(pm, ds, container):
    board = pm.seed_board("Engineering")
    todo = pm.seed_list(board.id, "To Do")
    card = pm.seed_card(todo.id, board.id, "Fix login bug", description="Users cannot log in")

    result = synchronize(["Engineering"], container)

    assert result.synced == 1
    assert result.skipped_boards == []
    assert f"trello-{card.id}" in result.document_ids

    doc = ds.get_document(SPACE_ID, DS_ID, f"trello-{card.id}")
    assert doc.title == "Fix login bug"
    assert "Fix login bug" in doc.section.prefix
    content = doc.section.sections[0].content
    assert "Users cannot log in" in content
    assert "To Do" in content
    assert "Engineering" in content


def test_all_card_fields_are_stored(pm, ds, container):
    board = pm.seed_board("Product")
    backlog = pm.seed_list(board.id, "Backlog")
    due = datetime(2026, 6, 1, 12, 0, 0)
    card = pm.seed_card(
        backlog.id,
        board.id,
        "Design onboarding",
        description="UX overhaul for new users",
        labels=["design", "ux"],
        member_ids=["user-abc", "user-xyz"],
        due=due,
    )

    synchronize(["Product"], container)

    doc = ds.get_document(SPACE_ID, DS_ID, f"trello-{card.id}")
    assert doc.tags == ["design", "ux"]
    content = doc.section.sections[0].content
    assert "UX overhaul for new users" in content
    assert "design" in content
    assert "ux" in content
    assert "user-abc" in content
    assert "user-xyz" in content
    assert "2026-06-01" in content
    assert "Backlog" in content
    assert "Product" in content
    assert card.id in content


def test_multiple_boards_and_lists(pm, ds, container):
    b1 = pm.seed_board("Alpha")
    l1 = pm.seed_list(b1.id, "In Progress")
    c1 = pm.seed_card(l1.id, b1.id, "Task A")
    c2 = pm.seed_card(l1.id, b1.id, "Task B")

    b2 = pm.seed_board("Beta")
    l2 = pm.seed_list(b2.id, "Review")
    c3 = pm.seed_card(l2.id, b2.id, "Task C")

    result = synchronize(["Alpha", "Beta"], container)

    assert result.synced == 3
    assert result.skipped_boards == []
    ids = set(result.document_ids)
    assert {f"trello-{c1.id}", f"trello-{c2.id}", f"trello-{c3.id}"} == ids


def test_unknown_board_is_skipped(pm, ds, container):
    pm.seed_board("Existing Board")

    result = synchronize(["Ghost Board"], container)

    assert result.synced == 0
    assert "Ghost Board" in result.skipped_boards


def test_mixed_known_and_unknown_boards(pm, ds, container):
    board = pm.seed_board("Known")
    lst = pm.seed_list(board.id, "Done")
    card = pm.seed_card(lst.id, board.id, "Finished task")

    result = synchronize(["Known", "Missing"], container)

    assert result.synced == 1
    assert "Missing" in result.skipped_boards
    assert f"trello-{card.id}" in result.document_ids


def test_sync_is_idempotent(pm, ds, container):
    board = pm.seed_board("Stable")
    lst = pm.seed_list(board.id, "Done")
    pm.seed_card(lst.id, board.id, "Completed")

    result1 = synchronize(["Stable"], container)
    result2 = synchronize(["Stable"], container)

    assert result1.synced == result2.synced == 1
    assert result1.document_ids == result2.document_ids
    assert len(ds.list_documents(SPACE_ID, DS_ID, limit=100)) == 1


def test_empty_board_syncs_nothing(pm, ds, container):
    board = pm.seed_board("Empty Board")
    pm.seed_list(board.id, "To Do")

    result = synchronize(["Empty Board"], container)

    assert result.synced == 0
    assert result.skipped_boards == []
    assert result.document_ids == []


def test_document_id_uses_trello_prefix(pm, ds, container):
    board = pm.seed_board("Team")
    lst = pm.seed_list(board.id, "Doing")
    card = pm.seed_card(lst.id, board.id, "Some ticket")

    result = synchronize(["Team"], container)

    assert result.document_ids == [f"trello-{card.id}"]
