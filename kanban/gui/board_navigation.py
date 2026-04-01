## @file
#  @brief Board rendering and navigation mixins for the PySide6 GUI.
"""Board rendering and navigation mixins for the PySide6 GUI."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QFrame,
	QHBoxLayout,
	QInputDialog,
	QLabel,
	QLineEdit,
	QListWidget,
	QListWidgetItem,
	QMessageBox,
	QVBoxLayout,
	QWidget,
)
from shiboken6 import isValid

from ..board import KanbanBoard
from ..models import CustomColumn
from .common import (
	column_can_add_card,
	column_color,
	column_identifier,
	column_label,
	column_target_value,
	resolve_column_target,
	resolve_hex_color,
)
from .embedded_board import (
	CardListItemContainer,
	CardListWidget,
	CardTile,
	ColumnAddButton,
	ColumnGroupBox,
	ColumnTitleButton,
)


class BoardNavigationMixin:
	"""Board view rendering and navigation helpers."""

	def _populate_columns(self, board: KanbanBoard):
		for column in board.get_columns_ordered():
			self.columns_layout.addWidget(self._create_column_widget(board, column))
		self.columns_layout.addStretch(1)

	def _create_column_widget(self, board: KanbanBoard, column: CustomColumn) -> QWidget:
		column_id = column_identifier(column)
		accent_color = resolve_hex_color(column_color(column), '#8f4a1d')
		column_box = ColumnGroupBox('', column_id, self, selected=column_id == self.selected_column_id)
		layout = QVBoxLayout(column_box)
		layout.setContentsMargins(6, 18, 6, 12)
		layout.setSpacing(10)

		title_row = QWidget()
		title_layout = QHBoxLayout(title_row)
		title_layout.setContentsMargins(0, 0, 0, 0)
		title_layout.setSpacing(8)

		title_button = ColumnTitleButton(
			column_label(column),
			click_callback=lambda _checked=False, cid=column_id: self.select_column(cid),
			double_click_callback=lambda cid=column_id: self.handle_column_double_click(cid),
			drag_callback=column_box.start_drag_from_hotspot,
			drag_target=column_box,
		)
		title_button.setStyleSheet(
			"QPushButton { text-align: left; background: rgba(98, 76, 58, 0.08); color: #3f2f21; border: none; border-radius: 10px; padding: 6px 10px; font-weight: 700; }"
			"QPushButton:hover { background: rgba(125, 59, 20, 0.12); }"
			"QPushButton:pressed { background: rgba(125, 59, 20, 0.18); }"
		)
		title_layout.addWidget(title_button, 1)

		if column_can_add_card(column):
			add_button = ColumnAddButton(accent_color)
			add_button.clicked.connect(lambda _checked=False, cid=column_target_value(column): self.create_card(cid))
			title_layout.addWidget(add_button)

		layout.addWidget(title_row)

		color_strip = QFrame()
		color_strip.setFixedHeight(8)
		color_strip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
		color_strip.setStyleSheet(
			f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent_color}, stop:1 {QColor(accent_color).lighter(120).name()}); border-radius: 4px;"
		)
		layout.addWidget(color_strip)

		list_widget = CardListWidget(column_id, self)
		list_widget.setFrameShape(QFrame.Shape.NoFrame)
		list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
		list_widget._apply_drop_style()
		list_widget.itemClicked.connect(lambda item, cid=column_id: self.on_card_clicked(cid, item))
		list_widget.itemDoubleClicked.connect(lambda _item: self.edit_selected_card())

		header_row = QWidget()
		header_layout = QHBoxLayout(header_row)
		header_layout.setContentsMargins(0, 0, 0, 0)
		header_layout.setSpacing(8)

		card_count_label = QLabel()
		card_count_label.setStyleSheet(
			"color: #6a5847; background: rgba(125, 59, 20, 0.06); border: 1px solid rgba(125, 59, 20, 0.08); border-radius: 10px; padding: 6px 8px; font-weight: 600;"
		)
		header_layout.addWidget(card_count_label)

		column_search_edit = QLineEdit(self._column_search_text(column_id))
		column_search_edit.setPlaceholderText('Search this column')
		column_search_edit.setClearButtonEnabled(True)
		column_search_edit.setStyleSheet(
			"background: #fffaf5; color: #3f2f21; border: 1px solid #d5bea0; border-radius: 10px; padding: 6px 10px;"
		)
		header_layout.addWidget(column_search_edit, 1)
		layout.addWidget(header_row)

		def populate_cards(search_text: str):
			active_cards = board.get_column_cards(column)
			filtered_cards = [
				card for card in self._filter_cards(board, active_cards)
				if self._card_matches_column_search(card, search_text)
			]
			list_widget.clear()
			for card in filtered_cards:
				item = QListWidgetItem()
				item.setData(Qt.ItemDataRole.UserRole, {'card_id': card.id, 'column_id': column_id})
				card_widget = CardTile(
					board,
					card,
					selected=card.id == self.selected_card_id,
					file_drop_callback=self.handle_card_file_drop,
					select_callback=lambda card_id, cid=column_id: self.select_card_from_tile(cid, card_id),
					edit_callback=lambda card_id, cid=column_id: self.edit_card_from_tile(cid, card_id),
					context_action_callback=lambda card_id, action, cid=column_id: self.handle_card_tile_action(cid, card_id, action),
					todo_toggle_callback=lambda card_id, todo_item_id, completed, cid=column_id: self.handle_card_tile_todo_toggle(cid, card_id, todo_item_id, completed),
				)
				row_widget = CardListItemContainer(card_widget)
				item.setSizeHint(row_widget.sizeHint())
				list_widget.addItem(item)
				list_widget.setItemWidget(item, row_widget)
				if card.id == self.selected_card_id:
					item.setSelected(True)
			count_text = f"{len(filtered_cards)} card" + ('' if len(filtered_cards) == 1 else 's')
			if search_text.strip() or (self._filters_active() and len(filtered_cards) != len(active_cards)):
				count_text = f"{len(filtered_cards)} of {len(active_cards)} cards"
			card_count_label.setText(count_text)
			QTimer.singleShot(0, lambda lw=list_widget: lw.refresh_card_sizes() if isValid(lw) else None)

		column_search_edit.textChanged.connect(lambda value, cid=column_id: self._set_column_search_text(cid, value))
		column_search_edit.textChanged.connect(populate_cards)
		populate_cards(column_search_edit.text())
		layout.addWidget(list_widget, 1)
		column_box.setMinimumWidth(280)
		return column_box

	def on_card_clicked(self, column_id: str, item: QListWidgetItem):
		payload = item.data(Qt.ItemDataRole.UserRole) or {}
		self.selected_column_id = column_id
		self.selected_card_id = payload.get('card_id')
		self.refresh_ui()

	def handle_column_double_click(self, column_id: str):
		self.selected_column_id = column_id
		self.selected_card_id = None
		self.edit_selected_column()

	def select_card_from_tile(self, column_id: str, card_id: str):
		self.selected_column_id = column_id
		self.selected_card_id = card_id
		self.refresh_ui()

	def edit_card_from_tile(self, column_id: str, card_id: str):
		self.selected_column_id = column_id
		self.selected_card_id = card_id
		self.edit_selected_card()

	def handle_card_tile_action(self, column_id: str, card_id: str, action: str):
		self.selected_column_id = column_id
		self.selected_card_id = card_id
		if action == 'add_subcard':
			self.add_subcard_to_selected_card()

	def handle_card_tile_todo_toggle(self, column_id: str, card_id: str, todo_item_id: str, completed: bool):
		board = self.ensure_writable_board()
		if board is None:
			return
		if board.update_card_todo_item(card_id, todo_item_id, completed=completed) is None:
			return
		self.selected_column_id = column_id
		self.selected_card_id = card_id
		self.refresh_ui()

	def select_column(self, column_id: str):
		self.selected_column_id = column_id
		self.selected_card_id = None
		self.refresh_ui()

	def handle_card_drop(self, card_id: Optional[str], source_column_id: Optional[str], target_column_id: Optional[str], target_card_id: Optional[str] = None, insert_after: bool = False):
		if not card_id or not target_column_id:
			return
		board = self.ensure_writable_board()
		if board is None:
			return
		target_value = resolve_column_target(board, target_column_id)
		if target_value is None:
			return
		if target_card_id == card_id and source_column_id == target_column_id:
			self.selected_column_id = target_column_id
			self.selected_card_id = card_id
			self.refresh_ui()
			return
		if not board.move_card(card_id, target_value, target_card_id=target_card_id, insert_after=insert_after):
			return
		self.selected_column_id = target_column_id
		self.selected_card_id = card_id
		self.refresh_ui()

	def handle_column_drop(self, dragged_column_id: Optional[str], target_column_id: Optional[str], insert_after: bool):
		if not dragged_column_id or not target_column_id or dragged_column_id == target_column_id:
			return
		board = self.ensure_writable_board()
		if board is None:
			return
		ordered_ids = [column.id for column in board.get_columns_ordered()]
		if dragged_column_id not in ordered_ids or target_column_id not in ordered_ids:
			return
		ordered_ids.remove(dragged_column_id)
		target_index = ordered_ids.index(target_column_id)
		if insert_after:
			target_index += 1
		ordered_ids.insert(target_index, dragged_column_id)
		board.reorder_columns(ordered_ids)
		self.selected_column_id = dragged_column_id
		self.refresh_ui()

	def handle_card_file_drop(self, card_id: Optional[str], file_paths: List[str]):
		if not card_id or not file_paths:
			return
		board = self.ensure_writable_board()
		if board is None:
			return
		try:
			added = board.add_card_attachments(card_id, file_paths)
		except Exception as exc:
			QMessageBox.warning(self.window, 'Attachment Error', f'Unable to attach dropped files.\n\n{exc}')
			return
		if not added:
			QMessageBox.information(self.window, 'No Files Added', 'No valid files were dropped onto the card.')
			return
		self.selected_card_id = card_id
		card = board.find_card(card_id)
		if card is not None:
			self.selected_column_id = card.column_id
		self.refresh_ui()

	def _refresh_board_menus(self, boards: List[Dict[str, object]]):
		self._refresh_recent_boards_menu(boards)
		self.switch_board_menu.clear()
		if not boards:
			empty_action = self.switch_board_menu.addAction('No Boards Available')
			empty_action.setEnabled(False)
			return
		for board_info in boards:
			label = board_info['name']
			if board_info.get('external'):
				label += ' [external]'
			if board_info.get('is_current'):
				label += ' [current]'
			action = self.switch_board_menu.addAction(label)
			action.setEnabled(not board_info.get('is_current'))
			action.triggered.connect(lambda _checked=False, board_id=board_info['id']: self._switch_board_by_id(board_id))

	def _refresh_recent_boards_menu(self, boards: List[Dict[str, object]]):
		self.recent_board_menu.clear()
		if not boards:
			empty_action = self.recent_board_menu.addAction('No Recent Boards')
			empty_action.setEnabled(False)
			return

		board_map = {board['id']: board for board in boards}
		self.recent_board_ids = [board_id for board_id in self.recent_board_ids if board_id in board_map]
		if not self.recent_board_ids:
			empty_action = self.recent_board_menu.addAction('No Recent Boards')
			empty_action.setEnabled(False)
			return

		for board_id in self.recent_board_ids:
			board_info = board_map[board_id]
			label = board_info['name']
			if board_info.get('external'):
				label += ' [external]'
			if board_info.get('is_current'):
				label += ' [current]'
			action = self.recent_board_menu.addAction(label)
			action.setEnabled(not board_info.get('is_current'))
			action.triggered.connect(lambda _checked=False, selected_board_id=board_id: self._switch_board_by_id(selected_board_id))

	def _remember_recent_board(self, board_id: str):
		if not board_id:
			return
		self.recent_board_ids = [existing_id for existing_id in self.recent_board_ids if existing_id != board_id]
		self.recent_board_ids.insert(0, board_id)
		self.recent_board_ids = self.recent_board_ids[:self.max_recent_boards]

	def _switch_board_by_id(self, board_id: str):
		if board_id and board_id != self.board_manager.current_board_id:
			if self.board_manager.switch_board(board_id):
				self._remember_recent_board(board_id)
				self.refresh_ui()

	def switch_board_prompt(self):
		boards = self.board_manager.get_board_list()
		if len(boards) <= 1:
			return
		choices = [board['name'] for board in boards]
		selected, ok = QInputDialog.getItem(self.window, 'Switch Board', 'Board', choices, editable=False)
		if not ok or not selected:
			return
		for board in boards:
			if board['name'] == selected:
				self._switch_board_by_id(board['id'])
				return


__all__ = ['BoardNavigationMixin']
