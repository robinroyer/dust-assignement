from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .models import Board, BoardList, Card


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
