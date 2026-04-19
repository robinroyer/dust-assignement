"""MCP server exposing Trello project management tools via FastMCP.

Auth: static bearer token from MCP_AUTH_TOKEN env var, checked on every request.

Secrets passed per-request as HTTP headers (no secrets stored server-side):
  X-Trello-Api-Key       Trello API key
  X-Trello-Api-Secret    Trello API secret
  X-Trello-Token         Trello OAuth token

Run locally:
    MCP_AUTH_TOKEN=secret PYTHONPATH=src uvicorn mcp_servers.server:app --host 0.0.0.0 --port 8080
"""

import contextvars
from dataclasses import dataclass
from typing import List, Optional

from fastmcp import FastMCP
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .settings import BOARD_PREFIX, MCP_AUTH_TOKEN
from project_management.abstract import ProjectManagementTool
from project_management.models import BoardWithCards, Card, ListWithCards
from project_management.trello_client import TrelloProjectManagementTool


@dataclass
class CardResponse:
    id: str
    name: str
    description: str
    due: Optional[str]
    labels: List[str]
    member_ids: List[str]
    url: str

    @classmethod
    def from_model(cls, card: Card) -> "CardResponse":
        return cls(
            id=card.id,
            name=card.name,
            description=card.description,
            due=card.due.isoformat() if card.due else None,
            labels=card.labels,
            member_ids=card.member_ids,
            url=card.url,
        )


@dataclass
class ListResponse:
    id: str
    name: str
    cards: List[CardResponse]

    @classmethod
    def from_model(cls, lst: ListWithCards) -> "ListResponse":
        return cls(
            id=lst.id,
            name=lst.name,
            cards=[CardResponse.from_model(c) for c in lst.cards],
        )


@dataclass
class BoardResponse:
    id: str
    name: str
    description: str
    list_count: int
    card_count: int
    lists: List[ListResponse]

    @classmethod
    def from_model(cls, board: BoardWithCards) -> "BoardResponse":
        lists = [ListResponse.from_model(lst) for lst in board.lists]
        return cls(
            id=board.id,
            name=board.name,
            description=board.description,
            list_count=len(lists),
            card_count=sum(len(lst.cards) for lst in lists),
            lists=lists,
        )

_creds: contextvars.ContextVar[dict] = contextvars.ContextVar("_creds", default={})


class _AuthMiddleware:
    """Pure-ASGI middleware: validates the static bearer token and captures
    Trello credentials from request headers into a contextvar."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope["headers"]}
        auth = headers.get(b"authorization", b"").decode()
        token = auth.removeprefix("Bearer ").strip()

        if token != MCP_AUTH_TOKEN:
            await Response("Unauthorized", status_code=401)(scope, receive, send)
            return

        _creds.set({
            "trello_api_key": headers.get(b"x-trello-api-key", b"").decode(),
            "trello_api_secret": headers.get(b"x-trello-api-secret", b"").decode(),
            "trello_token": headers.get(b"x-trello-token", b"").decode(),
        })

        await self.app(scope, receive, send)


def _get_pm() -> ProjectManagementTool:
    """Build a TrelloProjectManagementTool from the current request credentials."""
    creds = _creds.get()
    return TrelloProjectManagementTool(
        api_key=creds["trello_api_key"],
        api_secret=creds["trello_api_secret"],
        token=creds["trello_token"],
    )


mcp = FastMCP("trello-pm")

@mcp.tool()
def get_available_boards() -> dict:
    """Return board names accessible to the current user, filtered by BOARD_PREFIX env var.

    Returns:
        boards: list of matching board names.
        prefix: the prefix filter that was applied (empty string means no filter).
    """
    pm = _get_pm()
    boards = pm.list_boards()
    names = [b.name for b in boards if b.name.startswith(BOARD_PREFIX)]
    return {"boards": names, "prefix": BOARD_PREFIX}


@mcp.tool()
def get_boards_summary(board_names: list[str]) -> dict:
    """Return a summary of the requested Trello boards with list and card counts.

    Args:
        board_names: Exact names of the boards to summarise.

    Returns:
        boards array (found boards with id, name, description, list_count,
        card_count) and a skipped array for names that could not be matched.
    """
    pm = _get_pm()
    found, skipped = pm.get_cards_by_board_names(board_names)
    return {"boards": [BoardResponse.from_model(b) for b in found], "skipped": skipped}


app = _AuthMiddleware(mcp.http_app())
