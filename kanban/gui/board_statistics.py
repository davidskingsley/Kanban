## @file
#  @brief Board statistics dialog for the PySide6 multi-board GUI.
"""Statistics views for board and portfolio-level summaries."""

from __future__ import annotations

from datetime import date
from typing import Dict, List

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QAbstractItemView,
	QDialog,
	QDialogButtonBox,
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from ..board import KanbanBoard
from ..models import Priority
from .common import (
	PropagatingTableWidget,
	build_dialog_shell,
	create_dialog_hint_label,
	create_dialog_section_label,
	due_state_colors,
	due_state_label,
	priority_label,
)


class BoardStatisticsDialog(QDialog):
	"""Rich portfolio and current-board statistics dialog."""

	def __init__(self, boards: List[Dict[str, object]], loaded_boards: Dict[str, KanbanBoard], parent=None):
		super().__init__(parent)
		self.boards = boards
		self.loaded_boards = loaded_boards
		self.current_board_info = next((board for board in boards if board.get('is_current')), None)
		self.current_board = None
		if self.current_board_info is not None:
			self.current_board = loaded_boards.get(self.current_board_info['id'])

		self.setWindowTitle('Board Statistics')
		self.resize(1120, 760)
		self._build_ui()
		self._populate()

	def _build_ui(self):
		content_layout = build_dialog_shell(
			self,
			'Board Statistics',
			'Review portfolio totals, per-board summaries, and a deeper breakdown for the active board.',
			scrollable=False,
		)

		content_layout.addWidget(create_dialog_section_label('Overview'))
		stat_row = QWidget()
		stat_layout = QGridLayout(stat_row)
		stat_layout.setContentsMargins(0, 0, 0, 0)
		stat_layout.setHorizontalSpacing(10)
		stat_layout.setVerticalSpacing(10)
		self.stat_cards = {
			'boards': self._create_stat_card('Boards'),
			'cards': self._create_stat_card('Cards'),
			'completed': self._create_stat_card('Completed'),
			'overdue': self._create_stat_card('Overdue'),
			'due_soon': self._create_stat_card('Due Soon'),
			'read_only': self._create_stat_card('Read Only'),
		}
		for index, key in enumerate(['boards', 'cards', 'completed', 'overdue', 'due_soon', 'read_only']):
			stat_layout.addWidget(self.stat_cards[key]['frame'], index // 3, index % 3)
		content_layout.addWidget(stat_row)

		content_layout.addWidget(create_dialog_section_label('Boards'))
		self.boards_table = PropagatingTableWidget(0, 10)
		self.boards_table.setHorizontalHeaderLabels([
			'Board', 'Description', 'Backend', 'Status', 'Cards', 'Done', 'Overdue', 'Due Soon', 'Columns', 'Priority Mix'
		])
		self._configure_table(self.boards_table, stretch_columns={1})
		content_layout.addWidget(self.boards_table)

		content_layout.addWidget(create_dialog_section_label('Current Board Breakdown'))
		breakdown_row = QWidget()
		breakdown_layout = QHBoxLayout(breakdown_row)
		breakdown_layout.setContentsMargins(0, 0, 0, 0)
		breakdown_layout.setSpacing(10)

		self.columns_table = PropagatingTableWidget(0, 3)
		self.columns_table.setHorizontalHeaderLabels(['Column', 'Cards', 'Share'])
		self._configure_table(self.columns_table, stretch_columns={0})
		breakdown_layout.addWidget(self.columns_table, 1)

		self.priority_table = PropagatingTableWidget(0, 3)
		self.priority_table.setHorizontalHeaderLabels(['Priority', 'Cards', 'Share'])
		self._configure_table(self.priority_table, stretch_columns={0})
		breakdown_layout.addWidget(self.priority_table, 1)

		self.due_state_table = PropagatingTableWidget(0, 3)
		self.due_state_table.setHorizontalHeaderLabels(['Due State', 'Cards', 'Share'])
		self._configure_table(self.due_state_table, stretch_columns={0})
		breakdown_layout.addWidget(self.due_state_table, 1)
		content_layout.addWidget(breakdown_row)

		self.current_board_hint = create_dialog_hint_label('Select a current board to see its detailed breakdown.')
		content_layout.addWidget(self.current_board_hint)

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		self.button_box.rejected.connect(self.reject)
		self.button_box.accepted.connect(self.accept)
		self.layout().addWidget(self.button_box)

	def _create_stat_card(self, caption: str) -> Dict[str, QWidget]:
		frame = QFrame()
		frame.setObjectName('DialogCard')
		layout = QVBoxLayout(frame)
		layout.setContentsMargins(14, 12, 14, 12)
		layout.setSpacing(2)

		value_label = QLabel('0')
		value_label.setStyleSheet('font-size: 18pt; font-weight: 700; color: #2f241c;')
		layout.addWidget(value_label)

		caption_label = QLabel(caption)
		caption_label.setStyleSheet('color: #6d5d4e; font-size: 9pt; letter-spacing: 0.03em;')
		layout.addWidget(caption_label)

		return {'frame': frame, 'value': value_label}

	def _configure_table(self, table, stretch_columns: set[int]):
		table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		table.setAlternatingRowColors(True)
		table.setShowGrid(False)
		table.verticalHeader().setVisible(False)
		header = table.horizontalHeader()
		for index in range(table.columnCount()):
			mode = QHeaderView.ResizeMode.Stretch if index in stretch_columns else QHeaderView.ResizeMode.ResizeToContents
			header.setSectionResizeMode(index, mode)

	def _board_metrics(self, board: KanbanBoard) -> Dict[str, object]:
		cards = board.get_all_cards()
		total_cards = len(cards)
		completed = sum(1 for card in cards if board.is_card_done(card))
		overdue = sum(1 for card in cards if card.end_date and card.end_date < date.today() and not board.is_card_done(card))
		due_soon = sum(1 for card in cards if card.end_date and 0 <= (card.end_date - date.today()).days <= 7 and not board.is_card_done(card))
		column_counts = {column.name: len(column.cards) for column in board.get_columns_ordered()}
		priority_counts = {
			priority_label(priority): sum(1 for card in cards if card.priority == priority)
			for priority in Priority
		}
		due_state_counts: Dict[str, int] = {}
		for card in cards:
			state = due_state_label(board, card)
			due_state_counts[state] = due_state_counts.get(state, 0) + 1
		return {
			'total_cards': total_cards,
			'completed': completed,
			'overdue': overdue,
			'due_soon': due_soon,
			'columns': column_counts,
			'priorities': priority_counts,
			'due_states': due_state_counts,
		}

	def _share_text(self, count: int, total: int) -> str:
		if total <= 0:
			return '0%'
		return f'{(count / total) * 100:.0f}%'

	def _populate(self):
		total_cards = 0
		total_completed = 0
		total_overdue = 0
		total_due_soon = 0
		read_only_boards = 0
		board_rows: List[Dict[str, object]] = []

		for board_info in self.boards:
			board = self.loaded_boards.get(board_info['id'])
			if board is None:
				board_rows.append({
					'name': board_info['name'],
					'description': board_info.get('description') or '—',
					'backend': str(board_info.get('storage_backend', 'json')).upper(),
					'status': 'Metadata only',
					'cards': '—',
					'done': '—',
					'overdue': '—',
					'due_soon': '—',
					'columns': '—',
					'priority_mix': '—',
				})
				continue

			metrics = self._board_metrics(board)
			total_cards += metrics['total_cards']
			total_completed += metrics['completed']
			total_overdue += metrics['overdue']
			total_due_soon += metrics['due_soon']
			if board.is_read_only():
				read_only_boards += 1

			priority_mix = ', '.join(
				f"{name} {count}" for name, count in metrics['priorities'].items() if count
			) or 'No cards'
			status_parts = []
			if board_info.get('is_current'):
				status_parts.append('Current')
			status_parts.append('Read only' if board.is_read_only() else 'Writable')

			board_rows.append({
				'name': board_info['name'],
				'description': board_info.get('description') or '—',
				'backend': str(board_info.get('storage_backend', 'json')).upper(),
				'status': ' | '.join(status_parts),
				'cards': str(metrics['total_cards']),
				'done': str(metrics['completed']),
				'overdue': str(metrics['overdue']),
				'due_soon': str(metrics['due_soon']),
				'columns': str(len(metrics['columns'])),
				'priority_mix': priority_mix,
			})

		self.stat_cards['boards']['value'].setText(f"{len(self.boards)}")
		self.stat_cards['cards']['value'].setText(str(total_cards))
		self.stat_cards['completed']['value'].setText(str(total_completed))
		self.stat_cards['overdue']['value'].setText(str(total_overdue))
		self.stat_cards['due_soon']['value'].setText(str(total_due_soon))
		self.stat_cards['read_only']['value'].setText(str(read_only_boards))

		self.boards_table.setRowCount(len(board_rows))
		for row_index, row in enumerate(board_rows):
			for column_index, key in enumerate(['name', 'description', 'backend', 'status', 'cards', 'done', 'overdue', 'due_soon', 'columns', 'priority_mix']):
				item = QTableWidgetItem(row[key])
				if key == 'name' and self.current_board_info and row['name'] == self.current_board_info['name']:
					font = item.font()
					font.setBold(True)
					item.setFont(font)
				self.boards_table.setItem(row_index, column_index, item)

		self._populate_current_board_breakdown()

	def _populate_current_board_breakdown(self):
		if self.current_board is None:
			self.columns_table.setRowCount(0)
			self.priority_table.setRowCount(0)
			self.due_state_table.setRowCount(0)
			self.current_board_hint.setText('The current board is not loaded, so only portfolio-level statistics are available.')
			return

		metrics = self._board_metrics(self.current_board)
		total_cards = max(metrics['total_cards'], 1)
		self.current_board_hint.setText(
			f"{self.current_board_info['name']} uses {str(self.current_board_info.get('storage_backend', 'json')).upper()} storage and has {metrics['total_cards']} cards across {len(metrics['columns'])} columns."
		)

		self.columns_table.setRowCount(len(metrics['columns']))
		for row_index, (name, count) in enumerate(metrics['columns'].items()):
			values = [name, str(count), self._share_text(count, total_cards)]
			for column_index, value in enumerate(values):
				self.columns_table.setItem(row_index, column_index, QTableWidgetItem(value))

		self.priority_table.setRowCount(len(metrics['priorities']))
		for row_index, (name, count) in enumerate(metrics['priorities'].items()):
			values = [name, str(count), self._share_text(count, total_cards)]
			for column_index, value in enumerate(values):
				self.priority_table.setItem(row_index, column_index, QTableWidgetItem(value))

		due_rows = sorted(metrics['due_states'].items(), key=lambda item: (-item[1], item[0].lower()))
		self.due_state_table.setRowCount(len(due_rows))
		for row_index, (name, count) in enumerate(due_rows):
			values = [name, str(count), self._share_text(count, total_cards)]
			background, foreground = due_state_colors(name)
			for column_index, value in enumerate(values):
				item = QTableWidgetItem(value)
				item.setBackground(QColor(background))
				item.setForeground(QColor(foreground))
				self.due_state_table.setItem(row_index, column_index, item)


__all__ = ['BoardStatisticsDialog']
