## @file
#  @brief Card and archive commands for the direct-action CLI.
"""!Card and archive commands for the direct-action CLI."""

from __future__ import annotations

import argparse
from datetime import datetime

from .models import UNSET


class DirectCliCardCommandsMixin:
    """!Card, checklist, and archive commands for the direct CLI."""

    def cmd_create_card(self, args: argparse.Namespace):
        """!Cmd create card."""
        _, board_info, board = self._load_board(args.board)
        column_id = self._resolve_column(board, args.column).id if args.column else None
        card_type_id = self._resolve_card_type(board, args.card_type).id if args.card_type else None
        start_date = self._parse_date(args.start_date, 'start-date') if args.start_date else None
        end_date = self._parse_date(args.end_date, 'end-date') if args.end_date else None
        tags = self._parse_tags(args.tags)
        todo_items = self._parse_todo_items(args.todo)
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
            todo_items=todo_items,
        )
        print(f"Created card '{card.title}' ({card.id}) on board '{board_info['name']}'.")

    def cmd_edit_card(self, args: argparse.Namespace):
        """!Cmd edit card."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        description = self._pick_optional_value(args.description, args.clear_description, '')
        assignee = self._pick_optional_value(args.assignee, args.clear_assignee, None)
        project = self._pick_optional_value(args.project, args.clear_project, None)
        color = self._pick_optional_value(args.color, args.clear_color, None)
        start_date = self._pick_optional_date(args.start_date, args.clear_start_date, 'start-date')
        end_date = self._pick_optional_date(args.end_date, args.clear_end_date, 'end-date')
        tags = self._pick_optional_tags(args.tags, args.clear_tags)
        todo_items = self._pick_optional_todo_items(args.todo, args.clear_todo_list)
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
        if todo_items is not UNSET:
            card.todo_items = card._coerce_todo_items(todo_items)

        card.updated_at = datetime.now()
        board.save_board()
        print(f"Updated card '{card.title}' on board '{board_info['name']}'.")

    def cmd_add_subcard(self, args: argparse.Namespace):
        """!Cmd add subcard."""
        _, board_info, board = self._load_board(args.board)
        parent = self._resolve_card(board, args.parent_card)
        card_type_id = self._resolve_card_type(board, args.card_type).id if args.card_type else None
        start_date = self._parse_date(args.start_date, 'start-date') if args.start_date else None
        end_date = self._parse_date(args.end_date, 'end-date') if args.end_date else None
        tags = self._parse_tags(args.tags)
        todo_items = self._parse_todo_items(args.todo)
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
            todo_items,
        )
        print(f"Created subcard '{child.title}' ({child.id}) under '{parent.title}' on board '{board_info['name']}'.")

    def cmd_move_card(self, args: argparse.Namespace):
        """!Cmd move card."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        column = self._resolve_column(board, args.column)
        target_card_id = self._resolve_card(board, args.target_card).id if args.target_card else None
        if not board.move_card(card.id, column.id, target_card_id=target_card_id, insert_after=args.insert_after):
            raise ValueError(f"Unable to move card '{card.title}'.")
        print(f"Moved card '{card.title}' to column '{column.name}' on board '{board_info['name']}'.")

    def cmd_delete_card(self, args: argparse.Namespace):
        """!Cmd delete card."""
        self._require_force(args.force, 'Deleting a card requires --force.')
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        if not board.delete_card(card.id):
            raise ValueError(f"Unable to delete card '{card.title}'.")
        print(f"Deleted card '{card.title}' from board '{board_info['name']}'.")

    def cmd_search_cards(self, args: argparse.Namespace):
        """!Cmd search cards."""
        _, _, board = self._load_board(args.board)
        results = board.search_cards(args.query)
        self._print_cards(board, results)

    def cmd_filter_priority(self, args: argparse.Namespace):
        """!Cmd filter priority."""
        _, _, board = self._load_board(args.board)
        results = board.get_cards_by_priority(self._parse_priority(args.priority))
        self._print_cards(board, results)

    def cmd_filter_assignee(self, args: argparse.Namespace):
        """!Cmd filter assignee."""
        _, _, board = self._load_board(args.board)
        results = board.get_cards_by_assignee(args.assignee)
        self._print_cards(board, results)

    def cmd_add_tag(self, args: argparse.Namespace):
        """!Cmd add tag."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        if not board.add_card_tag(card.id, args.tag):
            raise ValueError(f"Unable to add tag '{args.tag}' to card '{card.title}'.")
        print(f"Added tag '{args.tag}' to card '{card.title}' on board '{board_info['name']}'.")

    def cmd_add_todo_item(self, args: argparse.Namespace):
        """!Cmd add todo item."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        todo_item = board.add_card_todo_item(card.id, args.text, completed=args.completed)
        if todo_item is None:
            raise ValueError(f"Unable to add a checklist item to card '{card.title}'.")
        state = 'completed' if todo_item.completed else 'open'
        print(
            f"Added checklist item '{todo_item.text}' ({todo_item.id}) to card '{card.title}' "
            f"on board '{board_info['name']}' as {state}."
        )

    def cmd_check_todo_item(self, args: argparse.Namespace):
        """!Cmd check todo item."""
        self._set_todo_item_completed(args, True)

    def cmd_uncheck_todo_item(self, args: argparse.Namespace):
        """!Cmd uncheck todo item."""
        self._set_todo_item_completed(args, False)

    def cmd_toggle_todo_item(self, args: argparse.Namespace):
        """!Cmd toggle todo item."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        todo_item = self._resolve_todo_item(card, args.item)
        updated = board.update_card_todo_item(card.id, todo_item.id, completed=not todo_item.completed)
        if updated is None:
            raise ValueError(f"Unable to toggle checklist item '{todo_item.text}' on card '{card.title}'.")
        state = 'completed' if updated.completed else 'open'
        print(
            f"Toggled checklist item '{updated.text}' ({updated.id}) on card '{card.title}' "
            f"on board '{board_info['name']}' to {state}."
        )

    def cmd_remove_todo_item(self, args: argparse.Namespace):
        """!Cmd remove todo item."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        todo_item = self._resolve_todo_item(card, args.item)
        if not board.delete_card_todo_item(card.id, todo_item.id):
            raise ValueError(f"Unable to remove checklist item '{todo_item.text}' from card '{card.title}'.")
        print(
            f"Removed checklist item '{todo_item.text}' ({todo_item.id}) from card '{card.title}' "
            f"on board '{board_info['name']}'."
        )

    def cmd_card_details(self, args: argparse.Namespace):
        """!Cmd card details."""
        _, _, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        self._print_card_details(board, card)

    def cmd_list_notes(self, args: argparse.Namespace):
        """!Cmd list notes."""
        _, _, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        self._print_card_notes(card, include_full_text=True)

    def cmd_add_note(self, args: argparse.Namespace):
        """!Cmd add note."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        note = board.add_card_note(card.id, args.text)
        if note is None:
            raise ValueError(f"Unable to add a note to card '{card.title}'.")
        print(
            f"Added note ({note.id}) to card '{card.title}' on board '{board_info['name']}'."
        )

    def cmd_edit_note(self, args: argparse.Namespace):
        """!Cmd edit note."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        note = self._resolve_note(card, args.note)
        updated = board.edit_card_note(card.id, note.id, args.text)
        if updated is None:
            raise ValueError(f"Unable to edit note '{note.id}' on card '{card.title}'.")
        print(
            f"Updated note ({updated.id}) on card '{card.title}' on board '{board_info['name']}'."
        )

    def cmd_delete_note(self, args: argparse.Namespace):
        """!Cmd delete note."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        note = self._resolve_note(card, args.note)
        if not board.delete_card_note(card.id, note.id):
            raise ValueError(f"Unable to delete note '{note.id}' from card '{card.title}'.")
        print(
            f"Deleted note ({note.id}) from card '{card.title}' on board '{board_info['name']}'."
        )

    def cmd_archive_done_cards(self, args: argparse.Namespace):
        """!Cmd archive done cards."""
        self._require_force(args.force, 'Archiving done cards requires --force.')
        _, board_info, board = self._load_board(args.board)
        archived = board.archive_done_cards()
        print(f"Archived {archived} done card(s) from board '{board_info['name']}'.")

    def cmd_list_archived_cards(self, args: argparse.Namespace):
        """!Cmd list archived cards."""
        _, _, board = self._load_board(args.board)
        cards = board.get_archived_cards()
        if not cards:
            print('No archived cards found.')
            return
        for card in cards:
            archived_label = card.archived_at.isoformat(sep=' ', timespec='seconds') if card.archived_at else '(unknown)'
            print(
                f"{card.title} ({card.id}) "
                f"[{board.get_card_location_label(card)}] archived={archived_label} assignee={card.assignee or '(none)'}"
            )

    def cmd_restore_archived_card(self, args: argparse.Namespace):
        """!Cmd restore archived card."""
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card, include_archived=True, archived_only=True)
        if not board.restore_archived_card(card.id):
            raise ValueError(f"Unable to restore archived card '{card.title}'.")
        print(f"Restored archived card '{card.title}' on board '{board_info['name']}'.")

    def cmd_delete_archived_card(self, args: argparse.Namespace):
        """!Cmd delete archived card."""
        self._require_force(args.force, 'Deleting an archived card requires --force.')
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card, include_archived=True, archived_only=True)
        if not board.delete_card(card.id):
            raise ValueError(f"Unable to delete archived card '{card.title}'.")
        print(f"Deleted archived card '{card.title}' from board '{board_info['name']}'.")