"""MCP server exposing Trello project management tools via FastAPI + FastMCP.

Auth: static bearer token from MCP_AUTH_TOKEN env var, checked on every request.

Secrets passed per-request as HTTP headers (no secrets stored server-side):
  X-Trello-Api-Key       Trello API key
  X-Trello-Api-Secret    Trello API secret
  X-Trello-Token         Trello OAuth token

Run locally:
    MCP_AUTH_TOKEN=secret PYTHONPATH=src uvicorn mcp_servers.server:app --host 0.0.0.0 --port 8080
"""

import contextvars

from fastapi import FastAPI
from fastmcp import FastMCP
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .settings import MCP_AUTH_TOKEN
from project_management.abstract import ProjectManagementTool
from project_management.trello_client import TrelloProjectManagementTool

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
def get_boards_summary(board_names: list[str]) -> dict:
    """Return a summary of the requested Trello boards with list and card counts.

    Args:
        board_names: Exact names of the boards to summarise.

    Returns:
        boards array (found boards with id, name, description, list_count,
        card_count) and a skipped array for names that could not be matched.
    """
    pm = _get_pm()
    by_name = {b.name: b for b in pm.list_boards()}
    summary = []
    skipped = []
    for name in board_names:
        board = by_name.get(name)
        if board is None:
            skipped.append(name)
            continue
        lists = pm.get_lists(board.id)
        card_count = sum(len(pm.get_cards(lst.id)) for lst in lists)
        summary.append({
            "id": board.id,
            "name": board.name,
            "description": board.description,
            "list_count": len(lists),
            "card_count": card_count,
        })
    return {"boards": summary, "skipped": skipped}


app = FastAPI(title="Trello MCP")
app.add_middleware(_AuthMiddleware)
app.mount("/", mcp.http_app())
