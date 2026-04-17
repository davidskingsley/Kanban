## @file
#  @brief Board overview and archive-inspection dialogs for the PySide6 multi-board GUI.
"""!Board overview and archive-inspection dialogs for the PySide6 GUI."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QDialog,
	QDialogButtonBox,
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QMessageBox,
	QPushButton,
	QTableWidgetItem,
	QTextBrowser,
	QVBoxLayout,
	QWidget,
)

from ..board import KanbanBoard
from .common import (
	PropagatingTableWidget,
	add_dialog_footer,
	build_dialog_shell,
	configure_form_layout,
	create_dialog_hint_label,
	create_dialog_section_label,
	due_state_colors,
	due_state_label,
	priority_label,
)
from .dialog_primitives import DueTimelineDelegate


class DueDateViewDialog(QDialog):
	"""!Due Date View Dialog."""
	def __init__(
		self,
		board: KanbanBoard,
		board_name: str,
		parent: Optional[QWidget] = None,
		on_focus_card=None,
		on_edit_card=None,
	):
		"""!Init."""
		super().__init__(parent)
		self.board = board
		self.board_name = board_name
		self.on_focus_card = on_focus_card
		self.on_edit_card = on_edit_card
		self.selected_card_id: Optional[str] = None
		self.selected_column_id: Optional[str] = None
		self.selected_action: Optional[str] = None
		self.entries = self._build_entries()
		self.timeline_delegate = DueTimelineDelegate(self)
		self.setWindowTitle(f'Due Date View - {board_name}')
		self.resize(1120, 760)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(18, 18, 18, 18)
		layout.setSpacing(14)

		hero = QFrame()
		hero.setObjectName('DueHero')
		hero_layout = QVBoxLayout(hero)
		hero_layout.setContentsMargins(18, 18, 18, 18)
		hero_layout.setSpacing(6)

		header_label = QLabel('Due Date View')
		header_label.setObjectName('DueHeroTitle')
		hero_layout.addWidget(header_label)

		subtitle_label = QLabel(f'Scheduled cards for {self.board_name}. Track overdue work, upcoming deadlines, and unscheduled items in one place.')
		subtitle_label.setObjectName('DueHeroSubtitle')
		subtitle_label.setWordWrap(True)
		hero_layout.addWidget(subtitle_label)
		layout.addWidget(hero)

		stats_row = QWidget()
		stats_layout = QHBoxLayout(stats_row)
		stats_layout.setContentsMargins(0, 0, 0, 0)
		stats_layout.setSpacing(12)
		self.shown_stat = self._create_stat_card('Shown')
		self.total_due_stat = self._create_stat_card('With Due Date')
		self.overdue_stat = self._create_stat_card('Overdue')
		self.due_soon_stat = self._create_stat_card('Due Soon')
		for stat_card in (self.shown_stat, self.total_due_stat, self.overdue_stat, self.due_soon_stat):
			stats_layout.addWidget(stat_card['frame'])
		layout.addWidget(stats_row)

		controls = QFrame()
		controls.setObjectName('DueControlsCard')
		controls_layout = QHBoxLayout(controls)
		controls_layout.setContentsMargins(16, 12, 16, 12)
		controls_layout.setSpacing(10)
		filter_label = QLabel('Filter')
		filter_label.setObjectName('DueFilterLabel')
		controls_layout.addWidget(filter_label)

		self.filter_combo = QComboBox()
		self.filter_combo.setObjectName('DueFilterCombo')
		self.filter_combo.addItems(['With Due Date', 'Overdue', 'Due in 7 Days', 'All Scheduled', 'No Due Date'])
		self.filter_combo.view().setStyleSheet(
			"""
			QListView {
				background: #fffaf2;
				color: #2d241c;
				border: 1px solid #ccb490;
				outline: 0;
				padding: 4px;
				selection-background-color: #7d3b14;
				selection-color: #ffffff;
			}
			QListView::item {
				min-height: 24px;
				padding: 6px 10px;
				border-radius: 6px;
			}
			QListView::item:hover {
				background: #eadfcf;
				color: #2d241c;
			}
			"""
		)
		self.filter_combo.currentIndexChanged.connect(self._populate_table)
		controls_layout.addWidget(self.filter_combo)
		controls_layout.addStretch(1)
		self.summary_label = QLabel()
		self.summary_label.setObjectName('DueSummaryText')
		self.summary_label.setWordWrap(True)
		controls_layout.addWidget(self.summary_label, 1)
		layout.addWidget(controls)

		table_card = QFrame()
		table_card.setObjectName('DueTableCard')
		table_layout = QVBoxLayout(table_card)
		table_layout.setContentsMargins(12, 12, 12, 12)
		table_layout.setSpacing(10)

		self.timeline_hint_label = QLabel()
		self.timeline_hint_label.setObjectName('DueTimelineHint')
		self.timeline_hint_label.setWordWrap(True)
		table_layout.addWidget(self.timeline_hint_label)

		self.table = PropagatingTableWidget(0, 6)
		self.table.setObjectName('DueDateTable')
		self.table.setHorizontalHeaderLabels(['Card', 'Column', 'Timeline', 'State', 'Assignee', 'Priority'])
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.setAlternatingRowColors(True)
		self.table.setShowGrid(False)
		self.table.verticalHeader().setVisible(False)
		self.table.itemDoubleClicked.connect(lambda _item: self._edit_selected_card())
		self.table.setItemDelegateForColumn(2, self.timeline_delegate)

		header = self.table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
		for column in range(3, self.table.columnCount()):
			header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
		table_layout.addWidget(self.table, 1)
		layout.addWidget(table_card, 1)

		button_row = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		button_row.rejected.connect(self.reject)
		layout.addWidget(button_row)

		self.table.itemSelectionChanged.connect(self._update_selection_state)
		self._populate_table()

	def _activate_selected_row(self, action: str):
		"""!Activate selected row."""
		self._update_selection_state()
		if not self.selected_card_id:
			return
		self.selected_action = action
		if action == 'edit' and self.on_edit_card is not None:
			self.on_edit_card(self.selected_card_id, self.selected_column_id)
			return
		if action == 'focus' and self.on_focus_card is not None:
			self.on_focus_card(self.selected_card_id, self.selected_column_id)
			return
		self.accept()

	def _create_stat_card(self, caption: str) -> Dict[str, QWidget]:
		"""!Create stat card."""
		frame = QFrame()
		frame.setObjectName('DueStatCard')
		layout = QVBoxLayout(frame)
		layout.setContentsMargins(14, 12, 14, 12)
		layout.setSpacing(2)

		value_label = QLabel('0')
		value_label.setObjectName('DueStatValue')
		layout.addWidget(value_label)

		caption_label = QLabel(caption)
		caption_label.setObjectName('DueStatCaption')
		layout.addWidget(caption_label)

		return {
			'frame': frame,
			'value': value_label,
		}

	def _build_entries(self) -> List[Dict[str, object]]:
		"""!Build entries."""
		today = date.today()
		entries: List[Dict[str, object]] = []
		for card in self.board.get_all_cards():
			entries.append({
				'card_id': card.id,
				'column_id': card.column_id,
				'title': card.title,
				'column': self.board.get_card_location_label(card),
				'start_date': card.start_date,
				'end_date': card.end_date,
				'state': due_state_label(self.board, card, today),
				'assignee': card.assignee or '—',
				'priority': priority_label(card.priority),
				'is_overdue': bool(card.end_date and card.end_date < today and not self.board.is_card_done(card)),
				'has_schedule': bool(card.start_date or card.end_date),
			})

		return sorted(
			entries,
			key=lambda entry: (
				(entry['start_date'] or entry['end_date']) is None,
				entry['start_date'] or entry['end_date'] or date.max,
				entry['end_date'] or entry['start_date'] or date.max,
				str(entry['title']).lower(),
			),
		)

	def _timeline_bounds(self, rows: List[Dict[str, object]]) -> tuple[date, date]:
		"""!Timeline bounds."""
		reference = date.today()
		anchors = [reference]
		for entry in rows:
			if entry['start_date'] is not None:
				anchors.append(entry['start_date'])
			if entry['end_date'] is not None:
				anchors.append(entry['end_date'])
		range_start = min(anchors) - timedelta(days=2)
		range_end = max(anchors) + timedelta(days=2)
		while (range_end - range_start).days < 13:
			range_start -= timedelta(days=1)
			range_end += timedelta(days=1)
		return range_start, range_end

	def _filtered_entries(self) -> List[Dict[str, object]]:
		"""!Filtered entries."""
		today = date.today()
		filter_name = self.filter_combo.currentText()
		if filter_name == 'Overdue':
			return [entry for entry in self.entries if entry['is_overdue']]
		if filter_name == 'Due in 7 Days':
			return [
				entry
				for entry in self.entries
				if entry['end_date'] is not None and 0 <= (entry['end_date'] - today).days <= 7
			]
		if filter_name == 'All Scheduled':
			return [entry for entry in self.entries if entry['has_schedule']]
		if filter_name == 'No Due Date':
			return [entry for entry in self.entries if entry['end_date'] is None]
		return [entry for entry in self.entries if entry['end_date'] is not None]

	def _populate_table(self):
		"""!Populate table."""
		rows = self._filtered_entries()
		total_due = sum(1 for entry in self.entries if entry['end_date'] is not None)
		overdue = sum(1 for entry in self.entries if entry['is_overdue'])
		due_soon = sum(
			1
			for entry in self.entries
			if entry['end_date'] is not None and 0 <= (entry['end_date'] - date.today()).days <= 7
		)
		self.summary_label.setText(
			f'{len(rows)} shown | {total_due} with due dates | {overdue} overdue | {due_soon} due within 7 days'
		)
		self.shown_stat['value'].setText(str(len(rows)))
		self.total_due_stat['value'].setText(str(total_due))
		self.overdue_stat['value'].setText(str(overdue))
		self.due_soon_stat['value'].setText(str(due_soon))
		range_start, range_end = self._timeline_bounds(rows)
		self.timeline_delegate.set_range(range_start, range_end)
		self.timeline_hint_label.setText(
			f"Timeline window {range_start.strftime('%b %d')} to {range_end.strftime('%b %d')} | red marker shows today | bars map scheduled work across the range."
		)
		self.table.horizontalHeaderItem(2).setText(f"Timeline ({range_start.strftime('%b %d')} - {range_end.strftime('%b %d')})")

		self.table.setRowCount(len(rows))
		for row_index, entry in enumerate(rows):
			values = [
				entry['title'],
				entry['column'],
				'',
				entry['state'],
				entry['assignee'],
				entry['priority'],
			]
			row_background, row_foreground = due_state_colors(str(entry['state']))
			for column_index, value in enumerate(values):
				item = QTableWidgetItem(str(value))
				if column_index == 0:
					item.setData(Qt.ItemDataRole.UserRole, {
						'card_id': entry['card_id'],
						'column_id': entry['column_id'],
					})
					font = item.font()
					font.setBold(True)
					item.setFont(font)
				if column_index == 2:
					item.setData(Qt.ItemDataRole.UserRole, {
						'start_date': entry['start_date'],
						'end_date': entry['end_date'],
						'state': entry['state'],
						'label': entry['title'],
					})
				if column_index == 3:
					font = item.font()
					font.setBold(True)
					item.setFont(font)
					item.setBackground(QColor(row_background))
					item.setForeground(QColor(row_foreground))
				self.table.setItem(row_index, column_index, item)
			self.table.setRowHeight(row_index, 56)

		self.table.clearSelection()
		self.selected_card_id = None
		self.selected_column_id = None

	def _update_selection_state(self):
		"""!Update selection state."""
		row = self.table.currentRow()
		if row < 0:
			self.selected_card_id = None
			self.selected_column_id = None
			return
		payload = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) or {}
		self.selected_card_id = payload.get('card_id')
		self.selected_column_id = payload.get('column_id')

	def _edit_selected_card(self):
		"""!Edit selected card."""
		self._activate_selected_row('edit')


class ActionLogDialog(QDialog):
	"""!Action Log Dialog."""

	def __init__(self, board: KanbanBoard, board_name: str, parent: Optional[QWidget] = None, card=None):
		"""!Init."""
		super().__init__(parent)
		self.board = board
		self.board_name = board_name
		self.card = card
		is_card_log = card is not None
		summary = f"Timestamped audit trail for board actions on {board_name}."
		headline = 'Action Log'
		log_text = self.board.export_action_log()
		window_label = board_name
		if is_card_log:
			headline = 'Card Action Log'
			window_label = card.title
			summary = f"Timestamped audit trail for actions recorded against card {card.title}."
			log_text = self.board.export_card_action_log(card.id, card_title=card.title)
		self.setWindowTitle(f'{headline} - {window_label}')
		self.resize(920, 620)

		content_layout = build_dialog_shell(
			self,
			headline,
			summary,
			scrollable=False,
		)

		self.log_browser = QTextBrowser()
		self.log_browser.setObjectName('ActionLogBrowser')
		self.log_browser.setReadOnly(True)
		self.log_browser.setOpenExternalLinks(False)
		self.log_browser.setStyleSheet(
			'QTextBrowser#ActionLogBrowser {'
			'background: #fffaf2; color: #4f4134; border: 1px solid #d8c6ab; border-radius: 12px; padding: 8px;'
			'}'
		)
		self.log_browser.setPlainText(log_text)
		content_layout.addWidget(self.log_browser)

		hint = 'Entries are stored with the actor name, date, time, and action description.'
		if is_card_log:
			hint = 'Only entries tagged to the selected card are shown here.'
		content_layout.addWidget(create_dialog_hint_label(hint))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


class ArchivedCardInfoDialog(QDialog):
	"""!Archived Card Info Dialog."""
	def __init__(self, card, column_label: str, parent: Optional[QWidget] = None):
		"""!Init."""
		super().__init__(parent)
		self.setWindowTitle(f'Archived Card: {card.title}')
		self.resize(640, 520)
		archived_label = card.archived_at.strftime('%Y-%m-%d %H:%M:%S') if card.archived_at else 'Unknown'
		completed_todos, total_todos = card.get_todo_progress()
		tags_label = ', '.join(card.tags) if card.tags else 'No tags'

		self.setStyleSheet('''
			QFrame#ArchivedInfoSectionCard {
				background: #fffdf8;
				border: 1px solid #dcc7a7;
				border-radius: 14px;
			}
			QLabel#ArchivedInfoBadge {
				background: #eadcc6;
				border: 1px solid #d1b28d;
				border-radius: 999px;
				color: #55351d;
				font-size: 9pt;
				font-weight: 700;
				padding: 5px 12px;
			}
			QLabel#ArchivedInfoBadge[variant="archived"] {
				background: #5c3920;
				border-color: #5c3920;
				color: #fff7ef;
			}
			QLabel#ArchivedInfoBadge[variant="priority"] {
				background: #efe3d1;
				border-color: #cfb08a;
			}
			QLabel#ArchivedInfoValue {
				color: #2d241c;
				font-size: 10pt;
			}
			QLabel#ArchivedInfoSecondaryValue {
				color: #6d5d4e;
				font-size: 9pt;
			}
			QTextBrowser#ArchivedInfoDescription {
				background: transparent;
				border: none;
				color: #2d241c;
				font-size: 10pt;
				padding: 0;
			}
		''')

		content_layout = build_dialog_shell(
			self,
			card.title,
			'Inspect the archived snapshot before restoring it to the board or deleting it permanently.',
			scrollable=False,
		)

		badge_row = QWidget()
		badge_layout = QHBoxLayout(badge_row)
		badge_layout.setContentsMargins(0, 0, 0, 0)
		badge_layout.setSpacing(8)

		def create_badge(text: str, variant: Optional[str] = None) -> QLabel:
			"""!Create badge."""
			badge = QLabel(text)
			badge.setObjectName('ArchivedInfoBadge')
			if variant:
				badge.setProperty('variant', variant)
				badge.style().unpolish(badge)
				badge.style().polish(badge)
			return badge

		badge_layout.addWidget(create_badge('Archived', 'archived'))
		badge_layout.addWidget(create_badge(f'{priority_label(card.priority)} Priority', 'priority'))
		badge_layout.addWidget(create_badge(f'Checklist {completed_todos}/{total_todos}'))
		badge_layout.addStretch(1)
		content_layout.addWidget(badge_row)

		location_hint = create_dialog_hint_label(
			f'Last visible in {column_label}. Archived cards remain searchable here until you restore or permanently delete them.'
		)
		content_layout.addWidget(location_hint)

		meta_card = QFrame()
		meta_card.setObjectName('ArchivedInfoSectionCard')
		meta_layout = QVBoxLayout(meta_card)
		meta_layout.setContentsMargins(16, 16, 16, 16)
		meta_layout.setSpacing(12)
		meta_layout.addWidget(create_dialog_section_label('Archived Snapshot'))

		metadata_form = QFormLayout()
		configure_form_layout(metadata_form)

		def create_value_label(text: str, secondary: bool = False) -> QLabel:
			"""!Create value label."""
			label = QLabel(text)
			label.setWordWrap(True)
			label.setObjectName('ArchivedInfoSecondaryValue' if secondary else 'ArchivedInfoValue')
			return label

		metadata_form.addRow('Column', create_value_label(column_label))
		metadata_form.addRow('Archived', create_value_label(archived_label))
		metadata_form.addRow('Assignee', create_value_label(card.assignee or 'Unassigned'))
		metadata_form.addRow('Project', create_value_label(card.project or 'No project'))
		metadata_form.addRow('Tags', create_value_label(tags_label, secondary=not bool(card.tags)))
		meta_layout.addLayout(metadata_form)
		content_layout.addWidget(meta_card)

		description_card = QFrame()
		description_card.setObjectName('ArchivedInfoSectionCard')
		description_layout = QVBoxLayout(description_card)
		description_layout.setContentsMargins(16, 16, 16, 16)
		description_layout.setSpacing(10)
		description_layout.addWidget(create_dialog_section_label('Description'))

		description_hint = create_dialog_hint_label(
			'This view is read only and mirrors the card state captured when it was archived.'
		)
		description_layout.addWidget(description_hint)

		description_browser = QTextBrowser()
		description_browser.setObjectName('ArchivedInfoDescription')
		description_browser.setOpenExternalLinks(False)
		description_browser.setReadOnly(True)
		description_browser.setPlainText(card.description or 'No description was saved for this archived card.')
		description_browser.setMinimumHeight(140)
		description_layout.addWidget(description_browser)
		content_layout.addWidget(description_card, 1)

		btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		btns.rejected.connect(self.reject)
		btns.accepted.connect(self.accept)
		add_dialog_footer(self, btns)


class ArchivedCardsDialog(QDialog):
	"""!Archived Cards Dialog."""
	def __init__(self, board: KanbanBoard, board_name: str, parent: Optional[QWidget] = None):
		"""!Init."""
		super().__init__(parent)
		self.board = board
		self.board_name = board_name
		self.selected_card_id: Optional[str] = None
		self.setWindowTitle(f'Archived Cards - {board_name}')
		self.resize(980, 640)
		self._build_ui()
		self._populate_table()

	def _build_ui(self):
		"""!Build ui."""
		content_layout = build_dialog_shell(
			self,
			'Archived Cards',
			'Review cards archived from completed columns, inspect their details, restore them to active board views, or permanently delete them.',
			scrollable=False,
		)

		self.setStyleSheet('''
			QDialog {
				border-radius: 16px;
				background: #f8f6f2;
			}
			#ArchivedCardsTable {
				border-radius: 8px;
				background: #fff;
				alternate-background-color: #f2ede6;
				selection-background-color: #e0cfa6;
				selection-color: #2d2210;
			}
			QPushButton[role="restore"] {
				background: #4caf50;
				color: white;
				border-radius: 8px;
				padding: 6px 18px;
				font-weight: bold;
			}
			QPushButton[role="delete"] {
				background: #e53935;
				color: white;
				border-radius: 8px;
				padding: 6px 18px;
				font-weight: bold;
			}
			QPushButton[role="details"] {
				background: #1976d2;
				color: white;
				border-radius: 8px;
				padding: 6px 18px;
				font-weight: bold;
			}
		''')

		self.summary_label = QLabel()
		self.summary_label.setWordWrap(True)
		self.summary_label.setStyleSheet('color: #4f4134; font-size: 15px; padding: 8px 0 8px 0;')
		content_layout.addWidget(self.summary_label)

		if self.board.is_read_only():
			content_layout.addWidget(create_dialog_hint_label('This board is read only. You can inspect archived cards here, but restoring or deleting them is disabled.'))

		self.table = PropagatingTableWidget(0, 5)
		self.table.setObjectName('ArchivedCardsTable')
		self.table.setHorizontalHeaderLabels(['Card', 'Column', 'Archived', 'Assignee', 'Priority'])
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.setAlternatingRowColors(True)
		self.table.setShowGrid(False)
		self.table.verticalHeader().setVisible(False)
		header = self.table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		for column_index in range(1, self.table.columnCount()):
			header.setSectionResizeMode(column_index, QHeaderView.ResizeMode.ResizeToContents)
		content_layout.addWidget(self.table, 1)

		actions_row = QWidget()
		actions_layout = QHBoxLayout(actions_row)
		actions_layout.setContentsMargins(0, 0, 0, 0)
		actions_layout.setSpacing(12)

		self.details_button = QPushButton('View Details')
		self.details_button.setProperty('role', 'details')
		self.details_button.clicked.connect(self._view_selected_card)
		actions_layout.addWidget(self.details_button)

		self.restore_button = QPushButton('Restore Card')
		self.restore_button.setProperty('role', 'restore')
		self.restore_button.clicked.connect(self._restore_selected_card)
		actions_layout.addWidget(self.restore_button)

		self.delete_button = QPushButton('Delete Permanently')
		self.delete_button.setProperty('role', 'delete')
		self.delete_button.clicked.connect(self._delete_selected_card)
		actions_layout.addWidget(self.delete_button)
		actions_layout.addStretch(1)
		content_layout.addWidget(actions_row)

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		self.button_box.rejected.connect(self.reject)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)

		self.table.itemSelectionChanged.connect(self._update_selection_state)
		self.table.itemDoubleClicked.connect(lambda _item: self._view_selected_card())

	def _archived_cards(self):
		"""!Archived cards."""
		return sorted(
			self.board.get_archived_cards(),
			key=lambda card: (
				card.archived_at or datetime.min,
				(card.title or '').lower(),
			),
			reverse=True,
		)

	def _populate_table(self):
		"""!Populate table."""
		cards = self._archived_cards()
		count = len(cards)
		if count == 0:
			self.summary_label.setText('No archived cards are stored on this board.')
		else:
			self.summary_label.setText(
				f'{count} archived card' + ('' if count == 1 else 's') + ' hidden from normal board views until restored.'
			)

		self.table.setRowCount(count)
		for row_index, card in enumerate(cards):
			archived_label = card.archived_at.strftime('%Y-%m-%d %H:%M:%S') if card.archived_at else 'Unknown'
			values = [
				card.title,
				self.board.get_card_location_label(card),
				archived_label,
				card.assignee or '—',
				priority_label(card.priority),
			]
			for column_index, value in enumerate(values):
				item = QTableWidgetItem(str(value))
				if column_index == 0:
					item.setData(Qt.ItemDataRole.UserRole, {'card_id': card.id})
					font = item.font()
					font.setBold(True)
					item.setFont(font)
				self.table.setItem(row_index, column_index, item)

		self.table.clearSelection()
		self.selected_card_id = None
		self._update_selection_state()

	def _update_selection_state(self):
		"""!Update selection state."""
		row = self.table.currentRow()
		payload = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 and self.table.item(row, 0) else {}
		self.selected_card_id = (payload or {}).get('card_id')
		has_selection = bool(self.selected_card_id)
		self.details_button.setEnabled(has_selection)
		can_mutate = has_selection and not self.board.is_read_only()
		self.restore_button.setEnabled(can_mutate)
		self.delete_button.setEnabled(can_mutate)

	def _selected_card(self):
		"""!Selected card."""
		if not self.selected_card_id:
			return None
		card = self.board.find_card(self.selected_card_id, include_archived=True)
		if card is None or not card.is_archived():
			return None
		return card

	def _view_selected_card(self):
		"""!View selected card."""
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self, 'Archived Cards', 'Select an archived card first.')
			return
		dialog = ArchivedCardInfoDialog(card, self.board.get_card_location_label(card), self)
		dialog.exec()

	def _restore_selected_card(self):
		"""!Restore selected card."""
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self, 'Restore Archived Card', 'Select an archived card first.')
			return
		if not card.is_archived():
			QMessageBox.warning(self, 'Restore Archived Card', 'This card is not archived.')
			return
		if not self.board.find_card(card.id, include_archived=True):
			QMessageBox.critical(self, 'Restore Archived Card', 'This card no longer exists.')
			return
		if self.board.restore_archived_card(card.id):
			self._populate_table()
			QMessageBox.information(self, 'Restore Archived Card', f"Restored '{card.title}'.")
		else:
			QMessageBox.warning(self, 'Restore Archived Card', f"Unable to restore '{card.title}'.")

	def _delete_selected_card(self):
		"""!Delete selected card."""
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self, 'Delete Archived Card', 'Select an archived card first.')
			return
		result = QMessageBox.question(
			self,
			'Delete Archived Card',
			f"Permanently delete archived card '{card.title}'?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result != QMessageBox.StandardButton.Yes:
			return
		if self.board.delete_card(card.id):
			self._populate_table()
			QMessageBox.information(self, 'Delete Archived Card', f"Deleted '{card.title}'.")
		else:
			QMessageBox.warning(self, 'Delete Archived Card', f"Unable to delete '{card.title}'.")




__all__ = [
	'ArchivedCardInfoDialog',
	'ArchivedCardsDialog',
	'DueDateViewDialog',
]