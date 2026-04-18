"""Synchronize Trello boards to a Dust data source.

Library usage::

    container = SyncContainer()
    container.config.from_dict({
        "trello_api_key": "...", "trello_api_secret": "...", "trello_token": "...",
        "dust_api_key": "...", "dust_workspace_id": "...",
        "space_id": "your-space-id", "ds_id": "your-ds-id",
    })
    result = synchronize(["Board Name 1", "Board Name 2"], container)

Script usage (from project root)::

    PYTHONPATH=src python -m use_cases.synchronize_trello_to_dust <space_id> <ds_id> "Board 1" ["Board 2" ...]
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import List

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
    """Dependency-injector container for the synchronize use case.

    Default providers wire up the real Trello and Dust clients.
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
class SyncResult:
    synced: int
    skipped_boards: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _card_to_section(card: Card, board: Board, lst: BoardList) -> Section:
    details = "\n".join([
        f"Board: {board.name}",
        f"List: {lst.name}",
        f"Card ID: {card.id}",
        f"Description: {card.description or '(none)'}",
        f"Labels: {', '.join(card.labels) if card.labels else '(none)'}",
        f"Members: {', '.join(card.member_ids) if card.member_ids else '(none)'}",
        f"Due: {card.due.isoformat() if card.due else '(none)'}",
        f"URL: {card.url or '(none)'}",
    ])
    return Section(
        prefix=f"# {card.name}",
        sections=[Section(prefix="## Details", content=details)],
    )


def synchronize(board_names: List[str], container: SyncContainer) -> SyncResult:
    """Synchronize all open cards from the named boards to the Dust data source.

    Each card is upserted as a document using ``trello-{card_id}`` as the
    document ID, making successive runs idempotent.

    Args:
        board_names: Names of the Trello boards to sync.
        container: Dependency-injector container providing clients and config.

    Returns:
        SyncResult with counts and IDs of the synced documents.
    """
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

    document_ids: List[str] = []
    for board in found:
        for lst in pm.get_lists(board.id):
            for card in pm.get_cards(lst.id):
                doc_id = f"trello-{card.id}"
                ds.upsert_document(
                    space_id,
                    ds_id,
                    doc_id,
                    section=_card_to_section(card, board, lst),
                    title=card.name,
                    source_url=card.url or None,
                    tags=list(card.labels),
                )
                document_ids.append(doc_id)

    return SyncResult(synced=len(document_ids), skipped_boards=skipped, document_ids=document_ids)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="use_cases.synchronize_trello_to_dust",
        description="Synchronize Trello boards to a Dust data source.",
    )
    parser.add_argument("space_id", help="Dust space ID")
    parser.add_argument("ds_id", help="Dust data source ID")
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

    result = synchronize(args.boards, container)
    print(json.dumps({
        "synced": result.synced,
        "skipped_boards": result.skipped_boards,
        "document_ids": result.document_ids,
    }, indent=2))


if __name__ == "__main__":
    main()
