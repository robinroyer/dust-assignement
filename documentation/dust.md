# Dust Data Sources

## Conceptual model

Data sources are **document stores** that AI agents can query via RAG (Retrieval-Augmented Generation). They act as knowledge bases — documents are pushed in, and agents retrieve relevant chunks when answering questions.

## Hierarchy

```
Workspace (wId)
  └── Space (spaceId)          ← access-control boundary
        └── Data Source (dsId) ← a named document store
              └── Document (documentId) ← individual pieces of content
```

- **Workspace** — your Dust organization
- **Space** — an access-control scope (e.g. "Engineering", "HR")
- **Data Source** — a named collection of documents (e.g. "Notion export", "Confluence", "Custom API feed")
- **Document** — the unit of content, addressed by a `documentId` you control

## Upsert Document Endpoint

`POST /api/v1/w/{wId}/spaces/{spaceId}/data_sources/{dsId}/documents/{documentId}`

Creates or overwrites a document (idempotent — rerunning with the same `documentId` updates in place).

### Path parameters

| Parameter    | Type   | Description              |
|--------------|--------|--------------------------|
| `wId`        | string | Workspace identifier     |
| `spaceId`    | string | Space identifier         |
| `dsId`       | string | Data source identifier   |
| `documentId` | string | Document identifier (your key) |

### Request body

| Field                   | Type             | Description                                                        |
|-------------------------|------------------|--------------------------------------------------------------------|
| `text`                  | string           | Raw content — Dust will chunk and embed this                       |
| `section`               | object           | Nestable structure for rich documents (page → sections → paragraphs) |
| `title`                 | string           | Human-readable label                                               |
| `mime_type`             | string           | Content type hint                                                  |
| `source_url`            | string           | Link back to the canonical source                                  |
| `tags`                  | array of strings | Labels for filtering at retrieval time                             |
| `timestamp`             | number           | Unix timestamp (ms) — lets agents reason about recency             |
| `light_document_output` | boolean          | Skip returning vectors/chunks in the response (useful for bulk ingestion) |
| `async`                 | boolean          | Fire-and-forget processing for large documents                     |
| `upsert_context`        | object           | Supplementary operation metadata                                   |

### Response codes

| Code | Meaning                          |
|------|----------------------------------|
| 200  | Success                          |
| 400  | Invalid parameters               |
| 401  | Authentication failure           |
| 403  | Managed data source restriction  |
| 404  | Resource not found               |
| 429  | Rate limit exceeded              |
| 500  | Server error                     |

## How indexing works

1. A document is pushed with `text` or `section` content
2. Dust **chunks** it into smaller pieces
3. Each chunk is **embedded** (converted to a vector)
4. At agent query time, the question is embedded and the closest chunks are retrieved via semantic search
5. Retrieved chunks are injected into the agent's context window

## Syncing Trello tickets to a data source

To make Trello tickets searchable by a Dust agent:

1. Fetch tickets from Trello
2. For each ticket, call the upsert endpoint with `documentId = card_id`
3. Put the ticket title, description, and comments in `text` or `section`
4. Add `tags` for the list name, labels, or status to enable filtering
5. Set `source_url` to the Trello card URL

Since the upsert is idempotent, re-syncing the same card ID updates the document in place.
