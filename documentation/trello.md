# Trello Data Model

## Hierarchy

```
Workspace (Organization)
  └── Board
        └── List
              └── Card
```

---

## Boards

The top-level container. Key fields:

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `name` | Board title |
| `desc` | Description |
| `idOrganization` | Links to a Workspace |
| `prefs` | Permissions, voting rules, card covers, etc. |
| `closed` | Whether the board is archived |

A board owns its **lists**, **labels**, **members**, and **custom fields**. Labels are defined at the board level and reused across cards.

---

## Lists

Columns within a board (e.g. "To Do", "In Progress", "Done"). Key fields:

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `name` | Display name |
| `idBoard` | Parent board reference |
| `pos` | Float for ordering (allows inserting between items) |
| `closed` | Archived state |
| `subscribed` | Whether the current user follows the list |

Lists are ordered containers. You can move a whole list to another board, or archive/move all its cards in bulk.

---

## Cards

The atomic unit of work. Key fields:

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `name` | Card title |
| `desc` | Description |
| `idList` | Which list it belongs to |
| `idBoard` | Board context |
| `pos` | Ordering within the list |
| `due` | Due date |
| `start` | Start date |
| `dueComplete` | Whether the due date is marked complete |
| `idMembers` | Assigned members |
| `closed` | Archived state |

Cards carry nested data:

| Nested | Description |
|---|---|
| **Labels** | Tags from the board's label set |
| **Checklists** | Sub-tasks with `checkItems` |
| **Attachments** | Files or links |
| **Cover** | Visual color/image |
| **Custom Fields** | Board-scoped extra metadata |
| **Comments** | Activity log entries |

---

## Relationships

```
Board  1 ──── * List
List   1 ──── * Card
Board  1 ──── * Label  (shared across cards)
Board  1 ──── * Member
Card   * ──── * Label
Card   * ──── * Member (assignments)
Card   1 ──── * Checklist ──── * CheckItem
```

**Key design choices:**
- **Labels are owned by the board**, not the card — a card references them by `idLabel`. Renaming a label on the board updates it everywhere.
- **Membership is granted at the board level**, then members are assigned to individual cards.
- **`pos` is a float** on both lists and cards, which allows reordering by inserting a value between two existing positions without renumbering everything.

---

## Useful API endpoints

| Endpoint | Description |
|---|---|
| `GET /boards/{id}/lists` | Get all lists on a board |
| `GET /boards/{id}/cards` | Get all cards on a board |
| `GET /lists/{id}/cards` | Get all cards in a list |
| `GET /cards/{id}/list` | Get the list a card belongs to |
| `GET /cards/{id}/board` | Get the board a card belongs to |

> Source: [Trello REST API documentation](https://developer.atlassian.com/cloud/trello/rest/)
