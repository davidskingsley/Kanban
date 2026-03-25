## @file
#  @brief Dialogs used by the PySide6 multi-board GUI.
"""Dialog layer for the PySide6 GUI."""

from __future__ import annotations

import os
from datetime import date
from typing import Dict, List, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QAbstractItemView,
	QCheckBox,
	QComboBox,
	QDateEdit,
	QDialog,
	QDialogButtonBox,
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QLabel,
	QListWidgetItem,
	QLineEdit,
	QMessageBox,
	QPushButton,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
	QHeaderView,
)

from ..board import KanbanBoard
from ..models import CardType, CustomColumn, Priority, Project
from .common import (
	ColorSelectionField,
	PropagatingListWidget,
	PropagatingTableWidget,
	PropagatingTextEdit,
	build_dialog_shell,
	choose_existing_directory_dialog,
	choose_open_files_dialog,
	column_label,
	column_target_value,
	configure_form_layout,
	create_dialog_hint_label,
	create_dialog_section_label,
	create_project_name_combo,
	display_date,
	due_state_colors,
	due_state_label,
	file_paths_from_mime_data,
	open_path_with_default_app,
	parse_tags,
	priority_label,
	resolve_hex_color,
)


class OptionalDateField(QWidget):
	"""A checkbox-controlled date input."""

	def __init__(self, label: str, initial_value: Optional[date] = None, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.checkbox = QCheckBox(label)
		self.editor = QDateEdit()
		self.clear_button = QPushButton('Clear')
		self.editor.setCalendarPopup(True)
		self.editor.setDisplayFormat('yyyy-MM-dd')
		self.editor.setSpecialValueText('')
		self.editor.setWrapping(False)
		self.editor.setEnabled(initial_value is not None)
		self.clear_button.setEnabled(initial_value is not None)
		self.clear_button.setFixedWidth(60)

		initial_qdate = QDate.currentDate()
		if initial_value is not None:
			initial_qdate = QDate(initial_value.year, initial_value.month, initial_value.day)
			self.checkbox.setChecked(True)
		self.editor.setDate(initial_qdate)

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(8)
		layout.addWidget(self.checkbox)
		layout.addWidget(self.editor, 1)
		layout.addWidget(self.clear_button)
		self.checkbox.toggled.connect(self._set_enabled_state)
		self.clear_button.clicked.connect(self.clear)

	def _set_enabled_state(self, checked: bool):
		self.editor.setEnabled(checked)
		self.clear_button.setEnabled(checked)
		if checked:
			if not self.editor.date().isValid():
				self.editor.setDate(QDate.currentDate())
			self.editor.setFocus(Qt.FocusReason.TabFocusReason)
			self.editor.selectAll()

	def clear(self):
		self.checkbox.setChecked(False)
		self.editor.setDate(QDate.currentDate())

	def value(self) -> Optional[date]:
		if not self.checkbox.isChecked():
			return None
		selected = self.editor.date()
		return date(selected.year(), selected.month(), selected.day())


class DueDateViewDialog(QDialog):
	"""Dialog showing due-date status for cards on the active board."""

	def __init__(self, board: KanbanBoard, board_name: str, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.board = board
		self.board_name = board_name
		self.selected_card_id: Optional[str] = None
		self.selected_column_id: Optional[str] = None
		self.entries = self._build_entries()

		self.setWindowTitle(f'Due Date View - {board_name}')
		self.resize(980, 620)
		self.setObjectName('DueDateViewDialog')
		self._build_ui()
		self._populate_table()

	def _build_ui(self):
		self.setStyleSheet(
			"""
			QDialog#DueDateViewDialog {
				background: #f6efe2;
			}
			QFrame#DueHero,
			QFrame#DueStatCard,
			QFrame#DueControlsCard,
			QFrame#DueTableCard {
				background: #fffaf2;
				border: 1px solid #d8c6ab;
				border-radius: 16px;
			}
			QFrame#DueHero {
				background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
					stop:0 #f9efe1, stop:1 #efe3d1);
				border: 1px solid #d2ba97;
			}
			QLabel#DueHeroTitle {
				font-size: 16pt;
				font-weight: 700;
				color: #2f241c;
			}
			QLabel#DueHeroSubtitle {
				color: #6d5d4e;
				font-size: 10pt;
			}
			QLabel#DueStatValue {
				font-size: 18pt;
				font-weight: 700;
				color: #2f241c;
			}
			QLabel#DueStatCaption {
				color: #6d5d4e;
				font-size: 9pt;
				letter-spacing: 0.03em;
			}
			QLabel#DueSummaryText {
				color: #5f5246;
				font-size: 10pt;
			}
			QTableWidget#DueDateTable {
				background: #fffdfa;
				alternate-background-color: #fbf3e8;
				border: none;
				border-radius: 12px;
				gridline-color: #eadfcd;
				selection-background-color: #d8c2a3;
				selection-color: #2d241c;
				outline: 0;
			}
			QTableWidget#DueDateTable::item {
				padding: 10px 8px;
				border-bottom: 1px solid #efe4d3;
			}
			QHeaderView::section {
				background: #eadfcf;
				color: #3a2d22;
				border: none;
				border-bottom: 1px solid #d2b99a;
				padding: 10px 8px;
				font-weight: 700;
			}
			QComboBox#DueFilterCombo {
				min-width: 180px;
				background: #fffdfa;
				border: 1px solid #ccb490;
				border-radius: 10px;
				padding: 7px 10px;
			}
			QLabel#DueFilterLabel {
				color: #53473b;
				font-weight: 600;
			}
			"""
		)

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

		self.table = PropagatingTableWidget(0, 7)
		self.table.setObjectName('DueDateTable')
		self.table.setHorizontalHeaderLabels(['Card', 'Column', 'Start', 'Due', 'State', 'Assignee', 'Priority'])
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.setAlternatingRowColors(True)
		self.table.setShowGrid(False)
		self.table.verticalHeader().setVisible(False)
		self.table.itemDoubleClicked.connect(lambda _item: self._open_selected_card())

		header = self.table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		for column in range(1, self.table.columnCount()):
			header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
		table_layout.addWidget(self.table, 1)
		layout.addWidget(table_card, 1)

		button_row = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		self.open_button = button_row.addButton('Open Card', QDialogButtonBox.ButtonRole.AcceptRole)
		self.open_button.setEnabled(False)
		self.open_button.clicked.connect(self._open_selected_card)
		button_row.rejected.connect(self.reject)
		layout.addWidget(button_row)

		self.table.itemSelectionChanged.connect(self._update_selection_state)

	def _create_stat_card(self, caption: str) -> Dict[str, QWidget]:
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
				entry['end_date'] is None,
				entry['end_date'] or date.max,
				entry['start_date'] or date.max,
				str(entry['title']).lower(),
			),
		)

	def _filtered_entries(self) -> List[Dict[str, object]]:
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

		self.table.setRowCount(len(rows))
		for row_index, entry in enumerate(rows):
			values = [
				entry['title'],
				entry['column'],
				display_date(entry['start_date']),
				display_date(entry['end_date']),
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
				if column_index == 4:
					font = item.font()
					font.setBold(True)
					item.setFont(font)
				item.setBackground(QColor(row_background))
				item.setForeground(QColor(row_foreground))
				self.table.setItem(row_index, column_index, item)
			self.table.setRowHeight(row_index, 42)

		self.table.clearSelection()
		self.selected_card_id = None
		self.selected_column_id = None
		self.open_button.setEnabled(False)

	def _update_selection_state(self):
		row = self.table.currentRow()
		if row < 0:
			self.selected_card_id = None
			self.selected_column_id = None
			self.open_button.setEnabled(False)
			return
		payload = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) or {}
		self.selected_card_id = payload.get('card_id')
		self.selected_column_id = payload.get('column_id')
		self.open_button.setEnabled(bool(self.selected_card_id))

	def _open_selected_card(self):
		if not self.selected_card_id:
			return
		self.accept()


class BoardDialog(QDialog):
	"""Dialog for creating a board."""

	def __init__(self, default_directory: str, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.setWindowTitle('Create Board')
		self.resize(620, 420)
		self.name_edit = QLineEdit()
		self.description_edit = PropagatingTextEdit()
		self.description_edit.setFixedHeight(90)
		self.directory_edit = QLineEdit(default_directory)
		browse_button = QPushButton('Browse')
		browse_button.clicked.connect(self.choose_directory)

		directory_row = QWidget()
		directory_layout = QHBoxLayout(directory_row)
		directory_layout.setContentsMargins(0, 0, 0, 0)
		directory_layout.addWidget(self.directory_edit)
		directory_layout.addWidget(browse_button)

		content_layout = build_dialog_shell(
			self,
			'Create Board',
			'Create a new board and choose where its data should be stored.',
		)
		content_layout.addWidget(create_dialog_section_label('Board Details'))
		form = QFormLayout()
		configure_form_layout(form)
		form.addRow('Name', self.name_edit)
		form.addRow('Description', self.description_edit)
		form.addRow('Storage Folder', directory_row)
		content_layout.addLayout(form)
		content_layout.addWidget(create_dialog_hint_label('Board names should be short and identifiable. The storage folder can be inside or outside the default boards directory.'))

		buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

	def choose_directory(self):
		directory = choose_existing_directory_dialog(self, 'Select Board Storage Folder', self.directory_edit.text())
		if directory:
			self.directory_edit.setText(directory)

	def values(self) -> Dict[str, str]:
		return {
			'name': self.name_edit.text().strip(),
			'description': self.description_edit.toPlainText().strip(),
			'storage_dir': self.directory_edit.text().strip(),
		}

	def accept(self):
		if not self.name_edit.text().strip():
			QMessageBox.warning(self, 'Missing Name', 'Board name is required.')
			return
		super().accept()


class ColumnDialog(QDialog):
	"""Dialog for creating or editing a column."""

	def __init__(self, column: Optional[CustomColumn] = None, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.setWindowTitle('Column')
		self.resize(560, 360)
		self.name_edit = QLineEdit()
		self.name_edit.setText(column.name if column is not None else '')
		self.color_field = ColorSelectionField(
			initial_color=column.color if column is not None else '#2196F3',
			allow_clear=False,
			default_label='Required',
			selected_label='Color selected',
		)
		self.completed_check = QCheckBox('Completed column')
		self.completed_check.setChecked(bool(column is not None and column.is_completed))
		self.add_card_check = QCheckBox('Show add-card action')
		self.add_card_check.setChecked(bool(column is not None and column.can_add_card))

		content_layout = build_dialog_shell(
			self,
			'Column Settings',
			'Choose the name, accent color, and workflow behavior for this column.',
		)
		content_layout.addWidget(create_dialog_section_label('Column Details'))
		form = QFormLayout()
		configure_form_layout(form)
		form.addRow('Name', self.name_edit)
		form.addRow('Color', self.color_field)
		form.addRow('', self.completed_check)
		form.addRow('', self.add_card_check)
		content_layout.addLayout(form)
		content_layout.addWidget(create_dialog_hint_label('Completed columns are treated as done. Add-card actions make the column a creation target from the board view.'))

		buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

	def values(self) -> Dict[str, object]:
		return {
			'name': self.name_edit.text().strip(),
			'color': self.color_field.color() or '#2196F3',
			'is_completed': self.completed_check.isChecked(),
			'can_add_card': self.add_card_check.isChecked(),
		}

	def accept(self):
		if not self.name_edit.text().strip():
			QMessageBox.warning(self, 'Missing Name', 'Column name is required.')
			return
		super().accept()


class ReorderColumnsDialog(QDialog):
	"""Dialog for reordering columns."""

	def __init__(self, columns: List[CustomColumn], parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.setWindowTitle('Reorder Columns')
		self.resize(560, 440)
		self.columns = list(columns)
		self.list_widget = PropagatingListWidget()
		self.refresh_items()

		up_button = QPushButton('Move Up')
		down_button = QPushButton('Move Down')
		up_button.clicked.connect(self.move_up)
		down_button.clicked.connect(self.move_down)

		button_row = QWidget()
		button_layout = QHBoxLayout(button_row)
		button_layout.setContentsMargins(0, 0, 0, 0)
		button_layout.addWidget(up_button)
		button_layout.addWidget(down_button)

		content_layout = build_dialog_shell(
			self,
			'Reorder Columns',
			'Adjust the sequence of columns as they appear in the board view.',
		)
		content_layout.addWidget(create_dialog_section_label('Column Order'))
		content_layout.addWidget(self.list_widget, 1)
		content_layout.addWidget(create_dialog_hint_label('Select a column, then use Move Up or Move Down until the order is correct.'))
		content_layout.addWidget(button_row)
		buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

	def refresh_items(self):
		self.list_widget.clear()
		for column in self.columns:
			self.list_widget.addItem(column.name)
		if self.columns:
			self.list_widget.setCurrentRow(0)

	def move_up(self):
		row = self.list_widget.currentRow()
		if row <= 0:
			return
		self.columns[row - 1], self.columns[row] = self.columns[row], self.columns[row - 1]
		self.refresh_items()
		self.list_widget.setCurrentRow(row - 1)

	def move_down(self):
		row = self.list_widget.currentRow()
		if row < 0 or row >= len(self.columns) - 1:
			return
		self.columns[row + 1], self.columns[row] = self.columns[row], self.columns[row + 1]
		self.refresh_items()
		self.list_widget.setCurrentRow(row + 1)

	def ordered_ids(self) -> List[str]:
		return [column.id for column in self.columns]


class CardTypeDialog(QDialog):
	"""Dialog for creating or editing a card type."""

	def __init__(self, card_type: Optional[CardType] = None, is_default: bool = False,
				 board: Optional[KanbanBoard] = None, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.card_type = card_type
		self.is_default = is_default
		self.setWindowTitle('Edit Card Type' if card_type else 'Create Card Type')
		self.resize(660, 480)

		self.name_edit = QLineEdit(card_type.name if card_type else '')
		self.name_edit.setEnabled(not is_default)
		self.description_edit = PropagatingTextEdit(card_type.description if card_type else '')
		self.description_edit.setFixedHeight(100)
		self.project_edit = create_project_name_combo(board, card_type.default_project if card_type else None)
		self.color_field = ColorSelectionField(
			initial_color=card_type.default_color if card_type else None,
			allow_clear=True,
			default_label='Default color',
			selected_label='Preset color selected',
		)

		content_layout = build_dialog_shell(
			self,
			'Card Type Preset',
			'Define reusable metadata that can prefill card creation fields across the board.',
		)
		content_layout.addWidget(create_dialog_section_label('Preset Details'))
		layout = QFormLayout()
		configure_form_layout(layout)
		layout.addRow('Name', self.name_edit)
		layout.addRow('Description', self.description_edit)
		layout.addRow('Project Preset', self.project_edit)
		layout.addRow('Color Preset', self.color_field)
		content_layout.addLayout(layout)
		content_layout.addWidget(create_dialog_hint_label('Card types can define reusable project and color presets. The default type cannot be renamed or deleted.'))

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

	def values(self) -> Dict[str, Optional[str]]:
		return {
			'name': self.name_edit.text().strip(),
			'description': self.description_edit.toPlainText().strip(),
			'default_project': self.project_edit.currentText().strip() or None,
			'default_color': self.color_field.color(),
		}

	def accept(self):
		if not self.card_type and not self.name_edit.text().strip():
			QMessageBox.warning(self, 'Missing Name', 'Card type name is required.')
			return
		if self.card_type and not self.is_default and not self.name_edit.text().strip():
			QMessageBox.warning(self, 'Missing Name', 'Card type name is required.')
			return
		super().accept()


class CardTypesBrowserDialog(QDialog):
	"""Read-only browser for board card types and their presets."""

	def __init__(self, board: KanbanBoard, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.board = board
		self.selected_card_type_id: Optional[str] = None
		self.setWindowTitle('Card Types')
		self.resize(920, 580)

		content_layout = build_dialog_shell(
			self,
			'Card Types',
			'Review reusable card presets, their project and color defaults, and how widely each one is used.',
		)
		content_layout.addWidget(create_dialog_section_label('Configured Types'))

		self.table = PropagatingTableWidget(0, 6)
		self.table.setHorizontalHeaderLabels(['Name', 'Description', 'Project Preset', 'Color Preset', 'Cards', 'Flags'])
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().setVisible(False)
		self.table.itemDoubleClicked.connect(lambda _item: self._activate_selected_card_type())
		header = self.table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
		content_layout.addWidget(self.table, 1)
		content_layout.addWidget(create_dialog_hint_label('Default marks the fallback type for new cards. Last used reflects the preset currently remembered for quick card creation.'))

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

		self.refresh_rows()

	def _create_color_swatch(self, color_value: Optional[str]) -> QWidget:
		container = QWidget()
		layout = QHBoxLayout(container)
		layout.setContentsMargins(8, 0, 8, 0)
		layout.setSpacing(8)

		swatch = QFrame()
		swatch.setFixedSize(18, 18)

		label = QLabel()
		label.setStyleSheet('color: #4f4134;')

		if color_value:
			resolved = resolve_hex_color(color_value, '#ddd4c6')
			swatch.setStyleSheet(
				f'background: {resolved}; border: 1px solid #b8a17f; border-radius: 5px;'
			)
			label.setText('Preset selected')
		else:
			swatch.setStyleSheet(
				'background: #efe6d8; border: 1px dashed #b8a17f; border-radius: 5px;'
			)
			label.setText('Default')

		layout.addWidget(swatch)
		layout.addWidget(label)
		layout.addStretch(1)
		return container

	def refresh_rows(self):
		default_type_id = self.board.get_default_card_type_id()
		last_used_id = self.board.get_last_used_card_type().id
		card_types = self.board.get_card_types_ordered()
		self.table.setRowCount(len(card_types))
		for row_index, card_type in enumerate(card_types):
			flags: List[str] = []
			if card_type.id == default_type_id:
				flags.append('default')
			if card_type.id == last_used_id:
				flags.append('last used')
			values = [
				card_type.name,
				card_type.description or '—',
				card_type.default_project or '—',
				'',
				str(len(self.board.get_cards_by_type(card_type.id))),
				' | '.join(flags) if flags else '—',
			]
			for column_index, value in enumerate(values):
				item = QTableWidgetItem(value)
				if column_index == 0:
					item.setData(Qt.ItemDataRole.UserRole, card_type.id)
				self.table.setItem(row_index, column_index, item)
			self.table.setCellWidget(row_index, 3, self._create_color_swatch(card_type.default_color))
			self.table.setRowHeight(row_index, 36)

	def _activate_selected_card_type(self):
		row = self.table.currentRow()
		if row < 0:
			return
		item = self.table.item(row, 0)
		if item is None:
			return
		self.selected_card_type_id = item.data(Qt.ItemDataRole.UserRole)
		if self.selected_card_type_id:
			self.accept()


class ProjectDialog(QDialog):
	"""Dialog for creating or editing a managed project."""

	def __init__(self, project: Optional[Project] = None, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.project = project
		self.setWindowTitle('Edit Project' if project else 'Create Project')
		self.resize(660, 420)

		self.name_edit = QLineEdit(project.name if project else '')
		self.description_edit = PropagatingTextEdit(project.description if project else '')
		self.description_edit.setFixedHeight(120)

		content_layout = build_dialog_shell(
			self,
			'Project',
			'Define reusable project names so cards and card-type presets can reference them consistently.',
		)
		content_layout.addWidget(create_dialog_section_label('Project Details'))
		layout = QFormLayout()
		configure_form_layout(layout)
		layout.addRow('Name', self.name_edit)
		layout.addRow('Description', self.description_edit)
		content_layout.addLayout(layout)
		content_layout.addWidget(create_dialog_hint_label('Renaming a project updates cards and any card-type project presets that reference it.'))

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

	def values(self) -> Dict[str, str]:
		return {
			'name': self.name_edit.text().strip(),
			'description': self.description_edit.toPlainText().strip(),
		}

	def accept(self):
		if not self.name_edit.text().strip():
			QMessageBox.warning(self, 'Missing Name', 'Project name is required.')
			return
		super().accept()


class ProjectsBrowserDialog(QDialog):
	"""Read-only browser for managed projects and their usage counts."""

	def __init__(self, board: KanbanBoard, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.board = board
		self.selected_project_id: Optional[str] = None
		self.setWindowTitle('Projects')
		self.resize(900, 560)

		content_layout = build_dialog_shell(
			self,
			'Projects',
			'Review managed project names, their descriptions, and how widely they are referenced across the board.',
		)
		content_layout.addWidget(create_dialog_section_label('Configured Projects'))

		self.table = PropagatingTableWidget(0, 4)
		self.table.setHorizontalHeaderLabels(['Name', 'Description', 'Cards', 'Card Type Presets'])
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().setVisible(False)
		self.table.itemDoubleClicked.connect(lambda _item: self._activate_selected_project())
		header = self.table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
		content_layout.addWidget(self.table, 1)
		content_layout.addWidget(create_dialog_hint_label('Double-click a project to open it for editing. Deleting a project can clear or reassign both card references and card-type presets.'))

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

		self.refresh_rows()

	def refresh_rows(self):
		projects = self.board.get_projects_ordered()
		self.table.setRowCount(len(projects))
		for row_index, project in enumerate(projects):
			values = [
				project.name,
				project.description or '—',
				str(len(self.board.get_cards_by_project(project.id))),
				str(len(self.board.get_card_types_by_project(project.id))),
			]
			for column_index, value in enumerate(values):
				item = QTableWidgetItem(value)
				if column_index == 0:
					item.setData(Qt.ItemDataRole.UserRole, project.id)
				self.table.setItem(row_index, column_index, item)
			self.table.setRowHeight(row_index, 36)

	def _activate_selected_project(self):
		row = self.table.currentRow()
		if row < 0:
			return
		item = self.table.item(row, 0)
		if item is None:
			return
		self.selected_project_id = item.data(Qt.ItemDataRole.UserRole)
		if self.selected_project_id:
			self.accept()


class AttachmentDropFrame(QFrame):
	"""Drop target used by the card dialog attachment area."""

	def __init__(self, dialog, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.dialog = dialog
		self.setObjectName('AttachmentDropFrame')
		self.setAcceptDrops(True)

	def dragEnterEvent(self, event):
		self.dialog._attachment_drag_enter_event(event)

	def dragLeaveEvent(self, event):
		self.dialog._attachment_drag_leave_event(event)

	def dropEvent(self, event):
		self.dialog._attachment_drop_event(event)


class CardDialog(QDialog):
	"""Dialog for creating or editing a card."""

	def __init__(self, board: KanbanBoard, card=None, target_column_id: Optional[str] = None,
				 parent_card=None,
				 parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.board = board
		self.card = card
		self.parent_card = parent_card
		self.did_mutate_board = False
		self.subcards: List[object] = []
		self.setWindowTitle('Edit Card' if card else ('Add Subcard' if parent_card else 'Create Card'))
		self.resize(720, 700)

		self.title_edit = QLineEdit(card.title if card else '')
		self.description_edit = PropagatingTextEdit(card.description if card else '')
		self.description_edit.setFixedHeight(120)

		self.priority_combo = QComboBox()
		for priority in Priority:
			self.priority_combo.addItem(priority_label(priority), priority)
		if card:
			self.priority_combo.setCurrentIndex(list(Priority).index(card.priority))

		self.column_combo = QComboBox()
		for column in board.get_columns_ordered():
			self.column_combo.addItem(column_label(column), column_target_value(column))
		desired_column = target_column_id
		if desired_column is None and card:
			desired_column = card.column_id
		if desired_column is None and parent_card is not None:
			desired_column = parent_card.column_id
		if desired_column is None:
			desired_column = board.get_default_add_card_column_id()
		if desired_column:
			for index in range(self.column_combo.count()):
				if self.column_combo.itemData(index) == desired_column:
					self.column_combo.setCurrentIndex(index)
					break
		if parent_card is not None:
			self.column_combo.setEnabled(False)

		self.assignee_edit = QLineEdit(card.assignee or '' if card else '')
		initial_project = card.project if card else (parent_card.project if parent_card else None)
		self.project_edit = create_project_name_combo(board, initial_project)
		self.tags_edit = QLineEdit(', '.join(card.tags) if card else '')
		self.color_field = ColorSelectionField(
			initial_color=card.color if card else (parent_card.color if parent_card else None),
			allow_clear=True,
			default_label='Board default color',
			selected_label='Card color selected',
		)

		self.start_date = OptionalDateField('Start Date', card.start_date if card else None)
		self.end_date = OptionalDateField('End Date', card.end_date if card else None)
		self.attachments_list = PropagatingListWidget()
		self.attachments_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.attachments_list.setMinimumHeight(140)
		self.attachments_list.itemDoubleClicked.connect(lambda _item: self.open_selected_attachment())

		self.attachment_drop_frame = AttachmentDropFrame(self)

		drop_layout = QVBoxLayout(self.attachment_drop_frame)
		drop_layout.setContentsMargins(14, 14, 14, 14)
		drop_layout.setSpacing(10)
		self.attachment_drop_label = QLabel(
			'Drop files here to attach them to this card.' if card else 'Create the card first, then reopen it to add attachments.'
		)
		self.attachment_drop_label.setWordWrap(True)
		drop_layout.addWidget(self.attachment_drop_label)
		drop_layout.addWidget(self.attachments_list)

		attachment_buttons = QWidget()
		attachment_button_layout = QHBoxLayout(attachment_buttons)
		attachment_button_layout.setContentsMargins(0, 0, 0, 0)
		attachment_button_layout.setSpacing(8)
		self.add_attachment_button = QPushButton('Add Files')
		self.add_attachment_button.clicked.connect(self.add_attachments_via_picker)
		attachment_button_layout.addWidget(self.add_attachment_button)
		self.open_attachment_button = QPushButton('Open')
		self.open_attachment_button.clicked.connect(self.open_selected_attachment)
		attachment_button_layout.addWidget(self.open_attachment_button)
		self.delete_attachment_button = QPushButton('Remove')
		self.delete_attachment_button.clicked.connect(self.delete_selected_attachment)
		attachment_button_layout.addWidget(self.delete_attachment_button)
		attachment_button_layout.addStretch(1)
		drop_layout.addWidget(attachment_buttons)

		self.card_type_combo = QComboBox()
		for card_type in board.get_card_types_ordered():
			self.card_type_combo.addItem(card_type.name, card_type.id)
		selected_type_id = None
		if card and card.card_type_id:
			selected_type_id = card.card_type_id
		elif parent_card and parent_card.card_type_id:
			selected_type_id = parent_card.card_type_id
		elif not card:
			selected_type_id = board.get_last_used_card_type().id
		if selected_type_id:
			for index in range(self.card_type_combo.count()):
				if self.card_type_combo.itemData(index) == selected_type_id:
					self.card_type_combo.setCurrentIndex(index)
					break

		shell_title = 'Card Details'
		shell_subtitle = 'Set the core metadata, scheduling, and reusable preset values for this card.'
		if parent_card is not None:
			shell_title = 'Subcard Details'
			shell_subtitle = f"Create a child card under '{parent_card.title}'. Subcards inherit the parent column and cannot contain nested subcards."

		content_layout = build_dialog_shell(
			self,
			shell_title,
			shell_subtitle,
		)
		content_layout.addWidget(create_dialog_section_label('Card Fields'))
		layout = QFormLayout()
		configure_form_layout(layout)
		layout.addRow('Title', self.title_edit)
		layout.addRow('Description', self.description_edit)
		layout.addRow('Priority', self.priority_combo)
		layout.addRow('Column', self.column_combo)
		layout.addRow('Assignee', self.assignee_edit)
		layout.addRow('Project', self.project_edit)
		layout.addRow('Tags', self.tags_edit)
		layout.addRow('Color', self.color_field)
		layout.addRow('Card Type', self.card_type_combo)
		layout.addRow('', self.start_date)
		layout.addRow('', self.end_date)
		content_layout.addLayout(layout)
		content_layout.addWidget(create_dialog_section_label('Attachments'))
		content_layout.addWidget(self.attachment_drop_frame)
		self._set_attachment_drop_active(False)
		self.refresh_attachments_list()

		if self._supports_subcard_management():
			content_layout.addWidget(create_dialog_section_label('Subcards'))
			subcards_frame = QFrame()
			subcards_frame.setObjectName('DialogCard')
			subcards_layout = QVBoxLayout(subcards_frame)
			subcards_layout.setContentsMargins(14, 14, 14, 14)
			subcards_layout.setSpacing(10)
			self.subcards_list = PropagatingListWidget()
			self.subcards_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
			self.subcards_list.setMinimumHeight(150)
			self.subcards_list.itemDoubleClicked.connect(lambda _item: self.edit_selected_subcard())
			subcards_layout.addWidget(self.subcards_list)

			subcard_buttons = QWidget()
			subcard_button_layout = QHBoxLayout(subcard_buttons)
			subcard_button_layout.setContentsMargins(0, 0, 0, 0)
			subcard_button_layout.setSpacing(8)
			self.add_subcard_button = QPushButton('Add Subcard')
			self.add_subcard_button.clicked.connect(self.add_subcard)
			subcard_button_layout.addWidget(self.add_subcard_button)
			self.delete_subcard_button = QPushButton('Delete Selected')
			self.delete_subcard_button.clicked.connect(self.delete_selected_subcard)
			subcard_button_layout.addWidget(self.delete_subcard_button)
			subcard_button_layout.addStretch(1)
			subcards_layout.addWidget(subcard_buttons)
			content_layout.addWidget(subcards_frame)
			self.refresh_subcards_list()

		buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		content_layout.addWidget(buttons)

	def _supports_subcard_management(self) -> bool:
		return self.card is not None and not self.card.parent_id

	def _set_attachment_drop_active(self, active: bool):
		border_color = '#3e7a5e' if active else '#d2ba97'
		background = '#eef7f0' if active else '#fffaf2'
		self.attachment_drop_frame.setStyleSheet(
			f"""
			QFrame#AttachmentDropFrame {{
				background: {background};
				border: 2px dashed {border_color};
				border-radius: 14px;
			}}
			QListWidget {{
				background: #fbf5ea;
				border: 1px solid #d8c6ab;
				border-radius: 10px;
				padding: 4px;
			}}
			"""
		)

	def _attachment_drag_enter_event(self, event):
		if self.card is None:
			event.ignore()
			return
		if not file_paths_from_mime_data(event.mimeData()):
			event.ignore()
			return
		self._set_attachment_drop_active(True)
		event.acceptProposedAction()

	def _attachment_drag_leave_event(self, event):
		self._set_attachment_drop_active(False)
		QFrame.dragLeaveEvent(self.attachment_drop_frame, event)

	def _attachment_drop_event(self, event):
		self._set_attachment_drop_active(False)
		if self.card is None:
			event.ignore()
			return
		paths = file_paths_from_mime_data(event.mimeData())
		if not paths:
			event.ignore()
			return
		self.add_attachments_from_drop(paths)
		event.acceptProposedAction()

	def refresh_attachments_list(self):
		self.attachments_list.clear()
		editable = self.card is not None and not self.board.is_read_only()
		self.attachment_drop_frame.setEnabled(editable)
		self.add_attachment_button.setEnabled(editable)
		self.delete_attachment_button.setEnabled(editable)
		self.open_attachment_button.setEnabled(self.card is not None)
		if self.card is None:
			placeholder = QListWidgetItem('Attachments are available after the card is created.')
			placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
			self.attachments_list.addItem(placeholder)
			return
		if not self.card.attachments:
			placeholder = QListWidgetItem('No attachments added yet.')
			placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
			self.attachments_list.addItem(placeholder)
			return
		for attachment in self.card.attachments:
			item = QListWidgetItem(attachment.name)
			item.setData(Qt.ItemDataRole.UserRole, attachment.id)
			self.attachments_list.addItem(item)

	def _selected_attachment_id(self) -> Optional[str]:
		item = self.attachments_list.currentItem()
		if item is None:
			return None
		return item.data(Qt.ItemDataRole.UserRole)

	def add_attachments_via_picker(self):
		if self.card is None:
			QMessageBox.information(self, 'Create Card First', 'Save the card before adding attachments.')
			return
		if self.board.is_read_only():
			QMessageBox.warning(self, 'Read Only Board', self.board.get_read_only_message())
			return
		paths = choose_open_files_dialog(self, 'Add Card Attachments')
		if paths:
			self.add_attachments_from_drop(paths)

	def add_attachments_from_drop(self, file_paths: List[str]):
		if self.card is None:
			return
		try:
			added = self.board.add_card_attachments(self.card.id, file_paths)
		except Exception as exc:
			QMessageBox.warning(self, 'Attachment Error', f'Unable to add attachments.\n\n{exc}')
			return
		if not added:
			QMessageBox.information(self, 'No Files Added', 'No valid files were provided.')
			return
		self.card = self.board.find_card(self.card.id)
		self.did_mutate_board = True
		self.refresh_attachments_list()

	def open_selected_attachment(self):
		if self.card is None:
			return
		attachment_id = self._selected_attachment_id()
		if not attachment_id:
			QMessageBox.information(self, 'No Attachment Selected', 'Select an attachment first.')
			return
		path = self.board.get_card_attachment_path(self.card.id, attachment_id)
		if not path or not os.path.exists(path):
			QMessageBox.warning(self, 'Attachment Missing', 'The attachment file could not be found.')
			return
		open_path_with_default_app(path)

	def delete_selected_attachment(self):
		if self.card is None:
			return
		if self.board.is_read_only():
			QMessageBox.warning(self, 'Read Only Board', self.board.get_read_only_message())
			return
		attachment_id = self._selected_attachment_id()
		if not attachment_id:
			QMessageBox.information(self, 'No Attachment Selected', 'Select an attachment first.')
			return
		result = QMessageBox.question(
			self,
			'Remove Attachment',
			'Remove the selected attachment from this card?',
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result != QMessageBox.StandardButton.Yes:
			return
		if not self.board.delete_card_attachment(self.card.id, attachment_id):
			QMessageBox.warning(self, 'Attachment Error', 'Unable to remove the selected attachment.')
			return
		self.card = self.board.find_card(self.card.id)
		self.did_mutate_board = True
		self.refresh_attachments_list()

	def refresh_subcards_list(self):
		if not hasattr(self, 'subcards_list'):
			return
		self.subcards = self.board.get_subcards(self.card.id)
		self.subcards_list.clear()
		editable = not self.board.is_read_only()
		self.add_subcard_button.setEnabled(editable)
		self.delete_subcard_button.setEnabled(editable and bool(self.subcards))
		if not self.subcards:
			placeholder = QListWidgetItem('No subcards yet.')
			placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
			self.subcards_list.addItem(placeholder)
			return
		for subcard in self.subcards:
			tick = '[x]' if self.board.is_card_done(subcard) else '[ ]'
			location = self.board.get_card_location_label(subcard)
			item = QListWidgetItem(f'{tick} {subcard.title} ({location})')
			item.setData(Qt.ItemDataRole.UserRole, subcard.id)
			self.subcards_list.addItem(item)

	def _selected_subcard(self):
		if not hasattr(self, 'subcards_list'):
			return None
		item = self.subcards_list.currentItem()
		if item is None:
			return None
		subcard_id = item.data(Qt.ItemDataRole.UserRole)
		if not subcard_id:
			return None
		return self.board.find_card(subcard_id)

	def add_subcard(self):
		if self.card is None:
			return
		if self.board.is_read_only():
			QMessageBox.warning(self, 'Read Only Board', self.board.get_read_only_message())
			return
		dialog = CardDialog(
			self.board,
			target_column_id=self.card.column_id,
			parent_card=self.card,
			parent=self,
		)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			if dialog.did_mutate_board:
				self.did_mutate_board = True
				self.card = self.board.find_card(self.card.id)
				self.refresh_subcards_list()
			return
		values = dialog.values()
		try:
			self.board.create_subcard(
				self.card.id,
				values['title'],
				values['description'],
				values['priority'],
				values['project'] or None,
				values['color'],
				values['card_type_id'],
				values['start_date'],
				values['end_date'],
				values['assignee'] or None,
				values['tags'],
			)
		except ValueError as error:
			QMessageBox.warning(self, 'Add Subcard', str(error))
			return
		self.did_mutate_board = True
		self.card = self.board.find_card(self.card.id)
		self.refresh_subcards_list()

	def edit_selected_subcard(self):
		subcard = self._selected_subcard()
		if subcard is None:
			return
		original_column_id = subcard.column_id
		dialog = CardDialog(self.board, card=subcard, parent=self)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			if dialog.did_mutate_board:
				self.did_mutate_board = True
				self.card = self.board.find_card(self.card.id)
				self.refresh_subcards_list()
			return
		values = dialog.values()
		self.board.edit_card(
			subcard.id,
			title=values['title'],
			description=values['description'],
			priority=values['priority'],
			assignee=values['assignee'] or None,
			project=values['project'] or None,
			start_date=values['start_date'],
			end_date=values['end_date'],
			color=values['color'],
			tags=values['tags'],
			card_type_id=values['card_type_id'],
		)
		if values['column_id'] != original_column_id:
			self.board.move_card(subcard.id, values['column_id'])
		self.did_mutate_board = True
		self.card = self.board.find_card(self.card.id)
		self.refresh_subcards_list()

	def delete_selected_subcard(self):
		subcard = self._selected_subcard()
		if subcard is None:
			QMessageBox.information(self, 'Delete Subcard', 'Select a subcard to delete.')
			return
		result = QMessageBox.question(
			self,
			'Delete Subcard',
			f"Delete subcard '{subcard.title}'?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result != QMessageBox.StandardButton.Yes:
			return
		self.board.delete_card(subcard.id)
		self.did_mutate_board = True
		self.card = self.board.find_card(self.card.id)
		self.refresh_subcards_list()

	def values(self) -> Dict[str, object]:
		return {
			'title': self.title_edit.text().strip(),
			'description': self.description_edit.toPlainText().strip(),
			'priority': self.priority_combo.currentData(),
			'column_id': self.column_combo.currentData(),
			'assignee': self.assignee_edit.text().strip(),
			'project': self.project_edit.currentText().strip(),
			'tags': parse_tags(self.tags_edit.text()),
			'color': self.color_field.color(),
			'card_type_id': self.card_type_combo.currentData(),
			'start_date': self.start_date.value(),
			'end_date': self.end_date.value(),
		}

	def accept(self):
		if not self.title_edit.text().strip():
			QMessageBox.warning(self, 'Missing Title', 'Card title is required.')
			return
		super().accept()


__all__ = [
	'AttachmentDropFrame',
	'BoardDialog',
	'CardDialog',
	'CardTypeDialog',
	'CardTypesBrowserDialog',
	'ColumnDialog',
	'DueDateViewDialog',
	'OptionalDateField',
	'ProjectDialog',
	'ProjectsBrowserDialog',
	'ReorderColumnsDialog',
]
