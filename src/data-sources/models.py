from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Section:
    """Nestable content section of a document.

    Maps directly to the ``section`` field in the Dust upsert payload.
    Sections can be nested arbitrarily deep via the ``sections`` list.
    """

    prefix: Optional[str] = None
    content: Optional[str] = None
    sections: List["Section"] = field(default_factory=list)


@dataclass
class Document:
    """A document stored in a Dust data source."""

    document_id: str
    title: Optional[str] = None
    text: Optional[str] = None
    section: Optional[Section] = None
    source_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    timestamp: Optional[int] = None   # Unix ms
    mime_type: Optional[str] = None
    token_count: Optional[int] = None
    created_at: Optional[int] = None  # Unix ms, set by Dust on first insert


@dataclass
class DataSource:
    """Metadata about a Dust data source."""

    id: str
    name: str
    space_id: str
    description: Optional[str] = None
