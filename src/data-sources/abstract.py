from abc import ABC, abstractmethod
from typing import List, Optional

try:
    from .models import DataSource, Document, Section
except ImportError:
    from models import DataSource, Document, Section


class AbstractDataSource(ABC):
    """Abstract interface for Dust data-source operations.

    Mirrors the Dust REST API surface:
      - List/inspect data sources in a space
      - CRUD on documents within a data source
      - Full-text search within a data source

    All document-level methods take ``space_id`` and ``ds_id`` explicitly so
    implementations remain stateless with respect to routing context.
    """

    # ------------------------------------------------------------------
    # Data source operations
    # ------------------------------------------------------------------

    @abstractmethod
    def list_data_sources(self, space_id: str) -> List[DataSource]:
        """Return all data sources available in a space."""

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

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
        """Return documents in a data source with optional pagination.

        Args:
            space_id: Space identifier.
            ds_id: Data source identifier.
            limit: Maximum number of documents to return.
            offset: Number of documents to skip before returning results.
            document_ids: When provided, only return documents whose IDs are
                in this list.

        Raises:
            KeyError: If the data source does not exist.
        """

    @abstractmethod
    def get_document(self, space_id: str, ds_id: str, document_id: str) -> Document:
        """Return a single document by ID.

        Raises:
            KeyError: If the document or data source does not exist.
        """

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
        """Create or update a document within a data source.

        Either ``text`` or ``section`` must be provided.

        Args:
            space_id: Space identifier.
            ds_id: Data source identifier.
            document_id: Caller-controlled document key (idempotent).
            text: Raw text content to index.
            section: Structured, nestable content (alternative to ``text``).
            title: Human-readable document title.
            mime_type: MIME type hint for the content.
            source_url: Canonical URL of the original source.
            tags: Labels attached to the document for filtering.
            timestamp: Unix timestamp in milliseconds representing document age.
            light_document_output: When True, the returned Document will not
                include text/chunks/vectors (useful for bulk ingestion).
            async_processing: When True, indexing happens asynchronously.

        Returns:
            The created or updated Document.

        Raises:
            KeyError: If the data source does not exist.
            ValueError: If neither ``text`` nor ``section`` is provided.
        """

    @abstractmethod
    def delete_document(self, space_id: str, ds_id: str, document_id: str) -> None:
        """Remove a document from a data source.

        Raises:
            KeyError: If the document or data source does not exist.
        """

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
        """Search for documents using a full-text query.

        Args:
            space_id: Space identifier.
            ds_id: Data source identifier.
            query: Search query string.
            top_k: Maximum number of results to return.
            tags: When provided, restrict results to documents carrying all
                of these tags.

        Returns:
            Matching documents ordered by relevance (most relevant first).

        Raises:
            KeyError: If the data source does not exist.
        """
