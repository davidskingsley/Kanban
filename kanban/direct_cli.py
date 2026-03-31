## @file
#  @brief Non-interactive command-line actions for the Kanban application.
"""Direct-action CLI support for automating Kanban board operations."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence, Tuple

from .board import KanbanBoard
from .board_manager import BoardLockCancelledError, BoardManager
from .models import UNSET, Card, CardType, CustomColumn, Priority


def add_direct_action_subcommands(subparsers: argparse._SubParsersAction):
    """Register non-interactive direct-action subcommands on an argparse parser."""
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

    card_details = subparsers.add_parser('card-details', help='Show detailed information about a card')
    card_details.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    card_details.add_argument('--card', required=True, help='Card id or exact card title')
    card_details.set_defaults(command='card-details')

    clear_done = subparsers.add_parser('clear-done-cards', help='Delete all cards from completed columns')
    clear_done.add_argument('--board', help='Board id or exact board name; omit to use the current board')
    clear_done.add_argument('--force', action='store_true', help='Confirm deletion of done cards')
    clear_done.set_defaults(command='clear-done-cards')

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


class DirectActionCLI:
    """Execute direct non-interactive board and card operations."""

    def __init__(self, board_manager: BoardManager, lock_action: str = 'cancel'):
        self.board_manager = board_manager
        self.lock_action = lock_action
        self.board_manager.set_lock_handler(lambda _file_path, _lock_details: lock_action)

    def execute(self, args: argparse.Namespace) -> int:
        """Dispatch the parsed direct-action command."""
        handler = getattr(self, f"cmd_{args.command.replace('-', '_')}", None)
        if handler is None:
            raise ValueError(f"Unsupported direct command: {args.command}")
        handler(args)
        return 0

    def cmd_list_boards(self, args: argparse.Namespace):
        boards = self.board_manager.get_board_list()
        if not boards:
            print('No boards found.')
            return

        for board in boards:
            markers = []
            if board.get('is_current'):
                markers.append('current')
            if board.get('external'):
                markers.append('external')
            marker_text = f" [{' | '.join(markers)}]" if markers else ''
            print(f"{board['name']} ({board['id']}){marker_text} backend={board.get('storage_backend', 'json')}")
            if board.get('description'):
                print(f"  {board['description']}")

    def cmd_create_board(self, args: argparse.Namespace):
        board_id = self.board_manager.create_board(
            args.name,
            args.description,
            target_directory=args.target_directory,
            storage_backend=args.storage_backend,
        )
        if args.switch and self.board_manager.current_board_id != board_id:
            self.board_manager.switch_board(board_id)
        print(f"Created board '{args.name}' ({board_id}) using {args.storage_backend} backend.")

    def cmd_switch_board(self, args: argparse.Namespace):
        board_id, board_info = self._resolve_board_reference(args.board)
        if not self.board_manager.switch_board(board_id):
            raise ValueError(f"Unable to switch to board '{board_info['name']}'.")
        print(f"Switched to board '{board_info['name']}'.")

    def cmd_rename_board(self, args: argparse.Namespace):
        board_id, board_info = self._resolve_board_reference(args.board)
        if not self.board_manager.rename_board(board_id, args.new_name):
            raise ValueError(f"Unable to rename board '{board_info['name']}'.")
        print(f"Renamed board '{board_info['name']}' to '{args.new_name}'.")

    def cmd_delete_board(self, args: argparse.Namespace):
        self._require_force(args.force, 'Deleting a board requires --force.')
        board_id, board_info = self._resolve_board_reference(args.board)
        if not self.board_manager.delete_board(board_id):
            raise ValueError(f"Unable to delete board '{board_info['name']}'.")
        print(f"Deleted board '{board_info['name']}'.")

    def cmd_board_stats(self, args: argparse.Namespace):
        if args.board:
            board_id, board_info, board = self._load_board(args.board)
            stats = board.get_board_stats()
            print(f"Board: {board_info['name']} ({board_id})")
            print(f"Total cards: {stats['total_cards']}")
            print(f"To Do: {stats['todo']}")
            print(f"In Progress: {stats['in_progress']}")
            print(f"Review: {stats['review']}")
            print(f"Done: {stats['done']}")
            return

        boards = self.board_manager.get_board_list()
        if not boards:
            print('No boards found.')
            return

        for board in boards:
            print(f"{board['name']} ({board['id']})")
            stats = board.get('stats')
            if stats is None:
                _, _, loaded_board = self._load_board(board['id'])
                stats = loaded_board.get_board_stats()
            print(f"  cards={stats['total_cards']} todo={stats['todo']} in_progress={stats['in_progress']} review={stats['review']} done={stats['done']}")

    def cmd_export_board(self, args: argparse.Namespace):
        board_id, board_info = self._resolve_board_reference(args.board)
        export_data = self.board_manager.export_board_data(board_id)
        self._write_json(args.output, export_data)
        print(f"Exported board '{board_info['name']}' to '{args.output}'.")

    def cmd_export_all_boards(self, args: argparse.Namespace):
        export_data = self.board_manager.export_all_boards()
        self._write_json(args.output, export_data)
        print(f"Exported all boards to '{args.output}'.")

    def cmd_import_boards(self, args: argparse.Namespace):
        self._require_force(args.force, 'Importing boards requires --force because it replaces the current registry.')
        with open(args.input, 'r', encoding='utf-8') as input_file:
            import_data = json.load(input_file)
        if not self.board_manager.import_boards(import_data):
            raise ValueError('Board import failed.')
        print(f"Imported boards from '{args.input}'.")

    def cmd_load_board_from_folder(self, args: argparse.Namespace):
        chosen = self._select_external_board(args.path, args.board)
        board_id = self.board_manager.add_external_board(
            chosen['data_file'],
            name=args.name or chosen['name'],
            description=args.description or chosen.get('description', ''),
            switch_to=args.switch,
        )
        if not board_id:
            raise ValueError('Board load cancelled.')
        print(f"Registered board '{args.name or chosen['name']}' from '{chosen['data_file']}'.")

    def cmd_undo_board_management(self, args: argparse.Namespace):
        description = self.board_manager.undo_last_action()
        if not description:
            raise ValueError('No board-management action is available to undo.')
        print(f"Undid board-management action: {description}")

    def cmd_redo_board_management(self, args: argparse.Namespace):
        description = self.board_manager.redo_last_action()
        if not description:
            raise ValueError('No board-management action is available to redo.')
        print(f"Redid board-management action: {description}")

    def cmd_show_board(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        print(f"Board: {board_info['name']}")
        print(board.export_board())

    def cmd_create_card(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        column_id = self._resolve_column(board, args.column).id if args.column else None
        card_type_id = self._resolve_card_type(board, args.card_type).id if args.card_type else None
        start_date = self._parse_date(args.start_date, 'start-date') if args.start_date else None
        end_date = self._parse_date(args.end_date, 'end-date') if args.end_date else None
        tags = self._parse_tags(args.tags)
        priority = self._parse_priority(args.priority)
        card = board.create_card(
            args.title,
            args.description,
            priority,
            column_id,
            args.project,
            start_date,
            end_date,
            color=args.color,
            card_type_id=card_type_id,
            assignee=args.assignee,
            tags=tags,
        )
        print(f"Created card '{card.title}' ({card.id}) on board '{board_info['name']}'.")

    def cmd_edit_card(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        description = self._pick_optional_value(args.description, args.clear_description, '')
        assignee = self._pick_optional_value(args.assignee, args.clear_assignee, None)
        project = self._pick_optional_value(args.project, args.clear_project, None)
        color = self._pick_optional_value(args.color, args.clear_color, None)
        start_date = self._pick_optional_date(args.start_date, args.clear_start_date, 'start-date')
        end_date = self._pick_optional_date(args.end_date, args.clear_end_date, 'end-date')
        tags = self._pick_optional_tags(args.tags, args.clear_tags)
        card_type_id = self._resolve_card_type(board, args.card_type).id if args.card_type else UNSET
        priority = self._parse_priority(args.priority) if args.priority else None

        board._ensure_writable()
        board._push_undo_state(f"Edit card '{card.title}'")

        if args.title is not None:
            card.title = args.title
        if description is not UNSET:
            card.description = description
        if priority is not None:
            card.priority = priority
        if assignee is not UNSET:
            card.assignee = assignee
        if project is not UNSET:
            card.project = project
            if project is not None:
                board._ensure_project_exists(project)
        if start_date is not UNSET:
            card.start_date = start_date
        if end_date is not UNSET:
            card.end_date = end_date
        if color is not UNSET:
            card.color = color
        if card_type_id is not UNSET:
            card.card_type_id = card_type_id
            board.last_used_card_type_id = card_type_id
        if tags is not UNSET:
            card.tags = list(dict.fromkeys(tags or []))

        card.updated_at = datetime.now()
        board.save_board()
        print(f"Updated card '{card.title}' on board '{board_info['name']}'.")

    def cmd_add_subcard(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        parent = self._resolve_card(board, args.parent_card)
        card_type_id = self._resolve_card_type(board, args.card_type).id if args.card_type else None
        start_date = self._parse_date(args.start_date, 'start-date') if args.start_date else None
        end_date = self._parse_date(args.end_date, 'end-date') if args.end_date else None
        tags = self._parse_tags(args.tags)
        priority = self._parse_priority(args.priority)
        child = board.create_subcard(
            parent.id,
            args.title,
            args.description,
            priority,
            args.project,
            args.color,
            card_type_id,
            start_date,
            end_date,
            args.assignee,
            tags,
        )
        print(f"Created subcard '{child.title}' ({child.id}) under '{parent.title}' on board '{board_info['name']}'.")

    def cmd_move_card(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        column = self._resolve_column(board, args.column)
        target_card_id = self._resolve_card(board, args.target_card).id if args.target_card else None
        if not board.move_card(card.id, column.id, target_card_id=target_card_id, insert_after=args.insert_after):
            raise ValueError(f"Unable to move card '{card.title}'.")
        print(f"Moved card '{card.title}' to column '{column.name}' on board '{board_info['name']}'.")

    def cmd_delete_card(self, args: argparse.Namespace):
        self._require_force(args.force, 'Deleting a card requires --force.')
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        if not board.delete_card(card.id):
            raise ValueError(f"Unable to delete card '{card.title}'.")
        print(f"Deleted card '{card.title}' from board '{board_info['name']}'.")

    def cmd_search_cards(self, args: argparse.Namespace):
        _, _, board = self._load_board(args.board)
        results = board.search_cards(args.query)
        self._print_cards(board, results)

    def cmd_filter_priority(self, args: argparse.Namespace):
        _, _, board = self._load_board(args.board)
        results = board.get_cards_by_priority(self._parse_priority(args.priority))
        self._print_cards(board, results)

    def cmd_filter_assignee(self, args: argparse.Namespace):
        _, _, board = self._load_board(args.board)
        results = board.get_cards_by_assignee(args.assignee)
        self._print_cards(board, results)

    def cmd_add_tag(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        if not board.add_card_tag(card.id, args.tag):
            raise ValueError(f"Unable to add tag '{args.tag}' to card '{card.title}'.")
        print(f"Added tag '{args.tag}' to card '{card.title}' on board '{board_info['name']}'.")

    def cmd_card_details(self, args: argparse.Namespace):
        _, _, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        self._print_card_details(board, card)

    def cmd_clear_done_cards(self, args: argparse.Namespace):
        self._require_force(args.force, 'Clearing done cards requires --force.')
        _, board_info, board = self._load_board(args.board)
        cleared = board.clear_done_cards()
        print(f"Cleared {cleared} done card(s) from board '{board_info['name']}'.")

    def cmd_create_column(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        column_id = board.create_column(
            args.name,
            position=args.position,
            color=args.color,
            is_completed=args.completed,
            can_add_card=args.can_add_card,
        )
        print(f"Created column '{args.name}' ({column_id}) on board '{board_info['name']}'.")

    def cmd_rename_column(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        column = self._resolve_column(board, args.column)
        if not board.rename_column(column.id, args.new_name):
            raise ValueError(f"Unable to rename column '{column.name}'.")
        print(f"Renamed column '{column.name}' to '{args.new_name}' on board '{board_info['name']}'.")

    def cmd_delete_column(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        column = self._resolve_column(board, args.column)
        move_target_id = self._resolve_column(board, args.move_cards_to).id if args.move_cards_to else None
        if not board.delete_column(column.id, move_cards_to=move_target_id):
            raise ValueError(f"Unable to delete column '{column.name}'.")
        print(f"Deleted column '{column.name}' from board '{board_info['name']}'.")

    def cmd_reorder_columns(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        ordered_ids = [self._resolve_column(board, token).id for token in self._normalize_order_tokens(args.order)]
        if not board.reorder_columns(ordered_ids):
            raise ValueError('Unable to reorder columns. Provide every column exactly once.')
        print(f"Reordered columns on board '{board_info['name']}'.")

    def cmd_change_column_color(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        column = self._resolve_column(board, args.column)
        if not board.change_column_color(column.id, args.color):
            raise ValueError(f"Unable to change color for column '{column.name}'.")
        print(f"Changed color for column '{column.name}' on board '{board_info['name']}'.")

    def cmd_edit_column_flags(self, args: argparse.Namespace):
        if args.is_completed is None and args.can_add_card is None:
            raise ValueError('Provide at least one of --completed/--not-completed or --can-add-card/--cannot-add-card.')
        _, board_info, board = self._load_board(args.board)
        column = self._resolve_column(board, args.column)
        if not board.update_column(
            column.id,
            is_completed=UNSET if args.is_completed is None else args.is_completed,
            can_add_card=UNSET if args.can_add_card is None else args.can_add_card,
        ):
            raise ValueError(f"Unable to update flags for column '{column.name}'.")
        print(f"Updated flags for column '{column.name}' on board '{board_info['name']}'.")

    def cmd_list_columns(self, args: argparse.Namespace):
        _, _, board = self._load_board(args.board)
        for column in board.get_columns_ordered():
            markers = []
            if column.can_add_card:
                markers.append('add')
            if column.is_completed:
                markers.append('done')
            marker_text = f" [{' | '.join(markers)}]" if markers else ''
            print(f"{column.name} ({column.id}){marker_text} color={column.color} cards={len(column.cards)}")

    def cmd_list_card_types(self, args: argparse.Namespace):
        _, _, board = self._load_board(args.board)
        default_type_id = board.get_default_card_type_id()
        last_used_id = board.get_last_used_card_type().id
        for card_type in board.get_card_types_ordered():
            markers = []
            if card_type.id == default_type_id:
                markers.append('default')
            if card_type.id == last_used_id:
                markers.append('last used')
            marker_text = f" [{' | '.join(markers)}]" if markers else ''
            print(f"{card_type.name} ({card_type.id}){marker_text}")
            print(f"  description={card_type.description or '(none)'} project={card_type.default_project or '(none)'} color={card_type.default_color or '(default)'}")

    def cmd_create_card_type(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        card_type_id = board.create_card_type(args.name, args.description, args.default_project, args.default_color)
        print(f"Created card type '{args.name}' ({card_type_id}) on board '{board_info['name']}'.")

    def cmd_edit_card_type(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        card_type = self._resolve_card_type(board, args.card_type)
        description = '' if args.clear_description else args.description
        default_project = self._pick_optional_value(args.default_project, args.clear_default_project, None)
        default_color = self._pick_optional_value(args.default_color, args.clear_default_color, None)
        updated = board.edit_card_type(
            card_type.id,
            args.name,
            description,
            default_project=default_project,
            default_color=default_color,
        )
        if updated is None:
            raise ValueError(f"Unable to edit card type '{card_type.name}'.")
        print(f"Updated card type '{updated.name}' on board '{board_info['name']}'.")

    def cmd_delete_card_type(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        card_type = self._resolve_card_type(board, args.card_type)
        replacement_type_id = self._resolve_card_type(board, args.replacement_card_type).id if args.replacement_card_type else None
        if not board.delete_card_type(card_type.id, delete_cards=args.delete_cards, replacement_type_id=replacement_type_id):
            raise ValueError(f"Unable to delete card type '{card_type.name}'.")
        print(f"Deleted card type '{card_type.name}' from board '{board_info['name']}'.")

    def cmd_create_backup(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        backup_path = board.storage.backup(args.output)
        if not backup_path:
            raise ValueError(f"Unable to create a backup for board '{board_info['name']}'.")
        print(f"Created backup for board '{board_info['name']}' at '{backup_path}'.")

    def cmd_cleanup_orphaned_attachments(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        result = board.cleanup_orphaned_attachment_files()
        print(
            f"Cleaned attachment store for board '{board_info['name']}': "
            f"removed_files={result['removed_files']} removed_directories={result['removed_directories']} "
            f"retained_files={result['retained_files']}"
        )

    def cmd_undo_current_board(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        description = board.undo_last_action()
        if not description:
            raise ValueError(f"No board action is available to undo on '{board_info['name']}'.")
        print(f"Undid board action on '{board_info['name']}': {description}")

    def cmd_redo_current_board(self, args: argparse.Namespace):
        _, board_info, board = self._load_board(args.board)
        description = board.redo_last_action()
        if not description:
            raise ValueError(f"No board action is available to redo on '{board_info['name']}'.")
        print(f"Redid board action on '{board_info['name']}': {description}")

    def _resolve_board_reference(self, identifier: Optional[str]) -> Tuple[str, Dict[str, object]]:
        metadata = self.board_manager.load_metadata()
        boards = metadata.get('boards', {})
        if not boards:
            raise ValueError('No boards are available.')

        if identifier is None:
            current_board_id = metadata.get('current_board')
            if current_board_id and current_board_id in boards:
                return current_board_id, boards[current_board_id]
            raise ValueError('No current board is selected. Provide --board.')

        if identifier in boards:
            return identifier, boards[identifier]

        normalized = identifier.strip().lower()
        matches = [
            (board_id, board_info)
            for board_id, board_info in boards.items()
            if board_info.get('name', '').strip().lower() == normalized
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple boards match '{identifier}'. Use a board id instead.")
        raise ValueError(f"Board '{identifier}' was not found.")

    def _load_board(self, identifier: Optional[str]) -> Tuple[str, Dict[str, object], KanbanBoard]:
        board_id, board_info = self._resolve_board_reference(identifier)
        if board_id in self.board_manager.boards:
            return board_id, board_info, self.board_manager.boards[board_id]

        try:
            board = self.board_manager._load_board_from_metadata(board_id, board_info)
        except BoardLockCancelledError as error:
            raise ValueError(f"Board '{board_info['name']}' could not be opened because it is locked.") from error
        return board_id, board_info, board

    def _resolve_column(self, board: KanbanBoard, identifier: str) -> CustomColumn:
        if identifier in board.custom_columns:
            return board.custom_columns[identifier]

        normalized = identifier.strip().lower()
        matches = [column for column in board.get_columns_ordered() if column.name.strip().lower() == normalized]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple columns match '{identifier}'. Use a column id instead.")
        raise ValueError(f"Column '{identifier}' was not found.")

    def _resolve_card(self, board: KanbanBoard, identifier: str) -> Card:
        card = board.find_card(identifier)
        if card is not None:
            return card

        normalized = identifier.strip().lower()
        matches = [candidate for candidate in board.get_all_cards() if candidate.title.strip().lower() == normalized]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple cards match '{identifier}'. Use a card id instead.")
        raise ValueError(f"Card '{identifier}' was not found.")

    def _resolve_card_type(self, board: KanbanBoard, identifier: str) -> CardType:
        card_type = board.get_card_type(identifier)
        if card_type is not None:
            return card_type

        normalized = identifier.strip().lower()
        matches = [candidate for candidate in board.get_card_types_ordered() if candidate.name.strip().lower() == normalized]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple card types match '{identifier}'. Use a card type id instead.")
        raise ValueError(f"Card type '{identifier}' was not found.")

    def _select_external_board(self, path: str, identifier: Optional[str]) -> Dict[str, object]:
        absolute_path = os.path.abspath(path)
        if os.path.isfile(absolute_path):
            inspected = self.board_manager.inspect_board_file(absolute_path)
            inspected['description'] = ''
            return inspected
        if not os.path.isdir(absolute_path):
            raise ValueError(f"Path '{path}' does not exist.")

        options = self._discover_external_boards(absolute_path)
        if not options:
            raise ValueError('No board files were found in the selected path.')
        if identifier is None:
            if len(options) == 1:
                return options[0]
            raise ValueError('Multiple boards were found. Provide --board to select one.')

        normalized = identifier.strip().lower()
        matches = [
            option
            for option in options
            if option['name'].strip().lower() == normalized
            or option.get('board_id', '').strip().lower() == normalized
            or os.path.splitext(os.path.basename(option['data_file']))[0].strip().lower() == normalized
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple boards match '{identifier}'. Use a more specific name or board id.")
        raise ValueError(f"Board '{identifier}' was not found in '{path}'.")

    def _discover_external_boards(self, folder: str) -> List[Dict[str, object]]:
        metadata_path = os.path.join(folder, 'boards_metadata.json')
        options: List[Dict[str, object]] = []

        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
                metadata = json.load(metadata_file)
            for board_id, board_info in metadata.get('boards', {}).items():
                if board_info.get('use_custom_columns') is False:
                    continue
                data_file = board_info.get('data_file')
                if not data_file:
                    continue
                if not os.path.isabs(data_file):
                    data_file = os.path.join(folder, data_file)
                options.append({
                    'board_id': board_id,
                    'data_file': os.path.abspath(data_file),
                    'name': board_info.get('name', board_id),
                    'description': board_info.get('description', ''),
                })
            return options

        for entry in sorted(os.listdir(folder)):
            candidate_path = os.path.join(folder, entry)
            if entry == 'boards_metadata.json' or os.path.isdir(candidate_path) or '.backup.' in entry.lower():
                continue
            try:
                inspected = self.board_manager.inspect_board_file(candidate_path)
            except (FileNotFoundError, ValueError):
                continue
            inspected['description'] = ''
            options.append(inspected)
        return options

    def _print_cards(self, board: KanbanBoard, cards: Sequence[Card]):
        if not cards:
            print('No cards matched.')
            return
        for card in cards:
            print(
                f"{card.title} ({card.id}) "
                f"[{board.get_card_location_label(card)}] priority={card.priority.value} assignee={card.assignee or '(none)'}"
            )

    def _print_card_details(self, board: KanbanBoard, card: Card):
        card_type = board.get_card_type(card.card_type_id)
        print(f"ID: {card.id}")
        print(f"Title: {card.title}")
        print(f"Description: {card.description or '(no description)'}")
        print(f"Column: {board.get_card_location_label(card)}")
        print(f"Priority: {card.priority.value}")
        print(f"Type: {card_type.name if card_type else board.get_default_card_type().name}")
        print(f"Project: {card.project or '(none)'}")
        print(f"Assignee: {card.assignee or '(unassigned)'}")
        print(f"Start Date: {card.start_date.isoformat() if card.start_date else '(none)'}")
        print(f"End Date: {card.end_date.isoformat() if card.end_date else '(none)'}")
        print(f"Color: {card.color or '(default)'}")
        print(f"Tags: {', '.join(card.tags) if card.tags else '(no tags)'}")
        parent_card = board.get_parent_card(card)
        if parent_card is not None:
            print(f"Parent Card: {parent_card.title}")
        completed, total = board.get_subcard_progress(card.id)
        if total:
            print(f"Subcards: {completed}/{total} done")

    def _pick_optional_value(self, value: Optional[str], clear: bool, clear_value):
        if clear:
            return clear_value
        if value is not None:
            return value
        return UNSET

    def _pick_optional_date(self, value: Optional[str], clear: bool, label: str):
        if clear:
            return None
        if value is not None:
            return self._parse_date(value, label)
        return UNSET

    def _pick_optional_tags(self, tags_text: Optional[str], clear: bool):
        if clear:
            return []
        if tags_text is not None:
            return self._parse_tags(tags_text)
        return UNSET

    def _normalize_order_tokens(self, values: Sequence[str]) -> List[str]:
        if len(values) == 1 and ',' in values[0]:
            return [token.strip() for token in values[0].split(',') if token.strip()]
        return [value.strip() for value in values if value.strip()]

    def _parse_date(self, value: str, label: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{label} must use YYYY-MM-DD format.") from error

    def _parse_priority(self, value: str) -> Priority:
        return Priority(value.strip().lower())

    def _parse_tags(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        tags = []
        for raw_tag in value.split(','):
            tag = raw_tag.strip().lstrip('#')
            if tag and tag not in tags:
                tags.append(tag)
        return tags

    def _write_json(self, output_path: str, payload: Dict[str, object]):
        directory = os.path.dirname(os.path.abspath(output_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as output_file:
            json.dump(payload, output_file, indent=2, ensure_ascii=False)

    def _require_force(self, enabled: bool, message: str):
        if not enabled:
            raise ValueError(message)
