## @file
#  @brief Non-interactive command-line actions for the Kanban application.
"""!Direct-action CLI support for automating Kanban board operations."""

from __future__ import annotations

import argparse
from typing import Any

from .board_manager import BoardManager
from .direct_cli_board_commands import DirectCliBoardCommandsMixin
from .direct_cli_card_commands import DirectCliCardCommandsMixin
from .direct_cli_structure_commands import DirectCliStructureCommandsMixin
from .direct_cli_support import DirectCliSupportMixin


def add_direct_action_subcommands(subparsers: Any) -> None:
    """!Register non-interactive direct-action subcommands on an argparse parser."""
    list_boards = subparsers.add_parser('list-boards', help='List all registered boards')
    list_boards.set_defaults(command='list-boards')

    create_board = subparsers.add_parser('create-board', help='Create a board without prompts')
    create_board.add_argument('--name', required=True, help='Board name')
    create_board.add_argument('--description', default='', help='Board description')
    create_board.add_argument('--storage-backend', choices=('json', 'sqlite'), default='json', help='Storage backend to use')
    create_board.add_argument('--target-directory', help='Directory where the board file should be created')
    create_board.add_argument('--switch', action='store_true', help='Switch to the new board after creation')
    create_board.set_defaults(command='create-board')

    switch_board = subparsers.add_parser('switch-board', help='Switch the current board')
    switch_board.add_argument('--board', required=True, help='Board id or exact board name')
    switch_board.set_defaults(command='switch-board')

    rename_board = subparsers.add_parser('rename-board', help='Rename an existing board')
    rename_board.add_argument('--board', required=True, help='Board id or exact board name')
    rename_board.add_argument('--new-name', required=True, help='New board name')
    rename_board.set_defaults(command='rename-board')

    convert_board = subparsers.add_parser('convert-board', help='Convert a board between JSON and SQLite storage')
    convert_board.add_argument('--board', required=True, help='Board id or exact board name')
    convert_board.add_argument('--storage-backend', required=True, choices=('json', 'sqlite'), help='Target storage backend')
    convert_board.add_argument('--target-directory', help='Optional target directory for the converted board file')
    convert_board.set_defaults(command='convert-board')

    delete_board = subparsers.add_parser('delete-board', help='Delete a board')
    delete_board.add_argument('--board', required=True, help='Board id or exact board name')
    delete_board.add_argument('--force', action='store_true', help='Confirm permanent deletion')
    delete_board.set_defaults(command='delete-board')

    board_stats = subparsers.add_parser('board-stats', help='Show board statistics')
    board_stats.add_argument('--board', help='Board id or exact board name; omit to show all boards')
    board_stats.set_defaults(command='board-stats')

    export_board = subparsers.add_parser('export-board', help='Export one board to a JSON file')
    export_board.add_argument('--board', help='Board id or exact board name; omit to export the current board')
    export_board.add_argument('--output', required=True, help='Output JSON file path')
    export_board.set_defaults(command='export-board')

    export_all = subparsers.add_parser('export-all-boards', help='Export all boards to a backup JSON file')
    export_all.add_argument('--output', required=True, help='Output JSON file path')
    export_all.set_defaults(command='export-all-boards')

    import_boards = subparsers.add_parser('import-boards', help='Import all boards from a backup JSON file')
    import_boards.add_argument('--input', required=True, help='Input JSON file path')
    import_boards.add_argument('--force', action='store_true', help='Confirm replacement of existing boards')
    import_boards.set_defaults(command='import-boards')

    load_board = subparsers.add_parser('load-board-from-folder', help='Register an external board from a file or folder')
    load_board.add_argument('--path', required=True, help='Board file path or folder containing boards')
    load_board.add_argument('--board', help='Board id or exact board name inside the folder when multiple are present')
    load_board.add_argument('--name', help='Override the registered board name')
    load_board.add_argument('--description', default='', help='Description to store for the registered board')
    load_board.add_argument('--no-switch', dest='switch', action='store_false', help='Register the board without making it current')
    load_board.set_defaults(command='load-board-from-folder', switch=True)

    undo_manager = subparsers.add_parser('undo-board-management', help='Undo the last board-management action')
    undo_manager.set_defaults(command='undo-board-management')

    redo_manager = subparsers.add_parser('redo-board-management', help='Redo the last undone board-management action')
    redo_manager.set_defaults(command='redo-board-management')

    show_board = subparsers.add_parser('show-board', help='Print the current board or a selected board')
    show_board.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    show_board.set_defaults(command='show-board')

    create_card = subparsers.add_parser('create-card', help='Create a card without prompts')
    create_card.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    create_card.add_argument('--title', required=True, help='Card title')
    create_card.add_argument('--description', default='', help='Card description')
    create_card.add_argument('--priority', choices=('low', 'medium', 'high', 'critical'), default='medium', help='Card priority')
    create_card.add_argument('--column', help='Column id or exact column name')
    create_card.add_argument('--project', help='Project name')
    create_card.add_argument('--start-date', help='Start date in YYYY-MM-DD format')
    create_card.add_argument('--end-date', help='End date in YYYY-MM-DD format')
    create_card.add_argument('--color', help='Hex color value or named color')
    create_card.add_argument('--card-type', help='Card type id or exact card type name')
    create_card.add_argument('--assignee', help='Assignee name')
    create_card.add_argument('--tags', help='Comma-separated tag list')
    create_card.add_argument('--todo', action='append', help='Checklist item text; prefix with [x] to create it completed')
    create_card.set_defaults(command='create-card')

    edit_card = subparsers.add_parser('edit-card', help='Edit an existing card without prompts')
    edit_card.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    edit_card.add_argument('--card', required=True, help='Card id or exact card title')
    edit_card.add_argument('--title', help='Updated title')
    edit_card.add_argument('--description', help='Updated description')
    edit_card.add_argument('--clear-description', action='store_true', help='Clear the card description')
    edit_card.add_argument('--priority', choices=('low', 'medium', 'high', 'critical'), help='Updated priority')
    edit_card.add_argument('--assignee', help='Updated assignee')
    edit_card.add_argument('--clear-assignee', action='store_true', help='Clear the assignee')
    edit_card.add_argument('--project', help='Updated project name')
    edit_card.add_argument('--clear-project', action='store_true', help='Clear the project')
    edit_card.add_argument('--start-date', help='Updated start date in YYYY-MM-DD format')
    edit_card.add_argument('--clear-start-date', action='store_true', help='Clear the start date')
    edit_card.add_argument('--end-date', help='Updated end date in YYYY-MM-DD format')
    edit_card.add_argument('--clear-end-date', action='store_true', help='Clear the end date')
    edit_card.add_argument('--color', help='Updated card color')
    edit_card.add_argument('--clear-color', action='store_true', help='Clear the custom card color')
    edit_card.add_argument('--card-type', help='Updated card type id or exact name')
    edit_card.add_argument('--tags', help='Replacement comma-separated tag list')
    edit_card.add_argument('--clear-tags', action='store_true', help='Clear all tags')
    edit_card.add_argument('--todo', action='append', help='Replacement checklist item text; prefix with [x] to mark completed')
    edit_card.add_argument('--clear-todo-list', action='store_true', help='Clear the checklist for the card')
    edit_card.set_defaults(command='edit-card')

    add_subcard = subparsers.add_parser('add-subcard', help='Create a subcard without prompts')
    add_subcard.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    add_subcard.add_argument('--parent-card', required=True, help='Parent card id or exact card title')
    add_subcard.add_argument('--title', required=True, help='Subcard title')
    add_subcard.add_argument('--description', default='', help='Subcard description')
    add_subcard.add_argument('--priority', choices=('low', 'medium', 'high', 'critical'), default='medium', help='Subcard priority')
    add_subcard.add_argument('--project', help='Project name')
    add_subcard.add_argument('--start-date', help='Start date in YYYY-MM-DD format')
    add_subcard.add_argument('--end-date', help='End date in YYYY-MM-DD format')
    add_subcard.add_argument('--color', help='Hex color value or named color')
    add_subcard.add_argument('--card-type', help='Card type id or exact card type name')
    add_subcard.add_argument('--assignee', help='Assignee name')
    add_subcard.add_argument('--tags', help='Comma-separated tag list')
    add_subcard.add_argument('--todo', action='append', help='Checklist item text; prefix with [x] to create it completed')
    add_subcard.set_defaults(command='add-subcard')

    move_card = subparsers.add_parser('move-card', help='Move a card to another column')
    move_card.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    move_card.add_argument('--card', required=True, help='Card id or exact card title')
    move_card.add_argument('--column', required=True, help='Target column id or exact column name')
    move_card.add_argument('--target-card', help='Insert relative to an existing card id or exact title')
    move_card.add_argument('--insert-after', action='store_true', help='Insert after the target card instead of before it')
    move_card.set_defaults(command='move-card')

    delete_card = subparsers.add_parser('delete-card', help='Delete a card')
    delete_card.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    delete_card.add_argument('--card', required=True, help='Card id or exact card title')
    delete_card.add_argument('--force', action='store_true', help='Confirm permanent deletion')
    delete_card.set_defaults(command='delete-card')

    search_cards = subparsers.add_parser('search-cards', help='Search cards by free text')
    search_cards.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    search_cards.add_argument('--query', required=True, help='Search query')
    search_cards.set_defaults(command='search-cards')

    filter_priority = subparsers.add_parser('filter-priority', help='List cards matching a priority')
    filter_priority.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    filter_priority.add_argument('--priority', required=True, choices=('low', 'medium', 'high', 'critical'), help='Priority to filter by')
    filter_priority.set_defaults(command='filter-priority')

    filter_assignee = subparsers.add_parser('filter-assignee', help='List cards assigned to a specific person')
    filter_assignee.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    filter_assignee.add_argument('--assignee', required=True, help='Assignee to filter by')
    filter_assignee.set_defaults(command='filter-assignee')

    add_tag = subparsers.add_parser('add-tag', help='Add a tag to a card')
    add_tag.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    add_tag.add_argument('--card', required=True, help='Card id or exact card title')
    add_tag.add_argument('--tag', required=True, help='Tag to add')
    add_tag.set_defaults(command='add-tag')

    add_todo_item = subparsers.add_parser('add-todo-item', help='Add a checklist item to a card')
    add_todo_item.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    add_todo_item.add_argument('--card', required=True, help='Card id or exact card title')
    add_todo_item.add_argument('--text', required=True, help='Checklist item text')
    add_todo_item.add_argument('--completed', action='store_true', help='Create the checklist item as completed')
    add_todo_item.set_defaults(command='add-todo-item')

    check_todo_item = subparsers.add_parser('check-todo-item', help='Mark a checklist item as completed')
    check_todo_item.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    check_todo_item.add_argument('--card', required=True, help='Card id or exact card title')
    check_todo_item.add_argument('--item', required=True, help='Checklist item id or exact text')
    check_todo_item.set_defaults(command='check-todo-item')

    uncheck_todo_item = subparsers.add_parser('uncheck-todo-item', help='Mark a checklist item as not completed')
    uncheck_todo_item.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    uncheck_todo_item.add_argument('--card', required=True, help='Card id or exact card title')
    uncheck_todo_item.add_argument('--item', required=True, help='Checklist item id or exact text')
    uncheck_todo_item.set_defaults(command='uncheck-todo-item')

    toggle_todo_item = subparsers.add_parser('toggle-todo-item', help='Toggle the completed state of a checklist item')
    toggle_todo_item.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    toggle_todo_item.add_argument('--card', required=True, help='Card id or exact card title')
    toggle_todo_item.add_argument('--item', required=True, help='Checklist item id or exact text')
    toggle_todo_item.set_defaults(command='toggle-todo-item')

    remove_todo_item = subparsers.add_parser('remove-todo-item', help='Remove a checklist item from a card')
    remove_todo_item.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    remove_todo_item.add_argument('--card', required=True, help='Card id or exact card title')
    remove_todo_item.add_argument('--item', required=True, help='Checklist item id or exact text')
    remove_todo_item.set_defaults(command='remove-todo-item')

    card_details = subparsers.add_parser('card-details', help='Show detailed information about a card')
    card_details.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    card_details.add_argument('--card', required=True, help='Card id or exact card title')
    card_details.set_defaults(command='card-details')

    list_notes = subparsers.add_parser('list-notes', help='List notes recorded on a card')
    list_notes.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    list_notes.add_argument('--card', required=True, help='Card id or exact card title')
    list_notes.set_defaults(command='list-notes')

    add_note = subparsers.add_parser('add-note', help='Add a note to a card')
    add_note.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    add_note.add_argument('--card', required=True, help='Card id or exact card title')
    add_note.add_argument('--text', required=True, help='Note text')
    add_note.set_defaults(command='add-note')

    edit_note = subparsers.add_parser('edit-note', help='Edit an existing note on a card')
    edit_note.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    edit_note.add_argument('--card', required=True, help='Card id or exact card title')
    edit_note.add_argument('--note', required=True, help='Note id or exact note text')
    edit_note.add_argument('--text', required=True, help='Replacement note text')
    edit_note.set_defaults(command='edit-note')

    delete_note = subparsers.add_parser('delete-note', help='Delete a note from a card')
    delete_note.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    delete_note.add_argument('--card', required=True, help='Card id or exact card title')
    delete_note.add_argument('--note', required=True, help='Note id or exact note text')
    delete_note.set_defaults(command='delete-note')

    archive_done = subparsers.add_parser('archive-done-cards', help='Archive all active cards from completed columns')
    archive_done.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    archive_done.add_argument('--force', action='store_true', help='Confirm archiving done cards')
    archive_done.set_defaults(command='archive-done-cards')

    list_archived = subparsers.add_parser('list-archived-cards', help='List archived cards for a board')
    list_archived.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    list_archived.set_defaults(command='list-archived-cards')

    restore_archived = subparsers.add_parser('restore-archived-card', help='Restore an archived card')
    restore_archived.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    restore_archived.add_argument('--card', required=True, help='Archived card id or exact card title')
    restore_archived.set_defaults(command='restore-archived-card')

    delete_archived = subparsers.add_parser('delete-archived-card', help='Permanently delete an archived card')
    delete_archived.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    delete_archived.add_argument('--card', required=True, help='Archived card id or exact card title')
    delete_archived.add_argument('--force', action='store_true', help='Confirm permanent deletion of the archived card')
    delete_archived.set_defaults(command='delete-archived-card')

    create_column = subparsers.add_parser('create-column', help='Create a new column')
    create_column.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    create_column.add_argument('--name', required=True, help='Column name')
    create_column.add_argument('--position', type=int, help='Zero-based column position')
    create_column.add_argument('--color', default='#2196F3', help='Column color')
    create_column.add_argument('--completed', action='store_true', help='Mark the column as completed')
    create_column.add_argument('--can-add-card', action='store_true', help='Allow direct add-card actions in the column')
    create_column.set_defaults(command='create-column')

    rename_column = subparsers.add_parser('rename-column', help='Rename a column')
    rename_column.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    rename_column.add_argument('--column', required=True, help='Column id or exact column name')
    rename_column.add_argument('--new-name', required=True, help='New column name')
    rename_column.set_defaults(command='rename-column')

    delete_column = subparsers.add_parser('delete-column', help='Delete a column')
    delete_column.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    delete_column.add_argument('--column', required=True, help='Column id or exact column name')
    delete_column.add_argument('--move-cards-to', help='Target column id or exact name for existing cards')
    delete_column.set_defaults(command='delete-column')

    reorder_columns = subparsers.add_parser('reorder-columns', help='Reorder columns by name or id')
    reorder_columns.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    reorder_columns.add_argument('--order', nargs='+', required=True, help='Full column order using ids or exact names')
    reorder_columns.set_defaults(command='reorder-columns')

    change_column_color = subparsers.add_parser('change-column-color', help='Change a column color')
    change_column_color.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    change_column_color.add_argument('--column', required=True, help='Column id or exact column name')
    change_column_color.add_argument('--color', required=True, help='New column color')
    change_column_color.set_defaults(command='change-column-color')

    edit_flags = subparsers.add_parser('edit-column-flags', help='Change completed/add-card flags for a column')
    edit_flags.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    edit_flags.add_argument('--column', required=True, help='Column id or exact column name')
    completed_group = edit_flags.add_mutually_exclusive_group()
    completed_group.add_argument('--completed', dest='is_completed', action='store_true', help='Mark the column as completed')
    completed_group.add_argument('--not-completed', dest='is_completed', action='store_false', help='Clear the completed flag')
    add_card_group = edit_flags.add_mutually_exclusive_group()
    add_card_group.add_argument('--can-add-card', dest='can_add_card', action='store_true', help='Enable add-card actions for the column')
    add_card_group.add_argument('--cannot-add-card', dest='can_add_card', action='store_false', help='Disable add-card actions for the column')
    edit_flags.set_defaults(command='edit-column-flags', is_completed=None, can_add_card=None)

    list_columns = subparsers.add_parser('list-columns', help='List columns for a board')
    list_columns.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    list_columns.set_defaults(command='list-columns')

    list_card_types = subparsers.add_parser('list-card-types', help='List card types for a board')
    list_card_types.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    list_card_types.set_defaults(command='list-card-types')

    create_card_type = subparsers.add_parser('create-card-type', help='Create a card type')
    create_card_type.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    create_card_type.add_argument('--name', required=True, help='Card type name')
    create_card_type.add_argument('--description', default='', help='Card type description')
    create_card_type.add_argument('--default-project', help='Default project name')
    create_card_type.add_argument('--default-color', help='Default card color')
    create_card_type.set_defaults(command='create-card-type')

    edit_card_type = subparsers.add_parser('edit-card-type', help='Edit a card type')
    edit_card_type.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    edit_card_type.add_argument('--card-type', required=True, help='Card type id or exact name')
    edit_card_type.add_argument('--name', help='New card type name')
    edit_card_type.add_argument('--description', help='New card type description')
    edit_card_type.add_argument('--clear-description', action='store_true', help='Clear the card type description')
    edit_card_type.add_argument('--default-project', help='New default project')
    edit_card_type.add_argument('--clear-default-project', action='store_true', help='Clear the default project')
    edit_card_type.add_argument('--default-color', help='New default color')
    edit_card_type.add_argument('--clear-default-color', action='store_true', help='Clear the default color')
    edit_card_type.set_defaults(command='edit-card-type')

    delete_card_type = subparsers.add_parser('delete-card-type', help='Delete a card type')
    delete_card_type.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    delete_card_type.add_argument('--card-type', required=True, help='Card type id or exact name')
    delete_card_type.add_argument('--delete-cards', action='store_true', help='Delete cards using this type instead of reassigning them')
    delete_card_type.add_argument('--replacement-card-type', help='Replacement card type id or exact name')
    delete_card_type.set_defaults(command='delete-card-type')

    create_backup = subparsers.add_parser('create-backup', help='Create a board backup file')
    create_backup.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    create_backup.add_argument('--output', help='Backup file path; omit to use the default backup naming')
    create_backup.set_defaults(command='create-backup')

    cleanup = subparsers.add_parser('cleanup-orphaned-attachments', help='Remove orphaned board attachment files')
    cleanup.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    cleanup.set_defaults(command='cleanup-orphaned-attachments')

    undo_board = subparsers.add_parser('undo-current-board', help='Undo the last action on a board')
    undo_board.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    undo_board.set_defaults(command='undo-current-board')

    redo_board = subparsers.add_parser('redo-current-board', help='Redo the last undone action on a board')
    redo_board.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    redo_board.set_defaults(command='redo-current-board')


class DirectActionCLI(
    DirectCliBoardCommandsMixin,
    DirectCliCardCommandsMixin,
    DirectCliStructureCommandsMixin,
    DirectCliSupportMixin,
):
    """!Execute direct non-interactive board and card operations."""

    def __init__(self, board_manager: BoardManager, lock_action: str = 'cancel'):
        """!Init."""
        self.board_manager = board_manager
        self.lock_action = lock_action
        self.board_manager.set_lock_handler(lambda _file_path, _lock_details: lock_action)

    def execute(self, args: argparse.Namespace) -> int:
        """!Dispatch the parsed direct-action command."""
        handler = getattr(self, f"cmd_{args.command.replace('-', '_')}", None)
        if handler is None:
            raise ValueError(f"Unsupported direct command: {args.command}")
        handler(args)
        return 0
