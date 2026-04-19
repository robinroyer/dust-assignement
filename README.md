# dust-assignement


### install deps

```
make install
```

### Testing Trello integration

Add TRELLO_API_KEY, TRELLO_API_SECRET and TRELLO_TOKEN to .env file


```
make trello ARGS="list-boards"
```


### Synchronize trello to dust datasources

Add `DUST_API_KEY` and `DUST_WORKSPACE_ID` to your `.env` file alongside the Trello credentials.

**CLI (via make)**

```bash
make sync ARGS="<space_id> <ds_id> 'Board Name'"
```

Example — sync two boards into space `sPxyz` / data source `dsAbc`:

```bash
make sync ARGS="sPxyz dsAbc 'Engineering Backlog' 'Sprint 42'"
```

The command prints a JSON summary on completion:

```json
{
  "synced": 12,
  "skipped_boards": [],
  "document_ids": [
    "trello-abc123",
    "trello-def456",
    "..."
  ]
}
```

**Python library**

```python
from use_cases.synchronize_trello_to_dust import SyncContainer, synchronize

container = SyncContainer()
container.config.from_dict({
    "trello_api_key": "YOUR_TRELLO_API_KEY",
    "trello_api_secret": "YOUR_TRELLO_API_SECRET",
    "trello_token": "YOUR_TRELLO_TOKEN",
    "dust_api_key": "YOUR_DUST_API_KEY",
    "dust_workspace_id": "YOUR_DUST_WORKSPACE_ID",
    "space_id": "sPxyz",
    "ds_id": "dsAbc",
})

result = synchronize(["Engineering Backlog", "Sprint 42"], container)
print(f"Synced {result.synced} cards, skipped boards: {result.skipped_boards}")
```

Or use environment variables directly:

```python
container = SyncContainer.from_env(space_id="sPxyz", ds_id="dsAbc")
result = synchronize(["Engineering Backlog"], container)
```


### Running the sync script with Docker

Build and run locally:

```bash
docker run --env-file .env synchronize-trello-to-dust:latest \
  <space_id> <ds_id> 'Board One' 'Board Two'
```

---

### Deploying to Docker Hub

Both images follow the same pattern. Set your Docker Hub username before pushing:

```bash
export DOCKER_USER=yourdockerhubusername
```

**Sync script image**

```bash
make push-script                      # tag: latest
make push-script IMAGE_TAG=1.0.0      # custom tag
```

This builds `synchronize-trello-to-dust` locally then pushes it as `$DOCKER_USER/synchronize-trello-to-dust:<tag>`.

**MCP server image**

```bash
make push-mcp                         # tag: latest
make push-mcp IMAGE_TAG=1.0.0         # custom tag
```

This builds `dust-sync-mcp` locally then pushes it as `$DOCKER_USER/dust-sync-mcp:<tag>`.

---

### Using the published images

**Sync script** — pull and run directly from Docker Hub:

```bash
docker run --env-file .env \
  yourdockerhubusername/synchronize-trello-to-dust:latest \
  <space_id> <ds_id> 'Board One' 'Board Two'
```

Required env vars (in `.env` or passed via `-e`):

| Variable | Description |
|---|---|
| `TRELLO_API_KEY` | Trello API key |
| `TRELLO_API_SECRET` | Trello API secret |
| `TRELLO_TOKEN` | Trello OAuth token |
| `DUST_API_KEY` | Dust API key |
| `DUST_WORKSPACE_ID` | Dust workspace ID |

**MCP server** — pull and start the HTTP server:

```bash
docker run -p 8080:8080 \
  -e MCP_AUTH_TOKEN=your-secret-token \
  yourdockerhubusername/dust-sync-mcp:latest
```

The server listens on port `8080`. Trello credentials are **not** stored server-side — pass them per-request via HTTP headers:

| Header | Description |
|---|---|
| `Authorization` | `Bearer <MCP_AUTH_TOKEN>` |
| `X-Trello-Api-Key` | Trello API key |
| `X-Trello-Api-Secret` | Trello API secret |
| `X-Trello-Token` | Trello OAuth token |