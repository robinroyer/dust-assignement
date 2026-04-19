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
