## @file
#  @brief Card, archive, and attachment mixins for the board domain.
"""Card, archive, and attachment mixins for the board domain."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Dict, List, Optional, Set, Union

from .models import UNSET, Card, CardAttachment, CardTodoItem, CustomColumn, Priority, Status


class BoardCardsMixin:
    """Card, archive, attachment, and statistics helpers for a Kanban board."""

    def create_card(self, title: str, description: str = '', priority: Priority = Priority.MEDIUM,
                    column_id: str = None, project: str = None, start_date: date = None,
                    end_date: date = None, parent_id: str = None, color: str = None,
                    card_type_id: str = None, assignee: str = None,
                    tags: Optional[List[str]] = None,
                    todo_items: Optional[List[object]] = None) -> Card:
        self._ensure_writable()
        card_type = self._resolve_card_type(card_type_id)
        effective_project = project if project is not None else card_type.default_project
        effective_color = color if color is not None else card_type.default_color
        self._ensure_project_exists(effective_project)

        if self.use_custom_columns:
            if not column_id:
                column_id = self._get_first_column_id()
                if not column_id:
                    raise ValueError('No columns available. Create a column first.')
            if column_id not in self.custom_columns:
                raise ValueError(f'Column {column_id} does not exist')

            self._push_undo_state(f"Create card '{title}'")
            card = Card(title, description, priority, column_id)
            card.project = effective_project
            card.start_date = start_date
            card.end_date = end_date
            if parent_id is not None:
                card.parent_id = parent_id
            card.color = effective_color
            card.card_type_id = card_type.id
            card.assignee = assignee
            if tags:
                card.tags = list(dict.fromkeys(tags))
            card.todo_items = card._coerce_todo_items(todo_items or [])
            self.custom_columns[column_id].add_card(card)
        else:
            self._push_undo_state(f"Create card '{title}'")
            card = Card(title, description, priority)
            card.project = effective_project
            card.start_date = start_date
            card.end_date = end_date
            if parent_id is not None:
                card.parent_id = parent_id
            card.color = effective_color
            card.card_type_id = card_type.id
            card.assignee = assignee
            if tags:
                card.tags = list(dict.fromkeys(tags))
            card.todo_items = card._coerce_todo_items(todo_items or [])
            self.columns[Status.TODO].add_card(card)

        self.last_used_card_type_id = card_type.id
        self.save_board()
        return card

    def edit_card(self, card_id: str, title: str = None, description: str = None,
                  priority: Priority = None, assignee: str = None, project: str = None,
                  start_date=UNSET, end_date=UNSET, parent_id: str = None, color=UNSET,
                  tags=UNSET, card_type_id=UNSET, todo_items=UNSET) -> Optional[Card]:
        self._ensure_writable()
        card = self.find_card(card_id)
        if card:
            resolved_type_id = card_type_id
            if card_type_id is not UNSET:
                resolved_type = self._resolve_card_type(card_type_id)
                resolved_type_id = resolved_type.id
                self.last_used_card_type_id = resolved_type.id
            self._push_undo_state(f"Edit card '{card.title}'")
            card.update(title, description, priority, assignee, project, start_date, end_date, parent_id, color, resolved_type_id, todo_items)
            if project is not None:
                self._ensure_project_exists(project)
            if tags is not UNSET:
                card.tags = list(dict.fromkeys(tags or []))
                card.updated_at = datetime.now()
            self.save_board()
            return card
        return None

    def update_card_tags(self, card_id: str, tags: List[str]) -> Optional[Card]:
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return None
        self._push_undo_state(f"Update tags on '{card.title}'")
        card.tags = list(dict.fromkeys(tags or []))
        card.updated_at = datetime.now()
        self.save_board()
        return card

    def add_card_tag(self, card_id: str, tag: str) -> bool:
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card or not tag or tag in card.tags:
            return False
        self._push_undo_state(f"Add tag to '{card.title}'")
        card.add_tag(tag)
        self.save_board()
        return True

    def add_card_todo_item(self, card_id: str, text: str, completed: bool = False) -> Optional[CardTodoItem]:
        self._ensure_writable()
        card = self.find_card(card_id)
        normalized_text = (text or '').strip()
        if not card or not normalized_text:
            return None
        self._push_undo_state(f"Add checklist item to '{card.title}'")
        todo_item = CardTodoItem(normalized_text, completed)
        card.todo_items.append(todo_item)
        card.updated_at = datetime.now()
        self.save_board()
        return todo_item

    def update_card_todo_item(self, card_id: str, todo_item_id: str, text=UNSET, completed=UNSET) -> Optional[CardTodoItem]:
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return None
        todo_item = next((item for item in card.todo_items if item.id == todo_item_id), None)
        if todo_item is None:
            return None
        new_text = todo_item.text if text is UNSET else (text or '').strip()
        new_completed = todo_item.completed if completed is UNSET else bool(completed)
        if not new_text:
            return None
        if new_text == todo_item.text and new_completed == todo_item.completed:
            return todo_item
        self._push_undo_state(f"Update checklist item on '{card.title}'")
        todo_item.text = new_text
        todo_item.completed = new_completed
        card.updated_at = datetime.now()
        self.save_board()
        return todo_item

    def delete_card_todo_item(self, card_id: str, todo_item_id: str) -> bool:
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return False
        for index, todo_item in enumerate(card.todo_items):
            if todo_item.id != todo_item_id:
                continue
            self._push_undo_state(f"Remove checklist item from '{card.title}'")
            card.todo_items.pop(index)
            card.updated_at = datetime.now()
            self.save_board()
            return True
        return False

    def get_all_cards(self, include_archived: bool = False) -> List[Card]:
        cards = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        for column in columns:
            for card in column:
                if include_archived or not card.is_archived():
                    cards.append(card)
        return cards

    def get_column_cards(self, column: Union[str, CustomColumn], include_archived: bool = False) -> List[Card]:
        target_column = column if isinstance(column, CustomColumn) else self.get_column_by_id(column)
        if target_column is None:
            return []
        if include_archived:
            return list(target_column.cards)
        return [card for card in target_column.cards if not card.is_archived()]

    def get_archived_cards(self) -> List[Card]:
        cards = [card for card in self.get_all_cards(include_archived=True) if card.is_archived()]
        return sorted(cards, key=lambda card: ((card.archived_at or card.updated_at), card.title.lower()))

    def get_parent_card(self, card: Card) -> Optional[Card]:
        if not card.parent_id:
            return None
        parent = self.find_card(card.parent_id)
        if parent is not None:
            return parent
        return self.find_card(card.parent_id, include_archived=True)

    def get_subcards(self, parent_id: str, include_archived: bool = False) -> List[Card]:
        return [card for card in self.get_all_cards(include_archived=include_archived) if card.parent_id == parent_id]

    def get_card_attachment(self, card_id: str, attachment_id: str) -> Optional[CardAttachment]:
        card = self.find_card(card_id)
        if not card:
            return None
        return card.get_attachment(attachment_id)

    def get_card_attachment_path(self, card_id: str, attachment_id: str) -> Optional[str]:
        attachment = self.get_card_attachment(card_id, attachment_id)
        if attachment is None:
            return None
        return self.storage.resolve_attachment_path(attachment.relative_path)

    def add_card_attachment(self, card_id: str, source_path: str) -> Optional[CardAttachment]:
        attachments = self.add_card_attachments(card_id, [source_path])
        return attachments[0] if attachments else None

    def add_card_attachments(self, card_id: str, source_paths: List[str]) -> List[CardAttachment]:
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return []
        normalized_paths = []
        for path in source_paths:
            absolute_path = os.path.abspath(path)
            if os.path.isfile(absolute_path) and absolute_path not in normalized_paths:
                normalized_paths.append(absolute_path)
        if not normalized_paths:
            return []
        count = len(normalized_paths)
        label = 'attachment' if count == 1 else 'attachments'
        self._push_undo_state(f"Add {count} {label} to '{card.title}'")
        attachments: List[CardAttachment] = []
        try:
            for source_path in normalized_paths:
                relative_path = self.storage.copy_attachment(source_path, card.id)
                attachments.append(card.add_attachment(os.path.basename(source_path), relative_path))
        except Exception:
            self._undo_stack.pop()
            raise
        self.save_board()
        return attachments

    def delete_card_attachment(self, card_id: str, attachment_id: str) -> bool:
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return False
        attachment = card.get_attachment(attachment_id)
        if attachment is None:
            return False
        self._push_undo_state(f"Remove attachment from '{card.title}'")
        removed = card.remove_attachment(attachment_id)
        if removed is None:
            self._undo_stack.pop()
            return False
        self.save_board()
        return True

    def _collect_attachment_paths_from_data(self, data: Dict) -> Set[str]:
        attachment_paths: Set[str] = set()
        for card_data in data.get('cards', []):
            for attachment_data in card_data.get('attachments', []):
                relative_path = attachment_data.get('relative_path')
                if not relative_path:
                    continue
                attachment_paths.add(os.path.normcase(os.path.abspath(self.storage.resolve_attachment_path(relative_path))))
        return attachment_paths

    def get_referenced_attachment_paths(self, include_history: bool = True) -> Set[str]:
        referenced_paths = self._collect_attachment_paths_from_data(self.export_data())
        if not include_history:
            return referenced_paths
        for snapshot in self._undo_stack:
            referenced_paths.update(self._collect_attachment_paths_from_data(snapshot['data']))
        for snapshot in self._redo_stack:
            referenced_paths.update(self._collect_attachment_paths_from_data(snapshot['data']))
        return referenced_paths

    def cleanup_orphaned_attachment_files(self) -> Dict[str, object]:
        self._ensure_writable()
        stored_files = self.storage.list_attachment_files()
        if not stored_files:
            return {
                'removed_files': 0,
                'removed_directories': 0,
                'scanned_files': 0,
                'retained_files': 0,
                'removed_paths': [],
            }
        referenced_paths = self.get_referenced_attachment_paths(include_history=True)
        removed_paths = []
        for file_path in stored_files:
            normalized_path = os.path.normcase(os.path.abspath(file_path))
            if normalized_path in referenced_paths:
                continue
            if self.storage.delete_attachment_file(file_path):
                removed_paths.append(file_path)
        removed_directories = self.storage.remove_empty_attachment_directories()
        return {
            'removed_files': len(removed_paths),
            'removed_directories': removed_directories,
            'scanned_files': len(stored_files),
            'retained_files': len(stored_files) - len(removed_paths),
            'removed_paths': removed_paths,
        }

    def add_card_note(self, card_id: str, text: str = ''):
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return None
        self._push_undo_state(f"Add note to '{card.title}'")
        note = card.add_note(text)
        self.save_board()
        return note

    def delete_card_note(self, card_id: str, note_id: str) -> bool:
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return False
        self._push_undo_state(f"Delete note from '{card.title}'")
        removed = card.remove_note(note_id)
        if removed:
            self.save_board()
        else:
            self._undo_stack.pop()
        return removed

    def edit_card_note(self, card_id: str, note_id: str, text: str = ''):
        self._ensure_writable()
        card = self.find_card(card_id)
        if not card:
            return None
        self._push_undo_state(f"Edit note on '{card.title}'")
        note = card.update_note(note_id, text)
        if note is not None:
            self.save_board()
        else:
            self._undo_stack.pop()
        return note

    def get_subcard_progress(self, parent_id: str) -> tuple[int, int]:
        subcards = self.get_subcards(parent_id)
        completed = sum(1 for card in subcards if self.is_card_done(card))
        return completed, len(subcards)

    def is_card_done(self, card: Card) -> bool:
        if self.use_custom_columns:
            column = self.get_column_by_id(card.column_id)
            return bool(column and column.is_completed)
        return card.status == Status.DONE

    def get_card_location_label(self, card: Card) -> str:
        if self.use_custom_columns:
            column = self.get_column_by_id(card.column_id)
            return column.name if column else 'Unknown'
        return card.status.value if card.status else 'Unknown'

    def create_subcard(self, parent_id: str, title: str, description: str = '', priority: Priority = Priority.MEDIUM,
                       project: str = None, color: str = None, card_type_id: str = None, start_date: date = None,
                       end_date: date = None, assignee: str = None, tags: Optional[List[str]] = None,
                       todo_items: Optional[List[object]] = None) -> Card:
        parent_card = self.find_card(parent_id)
        if not parent_card:
            raise ValueError('Parent card does not exist')
        if parent_card.parent_id:
            raise ValueError('Nested subcards are not supported')
        target = self.get_subcard_target(parent_card)
        return self.create_card(
            title,
            description,
            priority,
            target,
            project or parent_card.project,
            start_date,
            end_date,
            parent_id,
            color if color is not None else parent_card.color,
            card_type_id if card_type_id is not None else parent_card.card_type_id,
            assignee,
            tags,
            todo_items,
        )

    def _delete_card_internal(self, card_id: str) -> bool:
        for subcard in list(self.get_subcards(card_id, include_archived=True)):
            self._delete_card_internal(subcard.id)
        if self.use_custom_columns:
            for column in self.custom_columns.values():
                removed_card = column.remove_card(card_id)
                if removed_card:
                    return True
        else:
            for column in self.columns.values():
                removed_card = column.remove_card(card_id)
                if removed_card:
                    return True
        return False

    def delete_card(self, card_id: str) -> bool:
        self._ensure_writable()
        card = self.find_card(card_id, include_archived=True)
        if not card:
            return False
        self._push_undo_state(f"Delete card '{card.title}'")
        removed = self._delete_card_internal(card_id)
        if removed:
            self.save_board()
        return removed

    def move_card(self, card_id: str, to_column: Union[str, Status], target_card_id: Optional[str] = None, insert_after: bool = False) -> bool:
        self._ensure_writable()
        card = None
        existing_card = self.find_card(card_id)
        if not existing_card:
            return False
        self._push_undo_state(f"Move card '{existing_card.title}'")
        if self.use_custom_columns:
            if not isinstance(to_column, str) or to_column not in self.custom_columns:
                self._undo_stack.pop()
                return False
            target_column = self.custom_columns[to_column]
            source_column = self.custom_columns.get(existing_card.column_id)
            if source_column is None:
                self._undo_stack.pop()
                return False
            if target_card_id == card_id and source_column is target_column:
                self._undo_stack.pop()
                return False
            for column in self.custom_columns.values():
                card = column.remove_card(card_id)
                if card:
                    break
            if card:
                target_index = None
                if target_card_id is not None:
                    target_index = target_column.card_index(target_card_id)
                    if target_index is None:
                        self._undo_stack.pop()
                        return False
                    if insert_after:
                        target_index += 1
                card.move_to_column(to_column)
                target_column.add_card(card, target_index)
                self.save_board()
                return True
        else:
            for column in self.columns.values():
                card = column.remove_card(card_id)
                if card:
                    break
            if card and isinstance(to_column, Status):
                card.move_to_status(to_column)
                self.columns[to_column].add_card(card)
                self.save_board()
                return True
        self._undo_stack.pop()
        return False

    def find_card(self, card_id: str, include_archived: bool = False) -> Optional[Card]:
        if self.use_custom_columns:
            for column in self.custom_columns.values():
                card = column.get_card(card_id)
                if card and (include_archived or not card.is_archived()):
                    return card
        else:
            for column in self.columns.values():
                card = column.get_card(card_id)
                if card and (include_archived or not card.is_archived()):
                    return card
        return None

    def _set_card_archived_state(self, card: Card, archived: bool):
        for subcard in self.get_subcards(card.id, include_archived=True):
            self._set_card_archived_state(subcard, archived)
        if archived:
            card.archive()
        else:
            card.restore()

    def archive_card(self, card_id: str) -> bool:
        self._ensure_writable()
        card = self.find_card(card_id, include_archived=True)
        if not card or card.is_archived():
            return False
        self._push_undo_state(f"Archive card '{card.title}'")
        self._set_card_archived_state(card, archived=True)
        self.save_board()
        return True

    def restore_archived_card(self, card_id: str) -> bool:
        self._ensure_writable()
        card = self.find_card(card_id, include_archived=True)
        if not card or not card.is_archived():
            return False
        self._push_undo_state(f"Restore archived card '{card.title}'")
        self._set_card_archived_state(card, archived=False)
        self.save_board()
        return True

    def search_cards(self, query: str, include_archived: bool = False) -> List[Card]:
        results = []
        query_lower = query.lower()
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        for column in columns:
            for card in column:
                if card.is_archived() and not include_archived:
                    continue
                if (query_lower in card.title.lower()
                        or query_lower in card.description.lower()
                        or (card.project and query_lower in card.project.lower())
                        or any(query_lower in subcard.title.lower() for subcard in self.get_subcards(card.id, include_archived=include_archived))
                        or any(query_lower in tag.lower() for tag in card.tags)):
                    results.append(card)
        return results

    def get_cards_by_priority(self, priority: Priority, include_archived: bool = False) -> List[Card]:
        results = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        for column in columns:
            for card in column:
                if card.is_archived() and not include_archived:
                    continue
                if card.priority == priority:
                    results.append(card)
        return results

    def get_cards_by_assignee(self, assignee: str, include_archived: bool = False) -> List[Card]:
        results = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        for column in columns:
            for card in column:
                if card.is_archived() and not include_archived:
                    continue
                if card.assignee and card.assignee.lower() == assignee.lower():
                    results.append(card)
        return results

    def get_board_stats(self) -> Dict:
        if self.use_custom_columns:
            total_cards = sum(len(self.get_column_cards(column)) for column in self.custom_columns.values())
            column_stats = {column.name: len(self.get_column_cards(column)) for column in self.custom_columns.values()}
        else:
            total_cards = sum(len(column) for column in self.columns.values())
            column_stats = {
                'todo': len(self.columns[Status.TODO]),
                'in_progress': len(self.columns[Status.IN_PROGRESS]),
                'review': len(self.columns[Status.REVIEW]),
                'done': len(self.columns[Status.DONE]),
            }
        priority_counts = {priority: 0 for priority in Priority}
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        for column in columns:
            for card in column:
                if card.is_archived():
                    continue
                priority_counts[card.priority] += 1
        done_cards = sum(1 for card in self.get_all_cards() if self.is_card_done(card))
        stats = {
            'total_cards': total_cards,
            'done': done_cards,
            'priority_counts': priority_counts,
            'use_custom_columns': self.use_custom_columns,
            'archived_cards': len(self.get_archived_cards()),
        }
        stats.update(column_stats)
        return stats

    def archive_done_cards(self) -> int:
        self._ensure_writable()
        if not self.custom_columns:
            return 0
        completed_columns = [column for column in self.custom_columns.values() if column.is_completed]
        cards_to_archive: List[Card] = []
        seen_ids: Set[str] = set()
        for column in completed_columns:
            for card in self.get_column_cards(column):
                if card.id in seen_ids:
                    continue
                cards_to_archive.append(card)
                seen_ids.add(card.id)
        if not cards_to_archive:
            return 0
        self._push_undo_state('Archive done cards')
        for card in cards_to_archive:
            self._set_card_archived_state(card, archived=True)
        self.save_board()
        return len(cards_to_archive)

    def clear_done_cards(self) -> int:
        return self.archive_done_cards()