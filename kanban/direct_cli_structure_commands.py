## @file
#  @brief Column, card-type, and maintenance commands for the direct-action CLI.
"""Column, card-type, and maintenance commands for the direct-action CLI."""

from __future__ import annotations

import argparse

from .models import UNSET


class DirectCliStructureCommandsMixin:
    """Column, card-type, and maintenance commands for the direct CLI."""

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
            print(f"{column.name} ({column.id}){marker_text} color={column.color} cards={len(board.get_column_cards(column))}")

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
            print(
                f"  description={card_type.description or '(none)'} "
                f"project={card_type.default_project or '(none)'} color={card_type.default_color or '(default)'}"
            )

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