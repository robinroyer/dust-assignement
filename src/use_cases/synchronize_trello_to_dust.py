"""Synchronize Trello boards to Dust — one data source per board per week.

Creates (or reuses) a Dust data source named ``{team}-{year}-W{week}``
(e.g. ``software-2026-W16``) and upserts a single document with the same ID
containing the full board snapshot as nested sections (board → lists → cards).

Successive runs for the same week are idempotent.

Library usage::

    container = SyncContainer()
    container.config.from_dict({
        "trello_api_key": "...", "trello_api_secret": "...", "trello_token": "...",
        "dust_api_key": "...", "dust_workspace_id": "...",
        "space_id": "your-space-id",
    })
    result = synchronize_weekly(["Board Name 1", "Board Name 2"], container)

Script usage (from project root)::

    PYTHONPATH=src python -m use_cases.synchronize_trello_to_dust <space_id> <ds_id> "Board 1" ["Board 2" ...]
    PYTHONPATH=src python -m use_cases.synchronize_trello_to_dust <space_id> <ds_id> --week 2026-W16 "Board 1"
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

from dependency_injector import containers, providers

from data_sources.abstract import AbstractDataSource
from data_sources.dust_client import DustDataSourcesClient
from data_sources.models import Section
from project_management.abstract import ProjectManagementTool
from project_management.models import Board, BoardList, Card
from project_management.trello_client import TrelloProjectManagementTool


# ---------------------------------------------------------------------------
# IOC container
# ---------------------------------------------------------------------------


class SyncContainer(containers.DeclarativeContainer):
    """Dependency-injector container for the weekly sync use case.

    Override individual providers in tests to inject in-memory doubles::

        container = SyncContainer()
        container.project_management.override(providers.Object(InMemoryProjectManagementTool()))
        container.data_source.override(providers.Object(InMemoryDataSource()))
        container.config.from_dict({"space_id": "s1", "ds_id": "ds1"})
    """

    config = providers.Configuration()

    project_management: providers.Provider[ProjectManagementTool] = providers.Singleton(
        TrelloProjectManagementTool,
        api_key=config.trello_api_key,
        api_secret=config.trello_api_secret,
        token=config.trello_token,
    )

    data_source: providers.Provider[AbstractDataSource] = providers.Singleton(
        DustDataSourcesClient,
        api_key=config.dust_api_key,
        workspace_id=config.dust_workspace_id,
    )

    @classmethod
    def from_env(cls, space_id: str, ds_id: str) -> "SyncContainer":
        """Build a container wired to real clients from environment variables."""
        missing = [
            v for v in (
                "TRELLO_API_KEY", "TRELLO_API_SECRET", "TRELLO_TOKEN",
                "DUST_API_KEY", "DUST_WORKSPACE_ID",
            )
            if not os.getenv(v)
        ]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

        container = cls()
        container.config.from_dict({
            "trello_api_key": os.environ["TRELLO_API_KEY"],
            "trello_api_secret": os.environ["TRELLO_API_SECRET"],
            "trello_token": os.environ["TRELLO_TOKEN"],
            "dust_api_key": os.environ["DUST_API_KEY"],
            "dust_workspace_id": os.environ["DUST_WORKSPACE_ID"],
            "space_id": space_id,
            "ds_id": ds_id,
        })
        return container


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class WeeklySyncResult:
    week_label: str
    synced: int
    skipped_boards: List[str] = field(default_factory=list)
    data_source_names: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

_TEAM_TYPES = ("product", "sales", "software")


def _get_team(board_name: str) -> str:
    lower = board_name.lower()
    for team in _TEAM_TYPES:
        if team in lower:
            return team
    return "undefined"


def _current_week_label() -> str:
    cal = date.today().isocalendar()
    return f"{cal[0]}-W{cal[1]:02d}"


def _weekly_doc_id(board_name: str, week_label: str) -> str:
    return f"{_get_team(board_name)}-{week_label}"



def _card_to_section(card: Card) -> Section:
    content = "\n".join([
        f"Card ID: {card.id}",
        f"Description: {card.description or '(none)'}",
        f"Labels: {', '.join(card.labels) if card.labels else '(none)'}",
        f"Members: {', '.join(card.member_ids) if card.member_ids else '(none)'}",
        f"Due: {card.due.isoformat() if card.due else '(none)'}",
        f"URL: {card.url or '(none)'}",
    ])
    return Section(prefix=f"### {card.name}", content=content)


def _build_board_snapshot(
    board: Board,
    lists_with_cards: List[Tuple[BoardList, List[Card]]],
    week_label: str,
    team: str,
) -> Section:
    list_names = ", ".join(lst.name for lst, _ in lists_with_cards) or "(none)"
    board_context = "\n".join([
        f"Week: {week_label}",
        f"Team: {team}",
        f"Description: {board.description or '(none)'}",
        f"Lists: {list_names}",
    ])
    return Section(
        prefix=f"# {board.name}",
        content=board_context,
        sections=[
            Section(
                prefix=f"## {lst.name}",
                sections=[_card_to_section(card) for card in cards],
            )
            for lst, cards in lists_with_cards
        ],
    )


def synchronize_weekly(
    board_names: List[str],
    container: SyncContainer,
    week_label: Optional[str] = None,
) -> WeeklySyncResult:
    """Synchronize named boards to per-board, per-week Dust data sources.

    For each board, creates (or reuses) a data source named ``{team}-{week_label}``
    and upserts a single document with the same ID containing the full board
    snapshot as nested sections (board → lists → cards).

    Args:
        board_names: Names of the Trello boards to sync.
        container: Dependency-injector container providing clients and config.
        week_label: ISO week string like ``2026-W16``. Defaults to current week.

    Returns:
        WeeklySyncResult with the week label, counts, and data source names.
    """
    if week_label is None:
        week_label = _current_week_label()

    pm: ProjectManagementTool = container.project_management()
    ds: AbstractDataSource = container.data_source()
    space_id: str = container.config.space_id()
    ds_id: str = container.config.ds_id()

    board_by_name = {b.name: b for b in pm.list_boards()}

    found: List[Board] = []
    skipped: List[str] = []
    for name in board_names:
        if name in board_by_name:
            found.append(board_by_name[name])
        else:
            skipped.append(name)

    ds_names: List[str] = []
    for board in found:
        team = _get_team(board.name)
        doc_id = _weekly_doc_id(board.name, week_label)

        lists_with_cards: List[Tuple[BoardList, List[Card]]] = [
            (lst, pm.get_cards(lst.id))
            for lst in pm.get_lists(board.id)
        ]

        ds.upsert_document(
            space_id,
            ds_id,
            doc_id,
            section=_build_board_snapshot(board, lists_with_cards, week_label, team),
            title=f"{team} — {week_label}",
            tags=[team, week_label],
        )
        ds_names.append(doc_id)

    return WeeklySyncResult(
        week_label=week_label,
        synced=len(ds_names),
        skipped_boards=skipped,
        data_source_names=ds_names,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="use_cases.synchronize_trello_to_dust",
        description="Synchronize Trello boards to per-board, per-week Dust data sources.",
    )
    parser.add_argument("space_id", help="Dust space ID")
    parser.add_argument("ds_id", help="Dust data source ID")
    parser.add_argument(
        "--week",
        default=None,
        metavar="WEEK",
        help="ISO week label (e.g. 2026-W16). Defaults to the current week.",
    )
    parser.add_argument("boards", nargs="+", metavar="BOARD", help="Trello board names to sync")
    return parser


def main(argv: List[str] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        container = SyncContainer.from_env(args.space_id, args.ds_id)
    except EnvironmentError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    result = synchronize_weekly(args.boards, container, week_label=args.week)
    print(json.dumps({
        "week_label": result.week_label,
        "synced": result.synced,
        "skipped_boards": result.skipped_boards,
        "data_source_names": result.data_source_names,
    }, indent=2))


if __name__ == "__main__":
    main()
