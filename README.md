# Multi-Board Kanban Manager

A Python Kanban application with three ways to work: a PySide6 desktop GUI, an interactive multi-board terminal UI, and a direct-action CLI for scripting and automation. The current codebase supports JSON and SQLite board storage, external board registration, reusable card types, subcards, attachments, backups, import and export flows, and lock-aware read-only handling when a board is already open elsewhere.

## Highlights

- Multi-board PySide6 GUI with board creation, switching, rename, delete, import, export, statistics, and Help dialogs
- Interactive CLI for full terminal-driven board management and board-level card and column operations
- Direct-action CLI subcommands for non-interactive automation and scheduled jobs
- JSON and SQLite storage backends for boards
- External board loading by reference from folders containing `boards_metadata.json`, `.json`, or `.sqlite3` board files
- Card priorities, assignees, tags, projects, custom colors, reusable card types, real subcards, per-card checklists, and attachment cleanup tools
- Undo and redo support for board-management actions and current-board actions
- Lock handling that can open boards read-only, delete stale locks, or cancel access

## Requirements

- Python 3.9 through 3.14
- `uv` for environment management

On Windows, `winget install astral-sh.uv` is the simplest way to install `uv`.

## Installation

```bash
git clone https://github.com/davidskingsley/Kanban.git
cd Kanban
uv sync --all-groups
```

This installs the runtime dependency set plus development tools such as Ruff.

## Launch Modes

### GUI

```bash
uv run python main.py
```

This is the default launch mode. The GUI provides the board list, embedded board view, dialogs for cards and columns, board statistics, due-date views, Help dialogs, and keyboard shortcuts.

### Interactive CLI

```bash
uv run python main.py --cli
```

This opens the menu-based multi-board CLI. It is intended for terminal-first workflows where you still want guided prompts and board-level menus.

### Direct-Action CLI

```bash
uv run python main.py list-boards
uv run python main.py create-board --name "Automation" --storage-backend sqlite --switch
uv run python main.py create-card --board "Automation" --title "Ship release" --priority high --assignee david
uv run python main.py export-board --board "Automation" --output automation.json
```

Use direct subcommands when one action should run immediately with no interactive prompts. This mode is suitable for shell scripts, scheduled jobs, and external automation.

## Top-Level Options

```text
uv run python main.py [options]
uv run python main.py <direct-command> [command-options]

Options:
  --cli
  --boards-dir DIR
  --lock-action {cancel,open_read_only,delete_lock}
  --help
```

- `--cli` starts the interactive multi-board CLI instead of the GUI
- `--boards-dir DIR` uses a custom board registry directory for the session
- `--lock-action` controls how direct commands respond when the selected board is locked

Run `uv run python main.py --help` for launcher help, or `uv run python main.py <direct-command> --help` for the flags supported by a specific direct command.

## Direct-Action CLI Coverage

The direct CLI covers the same major workflows as the interactive CLI, but without prompts.

- Board management: `list-boards`, `create-board`, `switch-board`, `rename-board`, `delete-board`, `board-stats`, `export-board`, `export-all-boards`, `import-boards`, `load-board-from-folder`, `undo-board-management`, `redo-board-management`, `show-board`
- Card actions: `create-card`, `edit-card`, `add-subcard`, `move-card`, `delete-card`, `search-cards`, `filter-priority`, `filter-assignee`, `add-tag`, `add-todo-item`, `check-todo-item`, `uncheck-todo-item`, `toggle-todo-item`, `remove-todo-item`, `card-details`, `clear-done-cards`
- Column actions: `create-column`, `rename-column`, `delete-column`, `reorder-columns`, `change-column-color`, `edit-column-flags`, `list-columns`
- Card type and maintenance actions: `list-card-types`, `create-card-type`, `edit-card-type`, `delete-card-type`, `create-backup`, `cleanup-orphaned-attachments`, `undo-current-board`, `redo-current-board`

Safety notes:

- Destructive direct commands require `--force`
- Locked-board behavior in direct mode is controlled with `--lock-action`
- Date arguments use `YYYY-MM-DD`
- Checklist item commands accept exact item text or checklist item ids printed by `card-details`

## Checklist Workflows

Cards can include an optional checklist with individual completion state.

- GUI: open the card dialog to add, remove, or edit checklist entries, or tick checklist boxes directly on a card tile for quick progress updates.
- Interactive CLI: provide checklist items when creating or editing cards with pipe-delimited text such as `[x] Draft notes | Validate migrations`.
- Direct CLI: use repeated `--todo` flags on `create-card`, `edit-card`, and `add-subcard`, or mutate one item at a time with dedicated commands.

Examples:

```bash
uv run python main.py create-card --board "Automation" --title "Ship release" --todo "Draft notes" --todo "[x] Cut release candidate"
uv run python main.py add-todo-item --board "Automation" --card "Ship release" --text "Publish announcement"
uv run python main.py toggle-todo-item --board "Automation" --card "Ship release" --item "Publish announcement"
uv run python main.py card-details --board "Automation" --card "Ship release"
```

## Storage Backends

Boards can use either backend:

- JSON: portable `.json` board files
- SQLite: `.sqlite3` board files backed by a small SQLite schema

You can choose the backend when creating boards in the GUI, the interactive CLI, or the direct CLI.

Default board registry location:

- Multi-board mode: `$HOME/.kanban-ds/boards`

Backups, exports, imports, and external board discovery support both JSON and SQLite-backed boards.

## External Boards And Locking

The application can register boards stored outside the default boards directory.

- GUI: `Boards -> Load Board From Folder`
- Interactive CLI: `Load board from folder`
- Direct CLI: `load-board-from-folder`

Supported external sources:

- A folder containing `boards_metadata.json`
- Standalone `.json` board files
- Standalone `.sqlite3`, `.sqlite`, or `.db` board files

When a board is already open in another process, Kanban can:

- open it read-only
- delete a stale lock and retry
- cancel opening it

The interactive CLI prompts for that choice. The direct CLI uses `--lock-action`.

## GUI Workflow

The desktop application includes:

- board list and current-board switching
- embedded multi-column board view
- board statistics and due-date views
- create, edit, move, and delete actions for cards
- create, rename, delete, recolor, reorder, and flag editing for columns
- reusable card type management
- About and Command Line Guide dialogs under Help

Common GUI actions:

1. Create a board from the Boards menu and choose JSON or SQLite storage.
2. Load an external board from another folder without copying the source board into the default registry.
3. Use the Cards and Columns menus after selecting a card or column in the board view.
4. Double-click a card to edit it.
5. Use Help to open the About dialog or the Command Line Guide.

Visual cues include priority indicators, assignee labels, tags, custom card colors, checklist progress, subcard progress, and read-only state when a lock is held elsewhere.

## Interactive CLI Workflow

The interactive CLI starts with a board-management menu and then drops into the board-level CLI for card and column operations.

Board-management capabilities include:

- opening the current board
- switching, creating, renaming, and deleting boards
- board statistics
- exporting the current board
- exporting all boards
- importing boards from a backup JSON file
- loading a board from a folder
- undo and redo for board-management actions

Board-level capabilities include:

- card creation, editing, moving, deleting, searching, filtering, tag management, checklist entry, card details, clear-done, and subcards
- column creation, rename, deletion, reorder, recolor, flag editing, and listing
- card type listing, creation, editing, and deletion
- maintenance actions such as backup creation, orphaned attachment cleanup, undo, and redo

## Keyboard Shortcuts

### GUI Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Create new board |
| `Ctrl+Shift+O` | Load board from folder |
| `Ctrl+Shift+S` | Export current board |
| `Ctrl+O` | Switch board |
| `Ctrl+R` | Rename current board |
| `Ctrl+Shift+D` | Delete current board |
| `Ctrl+I` | Board statistics |
| `Ctrl+Shift+N` | Create card |
| `Ctrl+Shift+J` | Add subcard to the selected card |
| `Ctrl+E` | Edit selected card |
| `Ctrl+M` | Move selected card |
| `Ctrl+D` | Delete selected card |
| `Ctrl+Z` | Undo current board action |
| `Ctrl+Y` | Redo current board action |
| `Ctrl+Q` | Quit application |

## Development

This repository uses:

- `uv` for environment and dependency management
- `ruff` for linting
- `unittest` for regression tests

Useful commands:

```bash
uv run ruff check .
uv run ruff check . --fix
uv run python -m unittest discover -s tests
```

GitHub Actions runs the lint and test suite on Ubuntu with `uv` and PySide6 configured for offscreen execution.

## Packaging

A PyInstaller spec file is included as `Kanban.spec`. It packages `main.py` with the project assets folder and the application icon.

If you want to build the Windows executable yourself, install PyInstaller in your environment and run:

```bash
uv run pyinstaller Kanban.spec
```

## Project Layout

```text
Kanban/
├── assets/
├── build/
├── dist/
├── .github/workflows/
├── tests/
│   ├── gui_test_case.py
│   ├── test_direct_cli.py
│   ├── test_gui_board_regressions.py
│   └── test_gui_dialog_regressions.py
├── kanban/
│   ├── gui/
│   ├── board.py
│   ├── board_manager.py
│   ├── cli.py
│   ├── direct_cli.py
│   ├── models.py
│   ├── multi_board_cli.py
│   ├── multi_board_gui.py
│   └── storage.py
├── demo_kanban.json
├── demo_multiboard.py
├── example_kanban.json
├── example_usage.py
├── Kanban.spec
├── main.py
├── pyproject.toml
├── README.md
└── uv.lock
```

## Troubleshooting

1. GUI does not start.
   Run `uv sync --all-groups` first, then retry `uv run python main.py`. If PySide6 is unavailable, use `uv run python main.py --cli`.
2. A board opens read-only.
   Another process already owns the lock. Close the other instance, reopen the board later, or choose a different lock action.
3. Backup, import, or export fails.
   Confirm the source and destination paths are writable and that the JSON backup file is valid.
4. External boards are not discovered.
   Check that the folder contains `boards_metadata.json` or supported board files such as `.json` or `.sqlite3`.
5. You need scriptable automation.
   Use the direct CLI subcommands rather than the interactive `--cli` mode.

## License

See [LICENSE](LICENSE).
