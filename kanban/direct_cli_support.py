## @file
#  @brief Shared helpers for the direct-action CLI.
"""Support helpers for the direct-action CLI."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from .board import KanbanBoard
from .board_manager import BoardLockCancelledError
from .models import UNSET, Card, CardType, CustomColumn, Priority


class DirectCliSupportMixin:
    """Shared resolution, formatting, and parsing helpers for the direct CLI."""

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

    def _resolve_card(
        self,
        board: KanbanBoard,
        identifier: str,
        include_archived: bool = False,
        archived_only: bool = False,
    ) -> Card:
        card = board.find_card(identifier, include_archived=include_archived)
        if card is not None:
            if archived_only and not card.is_archived():
                raise ValueError(f"Card '{identifier}' is not archived.")
            return card

        normalized = identifier.strip().lower()
        matches = [
            candidate
            for candidate in board.get_all_cards(include_archived=include_archived)
            if candidate.title.strip().lower() == normalized and (not archived_only or candidate.is_archived())
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple cards match '{identifier}'. Use a card id instead.")
        if archived_only:
            raise ValueError(f"Archived card '{identifier}' was not found.")
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

    def _resolve_todo_item(self, card: Card, identifier: str):
        for todo_item in card.todo_items:
            if todo_item.id == identifier:
                return todo_item

        normalized = identifier.strip().lower()
        matches = [todo_item for todo_item in card.todo_items if todo_item.text.strip().lower() == normalized]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple checklist items match '{identifier}'. Use the checklist item id instead.")
        raise ValueError(f"Checklist item '{identifier}' was not found on card '{card.title}'.")

    def _resolve_note(self, card: Card, identifier: str):
        for note in card.notes:
            if note.id == identifier:
                return note

        normalized = identifier.strip()
        exact_matches = [note for note in card.notes if note.text.strip() == normalized]
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            raise ValueError(f"Multiple notes match '{identifier}'. Use the note id instead.")

        lowered = normalized.lower()
        matches = [note for note in card.notes if note.text.strip().lower() == lowered]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Multiple notes match '{identifier}'. Use the note id instead.")
        raise ValueError(f"Note '{identifier}' was not found on card '{card.title}'.")

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
        print(f'ID: {card.id}')
        print(f'Title: {card.title}')
        print(f"Description: {card.description or '(no description)'}")
        print(f"Column: {board.get_card_location_label(card)}")
        print(f'Priority: {card.priority.value}')
        print(f"Type: {card_type.name if card_type else board.get_default_card_type().name}")
        print(f"Project: {card.project or '(none)'}")
        print(f"Assignee: {card.assignee or '(unassigned)'}")
        print(f"Start Date: {card.start_date.isoformat() if card.start_date else '(none)'}")
        print(f"End Date: {card.end_date.isoformat() if card.end_date else '(none)'}")
        print(f"Archived: {card.archived_at.isoformat(sep=' ', timespec='seconds') if card.archived_at else '(active)'}")
        print(f"Color: {card.color or '(default)'}")
        print(f"Tags: {', '.join(card.tags) if card.tags else '(no tags)'}")
        todo_completed, todo_total = card.get_todo_progress()
        if todo_total:
            print(f'Checklist: {todo_completed}/{todo_total} done')
            for todo_item in card.todo_items:
                tick = '[x]' if todo_item.completed else '[ ]'
                print(f'  {tick} {todo_item.text} ({todo_item.id})')
        else:
            print('Checklist: (none)')
        self._print_card_notes(card)
        parent_card = board.get_parent_card(card)
        if parent_card is not None:
            print(f'Parent Card: {parent_card.title}')
        completed, total = board.get_subcard_progress(card.id)
        if total:
            print(f'Subcards: {completed}/{total} done')

    def _print_card_notes(self, card: Card, include_full_text: bool = False):
        if not card.notes:
            print('Notes: (none)')
            return

        ordered_notes = sorted(card.notes, key=lambda note: note.created_at, reverse=True)
        print(f'Notes: {len(ordered_notes)}')
        for note in ordered_notes:
            created_label = note.created_at.isoformat(sep=' ', timespec='seconds')
            print(f'  - {created_label} ({note.id})')
            note_lines = (note.text or '').splitlines() or ['(empty note)']
            if include_full_text:
                for line in note_lines:
                    print(f'      {line}')
            else:
                preview = ' '.join((note.text or '').split()) or '(empty note)'
                if len(preview) > 120:
                    preview = preview[:117] + '...'
                print(f'      {preview}')

    def _format_board_stat_lines(self, stats: Dict[str, object]) -> List[str]:
        if all(key in stats for key in ('todo', 'in_progress', 'review', 'done')):
            return [
                f"To Do: {stats['todo']}",
                f"In Progress: {stats['in_progress']}",
                f"Review: {stats['review']}",
                f"Done: {stats['done']}",
            ]

        ignored_keys = {'total_cards', 'priority_counts', 'use_custom_columns'}
        return [f'{name}: {count}' for name, count in stats.items() if name not in ignored_keys]

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

    def _pick_optional_todo_items(self, todo_values: Optional[Sequence[str]], clear: bool):
        if clear:
            return []
        if todo_values is not None:
            return self._parse_todo_items(todo_values)
        return UNSET

    def _normalize_order_tokens(self, values: Sequence[str]) -> List[str]:
        if len(values) == 1 and ',' in values[0]:
            return [token.strip() for token in values[0].split(',') if token.strip()]
        return [value.strip() for value in values if value.strip()]

    def _parse_date(self, value: str, label: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f'{label} must use YYYY-MM-DD format.') from error

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

    def _parse_todo_items(self, values: Optional[Sequence[str]]) -> List[Dict[str, object]]:
        items: List[Dict[str, object]] = []
        for raw_value in values or []:
            text = raw_value.strip()
            if not text:
                continue
            completed = False
            lowered = text.lower()
            if lowered.startswith('[x]'):
                completed = True
                text = text[3:].strip()
            elif lowered.startswith('[ ]'):
                text = text[3:].strip()
            if text:
                items.append({'text': text, 'completed': completed})
        return items

    def _set_todo_item_completed(self, args: argparse.Namespace, completed: bool):
        _, board_info, board = self._load_board(args.board)
        card = self._resolve_card(board, args.card)
        todo_item = self._resolve_todo_item(card, args.item)
        updated = board.update_card_todo_item(card.id, todo_item.id, completed=completed)
        if updated is None:
            state_text = 'completed' if completed else 'open'
            raise ValueError(f"Unable to mark checklist item '{todo_item.text}' as {state_text} on card '{card.title}'.")
        state_text = 'completed' if updated.completed else 'open'
        print(
            f"Marked checklist item '{updated.text}' ({updated.id}) on card '{card.title}' "
            f"on board '{board_info['name']}' as {state_text}."
        )

    def _write_json(self, output_path: str, payload: Dict[str, object]):
        directory = os.path.dirname(os.path.abspath(output_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as output_file:
            json.dump(payload, output_file, indent=2, ensure_ascii=False)

    def _require_force(self, enabled: bool, message: str):
        if not enabled:
            raise ValueError(message)