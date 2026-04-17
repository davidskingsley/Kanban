## @file
#  @brief Core Kanban board implementation.
"""!Core Kanban board implementation with internal mixin composition."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional

from .board_cards import BoardCardsMixin
from .board_catalog import BoardCatalogMixin
from .board_columns import BoardColumnsMixin
from .board_persistence import BoardPersistenceMixin
from .models import ActionLogEntry, CardType, CustomColumn, Project
from .storage import DataStorage, LockHandler, get_default_single_board_file


class KanbanBoard(BoardColumnsMixin, BoardCatalogMixin, BoardCardsMixin, BoardPersistenceMixin):
    """!Main Kanban board class for managing cards and columns."""

    DEFAULT_CARD_TYPE_NAME = 'Default'
    MAX_UNDO_STEPS = 100

    def __init__(self, data_file: str = None, use_custom_columns: bool = True,
                 lock_handler: Optional[LockHandler] = None, storage_backend: Optional[str] = None):
        """!Init."""
        if data_file is None:
            data_file = get_default_single_board_file()

        self.storage = DataStorage(data_file, lock_handler=lock_handler, backend=storage_backend)
        self.use_custom_columns = True
        self.card_types: Dict[str, CardType] = {}
        self.projects: Dict[str, Project] = {}
        self.last_used_card_type_id = None
        self.actor_name: Optional[str] = None
        self.action_log: List[ActionLogEntry] = []
        self._undo_stack: List[Dict[str, object]] = []
        self._redo_stack: List[Dict[str, object]] = []
        self.custom_columns: Dict[str, CustomColumn] = {}
        self.columns = None
        self.load_board()

    def is_read_only(self) -> bool:
        """!Is read only."""
        return self.storage.is_read_only()

    def get_read_only_message(self) -> str:
        """!Get read only message."""
        return self.storage.get_read_only_message()

    def close(self):
        """!Close."""
        self.storage.release_lock()

    def _ensure_writable(self):
        """!Ensure writable."""
        if self.is_read_only():
            raise PermissionError(self.get_read_only_message())

    def export_data(self) -> Dict:
        """!Export data."""
        self._ensure_default_card_type()
        if not self.last_used_card_type_id:
            self.last_used_card_type_id = self.get_default_card_type_id()
        card_types_data = [card_type.to_dict() for card_type in self.get_card_types_ordered()]
        projects_data = [project.to_dict() for project in self.get_projects_ordered()]
        columns_data = [column.to_dict() for column in self.custom_columns.values()]
        cards_data = []
        for column in self.custom_columns.values():
            for card in column:
                cards_data.append(card.to_dict())
        return {
            'columns': columns_data,
            'cards': cards_data,
            'card_types': card_types_data,
            'projects': projects_data,
            'action_log': [entry.to_dict() for entry in self.action_log],
            'last_used_card_type_id': self.last_used_card_type_id,
            'format_version': '2.1',
        }

    def _export_snapshot_data(self) -> Dict:
        """!Export board data for undo snapshots without audit entries."""
        snapshot = deepcopy(self.export_data())
        snapshot['action_log'] = []
        return snapshot

    def _push_history_state(self, stack: List[Dict[str, object]], description: str):
        """!Push history state."""
        stack.append({'description': description, 'data': self._export_snapshot_data()})
        if len(stack) > self.MAX_UNDO_STEPS:
            stack.pop(0)

    def _push_undo_state(self, description: str):
        """!Push undo state."""
        self._push_history_state(self._undo_stack, description)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        """!Can undo."""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """!Can redo."""
        return bool(self._redo_stack)

    def get_next_undo_description(self) -> Optional[str]:
        """!Get next undo description."""
        if not self._undo_stack:
            return None
        return self._undo_stack[-1]['description']

    def get_next_redo_description(self) -> Optional[str]:
        """!Get next redo description."""
        if not self._redo_stack:
            return None
        return self._redo_stack[-1]['description']

    def set_actor_name(self, actor_name: Optional[str]):
        """!Set actor name used for future audit-log entries."""
        normalized = (actor_name or '').strip()
        self.actor_name = normalized or None

    def get_actor_name(self) -> Optional[str]:
        """!Get actor name used for audit-log entries."""
        return self.actor_name

    def _audit_actor_name(self) -> str:
        """!Return the actor name to persist for an audit-log entry."""
        return self.actor_name or 'Unknown User'

    def _record_action(self, description: str, card_id: Optional[str] = None) -> ActionLogEntry:
        """!Append one audit-log entry for a completed board action."""
        entry = ActionLogEntry(self._audit_actor_name(), description, card_id=card_id)
        self.action_log.append(entry)
        return entry

    def _format_action_log(self, entries: List[ActionLogEntry], empty_message: str) -> str:
        """!Render one collection of audit-log entries in plain text."""
        if not entries:
            return empty_message
        lines = []
        for index, entry in enumerate(entries, start=1):
            timestamp = entry.occurred_at.strftime('%Y-%m-%d %H:%M:%S')
            lines.append(f"{index}. {timestamp} | {entry.actor_name} | {entry.description}")
        return '\n'.join(lines)

    def get_action_log(self, limit: Optional[int] = None) -> List[ActionLogEntry]:
        """!Return audit-log entries from newest to oldest."""
        entries = list(reversed(self.action_log))
        if limit is None:
            return entries
        return entries[:max(0, limit)]

    def get_card_action_log(self, card_id: str, limit: Optional[int] = None) -> List[ActionLogEntry]:
        """!Return audit-log entries related to one card from newest to oldest."""
        entries = [entry for entry in reversed(self.action_log) if entry.card_id == card_id]
        if limit is None:
            return entries
        return entries[:max(0, limit)]

    def export_action_log(self, limit: Optional[int] = None) -> str:
        """!Render audit-log entries in plain text."""
        return self._format_action_log(self.get_action_log(limit=limit), 'No action log entries recorded.')

    def export_card_action_log(self, card_id: str, limit: Optional[int] = None, card_title: Optional[str] = None) -> str:
        """!Render one card's audit-log entries in plain text."""
        target_label = card_title or card_id
        return self._format_action_log(
            self.get_card_action_log(card_id, limit=limit),
            f"No action log entries recorded for card '{target_label}'.",
        )

    def undo_last_action(self) -> Optional[str]:
        """!Undo last action."""
        self._ensure_writable()
        if not self._undo_stack:
            return None
        snapshot = self._undo_stack.pop()
        self._push_history_state(self._redo_stack, snapshot['description'])
        self._load_from_data(deepcopy(snapshot['data']), persist_defaults=False, preserve_action_log=True)
        self._record_action(f"Undid board action: {snapshot['description']}")
        self.save_board()
        return snapshot['description']

    def redo_last_action(self) -> Optional[str]:
        """!Redo last action."""
        self._ensure_writable()
        if not self._redo_stack:
            return None
        snapshot = self._redo_stack.pop()
        self._push_history_state(self._undo_stack, snapshot['description'])
        self._load_from_data(deepcopy(snapshot['data']), persist_defaults=False, preserve_action_log=True)
        self._record_action(f"Redid board action: {snapshot['description']}")
        self.save_board()
        return snapshot['description']