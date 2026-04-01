## @file
#  @brief Filter-related mixins for the PySide6 multi-board GUI.
"""Filter mixins for the PySide6 GUI."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtWidgets import QComboBox

from ..board import KanbanBoard
from .common import due_state_label


class BoardFiltersMixin:
	"""Filter toolbar behavior for the multi-board GUI."""

	def _default_filter_state(self) -> Dict[str, object]:
		return {
			'search': '',
			'priority': '',
			'assignee': '',
			'card_type': '',
			'tag': '',
			'due_state': '',
			'column_search': {},
		}

	def _get_current_filter_state(self) -> Dict[str, object]:
		board_id = self.board_manager.current_board_id
		if not board_id:
			return self._default_filter_state()
		state = self.board_filter_states.get(board_id)
		if state is None:
			state = self._default_filter_state()
			self.board_filter_states[board_id] = state
		return state

	def _filters_active(self) -> bool:
		state = self._get_current_filter_state()
		return any([
			state['search'],
			state['priority'],
			state['assignee'],
			state['card_type'],
			state['tag'],
			state['due_state'],
		])

	def _column_search_text(self, column_id: str) -> str:
		state = self._get_current_filter_state()
		column_search = state.get('column_search') or {}
		return str(column_search.get(column_id, ''))

	def _set_column_search_text(self, column_id: str, value: str):
		state = self._get_current_filter_state()
		column_search = dict(state.get('column_search') or {})
		normalized = value.strip()
		if normalized:
			column_search[column_id] = normalized
		else:
			column_search.pop(column_id, None)
		state['column_search'] = column_search

	def _card_matches_column_search(self, card, search_text: str) -> bool:
		needle = search_text.lower().strip()
		if not needle:
			return True
		haystacks = [card.title or '', card.description or '', card.project or '', card.assignee or '']
		haystacks.extend(card.tags or [])
		return any(needle in text.lower() for text in haystacks)

	def _set_filter_toolbar_enabled(self, enabled: bool):
		self.toolbar_search_entry.setEnabled(enabled)
		self.toolbar_priority_combo.setEnabled(enabled)
		self.toolbar_assignee_combo.setEnabled(enabled)
		self.toolbar_card_type_combo.setEnabled(enabled)
		self.toolbar_tag_combo.setEnabled(enabled)
		self.toolbar_due_state_combo.setEnabled(enabled)
		self.toolbar_clear_filters_button.setEnabled(enabled and self._filters_active())

	def _sync_filter_toolbar(self, board: Optional[KanbanBoard]):
		self._updating_filter_controls = True
		try:
			self._refresh_assignee_filter_options(board)
			self._refresh_card_type_filter_options(board)
			self._refresh_tag_filter_options(board)
			if board is None or self.board_manager.current_board_id is None:
				self.toolbar_search_entry.setText('')
				self.toolbar_priority_combo.setCurrentIndex(0)
				self.toolbar_assignee_combo.setCurrentIndex(0)
				self.toolbar_card_type_combo.setCurrentIndex(0)
				self.toolbar_tag_combo.setCurrentIndex(0)
				self.toolbar_due_state_combo.setCurrentIndex(0)
				self._set_filter_toolbar_enabled(False)
				return

			state = self._get_current_filter_state()
			self.toolbar_search_entry.setText(str(state['search']))
			self._set_combo_to_data(self.toolbar_priority_combo, state['priority'])
			self._set_combo_to_data(self.toolbar_assignee_combo, state['assignee'])
			self._set_combo_to_data(self.toolbar_card_type_combo, state['card_type'])
			self._set_combo_to_data(self.toolbar_tag_combo, state['tag'])
			self._set_combo_to_data(self.toolbar_due_state_combo, state['due_state'])
			self._set_filter_toolbar_enabled(True)
		finally:
			self._updating_filter_controls = False

	def _set_combo_to_data(self, combo_box: QComboBox, target_data):
		for index in range(combo_box.count()):
			if combo_box.itemData(index) == target_data:
				combo_box.setCurrentIndex(index)
				return
		combo_box.setCurrentIndex(0)

	def _refresh_assignee_filter_options(self, board: Optional[KanbanBoard]):
		selected_assignee = self.toolbar_assignee_combo.currentData() if hasattr(self, 'toolbar_assignee_combo') else ''
		self.toolbar_assignee_combo.blockSignals(True)
		self.toolbar_assignee_combo.clear()
		self.toolbar_assignee_combo.addItem('All Assignees', '')
		if board is not None:
			assignees = sorted({card.assignee.strip() for card in board.get_all_cards() if card.assignee and card.assignee.strip()}, key=str.lower)
			for assignee in assignees:
				self.toolbar_assignee_combo.addItem(assignee, assignee)
		self._set_combo_to_data(self.toolbar_assignee_combo, selected_assignee)
		self.toolbar_assignee_combo.blockSignals(False)

	def _refresh_card_type_filter_options(self, board: Optional[KanbanBoard]):
		selected_type = self.toolbar_card_type_combo.currentData() if hasattr(self, 'toolbar_card_type_combo') else ''
		self.toolbar_card_type_combo.blockSignals(True)
		self.toolbar_card_type_combo.clear()
		self.toolbar_card_type_combo.addItem('All Types', '')
		if board is not None:
			for card_type in board.get_card_types_ordered():
				self.toolbar_card_type_combo.addItem(card_type.name, card_type.id)
		self._set_combo_to_data(self.toolbar_card_type_combo, selected_type)
		self.toolbar_card_type_combo.blockSignals(False)

	def _refresh_tag_filter_options(self, board: Optional[KanbanBoard]):
		selected_tag = self.toolbar_tag_combo.currentData() if hasattr(self, 'toolbar_tag_combo') else ''
		self.toolbar_tag_combo.blockSignals(True)
		self.toolbar_tag_combo.clear()
		self.toolbar_tag_combo.addItem('All Tags', '')
		if board is not None:
			tags = sorted({tag for card in board.get_all_cards() for tag in card.tags}, key=str.lower)
			for tag in tags:
				self.toolbar_tag_combo.addItem(f'#{tag}', tag)
		self._set_combo_to_data(self.toolbar_tag_combo, selected_tag)
		self.toolbar_tag_combo.blockSignals(False)

	def apply_toolbar_filters(self, *_args):
		if self._updating_filter_controls or self.board_manager.current_board_id is None:
			return
		self.board_filter_states[self.board_manager.current_board_id] = {
			'search': self.toolbar_search_entry.text().strip(),
			'priority': self.toolbar_priority_combo.currentData() or '',
			'assignee': self.toolbar_assignee_combo.currentData() or '',
			'card_type': self.toolbar_card_type_combo.currentData() or '',
			'tag': self.toolbar_tag_combo.currentData() or '',
			'due_state': self.toolbar_due_state_combo.currentData() or '',
		}
		self.selected_card_id = None
		self.refresh_ui()

	def clear_toolbar_filters(self):
		if self.board_manager.current_board_id is None:
			return
		self._updating_filter_controls = True
		try:
			self.toolbar_search_entry.clear()
			self.toolbar_priority_combo.setCurrentIndex(0)
			self.toolbar_assignee_combo.setCurrentIndex(0)
			self.toolbar_card_type_combo.setCurrentIndex(0)
			self.toolbar_tag_combo.setCurrentIndex(0)
			self.toolbar_due_state_combo.setCurrentIndex(0)
		finally:
			self._updating_filter_controls = False
		self.board_filter_states[self.board_manager.current_board_id] = self._default_filter_state()
		self.selected_card_id = None
		self.refresh_ui()

	def _card_matches_filters(self, board: KanbanBoard, card) -> bool:
		state = self._get_current_filter_state()
		search_text = str(state['search']).lower().strip()
		if search_text:
			haystacks = [card.title or '', card.description or '', card.project or '']
			haystacks.extend(card.tags or [])
			if not any(search_text in text.lower() for text in haystacks):
				return False
		if state['priority'] and card.priority.value != state['priority']:
			return False
		if state['assignee'] and (card.assignee or '') != state['assignee']:
			return False
		if state['card_type'] and card.card_type_id != state['card_type']:
			return False
		if state['tag'] and state['tag'] not in card.tags:
			return False
		if state['due_state'] and due_state_label(board, card) != state['due_state']:
			return False
		return True

	def _filter_cards(self, board: KanbanBoard, cards: List[object]) -> List[object]:
		return [card for card in cards if self._card_matches_filters(board, card)]

	def _filter_summary_suffix(self) -> str:
		state = self._get_current_filter_state()
		if not any([state['search'], state['priority'], state['assignee'], state['card_type'], state['tag'], state['due_state']]):
			return ''
		parts: List[str] = []
		if state['search']:
			parts.append(f"search '{state['search']}'")
		if state['priority']:
			parts.append(str(state['priority']))
		if state['assignee']:
			parts.append(f"@{state['assignee']}")
		if state['card_type']:
			parts.append(f"type {self.toolbar_card_type_combo.currentText()}")
		if state['tag']:
			parts.append(f"#{state['tag']}")
		if state['due_state']:
			parts.append(str(state['due_state']))
		return f" | filtered: {', '.join(parts)}"


__all__ = ['BoardFiltersMixin']