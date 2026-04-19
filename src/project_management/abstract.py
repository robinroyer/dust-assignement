from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .models import Board, BoardList, BoardWithCards, Card, ListWithCards


class ProjectManagementTool(ABC):
    """Abstract interface for project management tools."""

    @abstractmethod
    def list_boards(self) -> List[Board]:
        """Return all boards accessible to the current user."""

    @abstractmethod
    def get_board(self, board_id: str) -> Board:
        """Return a single board by ID."""

    @abstractmethod
    def get_lists(self, board_id: str) -> List[BoardList]:
        """Return all open lists on a board, ordered by position."""

    @abstractmethod
    def get_cards(self, list_id: str) -> List[Card]:
        """Return all open cards in a list, ordered by position."""

    @abstractmethod
    def get_card(self, card_id: str) -> Card:
        """Return full details for a single card."""

    @abstractmethod
    def move_card(self, card_id: str, target_list_id: str) -> Card:
        """Move a card to a different list and return the updated card."""

    @abstractmethod
    def update_card(
        self,
        card_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due: Optional[datetime] = None,
        closed: Optional[bool] = None,
    ) -> Card:
        """Update one or more fields on a card and return the updated card."""

    def get_cards_by_board_names(
        self, board_names: List[str]
    ) -> tuple[List[BoardWithCards], List[str]]:
        """Return cards grouped by board then list, both sorted by name.

        Returns (found_boards, skipped_names) where skipped_names contains
        entries from board_names that did not match any accessible board.
        """
        by_name = {b.name: b for b in self.list_boards()}
        found: List[BoardWithCards] = []
        skipped: List[str] = []
        for name in sorted(board_names):
            board = by_name.get(name)
            if board is None:
                skipped.append(name)
                continue
            lists = sorted(self.get_lists(board.id), key=lambda l: l.name)
            found.append(BoardWithCards(
                id=board.id,
                name=board.name,
                description=board.description,
                lists=[
                    ListWithCards(id=lst.id, name=lst.name, cards=self.get_cards(lst.id))
                    for lst in lists
                ],
            ))
        return found, skipped
