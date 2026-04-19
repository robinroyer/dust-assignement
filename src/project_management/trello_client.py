"""Trello implementation of ProjectManagementTool.

Authentication uses three environment variables:
  TRELLO_API_KEY    — from https://trello.com/power-ups/admin
  TRELLO_API_SECRET — from the same page
  TRELLO_TOKEN      — OAuth token (run `python -m trello oauth` to generate one)

CLI usage (run from project root):
  python -m project_management.trello_client list-boards
  python -m project_management.trello_client get-board <board_id>
  python -m project_management.trello_client get-lists <board_id>
  python -m project_management.trello_client get-cards <list_id>
  python -m project_management.trello_client get-card <card_id>
  python -m project_management.trello_client move-card <card_id> <target_list_id>
  python -m project_management.trello_client update-card <card_id> [--name NAME] [--description DESC] [--due YYYY-MM-DD] [--closed]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Optional

from trello import TrelloClient

from .abstract import ProjectManagementTool
from .models import Board, BoardList, Card


class TrelloProjectManagementTool(ProjectManagementTool):
    """Trello-backed implementation using the py-trello library."""

    def __init__(self, api_key: str, api_secret: str, token: str) -> None:
        self._client = TrelloClient(api_key=api_key, api_secret=api_secret, token=token)

    @classmethod
    def from_env(cls) -> "TrelloProjectManagementTool":
        missing = [v for v in ("TRELLO_API_KEY", "TRELLO_API_SECRET", "TRELLO_TOKEN") if not os.getenv(v)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(
            api_key=os.environ["TRELLO_API_KEY"],
            api_secret=os.environ["TRELLO_API_SECRET"],
            token=os.environ["TRELLO_TOKEN"],
        )

    # ------------------------------------------------------------------
    # ProjectManagementTool interface
    # ------------------------------------------------------------------

    def list_boards(self) -> List[Board]:
        return [self._map_board(b) for b in self._client.list_boards()]

    def get_board(self, board_id: str) -> Board:
        return self._map_board(self._client.get_board(board_id))

    def get_lists(self, board_id: str) -> List[BoardList]:
        board = self._client.get_board(board_id)
        return [self._map_list(lst) for lst in board.open_lists()]

    def get_cards(self, list_id: str) -> List[Card]:
        lst = self._client.get_list(list_id)
        return [self._map_card(c) for c in lst.list_cards()]

    def get_card(self, card_id: str) -> Card:
        card = self._client.get_card(card_id)
        card.fetch(eager=True)
        return self._map_card(card)

    def move_card(self, card_id: str, target_list_id: str) -> Card:
        card = self._client.get_card(card_id)
        card.change_list(target_list_id)
        return self._map_card(card)

    def update_card(
        self,
        card_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due: Optional[datetime] = None,
        closed: Optional[bool] = None,
    ) -> Card:
        card = self._client.get_card(card_id)
        if name is not None:
            card.set_name(name)
        if description is not None:
            card.set_description(description)
        if due is not None:
            card.set_due(due)
        if closed is not None:
            card.set_closed(closed)
        return self._map_card(card)

    # ------------------------------------------------------------------
    # Private mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_board(b) -> Board:
        return Board(
            id=b.id,
            name=b.name,
            description=getattr(b, "description", None) or "",
            closed=getattr(b, "closed", False),
        )

    @staticmethod
    def _map_list(lst) -> BoardList:
        return BoardList(
            id=lst.id,
            name=lst.name,
            board_id=lst.board.id,
            pos=float(getattr(lst, "pos", 0) or 0),
            closed=getattr(lst, "closed", False),
        )

    @staticmethod
    def _map_card(c) -> Card:
        labels = [lbl.name for lbl in (getattr(c, "labels", None) or []) if lbl.name]
        return Card(
            id=c.id,
            name=c.name,
            list_id=c.list_id,
            board_id=c.board_id,
            description=getattr(c, "description", None) or "",
            due=c.due_date,
            labels=labels,
            member_ids=list(c.member_id or []),
            closed=getattr(c, "closed", False),
            url=getattr(c, "short_url", None) or "",
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _to_dict(obj) -> dict:
    d = obj.__dict__.copy()
    if d.get("due") and isinstance(d["due"], datetime):
        d["due"] = d["due"].isoformat()
    return d


def _print_json(data) -> None:
    if isinstance(data, list):
        print(json.dumps([_to_dict(item) for item in data], indent=2))
    else:
        print(json.dumps(_to_dict(data), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="project_management.trello_client", description="CLI for the Trello ProjectManagementTool")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-boards")

    p = sub.add_parser("get-board")
    p.add_argument("board_id")

    p = sub.add_parser("get-lists")
    p.add_argument("board_id")

    p = sub.add_parser("get-cards")
    p.add_argument("list_id")

    p = sub.add_parser("get-card")
    p.add_argument("card_id")

    p = sub.add_parser("move-card")
    p.add_argument("card_id")
    p.add_argument("target_list_id")

    p = sub.add_parser("update-card")
    p.add_argument("card_id")
    p.add_argument("--name", default=None)
    p.add_argument("--description", default=None)
    p.add_argument("--due", default=None, metavar="YYYY-MM-DD")
    p.add_argument("--closed", action="store_true", default=None)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        client = TrelloProjectManagementTool.from_env()
    except EnvironmentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.command == "list-boards":
            _print_json(client.list_boards())
        elif args.command == "get-board":
            _print_json(client.get_board(args.board_id))
        elif args.command == "get-lists":
            _print_json(client.get_lists(args.board_id))
        elif args.command == "get-cards":
            _print_json(client.get_cards(args.list_id))
        elif args.command == "get-card":
            _print_json(client.get_card(args.card_id))
        elif args.command == "move-card":
            _print_json(client.move_card(args.card_id, args.target_list_id))
        elif args.command == "update-card":
            due = datetime.strptime(args.due, "%Y-%m-%d") if args.due else None
            closed = True if args.closed else None
            _print_json(client.update_card(args.card_id, name=args.name, description=args.description, due=due, closed=closed))
    except (KeyError, Exception) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
