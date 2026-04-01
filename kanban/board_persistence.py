## @file
#  @brief Persistence and import/export mixins for the board domain.
"""Persistence and import/export mixins for the board domain."""

from __future__ import annotations

import uuid
from typing import Dict, List

from .models import Card, CardType, CustomColumn, Project, Status


class BoardPersistenceMixin:
    """Persistence and export helpers for a Kanban board."""

    def load_board(self):
        data = self.storage.load()
        self._load_from_data(data, persist_defaults=not self.is_read_only())

    def _load_from_data(self, data: Dict, persist_defaults: bool = True):
        self.custom_columns.clear()
        self.card_types.clear()
        self.projects.clear()
        self.last_used_card_type_id = None
        has_custom_columns = 'columns' in data
        is_legacy_data = 'cards' in data and not has_custom_columns
        is_empty_board = not data.get('cards') and not has_custom_columns

        if is_empty_board:
            self._init_default_custom_columns(persist=persist_defaults)
            return

        if has_custom_columns:
            self._load_custom_columns(data)
        elif is_legacy_data:
            raise ValueError('Legacy boards are no longer supported. Boards must use custom columns.')
        elif not self.custom_columns:
            self._init_default_custom_columns(persist=persist_defaults)

    def _load_custom_columns(self, data: Dict):
        self.custom_columns.clear()
        self.card_types.clear()
        self.projects.clear()
        for card_type_data in data.get('card_types', []):
            card_type = CardType.from_dict(card_type_data)
            self.card_types[card_type.id] = card_type
        for project_data in data.get('projects', []):
            project = Project.from_dict(project_data)
            if self.get_project_by_name(project.name) is None:
                self.projects[project.id] = project
        self._ensure_default_card_type()
        self.last_used_card_type_id = data.get('last_used_card_type_id') or self.get_default_card_type_id()
        for column_data in data.get('columns', []):
            column = CustomColumn.from_dict(column_data)
            self.custom_columns[column.id] = column
        self._apply_missing_column_defaults(data.get('columns', []))
        for card_data in data.get('cards', []):
            card = Card.from_dict(card_data)
            if not card.card_type_id or card.card_type_id not in self.card_types:
                card.card_type_id = self.get_default_card_type_id()
            if card.column_id in self.custom_columns:
                self.custom_columns[card.column_id].add_card(card)
        self._sync_projects_from_references()

    def _load_legacy_data(self, data: Dict):
        self.card_types.clear()
        self.projects.clear()
        self._ensure_default_card_type()
        self.last_used_card_type_id = data.get('last_used_card_type_id') or self.get_default_card_type_id()
        for column in self.columns.values():
            column.cards.clear()
        for card_data in data.get('cards', []):
            card = Card.from_dict(card_data)
            if not card.card_type_id or card.card_type_id not in self.card_types:
                card.card_type_id = self.get_default_card_type_id()
            if card.status:
                self.columns[card.status].add_card(card)
        self._sync_projects_from_references()

    def _convert_legacy_to_custom(self, data: Dict, persist: bool = True):
        self.custom_columns.clear()
        self.card_types.clear()
        self.projects.clear()
        self._ensure_default_card_type()
        self.last_used_card_type_id = self.get_default_card_type_id()
        status_to_column_id = {}
        colors = ['#FF9800', '#2196F3', '#9C27B0', '#4CAF50']
        for index, status in enumerate(Status):
            column_id = str(uuid.uuid4())
            column = CustomColumn(column_id, status.value, index, colors[index], is_completed=(status == Status.DONE), can_add_card=(status == Status.TODO))
            self.custom_columns[column_id] = column
            status_to_column_id[status] = column_id
        for card_data in data.get('cards', []):
            card = Card.from_dict(card_data)
            if not card.card_type_id or card.card_type_id not in self.card_types:
                card.card_type_id = self.get_default_card_type_id()
            if card.status in status_to_column_id:
                column_id = status_to_column_id[card.status]
                card.move_to_column(column_id)
                self.custom_columns[column_id].add_card(card)
        self._sync_projects_from_references()
        if persist:
            self.save_board()

    def _init_default_custom_columns(self, persist: bool = True):
        self._ensure_default_card_type()
        if not self.last_used_card_type_id:
            self.last_used_card_type_id = self.get_default_card_type_id()
        default_columns = [('To Do', '#FF9800'), ('In Progress', '#2196F3'), ('Review', '#9C27B0'), ('Done', '#4CAF50')]
        for index, (name, color) in enumerate(default_columns):
            column_id = str(uuid.uuid4())
            column = CustomColumn(column_id, name, index, color, is_completed=(name == 'Done'), can_add_card=(name == 'To Do'))
            self.custom_columns[column_id] = column
        if persist:
            self.save_board()

    def save_board(self):
        self.storage.save(self.export_data())

    def _apply_missing_column_defaults(self, columns_data: List[Dict]):
        if not self.custom_columns:
            return
        if not any('is_completed' in column_data for column_data in columns_data):
            ordered_columns = self.get_columns_ordered()
            if ordered_columns:
                ordered_columns[-1].set_completed(True)
        if not any('can_add_card' in column_data for column_data in columns_data):
            ordered_columns = self.get_columns_ordered()
            if ordered_columns:
                ordered_columns[0].set_can_add_card(True)

    def export_board(self, format_type: str = 'text') -> str:
        if format_type == 'text':
            output = []
            output.append('=' * 60)
            output.append('KANBAN BOARD')
            output.append('=' * 60)
            if self.use_custom_columns:
                ordered_columns = self.get_columns_ordered()
                for column in ordered_columns:
                    output.append(f"\n{column.name} ({len(column)} cards)")
                    output.append('-' * 30)
                    if len(column) == 0:
                        output.append('  (no cards)')
                    else:
                        for index, card in enumerate(column, 1):
                            output.append(f'  {index}. {card}')
                            if card.description:
                                output.append(f'     Description: {card.description}')
                            if card.project:
                                output.append(f'     Project: {card.project}')
                            todo_completed, todo_total = card.get_todo_progress()
                            if todo_total:
                                output.append(f'     Checklist: [{todo_completed}/{todo_total} done]')
                                for todo_item in card.todo_items[:3]:
                                    tick = '[x]' if todo_item.completed else '[ ]'
                                    output.append(f'       {tick} {todo_item.text}')
                                if todo_total > 3:
                                    output.append(f'       ... {todo_total - 3} more item(s)')
                            parent_card = self.get_parent_card(card)
                            if parent_card:
                                output.append(f'     Parent: {parent_card.title}')
                            completed, total = self.get_subcard_progress(card.id)
                            if total:
                                output.append(f'     Subcards: [{completed}/{total} done]')
            else:
                for status in Status:
                    column = self.columns[status]
                    output.append(f"\n{status.value} ({len(column)} cards)")
                    output.append('-' * 30)
                    if len(column) == 0:
                        output.append('  (no cards)')
                    else:
                        for index, card in enumerate(column, 1):
                            output.append(f'  {index}. {card}')
                            if card.description:
                                output.append(f'     Description: {card.description}')
                            if card.project:
                                output.append(f'     Project: {card.project}')
                            todo_completed, todo_total = card.get_todo_progress()
                            if todo_total:
                                output.append(f'     Checklist: [{todo_completed}/{todo_total} done]')
                                for todo_item in card.todo_items[:3]:
                                    tick = '[x]' if todo_item.completed else '[ ]'
                                    output.append(f'       {tick} {todo_item.text}')
                                if todo_total > 3:
                                    output.append(f'       ... {todo_total - 3} more item(s)')
                            parent_card = self.get_parent_card(card)
                            if parent_card:
                                output.append(f'     Parent: {parent_card.title}')
                            completed, total = self.get_subcard_progress(card.id)
                            if total:
                                output.append(f'     Subcards: [{completed}/{total} done]')
            return '\n'.join(output)
        return 'Unsupported format'