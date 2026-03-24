# Multi-Board Kanban Manager

A Python Kanban application focused on multi-board management with a Tkinter GUI and CLI workflows. It supports custom columns, drag-and-drop card movement, file attachments on cards, external board loading, read-only fallback when a board is already open elsewhere, and a legacy single-board CLI mode.

## Features

- Multi-board GUI for creating, switching, renaming, deleting, importing, and exporting boards
- Multi-board CLI for terminal-based board management
- Legacy single-board CLI for working with a standalone board data file
- Custom columns with rename, reorder, recolor, and delete support
- Card priorities, assignees, tags, projects, custom colors, reusable card types, real subcards, and copied file attachments
- Drag-and-drop movement in the multi-board GUI
- Drag-and-drop file attachments onto cards and the edit-card dialog
- Cleanup of orphaned copied attachment files that are no longer referenced by the board or its undo/redo history
- External board loading by reference
- Lock files with automatic read-only fallback when another process owns the board

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

### Legacy Single-Board CLI

```bash
python main.py --single-board
```

Use a custom single-board data file if needed:

```bash
python main.py --single-board --data-file my_board.json
```

### Demo Scripts

```bash
python demo_multiboard.py
python example_usage.py
```

## Command Options

```bash
python main.py [options]

Options:
  --cli              Use the multi-board command-line interface
  --single-board     Use the legacy single-board CLI mode
  --data-file FILE   Specify a custom data file for single-board CLI mode
  --boards-dir DIR   Specify a custom boards directory for multi-board mode
  --help             Show help message
```

## Storage

Default runtime storage locations:

- Multi-board mode: `$HOME/.kanban-ds/boards`
- Single-board CLI mode: `$HOME/.kanban-ds/kanban_data.json`

External board loading:

- Multi-board GUI: `Boards -> Load Board From Folder`
- Multi-board CLI: `9. Load board from folder`
- You can select either a folder containing `boards_metadata.json` or a folder with standalone board `.json` files
- External boards remain in their original location and are registered by reference
- If a board is already open in another process, it opens read-only until that lock is released

## Multi-Board GUI Guide

### Main Areas

- Menu bar for boards, cards, filters, columns, tools, and help
- Toolbar board selector for switching the active board
- Summary area showing card counts, completed counts, and read-only status
- Board canvas with draggable cards and per-column add-card actions
- Card type management with reusable project and color presets
- Card attachments that can be opened from cards and managed in the edit-card dialog

### Common Actions

1. Create a board from the Boards menu.
   The create-board dialog defaults to the standard boards folder, but you can browse to a different storage folder and the board will still be remembered in the board list.
2. Load an external board with `Boards -> Load Board From Folder`.
3. Switch boards from the dropdown or with `Ctrl+O`.
4. Double-click a card to edit it.
5. Right-click cards or columns for context actions.
6. Choose a custom card color in the create or edit card dialog, or leave it on the default board style.
7. Manage reusable card types from the Cards menu to prefill project and color when creating cards.
8. Drop files onto a card to copy them into the board attachments folder and create dated links on the card.
9. Use the edit-card dialog to add files, drop files into the dialog, open attached files, or remove attachment links.
10. Run `Tools -> Clean Up Orphaned Attachments` when you want to prune copied files that are no longer referenced anywhere in the board or its undo/redo history.

### Visual Indicators

- Priority bars show urgency from low to critical
- Assignees display as `@name`
- Tags display as `#tag`
- Attachments display as dated `📎` links on cards
- Card backgrounds can use a custom color while preserving readable text contrast
- Parent cards show subcard progress
- Read-only mode is shown when another process holds the lock

## Keyboard Shortcuts

### Multi-Board GUI

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Create new board |
| `Ctrl+Shift+O` | Load board from folder |
| `Ctrl+O` | Switch board |
| `Ctrl+R` | Rename current board |
| `Ctrl+Shift+D` | Delete current board |
| `Ctrl+I` | Board statistics |
| `Ctrl+Q` | Quit application |

### Mouse Actions

| Action | Result |
|--------|--------|
| Double-click card | Edit card |
| Right-click card | Open card context menu |
| Drag and drop | Move card between columns |
| Drop files on card | Attach copied files to that card |

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
   Try `python -m tkinter` to confirm Tkinter is available, or run `python main.py --cli`.
2. Permission errors:
   Check write access to `$HOME/.kanban-ds` or the external board folder, and verify the board file and adjacent `.lock` file are writable.
3. Board opens read-only:
   Another process currently owns the lock. Close that instance or reopen the board after the lock is released.
4. Backup or import problems:
   Verify the target path exists and that the JSON files are not corrupted.
5. Attachment storage keeps growing:
   Use `Tools -> Clean Up Orphaned Attachments` in the GUI or the matching CLI maintenance action to remove copied files that are no longer referenced.

## License

This project is intended for educational and personal use. Modify and distribute it as needed.
