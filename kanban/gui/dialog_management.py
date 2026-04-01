## @file
#  @brief Board, column, card-type, and project management dialogs for the PySide6 multi-board GUI.
"""Management dialogs for the PySide6 GUI."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QAbstractItemView,
	QCheckBox,
	QComboBox,
	QDialog,
	QDialogButtonBox,
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QLineEdit,
	QMessageBox,
	QPushButton,
	QTableWidgetItem,
	QWidget,
)

from ..board import KanbanBoard
from ..models import CardType, CustomColumn, Project
from ..storage import JSON_STORAGE_BACKEND, SQLITE_STORAGE_BACKEND
from .common import (
	ColorSelectionField,
	PropagatingListWidget,
	PropagatingTableWidget,
	PropagatingTextEdit,
	add_dialog_footer,
	build_dialog_shell,
	choose_existing_directory_dialog,
	configure_form_layout,
	create_dialog_hint_label,
	create_dialog_section_label,
	create_project_name_combo,
	resolve_hex_color,
)


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
		self.backend_combo = QComboBox()
		self.backend_combo.addItem('Current Backend (JSON File)', JSON_STORAGE_BACKEND)
		self.backend_combo.addItem('SQLite3 Backend', SQLITE_STORAGE_BACKEND)
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
		form.addRow('Backend', self.backend_combo)
		form.addRow('Storage Folder', directory_row)
		content_layout.addLayout(form)
		content_layout.addWidget(create_dialog_hint_label('Board names should be short and identifiable. Choose the existing JSON backend or SQLite3, then select where the board file should be stored.'))

		buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		add_dialog_footer(self, buttons)

	def choose_directory(self):
		directory = choose_existing_directory_dialog(self, 'Select Board Storage Folder', self.directory_edit.text())
		if directory:
			self.directory_edit.setText(directory)

	def values(self) -> Dict[str, str]:
		return {
			'name': self.name_edit.text().strip(),
			'description': self.description_edit.toPlainText().strip(),
			'storage_backend': self.backend_combo.currentData(),
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
		add_dialog_footer(self, buttons)

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
		add_dialog_footer(self, buttons)

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

	def __init__(self, card_type: Optional[CardType] = None, is_default: bool = False, board: Optional[KanbanBoard] = None, parent: Optional[QWidget] = None):
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
		add_dialog_footer(self, buttons)

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
		add_dialog_footer(self, buttons)

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
		add_dialog_footer(self, buttons)

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
		add_dialog_footer(self, buttons)

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


__all__ = [
	'BoardDialog',
	'CardTypeDialog',
	'CardTypesBrowserDialog',
	'ColumnDialog',
	'ProjectDialog',
	'ProjectsBrowserDialog',
	'ReorderColumnsDialog',
]