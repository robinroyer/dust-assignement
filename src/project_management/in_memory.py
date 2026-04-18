"""In-memory implementation of ProjectManagementTool for integration tests."""

import uuid
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

from .abstract import ProjectManagementTool
from .models import Board, BoardList, Card


class InMemoryProjectManagementTool(ProjectManagementTool):
    """Fully in-memory project management tool for use in tests."""

    def __init__(self) -> None:
        self._boards: Dict[str, Board] = {}
        self._lists: Dict[str, BoardList] = {}
        self._cards: Dict[str, Card] = {}

    # ------------------------------------------------------------------
    # Seed helpers
    # ------------------------------------------------------------------

    def seed_board(self, name: str, description: str = "") -> Board:
        board = Board(id=str(uuid.uuid4()), name=name, description=description)
        self._boards[board.id] = board
        return deepcopy(board)

    def seed_list(self, board_id: str, name: str, pos: float = 0.0) -> BoardList:
        if board_id not in self._boards:
            raise KeyError(f"Board {board_id!r} not found")
        lst = BoardList(id=str(uuid.uuid4()), name=name, board_id=board_id, pos=pos)
        self._lists[lst.id] = lst
        return deepcopy(lst)

    def seed_card(
        self,
        list_id: str,
        board_id: str,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        member_ids: Optional[List[str]] = None,
        due: Optional[datetime] = None,
    ) -> Card:
        if list_id not in self._lists:
            raise KeyError(f"List {list_id!r} not found")
        card = Card(
            id=str(uuid.uuid4()),
            name=name,
            list_id=list_id,
            board_id=board_id,
            description=description,
            labels=labels or [],
            member_ids=member_ids or [],
            due=due,
        )
        self._cards[card.id] = card
        return deepcopy(card)

    # ------------------------------------------------------------------
    # ProjectManagementTool interface
    # ------------------------------------------------------------------

    def list_boards(self) -> List[Board]:
        return [deepcopy(b) for b in self._boards.values() if not b.closed]

    def get_board(self, board_id: str) -> Board:
        if board_id not in self._boards:
            raise KeyError(f"Board {board_id!r} not found")
        return deepcopy(self._boards[board_id])

    def get_lists(self, board_id: str) -> List[BoardList]:
        if board_id not in self._boards:
            raise KeyError(f"Board {board_id!r} not found")
        results = [lst for lst in self._lists.values() if lst.board_id == board_id and not lst.closed]
        return [deepcopy(lst) for lst in sorted(results, key=lambda l: l.pos)]

    def get_cards(self, list_id: str) -> List[Card]:
        if list_id not in self._lists:
            raise KeyError(f"List {list_id!r} not found")
        return [deepcopy(c) for c in self._cards.values() if c.list_id == list_id and not c.closed]

    def get_card(self, card_id: str) -> Card:
        if card_id not in self._cards:
            raise KeyError(f"Card {card_id!r} not found")
        return deepcopy(self._cards[card_id])

    def move_card(self, card_id: str, target_list_id: str) -> Card:
        if card_id not in self._cards:
            raise KeyError(f"Card {card_id!r} not found")
        if target_list_id not in self._lists:
            raise KeyError(f"List {target_list_id!r} not found")
        self._cards[card_id].list_id = target_list_id
        return deepcopy(self._cards[card_id])

    def update_card(
        self,
        card_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due: Optional[datetime] = None,
        closed: Optional[bool] = None,
    ) -> Card:
        if card_id not in self._cards:
            raise KeyError(f"Card {card_id!r} not found")
        card = self._cards[card_id]
        if name is not None:
            card.name = name
        if description is not None:
            card.description = description
        if due is not None:
            card.due = due
        if closed is not None:
            card.closed = closed
        return deepcopy(card)
