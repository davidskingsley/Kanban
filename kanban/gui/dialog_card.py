## @file
#  @brief Card editing dialogs and attachment widgets for the PySide6 multi-board GUI.
"""Card editing dialogs for the PySide6 GUI."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QDialog,
	QDialogButtonBox,
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QListWidgetItem,
	QMessageBox,
	QPushButton,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)

from ..board import KanbanBoard
from ..models import Priority
from .common import (
	ColorSelectionField,
	PropagatingListWidget,
	PropagatingTextEdit,
	add_dialog_footer,
	build_dialog_shell,
	choose_open_files_dialog,
	configure_form_layout,
	create_dialog_hint_label,
	create_dialog_section_label,
	create_project_name_combo,
	file_paths_from_mime_data,
	open_path_with_default_app,
	parse_tags,
	priority_label,
	resolve_hex_color,
)
from .dialog_primitives import (
	OptionalDateField,
	SubcardListItemContainer,
	SubcardRowWidget,
	SubcardsListWidget,
)


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


CARD_DIALOG_SECTION_FRAME_STYLESHEET = """
	QFrame#DialogCard,
	QFrame#AttachmentDropFrame {
		background: #fff9f0;
		border: 1px solid #dcc7a7;
		border-radius: 14px;
	}
"""


class CardDialog(QDialog):
	"""Dialog for creating or editing a card."""

	def _dialog_facade(self):
		from . import dialogs as dialog_facade

		return dialog_facade

	def __init__(self, board: KanbanBoard, card=None, target_column_id: Optional[str] = None,
				 parent_card=None, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.board = board
		self.card = card
		self.parent_card = parent_card
		self.did_mutate_board = False
		self.editing_note_id: Optional[str] = None
		self.subcards: List[object] = []
		window_title = 'Edit Card'
		if card is None:
			window_title = 'Add Subcard' if parent_card else 'Create Card'
		self.setWindowTitle(window_title)
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
			self.column_combo.addItem(column.name, column.id)
		desired_column = target_column_id
		if desired_column is None and card:
			desired_column = card.column_id
		if desired_column is None and parent_card is not None:
			desired_column = board.get_subcard_target(parent_card)
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
		initial_project = None
		if card:
			initial_project = card.project
		elif parent_card:
			initial_project = parent_card.project
		self.project_edit = create_project_name_combo(board, initial_project)
		self.tags_edit = QLineEdit(', '.join(card.tags) if card else '')
		initial_color = None
		if card:
			initial_color = card.color
		elif parent_card:
			initial_color = parent_card.color
		self.color_field = ColorSelectionField(
			initial_color=initial_color,
			allow_clear=True,
			default_label='Board default color',
			selected_label='Card color selected',
		)

		self.start_date = OptionalDateField('Start Date', card.start_date if card else None)
		self.end_date = OptionalDateField('End Date', card.end_date if card else None)
		self.todo_list = PropagatingListWidget()
		self.todo_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.todo_list.setMinimumHeight(150)
		self.todo_list.setEditTriggers(
			QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
		)
		self.todo_list.itemDoubleClicked.connect(self._edit_todo_item)
		self.todo_list.itemSelectionChanged.connect(self._refresh_todo_controls)
		self.todo_list.itemChanged.connect(lambda _item: self._refresh_todo_controls())
		self.todo_entry = QLineEdit()
		self.todo_entry.setPlaceholderText('Add a checklist item and press Enter')
		self.todo_entry.returnPressed.connect(self.add_todo_item)
		self.add_todo_button = QPushButton('Add Item')
		self.add_todo_button.clicked.connect(self.add_todo_item)
		self.remove_todo_button = QPushButton('Remove Selected')
		self.remove_todo_button.clicked.connect(self.remove_selected_todo_item)
		self.checklist_frame = QFrame()
		self.checklist_frame.setObjectName('DialogCard')
		self.checklist_frame.setStyleSheet(CARD_DIALOG_SECTION_FRAME_STYLESHEET)
		checklist_layout = QVBoxLayout(self.checklist_frame)
		checklist_layout.setContentsMargins(14, 14, 14, 14)
		checklist_layout.setSpacing(10)
		checklist_layout.addWidget(create_dialog_hint_label('Add optional checklist items. Tick items off as the card progresses.'))
		checklist_layout.addWidget(self.todo_list)
		todo_buttons = QWidget()
		todo_button_layout = QHBoxLayout(todo_buttons)
		todo_button_layout.setContentsMargins(0, 0, 0, 0)
		todo_button_layout.setSpacing(8)
		todo_button_layout.addWidget(self.todo_entry, 1)
		todo_button_layout.addWidget(self.add_todo_button)
		todo_button_layout.addWidget(self.remove_todo_button)
		checklist_layout.addWidget(todo_buttons)
		self.attachments_list = PropagatingListWidget()
		self.attachments_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.attachments_list.setMinimumHeight(140)
		self.attachments_list.itemDoubleClicked.connect(lambda _item: self.open_selected_attachment())

		self.attachment_drop_frame = AttachmentDropFrame(self)
		self.attachment_drop_frame.setStyleSheet(CARD_DIALOG_SECTION_FRAME_STYLESHEET)

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

		self.notes_list = PropagatingListWidget()
		self.notes_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.notes_list.setMinimumHeight(150)
		self.notes_list.itemSelectionChanged.connect(self._refresh_note_controls)
		self.notes_list.itemDoubleClicked.connect(lambda _item: self.edit_selected_note())
		self.note_entry = PropagatingTextEdit()
		self.note_entry.setPlaceholderText('Write a timestamped note for this card')
		self.note_entry.setFixedHeight(100)
		self.note_entry.textChanged.connect(self._refresh_note_controls)
		self.add_note_button = QPushButton('Add Note')
		self.add_note_button.clicked.connect(self.save_note)
		self.edit_note_button = QPushButton('Load Selected')
		self.edit_note_button.clicked.connect(self.edit_selected_note)
		self.clear_note_button = QPushButton('Clear Editor')
		self.clear_note_button.clicked.connect(self.clear_note_editor)
		self.delete_note_button = QPushButton('Remove Selected')
		self.delete_note_button.clicked.connect(self.delete_selected_note)
		self.notes_frame = QFrame()
		self.notes_frame.setObjectName('DialogCard')
		self.notes_frame.setStyleSheet(CARD_DIALOG_SECTION_FRAME_STYLESHEET)
		notes_layout = QVBoxLayout(self.notes_frame)
		notes_layout.setContentsMargins(14, 14, 14, 14)
		notes_layout.setSpacing(10)
		notes_layout.addWidget(create_dialog_hint_label('Notes are timestamped and saved immediately to the card. Double-click a note to load it back into the editor.'))
		notes_layout.addWidget(self.notes_list)
		notes_layout.addWidget(self.note_entry)
		note_buttons = QWidget()
		note_button_layout = QHBoxLayout(note_buttons)
		note_button_layout.setContentsMargins(0, 0, 0, 0)
		note_button_layout.setSpacing(8)
		note_button_layout.addWidget(self.add_note_button)
		note_button_layout.addWidget(self.edit_note_button)
		note_button_layout.addWidget(self.clear_note_button)
		note_button_layout.addWidget(self.delete_note_button)
		note_button_layout.addStretch(1)
		notes_layout.addWidget(note_buttons)

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
			shell_subtitle = (
				f"Create a child card under '{parent_card.title}'. Subcards stay in the parent column "
				'when that column allows adding cards; otherwise they start in the left-most column. '
				'Nested subcards are not supported.'
			)

		content_layout = build_dialog_shell(self, shell_title, shell_subtitle)
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
		content_layout.addWidget(create_dialog_section_label('Checklist'))
		content_layout.addWidget(self.checklist_frame)
		content_layout.addWidget(create_dialog_section_label('Attachments'))
		content_layout.addWidget(self.attachment_drop_frame)
		self.refresh_todo_list()
		self._set_attachment_drop_active(False)
		self.refresh_attachments_list()
		if self.card is not None:
			content_layout.addWidget(create_dialog_section_label('Notes'))
			content_layout.addWidget(self.notes_frame)
			self.refresh_notes_list()

		if self._supports_subcard_management():
			content_layout.addWidget(create_dialog_section_label('Subcards'))
			subcards_frame = QFrame()
			subcards_frame.setObjectName('DialogCard')
			subcards_frame.setStyleSheet(
				CARD_DIALOG_SECTION_FRAME_STYLESHEET +
				"""
				QLabel#SubcardsPanelTitle {
					color: #3d2d20;
					font-size: 11pt;
					font-weight: 700;
				}
				QLabel#SubcardsSummary {
					background: rgba(125, 59, 20, 0.10);
					color: #6f3d1c;
					border: 1px solid rgba(125, 59, 20, 0.18);
					border-radius: 11px;
					padding: 4px 10px;
					font-weight: 700;
				}
				QLabel#SubcardsProgress {
					background: rgba(62, 122, 94, 0.10);
					color: #2f654b;
					border: 1px solid rgba(62, 122, 94, 0.18);
					border-radius: 11px;
					padding: 4px 10px;
					font-weight: 700;
				}
				QListWidget#SubcardsList {
					background: #fcf6ec;
					border: 1px solid #d9c4a2;
					border-radius: 12px;
					padding: 6px;
					outline: 0;
				}
				QListWidget#SubcardsList::item {
					padding: 9px 10px;
					margin: 2px 0;
					border-radius: 10px;
				}
				QListWidget#SubcardsList::item:selected {
					background: #ead7bb;
					color: #2d241c;
					border: 1px solid #d2af7f;
				}
				QPushButton#SubcardSecondaryButton {
					background: #f5ecdf;
					color: #5c4633;
					border: 1px solid #d2be9d;
				}
				QPushButton#SubcardSecondaryButton:hover {
					background: #eadfce;
				}
				QPushButton#SubcardSecondaryButton:pressed {
					background: #dcccb6;
				}
				"""
			)
			subcards_layout = QVBoxLayout(subcards_frame)
			subcards_layout.setContentsMargins(14, 14, 14, 14)
			subcards_layout.setSpacing(12)

			subcards_header = QWidget()
			subcards_header_layout = QHBoxLayout(subcards_header)
			subcards_header_layout.setContentsMargins(0, 0, 0, 0)
			subcards_header_layout.setSpacing(10)
			subcards_header_text = QWidget()
			subcards_header_text_layout = QVBoxLayout(subcards_header_text)
			subcards_header_text_layout.setContentsMargins(0, 0, 0, 0)
			subcards_header_text_layout.setSpacing(3)
			self.subcards_panel_title = QLabel('Child Cards')
			self.subcards_panel_title.setObjectName('SubcardsPanelTitle')
			subcards_header_text_layout.addWidget(self.subcards_panel_title)
			self.subcards_hint_label = create_dialog_hint_label('Double-click a subcard to edit it. Child cards stay linked to the parent card and share its board history.')
			subcards_header_text_layout.addWidget(self.subcards_hint_label)
			subcards_header_layout.addWidget(subcards_header_text, 1)
			badge_stack = QWidget()
			badge_stack_layout = QVBoxLayout(badge_stack)
			badge_stack_layout.setContentsMargins(0, 0, 0, 0)
			badge_stack_layout.setSpacing(6)
			self.subcards_summary_label = QLabel()
			self.subcards_summary_label.setObjectName('SubcardsSummary')
			self.subcards_summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			badge_stack_layout.addWidget(self.subcards_summary_label)
			self.subcards_progress_label = QLabel()
			self.subcards_progress_label.setObjectName('SubcardsProgress')
			self.subcards_progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			badge_stack_layout.addWidget(self.subcards_progress_label)
			subcards_header_layout.addWidget(badge_stack)
			subcards_layout.addWidget(subcards_header)

			self.subcards_list = SubcardsListWidget()
			self.subcards_list.setObjectName('SubcardsList')
			self.subcards_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
			self.subcards_list.setMinimumHeight(170)
			self.subcards_list.itemDoubleClicked.connect(lambda _item: self.edit_selected_subcard())
			self.subcards_list.itemSelectionChanged.connect(self._refresh_subcard_row_styles)
			subcards_layout.addWidget(self.subcards_list)

			subcard_buttons = QWidget()
			subcard_button_layout = QHBoxLayout(subcard_buttons)
			subcard_button_layout.setContentsMargins(0, 0, 0, 0)
			subcard_button_layout.setSpacing(8)
			self.add_subcard_button = QPushButton('Add Subcard')
			self.add_subcard_button.clicked.connect(self.add_subcard)
			subcard_button_layout.addWidget(self.add_subcard_button)
			self.edit_subcard_button = QPushButton('Edit Selected')
			self.edit_subcard_button.setObjectName('SubcardSecondaryButton')
			self.edit_subcard_button.clicked.connect(self.edit_selected_subcard)
			subcard_button_layout.addWidget(self.edit_subcard_button)
			self.delete_subcard_button = QPushButton('Delete Selected')
			self.delete_subcard_button.setObjectName('SubcardSecondaryButton')
			self.delete_subcard_button.clicked.connect(self.delete_selected_subcard)
			subcard_button_layout.addWidget(self.delete_subcard_button)
			subcard_button_layout.addStretch(1)
			subcards_layout.addWidget(subcard_buttons)
			content_layout.addWidget(subcards_frame)
			self.refresh_subcards_list()

		buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		add_dialog_footer(self, buttons)

	def _append_todo_list_item(self, text: str, completed: bool = False, item_id: Optional[str] = None):
		item = QListWidgetItem(text)
		item.setFlags(
			Qt.ItemFlag.ItemIsEnabled
			| Qt.ItemFlag.ItemIsSelectable
			| Qt.ItemFlag.ItemIsEditable
			| Qt.ItemFlag.ItemIsUserCheckable
		)
		item.setCheckState(Qt.CheckState.Checked if completed else Qt.CheckState.Unchecked)
		item.setData(Qt.ItemDataRole.UserRole, item_id)
		self.todo_list.addItem(item)

	def _selected_todo_item(self):
		item = self.todo_list.currentItem()
		if item is None:
			return None
		if not item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
			return None
		return item

	def _ensure_todo_placeholder(self):
		if self.todo_list.count() > 0:
			return
		placeholder = QListWidgetItem('No checklist items yet.')
		placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
		placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
		self.todo_list.addItem(placeholder)

	def _clear_todo_placeholder(self):
		if self.todo_list.count() != 1:
			return
		item = self.todo_list.item(0)
		if item is not None and not item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
			self.todo_list.clear()

	def refresh_todo_list(self):
		self.todo_list.clear()
		for todo_item in (self.card.todo_items if self.card else []):
			self._append_todo_list_item(todo_item.text, todo_item.completed, todo_item.id)
		self._ensure_todo_placeholder()
		self._refresh_todo_controls()

	def _refresh_todo_controls(self):
		self.remove_todo_button.setEnabled(self._selected_todo_item() is not None)

	def add_todo_item(self):
		text = self.todo_entry.text().strip()
		if not text:
			return
		self._clear_todo_placeholder()
		self._append_todo_list_item(text)
		self.todo_entry.clear()
		self.todo_list.setCurrentRow(self.todo_list.count() - 1)
		self._refresh_todo_controls()

	def _edit_todo_item(self, item: QListWidgetItem):
		if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
			self.todo_list.editItem(item)

	def remove_selected_todo_item(self):
		item = self._selected_todo_item()
		if item is None:
			return
		self.todo_list.takeItem(self.todo_list.row(item))
		self._ensure_todo_placeholder()
		self._refresh_todo_controls()

	def _todo_values(self) -> List[Dict[str, object]]:
		values: List[Dict[str, object]] = []
		for index in range(self.todo_list.count()):
			item = self.todo_list.item(index)
			if not item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
				continue
			values.append({
				'id': item.data(Qt.ItemDataRole.UserRole),
				'text': item.text().strip(),
				'completed': item.checkState() == Qt.CheckState.Checked,
			})
		return values

	def _supports_subcard_management(self) -> bool:
		return self.card is not None and not self.card.parent_id

	def _set_attachment_drop_active(self, active: bool):
		border_color = '#3e7a5e' if active else '#dcc7a7'
		background = '#eef7f0' if active else '#fff9f0'
		self.attachment_drop_frame.setStyleSheet(
			f"""
			QFrame#AttachmentDropFrame {{
				background: {background};
				border: 1px solid {border_color};
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

	def _note_preview(self, text: str, limit: int = 120) -> str:
		single_line = ' '.join((text or '').split())
		if not single_line:
			return '(empty note)'
		if len(single_line) <= limit:
			return single_line
		return single_line[: limit - 3] + '...'

	def refresh_notes_list(self, selected_note_id: Optional[str] = None):
		if not hasattr(self, 'notes_list') or self.card is None:
			return
		self.notes_list.clear()
		notes = sorted(self.card.notes, key=lambda note: note.created_at, reverse=True)
		if not notes:
			placeholder = QListWidgetItem('No notes added yet.')
			placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
			placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.notes_list.addItem(placeholder)
			self._refresh_note_controls()
			return
		for note in notes:
			created_label = note.created_at.strftime('%Y-%m-%d %H:%M')
			item = QListWidgetItem(f'{created_label}\n{self._note_preview(note.text)}')
			item.setData(Qt.ItemDataRole.UserRole, note.id)
			item.setToolTip(note.text)
			self.notes_list.addItem(item)
			if selected_note_id and note.id == selected_note_id:
				self.notes_list.setCurrentItem(item)
		self._refresh_note_controls()

	def _selected_note_id(self) -> Optional[str]:
		if not hasattr(self, 'notes_list'):
			return None
		item = self.notes_list.currentItem()
		if item is None:
			return None
		return item.data(Qt.ItemDataRole.UserRole)

	def _selected_note(self):
		note_id = self._selected_note_id()
		if not note_id or self.card is None:
			return None
		for note in self.card.notes:
			if note.id == note_id:
				return note
		return None

	def _refresh_note_controls(self):
		if not hasattr(self, 'notes_list'):
			return
		editable = self.card is not None and not self.board.is_read_only()
		has_text = bool(self.note_entry.toPlainText().strip())
		has_selection = self._selected_note() is not None
		self.note_entry.setEnabled(editable)
		self.add_note_button.setEnabled(editable and has_text)
		self.add_note_button.setText('Update Note' if self.editing_note_id else 'Add Note')
		self.edit_note_button.setEnabled(editable and has_selection)
		self.clear_note_button.setEnabled(editable and (has_text or self.editing_note_id is not None))
		self.delete_note_button.setEnabled(editable and has_selection)

	def clear_note_editor(self):
		if not hasattr(self, 'note_entry'):
			return
		self.editing_note_id = None
		self.note_entry.clear()
		if hasattr(self, 'notes_list'):
			self.notes_list.clearSelection()
		self._refresh_note_controls()

	def edit_selected_note(self):
		note = self._selected_note()
		if note is None:
			QMessageBox.information(self, 'No Note Selected', 'Select a note first.')
			return
		self.editing_note_id = note.id
		self.note_entry.setPlainText(note.text)
		self.note_entry.setFocus(Qt.FocusReason.TabFocusReason)
		self._refresh_note_controls()

	def save_note(self):
		if self.card is None:
			QMessageBox.information(self, 'Create Card First', 'Save the card before adding notes.')
			return
		if self.board.is_read_only():
			QMessageBox.warning(self, 'Read Only Board', self.board.get_read_only_message())
			return
		text = self.note_entry.toPlainText().strip()
		if not text:
			return
		if self.editing_note_id:
			note = self.board.edit_card_note(self.card.id, self.editing_note_id, text)
			if note is None:
				QMessageBox.warning(self, 'Edit Note', 'Unable to update the selected note.')
				return
		else:
			note = self.board.add_card_note(self.card.id, text)
			if note is None:
				QMessageBox.warning(self, 'Add Note', 'Unable to add the note to this card.')
				return
		self.card = self.board.find_card(self.card.id)
		self.did_mutate_board = True
		self.editing_note_id = None
		self.note_entry.clear()
		self.refresh_notes_list(selected_note_id=note.id)

	def delete_selected_note(self):
		if self.card is None:
			return
		if self.board.is_read_only():
			QMessageBox.warning(self, 'Read Only Board', self.board.get_read_only_message())
			return
		note = self._selected_note()
		if note is None:
			QMessageBox.information(self, 'No Note Selected', 'Select a note first.')
			return
		result = QMessageBox.question(
			self,
			'Remove Note',
			'Remove the selected note from this card?',
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result != QMessageBox.StandardButton.Yes:
			return
		if not self.board.delete_card_note(self.card.id, note.id):
			QMessageBox.warning(self, 'Remove Note', 'Unable to remove the selected note.')
			return
		self.card = self.board.find_card(self.card.id)
		self.did_mutate_board = True
		self.clear_note_editor()
		self.refresh_notes_list()

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
		self.edit_subcard_button.setEnabled(editable and bool(self.subcards))
		self.delete_subcard_button.setEnabled(editable and bool(self.subcards))
		if hasattr(self, 'subcards_summary_label'):
			count = len(self.subcards)
			self.subcards_summary_label.setText(f'{count} subcard' + ('' if count == 1 else 's'))
			completed = sum(1 for subcard in self.subcards if self.board.is_card_done(subcard))
			self.subcards_progress_label.setText(f'{completed} done')
		if not self.subcards:
			placeholder = QListWidgetItem('No subcards yet.')
			placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
			placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.subcards_list.addItem(placeholder)
			return
		for subcard in self.subcards:
			item = QListWidgetItem(subcard.title)
			item.setData(Qt.ItemDataRole.UserRole, subcard.id)
			row_widget = self._create_subcard_row_widget(subcard)
			row_container = SubcardListItemContainer(row_widget)
			item.setSizeHint(row_container.sizeHint())
			self.subcards_list.addItem(item)
			self.subcards_list.setItemWidget(item, row_container)
		self._refresh_subcard_row_styles()
		QTimer.singleShot(0, self.subcards_list.refresh_item_sizes)

	def _subcard_priority_color(self, priority: Priority) -> str:
		palette = {
			Priority.LOW: '#6a8c63',
			Priority.MEDIUM: '#8f6b2a',
			Priority.HIGH: '#b8612a',
			Priority.CRITICAL: '#a63c30',
		}
		return palette.get(priority, '#7d5b3d')

	def _create_subcard_row_widget(self, subcard) -> QWidget:
		row = SubcardRowWidget()
		row.setObjectName('SubcardRow')
		row.setProperty('accentColor', self._subcard_priority_color(subcard.priority))
		layout = QVBoxLayout(row)
		layout.setContentsMargins(12, 10, 12, 10)
		layout.setSpacing(6)

		header = QWidget()
		header_layout = QVBoxLayout(header)
		header_layout.setContentsMargins(0, 1, 0, 3)
		header_layout.setSpacing(6)

		badge_row = QWidget()
		badge_row_layout = QHBoxLayout(badge_row)
		badge_row_layout.setContentsMargins(0, 0, 0, 0)
		badge_row_layout.setSpacing(8)

		status_badge = QLabel('Done' if self.board.is_card_done(subcard) else 'Open')
		status_badge.setObjectName('SubcardStatusBadge')
		status_color = '#3e7a5e' if self.board.is_card_done(subcard) else self._subcard_priority_color(subcard.priority)
		status_badge.setStyleSheet(
			f'background: {resolve_hex_color(status_color, "#7d5b3d")}20; color: {status_color}; border: 1px solid {status_color}33; border-radius: 9px; padding: 3px 8px; font-size: 7pt; font-weight: 700;'
		)
		badge_row_layout.addWidget(status_badge)
		badge_row_layout.addStretch(1)

		priority_badge = QLabel(priority_label(subcard.priority).title())
		priority_badge.setStyleSheet(
			f'background: rgba(79, 65, 52, 0.06); color: {self._subcard_priority_color(subcard.priority)}; border: 1px solid rgba(79, 65, 52, 0.10); border-radius: 9px; padding: 3px 8px; font-size: 7pt; font-weight: 700;'
		)
		badge_row_layout.addWidget(priority_badge)
		header_layout.addWidget(badge_row)

		title_label = QLabel(subcard.title)
		title_label.setObjectName('SubcardRowTitle')
		title_label.setWordWrap(True)
		title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
		title_label.setStyleSheet('color: #2d241c; font-size: 9pt; font-weight: 700;')
		header_layout.addWidget(title_label)
		layout.addWidget(header)

		meta_parts = [self.board.get_card_location_label(subcard)]
		if subcard.assignee:
			meta_parts.append(f'@{subcard.assignee}')
		if subcard.project:
			meta_parts.append(subcard.project)
		meta_label = QLabel('  •  '.join(meta_parts))
		meta_label.setObjectName('SubcardRowMeta')
		meta_label.setWordWrap(True)
		meta_label.setStyleSheet('color: #6b5a4a; font-size: 7.5pt; font-weight: 600;')
		layout.addWidget(meta_label)

		if subcard.description:
			description_text = subcard.description[:120]
			if len(subcard.description) > 120:
				description_text += '...'
			description_label = QLabel(description_text)
			description_label.setWordWrap(True)
			description_label.setStyleSheet('color: #756658; font-size: 7.5pt;')
			layout.addWidget(description_label)

		return row

	def _apply_subcard_row_style(self, row_widget: QWidget, selected: bool):
		accent = row_widget.property('accentColor') or '#7d5b3d'
		background = '#f5e4cb' if selected else '#fffdf9'
		border = accent if selected else '#dec7a5'
		row_widget.setStyleSheet(
			f'QFrame#SubcardRow {{ background: {background}; border: 1px solid {border}; border-left: 4px solid {accent}; border-radius: 12px; }}'
		)

	def _refresh_subcard_row_styles(self):
		if not hasattr(self, 'subcards_list'):
			return
		for index in range(self.subcards_list.count()):
			item = self.subcards_list.item(index)
			widget = self.subcards_list.itemWidget(item)
			if widget is None:
				continue
			row_widget = widget.row_widget if isinstance(widget, SubcardListItemContainer) else widget
			self._apply_subcard_row_style(row_widget, item.isSelected())

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
		dialog = self._dialog_facade().CardDialog(
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
				values['todo_items'],
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
		dialog = self._dialog_facade().CardDialog(self.board, card=subcard, parent=self)
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
			todo_items=values['todo_items'],
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
			'todo_items': self._todo_values(),
			'color': self.color_field.color(),
			'card_type_id': self.card_type_combo.currentData(),
			'start_date': self.start_date.value(),
			'end_date': self.end_date.value(),
		}

	def accept(self):
		if not self.title_edit.text().strip():
			QMessageBox.warning(self, 'Missing Title', 'Card title is required.')
			return
		if any(not todo_item['text'] for todo_item in self._todo_values()):
			QMessageBox.warning(self, 'Checklist Item Required', 'Checklist items cannot be blank.')
			return
		super().accept()


__all__ = [
	'AttachmentDropFrame',
	'CARD_DIALOG_SECTION_FRAME_STYLESHEET',
	'CardDialog',
]