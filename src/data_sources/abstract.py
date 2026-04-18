from abc import ABC, abstractmethod
from typing import List, Optional

from .models import DataSource, Document, Section


class AbstractDataSource(ABC):
    """Abstract interface for Dust data-source operations."""

    @abstractmethod
    def list_data_sources(self, space_id: str) -> List[DataSource]:
        """Return all data sources available in a space."""

    @abstractmethod
    def list_documents(
        self,
        space_id: str,
        ds_id: str,
        *,
        limit: int = 10,
        offset: int = 0,
        document_ids: Optional[List[str]] = None,
    ) -> List[Document]:
        """Return documents in a data source with optional pagination."""

    @abstractmethod
    def get_document(self, space_id: str, ds_id: str, document_id: str) -> Document:
        """Return a single document by ID."""

    @abstractmethod
    def upsert_document(
        self,
        space_id: str,
        ds_id: str,
        document_id: str,
        *,
        text: Optional[str] = None,
        section: Optional[Section] = None,
        title: Optional[str] = None,
        mime_type: Optional[str] = None,
        source_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        timestamp: Optional[int] = None,
        light_document_output: bool = False,
        async_processing: bool = False,
    ) -> Document:
        """Create or update a document within a data source."""

    @abstractmethod
    def delete_document(self, space_id: str, ds_id: str, document_id: str) -> None:
        """Remove a document from a data source."""

    @abstractmethod
    def search_documents(
        self,
        space_id: str,
        ds_id: str,
        query: str,
        *,
        top_k: int = 10,
        tags: Optional[List[str]] = None,
    ) -> List[Document]:
        """Search for documents using a full-text query."""
