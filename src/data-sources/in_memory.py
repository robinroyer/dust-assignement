"""In-memory implementation of AbstractDataSource.

Intended for unit and integration tests. All data lives in plain Python dicts
and is lost when the object is garbage-collected.

Usage in tests::

    from in_memory import InMemoryDataSource

    store = InMemoryDataSource()
    ds = store.seed_data_source("space-1", "ds-1", "My Knowledge Base")
    doc = store.upsert_document(
        "space-1", "ds-1", "doc-1",
        text="Hello world",
        title="Intro",
        tags=["onboarding"],
    )

    results = store.search_documents("space-1", "ds-1", "hello")
    assert results[0].document_id == "doc-1"
"""

import time
import uuid
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

try:
    from .abstract import AbstractDataSource
    from .models import DataSource, Document, Section
except ImportError:
    from abstract import AbstractDataSource
    from models import DataSource, Document, Section


class InMemoryDataSource(AbstractDataSource):
    """Fully in-memory data source implementation for tests."""

    def __init__(self) -> None:
        # (space_id, ds_id) -> DataSource
        self._data_sources: Dict[Tuple[str, str], DataSource] = {}
        # (space_id, ds_id, document_id) -> Document
        self._documents: Dict[Tuple[str, str, str], Document] = {}

    # ------------------------------------------------------------------
    # Seed helpers
    # ------------------------------------------------------------------

    def seed_data_source(
        self,
        space_id: str,
        ds_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> DataSource:
        """Register a data source. Returns the new object."""
        ds = DataSource(id=ds_id, name=name, space_id=space_id, description=description)
        self._data_sources[(space_id, ds_id)] = ds
        return deepcopy(ds)

    # ------------------------------------------------------------------
    # AbstractDataSource interface
    # ------------------------------------------------------------------

    def list_data_sources(self, space_id: str) -> List[DataSource]:
        return [
            deepcopy(ds)
            for (sid, _), ds in self._data_sources.items()
            if sid == space_id
        ]

    def list_documents(
        self,
        space_id: str,
        ds_id: str,
        *,
        limit: int = 10,
        offset: int = 0,
        document_ids: Optional[List[str]] = None,
    ) -> List[Document]:
        self._require_data_source(space_id, ds_id)
        docs = [
            doc
            for (sid, did, _), doc in self._documents.items()
            if sid == space_id and did == ds_id
        ]
        if document_ids is not None:
            id_set = set(document_ids)
            docs = [d for d in docs if d.document_id in id_set]
        return [deepcopy(d) for d in docs[offset: offset + limit]]

    def get_document(self, space_id: str, ds_id: str, document_id: str) -> Document:
        self._require_data_source(space_id, ds_id)
        key = (space_id, ds_id, document_id)
        if key not in self._documents:
            raise KeyError(f"Document {document_id!r} not found in data source {ds_id!r}")
        return deepcopy(self._documents[key])

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
        self._require_data_source(space_id, ds_id)
        if text is None and section is None:
            raise ValueError("Either 'text' or 'section' must be provided")

        key = (space_id, ds_id, document_id)
        existing = self._documents.get(key)
        now_ms = int(time.time() * 1000)

        doc = Document(
            document_id=document_id,
            title=title,
            text=None if light_document_output else text,
            section=None if light_document_output else section,
            source_url=source_url,
            tags=list(tags) if tags else [],
            timestamp=timestamp,
            mime_type=mime_type,
            created_at=existing.created_at if existing else now_ms,
        )
        self._documents[key] = doc
        return deepcopy(doc)

    def delete_document(self, space_id: str, ds_id: str, document_id: str) -> None:
        self._require_data_source(space_id, ds_id)
        key = (space_id, ds_id, document_id)
        if key not in self._documents:
            raise KeyError(f"Document {document_id!r} not found in data source {ds_id!r}")
        del self._documents[key]

    def search_documents(
        self,
        space_id: str,
        ds_id: str,
        query: str,
        *,
        top_k: int = 10,
        tags: Optional[List[str]] = None,
    ) -> List[Document]:
        """Naive substring search over text content and title."""
        self._require_data_source(space_id, ds_id)
        query_lower = query.lower()

        results = []
        for (sid, did, _), doc in self._documents.items():
            if sid != space_id or did != ds_id:
                continue
            if tags and not all(t in doc.tags for t in tags):
                continue
            haystack = " ".join(filter(None, [doc.title, doc.text]))
            if query_lower in haystack.lower():
                results.append(deepcopy(doc))

        return results[:top_k]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_data_source(self, space_id: str, ds_id: str) -> None:
        if (space_id, ds_id) not in self._data_sources:
            raise KeyError(f"Data source {ds_id!r} not found in space {space_id!r}")
