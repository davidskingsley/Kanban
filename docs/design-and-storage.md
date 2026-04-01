# Project Design And Storage Reference

## Overview

This repository implements a multi-surface Kanban application with three primary entry points:

- Desktop GUI built with PySide6
- Interactive multi-board CLI for guided terminal workflows
- Direct-action CLI for automation and scripting

The core design separates board behavior from user interfaces. All surfaces operate on the same `KanbanBoard` domain object and the same persistence layer, so GUI and CLI features share the same underlying state transitions and storage formats.

## Runtime Architecture

### Entry Points

- `main.py`
  - Parses top-level arguments.
  - Chooses between GUI, interactive CLI, and direct-action CLI.
  - Creates a `BoardManager` instance for the selected boards directory.
- `kanban/multi_board_cli.py`
  - Implements the multi-board terminal menu.
  - Handles board selection, board creation, import/export, backend conversion, and lock prompts.
- `kanban/direct_cli.py`
  - Registers direct-action subcommands for non-interactive automation.
- `kanban/multi_board_gui.py`
  - Compatibility wrapper for the split GUI package.

### Domain Core

- `kanban/board.py`
  - Public facade that re-exports `KanbanBoard`.
- `kanban/board_core.py`
  - Composes the full board object from mixins.
  - Owns the `DataStorage` instance.
  - Exports normalized board payloads through `export_data()`.

`KanbanBoard` is composed from these main mixins:

- `kanban/board_columns.py`
  - Column creation, renaming, deletion, reordering, and layout helpers.
- `kanban/board_catalog.py`
  - Project and card-type catalogs.
  - Default card type creation and synchronization of project references.
- `kanban/board_cards.py`
  - Card CRUD, tags, notes, attachments, checklist items, archive flows, and statistics helpers.
- `kanban/board_persistence.py`
  - Serialization and deserialization of board state.
  - Default column initialization and migration logic for legacy formats.

### Shared Models

`kanban/models.py` defines the persisted object model:

- `Priority`
- `Status`
- `CardNote`
- `CardAttachment`
- `CardTodoItem`
- `CardType`
- `Project`
- `CustomColumn`
- `Card`
- `Column` for legacy compatibility only

### Persistence Layer

- `kanban/storage.py`
  - Detects JSON versus SQLite storage.
  - Implements file I/O helpers, backup and restore helpers, lock files, and the `DataStorage` class.
- `kanban/board_manager.py`
  - Stores multi-board metadata in `boards_metadata.json`.
  - Loads board files through `KanbanBoard`.
  - Handles board import/export and JSON/SQLite backend conversion.

## Repository Layout

### Top Level

- `main.py`: launcher
- `README.md`: user-facing overview and usage
- `pyproject.toml`: package metadata and tooling config
- `Kanban.spec`: PyInstaller packaging definition
- `docs/`: supplemental reference material
- `tests/`: unit and GUI regression tests
- `assets/`: packaged application assets

### Python Package

- `kanban/board.py`: public board facade
- `kanban/board_core.py`: board composition root
- `kanban/board_cards.py`: card and archive behavior
- `kanban/board_columns.py`: column behavior
- `kanban/board_catalog.py`: card type and project behavior
- `kanban/board_persistence.py`: load/save orchestration
- `kanban/board_manager.py`: multi-board registry and metadata
- `kanban/storage.py`: JSON, SQLite, backup, and lock handling
- `kanban/cli.py`: board-level interactive CLI
- `kanban/multi_board_cli.py`: multi-board interactive CLI
- `kanban/direct_cli.py`: direct CLI parser registration
- `kanban/direct_cli_board_commands.py`: direct board actions
- `kanban/direct_cli_card_commands.py`: direct card, note, checklist, and archive actions
- `kanban/direct_cli_structure_commands.py`: direct column and card-type actions
- `kanban/direct_cli_support.py`: shared parsing and lookup helpers for direct CLI
- `kanban/gui/`: split GUI implementation

## State Model

At runtime, a board contains four primary categories of state:

- Columns
- Cards
- Card types
- Projects

Cards can also own nested substructures:

- Notes
- Attachments
- Checklist items
- Tags

The persistence format is board-centric. Both JSON board files and SQLite board files store the same logical board payload.

## Board JSON Payload Schema

### Canonical Board Document

The canonical serialized board document is produced by `KanbanBoard.export_data()` and has this top-level shape:

```json
{
  "columns": [],
  "cards": [],
  "card_types": [],
  "projects": [],
  "last_used_card_type_id": "string-or-null",
  "format_version": "2.0"
}
```

Top-level fields:

- `columns`
  - Array of column objects.
  - Defines board layout and per-column behavior flags.
- `cards`
  - Flat array of cards.
  - Cards reference columns by `column_id` and subcard parents by `parent_id`.
- `card_types`
  - Array of reusable card-type presets.
- `projects`
  - Array of reusable project records.
- `last_used_card_type_id`
  - ID of the most recently selected card type.
  - Used as the default type for future card creation.
- `format_version`
  - Current exported version string, currently `2.0`.

### Column Object Schema

Each entry in `columns` has this shape:

```json
{
  "id": "uuid",
  "name": "To Do",
  "position": 0,
  "color": "#FF9800",
  "is_completed": false,
  "can_add_card": true,
  "created_at": "2026-04-01T12:34:56.789012",
  "updated_at": "2026-04-01T12:34:56.789012"
}
```

Field details:

- `id`: unique column identifier
- `name`: display label
- `position`: zero-based ordering index
- `color`: UI color string, typically hex
- `is_completed`: whether the column counts as done for archive and progress logic
- `can_add_card`: whether this column is the preferred direct add-card target
- `created_at`: ISO 8601 timestamp
- `updated_at`: ISO 8601 timestamp

### Card Type Object Schema

Each entry in `card_types` has this shape:

```json
{
  "id": "uuid",
  "name": "Bug",
  "description": "Reusable preset",
  "default_project": "Platform",
  "default_color": "#D32F2F",
  "created_at": "2026-04-01T12:34:56.789012",
  "updated_at": "2026-04-01T12:34:56.789012"
}
```

Field details:

- `id`: unique card type identifier
- `name`: unique display name per board
- `description`: optional explanatory text
- `default_project`: optional project name automatically applied to cards of this type
- `default_color`: optional default card color
- `created_at`: ISO 8601 timestamp
- `updated_at`: ISO 8601 timestamp

### Project Object Schema

Each entry in `projects` has this shape:

```json
{
  "id": "uuid",
  "name": "Platform",
  "description": "Shared project record",
  "created_at": "2026-04-01T12:34:56.789012",
  "updated_at": "2026-04-01T12:34:56.789012"
}
```

Field details:

- `id`: unique project identifier
- `name`: project display name, referenced by cards and card-type presets
- `description`: optional explanatory text
- `created_at`: ISO 8601 timestamp
- `updated_at`: ISO 8601 timestamp

### Card Object Schema

Each entry in `cards` has this shape:

```json
{
  "id": "uuid",
  "title": "Ship release",
  "description": "Release coordination",
  "priority": "high",
  "column_id": "uuid",
  "status": null,
  "created_at": "2026-04-01T12:34:56.789012",
  "updated_at": "2026-04-01T12:34:56.789012",
  "project": "Platform",
  "assignee": "david",
  "color": "#1976D2",
  "card_type_id": "uuid",
  "parent_id": null,
  "start_date": "2026-04-01",
  "end_date": "2026-04-10",
  "tags": ["release", "cli"],
  "notes": [],
  "attachments": [],
  "todo_items": [],
  "archived_at": null
}
```

Field details:

- `id`: unique card identifier
- `title`: required card title
- `description`: optional body text
- `priority`: one of `low`, `medium`, `high`, `critical`
- `column_id`: owning column ID in the custom-column model
- `status`: legacy compatibility field; retained for backward compatibility
- `created_at`: ISO 8601 timestamp
- `updated_at`: ISO 8601 timestamp
- `project`: optional project name reference, not project ID
- `assignee`: optional assignee name
- `color`: optional card-specific color override
- `card_type_id`: optional card-type ID reference
- `parent_id`: optional parent card ID for subcards
- `start_date`: optional ISO 8601 date string
- `end_date`: optional ISO 8601 date string
- `tags`: array of unique tag strings
- `notes`: array of note objects
- `attachments`: array of attachment objects
- `todo_items`: array of checklist item objects
- `archived_at`: optional ISO 8601 timestamp marking archive state

### Note Object Schema

Each entry in `card.notes` has this shape:

```json
{
  "id": "uuid",
  "text": "Drafted release notes",
  "created_at": "2026-04-01T12:34:56.789012"
}
```

Field details:

- `id`: unique note identifier
- `text`: note body text
- `created_at`: creation timestamp

### Attachment Object Schema

Each entry in `card.attachments` has this shape:

```json
{
  "id": "uuid",
  "name": "release-plan.pdf",
  "relative_path": "ship_release/<stored-file>",
  "created_at": "2026-04-01T12:34:56.789012"
}
```

Field details:

- `id`: unique attachment identifier
- `name`: original or display filename
- `relative_path`: path relative to the board directory or attachments directory
- `created_at`: creation timestamp

### Checklist Item Object Schema

Each entry in `card.todo_items` has this shape:

```json
{
  "id": "uuid",
  "text": "Publish announcement",
  "completed": false
}
```

Field details:

- `id`: unique checklist item identifier
- `text`: item text
- `completed`: boolean completion state

## Multi-Board Metadata JSON Schema

The multi-board registry lives in `boards_metadata.json` under the boards directory managed by `BoardManager`.

Top-level shape:

```json
{
  "boards": {
    "board-id": {
      "name": "Automation",
      "description": "Board description",
      "created_at": "2026-04-01T12:34:56.789012",
      "data_file": "C:/path/to/board.sqlite3",
      "storage_backend": "sqlite",
      "use_custom_columns": true,
      "external": false
    }
  },
  "current_board": "board-id"
}
```

Metadata field details:

- `boards`
  - Object keyed by board ID.
- `current_board`
  - Selected current board ID or `null`.

Per-board metadata entry fields:

- `name`: board display name
- `description`: optional board description
- `created_at`: creation timestamp
- `data_file`: absolute or managed path to the board payload file
- `storage_backend`: normalized backend name, `json` or `sqlite`
- `use_custom_columns`: compatibility flag; modern boards use `true`
- `external`: whether the board file lives outside the managed boards directory

## Full Backup And Import JSON Schema

The `export-all-boards` flow writes a backup document that wraps registry metadata plus each board payload.

Top-level shape:

```json
{
  "metadata": {
    "boards": {},
    "current_board": "board-id"
  },
  "boards": {
    "board-id": {
      "columns": [],
      "cards": [],
      "card_types": [],
      "projects": [],
      "last_used_card_type_id": "uuid",
      "format_version": "2.0"
    }
  }
}
```

This format is used for full backup/export and full import. It is not the same as a standalone board file.

## Lock File JSON Schema

Each board file may have an adjacent lock file with the suffix `.lock`.

Example shape:

```json
{
  "pid": 12345,
  "hostname": "WORKSTATION",
  "opened_at": "2026-04-01T12:34:56.789012",
  "file_path": "C:/Users/david/.kanban-ds/boards/automation.sqlite3"
}
```

Field details:

- `pid`: process ID of the owner
- `hostname`: machine name of the lock owner
- `opened_at`: timestamp when the lock was created
- `file_path`: absolute board file path

## SQLite Storage Schema

### Design Choice

SQLite is used as a container for the exact same board payload described in the JSON schema above. The application does not map cards, columns, projects, and notes into separate normalized tables. Instead, it stores the entire board document as one JSON blob inside a single table.

This means:

- JSON and SQLite board backends are logically equivalent
- Backend conversion can be implemented as file-level translation without object-model changes
- Schema changes to cards, notes, or projects do not require separate relational migrations as long as the JSON payload remains loadable

### Table Definition

The SQLite schema is created by `_ensure_sqlite_schema()` in `kanban/storage.py`.

```sql
CREATE TABLE IF NOT EXISTS board_state (
    board_id INTEGER PRIMARY KEY CHECK (board_id = 1),
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

Column details:

- `board_id`
  - Integer primary key.
  - Constrained to `1`, so each SQLite file stores exactly one board row.
- `state_json`
  - Text column containing the full board payload JSON.
  - Written with pretty-printed JSON via `json.dumps(..., indent=2, ensure_ascii=False)`.
- `updated_at`
  - ISO 8601 timestamp for when the payload row was last written.

### Write Behavior

SQLite writes use an upsert keyed on `board_id = 1`:

```sql
INSERT INTO board_state (board_id, state_json, updated_at)
VALUES (1, ?, ?)
ON CONFLICT(board_id) DO UPDATE SET
    state_json = excluded.state_json,
    updated_at = excluded.updated_at
```

Implications:

- One SQLite file stores one board
- The latest persisted board payload always lives in the single `board_state` row
- There are no child tables for cards, columns, notes, tags, or attachments

### Read Behavior

Reads execute:

```sql
SELECT state_json FROM board_state WHERE board_id = 1
```

The returned JSON string is then parsed into the same Python structure used by the JSON backend.

## Backend Conversion Model

Board backend conversion in `BoardManager.convert_board_backend()` works like this:

1. Load the current board into memory.
2. Export the canonical board payload via `export_data()`.
3. Write that payload to a target file using the selected backend.
4. Update the corresponding board metadata entry.
5. Remove the old file if the target path differs.

Because both backends share the same logical payload, conversion is lossless as long as the payload itself is valid.

## Attachments Layout

Attachments are stored outside the main board payload.

Relevant behavior:

- Each board has a board-specific attachments directory.
- The directory name is derived from the board filename stem with `_attachments` appended.
- Attachment records stored in the card payload reference files through `relative_path`.

This means the persisted board document stores attachment metadata, but the file contents live alongside the board file on disk.

## Default Storage Locations

Defined in `kanban/storage.py`:

- Default application storage root: `$HOME/.kanban-ds`
- Default standalone board file: `$HOME/.kanban-ds/kanban_data.json`
- Default multi-board registry directory: `$HOME/.kanban-ds/boards`

In multi-board mode, the registry directory contains:

- `boards_metadata.json`
- one board file per managed board, as `.json` or `.sqlite3`
- adjacent `.lock` files when boards are open for writing
- attachment directories for boards that use attachments

## Compatibility And Migration Notes

- Legacy fixed-status boards without `columns` are no longer supported for normal loading.
- Compatibility fields such as `status` remain in card serialization for backward compatibility.
- Empty or new boards are initialized with four default custom columns:
  - `To Do`
  - `In Progress`
  - `Review`
  - `Done`
- A default card type named `Default` is always ensured by the catalog layer.

## Practical Summary

The project design centers on one canonical board state model shared by every interface. JSON board files and SQLite board files differ only in transport and storage mechanics:

- JSON backend: the canonical payload is the file itself
- SQLite backend: the canonical payload is stored as JSON text in the `board_state.state_json` column

That design keeps the domain model simple, allows straightforward backend conversion, and ensures GUI, interactive CLI, and direct CLI behavior all operate on the same underlying schema.