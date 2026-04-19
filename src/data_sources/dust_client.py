"""Dust implementation of AbstractDataSource.

Authentication uses two environment variables:
  DUST_API_KEY        — API key from https://dust.tt/home/api-keys
  DUST_WORKSPACE_ID   — Workspace ID (wId) visible in the Dust URL

CLI usage (run from project root):
  python -m data_sources.dust_client list-data-sources <space_id>
  python -m data_sources.dust_client list-documents <space_id> <ds_id> [--limit N] [--offset N]
  python -m data_sources.dust_client get-document <space_id> <ds_id> <document_id>
  python -m data_sources.dust_client upsert-document <space_id> <ds_id> <document_id> --text TEXT
  python -m data_sources.dust_client delete-document <space_id> <ds_id> <document_id>
  python -m data_sources.dust_client search-documents <space_id> <ds_id> <query>
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests

from .abstract import AbstractDataSource
from .models import DataSource, Document, Section

_BASE_URL = "https://dust.tt/api/v1"


class DustDataSourcesClient(AbstractDataSource):
    """Dust-backed implementation that calls the Dust REST API."""

    def __init__(self, api_key: str, workspace_id: str) -> None:
        self._workspace_id = workspace_id
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    @classmethod
    def from_env(cls) -> "DustDataSourcesClient":
        missing = [v for v in ("DUST_API_KEY", "DUST_WORKSPACE_ID") if not os.getenv(v)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(api_key=os.environ["DUST_API_KEY"], workspace_id=os.environ["DUST_WORKSPACE_ID"])

    # ------------------------------------------------------------------
    # AbstractDataSource interface
    # ------------------------------------------------------------------

    def list_data_sources(self, space_id: str) -> List[DataSource]:
        url = f"{_BASE_URL}/w/{self._workspace_id}/spaces/{space_id}/data_sources"
        data = self._get(url)
        return [self._map_data_source(ds, space_id) for ds in data.get("data_sources", [])]

    def list_documents(
        self,
        space_id: str,
        ds_id: str,
        *,
        limit: int = 10,
        offset: int = 0,
        document_ids: Optional[List[str]] = None,
    ) -> List[Document]:
        url = f"{_BASE_URL}/w/{self._workspace_id}/spaces/{space_id}/data_sources/{ds_id}/documents"
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if document_ids:
            params["document_ids"] = document_ids
        data = self._get(url, params=params)
        return [self._map_document(d) for d in data.get("documents", [])]

    def get_document(self, space_id: str, ds_id: str, document_id: str) -> Document:
        url = (
            f"{_BASE_URL}/w/{self._workspace_id}/spaces/{space_id}"
            f"/data_sources/{ds_id}/documents/{document_id}"
        )
        data = self._get(url)
        return self._map_document(data.get("document", data))

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
        if text is None and section is None:
            raise ValueError("Either 'text' or 'section' must be provided")

        url = (
            f"{_BASE_URL}/w/{self._workspace_id}/spaces/{space_id}"
            f"/data_sources/{ds_id}/documents/{document_id}"
        )
        payload: Dict[str, Any] = {
            "light_document_output": light_document_output,
            "async": async_processing,
        }
        if text is not None:
            payload["text"] = text
        if section is not None:
            payload["section"] = self._serialize_section(section)
        if title is not None:
            payload["title"] = title
        if mime_type is not None:
            payload["mime_type"] = mime_type
        if source_url is not None:
            payload["source_url"] = source_url
        if tags is not None:
            payload["tags"] = tags
        if timestamp is not None:
            payload["timestamp"] = timestamp

        data = self._post(url, payload)
        return self._map_document(data.get("document", data))

    def delete_document(self, space_id: str, ds_id: str, document_id: str) -> None:
        url = (
            f"{_BASE_URL}/w/{self._workspace_id}/spaces/{space_id}"
            f"/data_sources/{ds_id}/documents/{document_id}"
        )
        self._delete(url)

    def search_documents(
        self,
        space_id: str,
        ds_id: str,
        query: str,
        *,
        top_k: int = 10,
        tags: Optional[List[str]] = None,
    ) -> List[Document]:
        url = (
            f"{_BASE_URL}/w/{self._workspace_id}/spaces/{space_id}"
            f"/data_sources/{ds_id}/search"
        )
        payload: Dict[str, Any] = {"query": query, "top_k": top_k}
        if tags:
            payload["tags_filter"] = {"tags": tags, "mode": "and"}
        data = self._post(url, payload)
        return [self._map_document(d) for d in data.get("documents", [])]

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self._session.get(url, params=params)
        self._raise_for_status(response)
        return response.json()

    def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self._session.post(url, json=payload)
        self._raise_for_status(response)
        return response.json()

    def _delete(self, url: str) -> None:
        response = self._session.delete(url)
        self._raise_for_status(response)

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.status_code == 401:
            raise PermissionError("Dust API: authentication failed — check DUST_API_KEY")
        if response.status_code == 403:
            raise PermissionError("Dust API: this data source is managed and cannot be modified")
        if response.status_code == 404:
            raise KeyError(f"Dust API: resource not found ({response.url})")
        if response.status_code == 429:
            raise RuntimeError("Dust API: rate limit exceeded")
        if not response.ok:
            raise RuntimeError(f"Dust API error {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_data_source(raw: Dict[str, Any], space_id: str) -> DataSource:
        return DataSource(
            id=raw.get("sId") or raw.get("id", ""),
            name=raw.get("name", ""),
            space_id=space_id,
            description=raw.get("description"),
        )

    @staticmethod
    def _map_document(raw: Dict[str, Any]) -> Document:
        section_raw = raw.get("section")
        return Document(
            document_id=raw.get("document_id", raw.get("id", "")),
            title=raw.get("title"),
            text=raw.get("text"),
            section=DustDataSourcesClient._map_section(section_raw) if section_raw else None,
            source_url=raw.get("source_url"),
            tags=raw.get("tags") or [],
            timestamp=raw.get("timestamp"),
            mime_type=raw.get("mime_type"),
            token_count=raw.get("token_count"),
            created_at=raw.get("created_at"),
        )

    @staticmethod
    def _map_section(raw: Dict[str, Any]) -> Section:
        return Section(
            prefix=raw.get("prefix"),
            content=raw.get("content"),
            sections=[DustDataSourcesClient._map_section(s) for s in raw.get("sections", [])],
        )

    @staticmethod
    def _serialize_section(section: Section) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "content": section.content if section.content is not None else "",
            "sections": [DustDataSourcesClient._serialize_section(s) for s in section.sections],
        }
        if section.prefix is not None:
            d["prefix"] = section.prefix
        return d


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_json(data) -> None:
    def _default(obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    if isinstance(data, list):
        print(json.dumps([d.__dict__ if hasattr(d, "__dict__") else d for d in data], indent=2, default=_default))
    else:
        print(json.dumps(data.__dict__ if hasattr(data, "__dict__") else data, indent=2, default=_default))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="data_sources.dust_client", description="CLI for the Dust DataSources API")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list-data-sources")
    p.add_argument("space_id")

    p = sub.add_parser("list-documents")
    p.add_argument("space_id")
    p.add_argument("ds_id")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--offset", type=int, default=0)

    p = sub.add_parser("get-document")
    p.add_argument("space_id")
    p.add_argument("ds_id")
    p.add_argument("document_id")

    p = sub.add_parser("upsert-document")
    p.add_argument("space_id")
    p.add_argument("ds_id")
    p.add_argument("document_id")
    p.add_argument("--text", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--source-url", default=None, dest="source_url")
    p.add_argument("--mime-type", default=None, dest="mime_type")
    p.add_argument("--tags", default=None, help="Comma-separated tags")
    p.add_argument("--timestamp", type=int, default=None)
    p.add_argument("--light", action="store_true")
    p.add_argument("--async", action="store_true", dest="async_processing")

    p = sub.add_parser("delete-document")
    p.add_argument("space_id")
    p.add_argument("ds_id")
    p.add_argument("document_id")

    p = sub.add_parser("search-documents")
    p.add_argument("space_id")
    p.add_argument("ds_id")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=10, dest="top_k")
    p.add_argument("--tags", default=None)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        client = DustDataSourcesClient.from_env()
    except EnvironmentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.command == "list-data-sources":
            _print_json(client.list_data_sources(args.space_id))
        elif args.command == "list-documents":
            _print_json(client.list_documents(args.space_id, args.ds_id, limit=args.limit, offset=args.offset))
        elif args.command == "get-document":
            _print_json(client.get_document(args.space_id, args.ds_id, args.document_id))
        elif args.command == "upsert-document":
            tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
            _print_json(client.upsert_document(
                args.space_id, args.ds_id, args.document_id,
                text=args.text, title=args.title, source_url=args.source_url,
                mime_type=args.mime_type, tags=tags, timestamp=args.timestamp,
                light_document_output=args.light, async_processing=args.async_processing,
            ))
        elif args.command == "delete-document":
            client.delete_document(args.space_id, args.ds_id, args.document_id)
            print(f"Deleted document {args.document_id!r}")
        elif args.command == "search-documents":
            tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
            _print_json(client.search_documents(args.space_id, args.ds_id, args.query, top_k=args.top_k, tags=tags))
    except (KeyError, PermissionError, Exception) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
