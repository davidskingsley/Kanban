# Multi-Board Kanban Manager

A Python Kanban application focused on multi-board management with a PySide6 GUI and CLI workflows. It supports custom columns, card priorities, reusable card types, external board loading, and interactive lock handling when a board is already open elsewhere.

## Features

- Multi-board PySide6 GUI for creating, switching, renaming, deleting, importing, and exporting boards
- Multi-board CLI for terminal-based board management and per-board card operations
- Custom columns with rename, reorder, recolor, and delete support
- Card priorities, assignees, tags, projects, custom colors, reusable card types, and real subcards
- External board loading by reference
- Lock files with prompts to open read only, delete the lock, or cancel opening the board

## Installation

1. Install Python 3.8 or newer.
2. Change into the project directory.
3. Install the Python dependencies.

```bash
cd Kanban
pip install -r requirements.txt
```

## Usage

### Multi-Board GUI

```bash
python main.py
```

This is the default mode and the primary GUI workflow.

### Multi-Board CLI

```bash
python main.py --cli
```

### Demo Scripts

```bash
python demo_multiboard.py
python example_usage.py
```

## Testing

Run the regression suite with the workspace virtual environment:

```bash
python -m unittest discover -s tests
```

## Command Options

```bash
python main.py [options]

Options:
  --cli              Use the multi-board command-line interface
  --boards-dir DIR   Specify a custom boards directory for multi-board mode
  --help             Show help message
```

## Storage

Default runtime storage locations:

- Multi-board mode: `$HOME/.kanban-ds/boards`

External board loading:

- Multi-board GUI: `Boards -> Load Board From Folder`
- Multi-board CLI: `9. Load board from folder`
- You can select either a folder containing `boards_metadata.json` or a folder with standalone board `.json` files
- External boards remain in their original location and are registered by reference
- If a board is already open in another process, it opens read-only until that lock is released

## Multi-Board GUI Guide

### Main Areas

- Menu bar for boards, cards, and columns
- Left-side board list for switching between boards
- Summary area showing card counts, completed counts, and read-only status
- Horizontal board view with one list per column and per-column add-card actions
- Dialog-driven card and column management built on PySide6 widgets

### Common Actions

1. Create a board from the Boards menu.
   The create-board dialog defaults to the standard boards folder, but you can browse to a different storage folder and the board will still be remembered in the board list.
2. Load an external board with `Boards -> Load Board From Folder`.
3. Export the current board with `Boards -> Export Current Board` to create a standalone board JSON file that can be loaded later from a folder.
4. Switch boards from the dropdown or with `Ctrl+O`.
5. Double-click a card to edit it.
6. Select a column and use the Columns menu to edit, delete, or reorder it.
7. Choose a custom card color in the create or edit card dialog, or leave it blank to use the default board style.
8. Manage reusable card types from the card dialog when creating or editing cards.

### Visual Indicators

- Priority bars show urgency from low to critical
- Assignees display as `@name`
- Tags display as `#tag`
- Card backgrounds can use a custom color while preserving readable text contrast
- Parent cards show subcard progress
- Read-only mode is shown when another process holds the lock

## Keyboard Shortcuts

### Multi-Board GUI

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
| `Ctrl+E` | Edit selected card |
| `Ctrl+M` | Move selected card |
| `Ctrl+Shift+C` | Create column |
| `Ctrl+Q` | Quit application |

### Mouse Actions

| Action | Result |
|--------|--------|
| Select board | Switch current board |
| Select column | Mark column as active for add/edit actions |
| Select card | Mark card as active for edit/move/delete actions |
| Double-click card | Edit card |

## Project Structure

```text
Kanban/
├── main.py
├── demo_multiboard.py
├── example_usage.py
├── README.md
├── requirements.txt
├── demo_kanban.json
├── example_kanban.json
├── kanban_data.json
└── kanban/
    ├── __init__.py
    ├── board.py
    ├── board_manager.py
    ├── cli.py
    ├── models.py
    ├── multi_board_cli.py
    ├── multi_board_gui.py
    └── storage.py
```

## Troubleshooting

1. GUI will not start:
   Verify `PySide6` is installed from `requirements.txt`, or run `python main.py --cli`.
2. Permission errors:
   Check write access to `$HOME/.kanban-ds` or the external board folder, and verify the board file and adjacent `.lock` file are writable.
3. Board opens read-only:
   Another process currently owns the lock. Close that instance or reopen the board after the lock is released.
4. Backup or import problems:
   Verify the target path exists and that the JSON files are not corrupted.
5. Need advanced maintenance operations:
   Use `python main.py --cli` for attachment, note, and other advanced board-management commands.

## License

This project is intended for educational and personal use. Modify and distribute it as needed.
