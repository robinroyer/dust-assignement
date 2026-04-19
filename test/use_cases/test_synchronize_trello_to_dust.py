"""Integration tests for the synchronize_trello_to_dust weekly use case.

Uses InMemoryProjectManagementTool and InMemoryDataSource as test doubles,
injected via dependency-injector provider overrides on SyncContainer.
No real Trello or Dust API calls are made.
"""

from datetime import date, datetime

import pytest
from dependency_injector import providers

from data_sources.in_memory import InMemoryDataSource
from project_management.in_memory import InMemoryProjectManagementTool
from use_cases.synchronize_trello_to_dust import SyncContainer, synchronize_weekly

SPACE_ID = "space-1"
DS_ID = "ds-1"
WEEK_LABEL = "2026-W16"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pm():
    return InMemoryProjectManagementTool()


@pytest.fixture
def ds():
    store = InMemoryDataSource()
    store.seed_data_source(SPACE_ID, DS_ID, "Trello Weekly Sync")
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


def test_board_is_synced_as_single_document(pm, ds, container):
    board = pm.seed_board("Software Engineering")
    todo = pm.seed_list(board.id, "To Do")
    pm.seed_card(todo.id, board.id, "Fix login bug", description="Users cannot log in")

    result = synchronize_weekly(["Software Engineering"], container, week_label=WEEK_LABEL)

    assert result.synced == 1
    assert result.skipped_boards == []
    assert "software-2026-W16" in result.data_source_names

    doc = ds.get_document(SPACE_ID, DS_ID, "software-2026-W16")
    assert doc.title == "software — 2026-W16"
    assert "Software Engineering" in doc.section.prefix
    assert "2026-W16" in doc.section.content
    assert "software" in doc.section.content

    list_section = doc.section.sections[0]
    assert "To Do" in list_section.prefix

    card_section = list_section.sections[0]
    assert "Fix login bug" in card_section.prefix
    assert "Users cannot log in" in card_section.content


def test_all_card_fields_are_stored(pm, ds, container):
    board = pm.seed_board("Product Design")
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

    synchronize_weekly(["Product Design"], container, week_label=WEEK_LABEL)

    doc = ds.get_document(SPACE_ID, DS_ID, "product-2026-W16")
    card_section = doc.section.sections[0].sections[0]
    assert "UX overhaul for new users" in card_section.content
    assert "design" in card_section.content
    assert "ux" in card_section.content
    assert "user-abc" in card_section.content
    assert "user-xyz" in card_section.content
    assert "2026-06-01" in card_section.content
    assert card.id in card_section.content


def test_multiple_boards_produce_separate_documents(pm, ds, container):
    b1 = pm.seed_board("Software Team")
    l1 = pm.seed_list(b1.id, "In Progress")
    pm.seed_card(l1.id, b1.id, "Task A")
    pm.seed_card(l1.id, b1.id, "Task B")

    b2 = pm.seed_board("Product Team")
    l2 = pm.seed_list(b2.id, "Review")
    pm.seed_card(l2.id, b2.id, "Task C")

    result = synchronize_weekly(["Software Team", "Product Team"], container, week_label=WEEK_LABEL)

    assert result.synced == 2
    assert result.skipped_boards == []
    assert set(result.data_source_names) == {"software-2026-W16", "product-2026-W16"}

    software_doc = ds.get_document(SPACE_ID, DS_ID, "software-2026-W16")
    assert len(software_doc.section.sections[0].sections) == 2

    product_doc = ds.get_document(SPACE_ID, DS_ID, "product-2026-W16")
    assert len(product_doc.section.sections[0].sections) == 1


def test_unknown_board_is_skipped(pm, ds, container):
    pm.seed_board("Software Board")

    result = synchronize_weekly(["Ghost Board"], container, week_label=WEEK_LABEL)

    assert result.synced == 0
    assert "Ghost Board" in result.skipped_boards


def test_mixed_known_and_unknown_boards(pm, ds, container):
    board = pm.seed_board("Software Known")
    lst = pm.seed_list(board.id, "Done")
    pm.seed_card(lst.id, board.id, "Finished task")

    result = synchronize_weekly(["Software Known", "Missing"], container, week_label=WEEK_LABEL)

    assert result.synced == 1
    assert "Missing" in result.skipped_boards
    assert "software-2026-W16" in result.data_source_names


def test_sync_is_idempotent(pm, ds, container):
    board = pm.seed_board("Software Stable")
    lst = pm.seed_list(board.id, "Done")
    pm.seed_card(lst.id, board.id, "Completed")

    result1 = synchronize_weekly(["Software Stable"], container, week_label=WEEK_LABEL)
    result2 = synchronize_weekly(["Software Stable"], container, week_label=WEEK_LABEL)

    assert result1.synced == result2.synced == 1
    assert result1.data_source_names == result2.data_source_names
    assert len(ds.list_documents(SPACE_ID, DS_ID, limit=100)) == 1


def test_board_with_no_cards_produces_document(pm, ds, container):
    board = pm.seed_board("Software Empty")
    pm.seed_list(board.id, "To Do")

    result = synchronize_weekly(["Software Empty"], container, week_label=WEEK_LABEL)

    assert result.synced == 1
    assert result.skipped_boards == []
    doc = ds.get_document(SPACE_ID, DS_ID, "software-2026-W16")
    assert doc.section.sections[0].sections == []


def test_document_id_uses_team_and_week(pm, ds, container):
    board = pm.seed_board("Sales Board")
    lst = pm.seed_list(board.id, "Doing")
    pm.seed_card(lst.id, board.id, "Some ticket")

    result = synchronize_weekly(["Sales Board"], container, week_label=WEEK_LABEL)

    assert result.data_source_names == ["sales-2026-W16"]


def test_tags_contain_team_and_week(pm, ds, container):
    board = pm.seed_board("Product Board")
    lst = pm.seed_list(board.id, "Backlog")
    pm.seed_card(lst.id, board.id, "Feature")

    synchronize_weekly(["Product Board"], container, week_label=WEEK_LABEL)

    doc = ds.get_document(SPACE_ID, DS_ID, "product-2026-W16")
    assert "product" in doc.tags
    assert WEEK_LABEL in doc.tags


def test_week_label_defaults_to_current_week(pm, container):
    board = pm.seed_board("Software Current")
    lst = pm.seed_list(board.id, "Backlog")
    pm.seed_card(lst.id, board.id, "Feature")

    result = synchronize_weekly(["Software Current"], container)

    cal = date.today().isocalendar()
    assert result.week_label == f"{cal[0]}-W{cal[1]:02d}"
