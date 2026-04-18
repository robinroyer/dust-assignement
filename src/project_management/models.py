from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Board:
    id: str
    name: str
    description: str = ""
    closed: bool = False


@dataclass
class BoardList:
    id: str
    name: str
    board_id: str
    pos: float = 0.0
    closed: bool = False


@dataclass
class Card:
    id: str
    name: str
    list_id: str
    board_id: str
    description: str = ""
    due: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    member_ids: List[str] = field(default_factory=list)
    closed: bool = False
    url: str = ""
