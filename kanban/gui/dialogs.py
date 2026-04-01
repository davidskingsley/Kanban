## @file
#  @brief Dialogs used by the PySide6 multi-board GUI.
"""Dialog layer for the PySide6 GUI."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from PySide6.QtCore import QDate, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
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
	QHeaderView,
	QLabel,
	QLineEdit,
	QListWidgetItem,
	QMessageBox,
	QPushButton,
	QSizePolicy,
	QStyle,
	QStyledItemDelegate,
	QTableWidgetItem,
	QTextBrowser,
	QVBoxLayout,
	QWidget,
)
from ..board import KanbanBoard
from ..models import CardType, CustomColumn, Priority, Project
from ..storage import JSON_STORAGE_BACKEND, SQLITE_STORAGE_BACKEND
from .common import (
	ColorSelectionField,
	PropagatingListWidget,
	PropagatingTableWidget,
	PropagatingTextEdit,
	add_dialog_footer,
	build_dialog_shell,
	choose_existing_directory_dialog,
	choose_open_files_dialog,
	column_label,
	column_target_value,
	configure_form_layout,
	create_dialog_hint_label,
	create_dialog_section_label,
	create_project_name_combo,
	due_state_colors,
	due_state_label,
	file_paths_from_mime_data,
	open_path_with_default_app,
	parse_tags,
	priority_label,
	resolve_hex_color,
)


class DueTimelineDelegate(QStyledItemDelegate):
	"""Paint a gantt-style schedule bar inside the due-date table."""

	def __init__(self, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.range_start = date.today() - timedelta(days=3)
		self.range_end = date.today() + timedelta(days=10)

	def set_range(self, start_date: date, end_date: date):
		self.range_start = start_date
		self.range_end = end_date

	def paint(self, painter: QPainter, option, index):
		payload = index.data(Qt.ItemDataRole.UserRole) or {}
		painter.save()

		if option.state & QStyle.StateFlag.State_Selected:
			painter.fillRect(option.rect, option.palette.highlight())
		else:
			background = QColor('#fffdfa' if index.row() % 2 == 0 else '#fbf3e8')
			painter.fillRect(option.rect, background)

		content_rect = QRectF(option.rect.adjusted(10, 10, -10, -10))
		if content_rect.width() <= 0 or content_rect.height() <= 0:
			painter.restore()
			return

		total_days = max(1, (self.range_end - self.range_start).days + 1)
		day_width = content_rect.width() / total_days
		today = date.today()

		for day_index in range(total_days):
			day = self.range_start + timedelta(days=day_index)
			left = content_rect.left() + (day_index * day_width)
			right = content_rect.left() + ((day_index + 1) * day_width)
			day_rect = QRectF(left, content_rect.top(), max(1.0, right - left), content_rect.height())
			if day.weekday() >= 5:
				painter.fillRect(day_rect, QColor(244, 236, 224, 165))
			if day == today:
				painter.setPen(QPen(QColor('#a63c30'), 2))
				marker_x = day_rect.left() + (day_rect.width() / 2)
				painter.drawLine(int(marker_x), int(content_rect.top()), int(marker_x), int(content_rect.bottom()))
			elif day_index > 0:
				painter.setPen(QPen(QColor('#eadfcd'), 1))
				painter.drawLine(int(day_rect.left()), int(content_rect.top()), int(day_rect.left()), int(content_rect.bottom()))

		painter.setPen(QPen(QColor('#d7c5ac'), 1))
		painter.drawRoundedRect(content_rect, 10, 10)

		start_date = payload.get('start_date')
		end_date = payload.get('end_date')
		state = str(payload.get('state') or '')
		label = str(payload.get('label') or '')

		if not start_date and not end_date:
			painter.setPen(QColor('#7a6c5f'))
			painter.drawText(content_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, 'No scheduled dates')
			painter.restore()
			return

		bar_start = start_date or end_date
		bar_end = end_date or start_date
		if bar_start is None:
			bar_start = today
		if bar_end is None:
			bar_end = bar_start
		if bar_end < bar_start:
			bar_start, bar_end = bar_end, bar_start

		bar_start = max(bar_start, self.range_start)
		bar_end = min(bar_end, self.range_end)
		start_offset = (bar_start - self.range_start).days
		end_offset = (bar_end - self.range_start).days + 1
		bar_left = content_rect.left() + (start_offset * day_width) + 2
		bar_right = content_rect.left() + (end_offset * day_width) - 2
		bar_width = max(10.0, bar_right - bar_left)
		bar_rect = QRectF(bar_left, content_rect.top() + 8, bar_width, max(18.0, content_rect.height() - 16))

		bar_background, bar_foreground = due_state_colors(state)
		painter.setBrush(QColor(bar_background).darker(104))
		painter.setPen(QPen(QColor(bar_foreground).darker(105), 1))
		if start_date and end_date and start_date != end_date:
			painter.drawRoundedRect(bar_rect, 8, 8)
		else:
			center_x = bar_rect.center().x()
			milestone = QRectF(center_x - 7, bar_rect.center().y() - 7, 14, 14)
			painter.drawEllipse(milestone)

		painter.setPen(QColor(bar_foreground))
		text_rect = bar_rect.adjusted(8, 0, -8, 0)
		if start_date and end_date and start_date != end_date and text_rect.width() > 72:
			painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
		else:
			trailing_rect = QRectF(min(content_rect.right() - 120, bar_rect.right() + 8), content_rect.top(), 120, content_rect.height())
			painter.drawText(trailing_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)

		painter.restore()


class SubcardsListWidget(PropagatingListWidget):
	"""List widget that keeps custom subcard rows sized to the current viewport width."""

	def __init__(self, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		self.verticalScrollBar().setSingleStep(20)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self.refresh_item_sizes()

	def refresh_item_sizes(self):
		available_width = self.viewport().width() - 12
		if available_width <= 0:
			return
		for index in range(self.count()):
			item = self.item(index)
			widget = self.itemWidget(item)
			if widget is None:
				continue
			if isinstance(widget, SubcardListItemContainer):
				widget.apply_width(available_width)
				widget.updateGeometry()
				height = widget.heightForWidth(available_width)
			else:
				widget.setFixedWidth(available_width)
				widget.updateGeometry()
				height = widget.heightForWidth(available_width) if widget.hasHeightForWidth() else widget.sizeHint().height()
			widget.setMinimumHeight(height)
			item.setSizeHint(QSize(available_width, height))


class SubcardListItemContainer(QWidget):
	"""Full-width row container that adds bottom-only spacing for subcards."""

	BOTTOM_SPACING = 5

	def __init__(self, row_widget: SubcardRowWidget, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.row_widget = row_widget
		self._layout = QHBoxLayout(self)
		self._layout.setContentsMargins(0, 0, 0, self.BOTTOM_SPACING)
		self._layout.setSpacing(0)
		self._layout.addWidget(row_widget)

	def apply_width(self, row_width: int):
		margins = self._layout.contentsMargins()
		content_width = max(120, row_width - margins.left() - margins.right())
		self.setFixedWidth(row_width)
		self.row_widget.setFixedWidth(content_width)
		self.row_widget.updateGeometry()

	def hasHeightForWidth(self) -> bool:
		return True

	def heightForWidth(self, width: int) -> int:
		margins = self._layout.contentsMargins()
		content_width = max(120, width - margins.left() - margins.right())
		row_height = self.row_widget.heightForWidth(content_width) if self.row_widget.hasHeightForWidth() else self.row_widget.sizeHint().height()
		return row_height + margins.top() + margins.bottom()

	def sizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else self.row_widget.sizeHint().width()
		return QSize(width, self.heightForWidth(width))

	def minimumSizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else self.row_widget.minimumSizeHint().width()
		return QSize(width, self.heightForWidth(width))


class SubcardRowWidget(QFrame):
	"""Custom row widget for the subcards panel that supports proper height-for-width sizing."""

	def hasHeightForWidth(self) -> bool:
		return True

	def heightForWidth(self, width: int) -> int:
		layout = self.layout()
		if layout is None:
			return super().sizeHint().height()
		return max(layout.totalHeightForWidth(max(width, 180)), super().minimumSizeHint().height())

	def sizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else super().sizeHint().width()
		return QSize(width, self.heightForWidth(width))

	def minimumSizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else super().minimumSizeHint().width()
		return QSize(width, self.heightForWidth(width))


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


class AboutDialog(QDialog):
	"""Application help and version dialog."""

	def __init__(self, parent: Optional[QWidget] = None, version: str = '2.0'):
		super().__init__(parent)
		self.setWindowTitle('About Kanban')
		self.resize(700, 620)

		content_layout = build_dialog_shell(
			self,
			'About Kanban',
			'Multi-board planning for day-to-day work. This dialog covers the current release, the main workflow, and the keyboard shortcuts that matter most.',
		)

		content_layout.addWidget(create_dialog_section_label('Version'))
		self.version_label = QLabel(f'Kanban Version {version}')
		self.version_label.setObjectName('AboutVersion')
		self.version_label.setStyleSheet(
			'background: rgba(125, 59, 20, 0.10); color: #6f3d1c; border: 1px solid rgba(125, 59, 20, 0.18); border-radius: 12px; padding: 8px 12px; font-size: 10pt; font-weight: 700;'
		)
		content_layout.addWidget(self.version_label)

		content_layout.addWidget(create_dialog_section_label('How To Use'))
		self.usage_label = QLabel(
			'<b>1.</b> Create or switch to a board, then shape the workflow with custom columns.<br>'
			'<b>2.</b> Add cards into active columns and use selection to edit, move, or delete the current card.<br>'
			'<b>3.</b> Use the toolbar filters and search field to narrow what is visible on the board.<br>'
			'<b>4.</b> Open card details to manage descriptions, dates, tags, checklists, attachments, and subcards.<br>'
			'<b>5.</b> Use the Due Date View and Board Statistics screens to review progress and deadlines.'
		)
		self.usage_label.setObjectName('AboutUsage')
		self.usage_label.setWordWrap(True)
		self.usage_label.setTextFormat(Qt.TextFormat.RichText)
		self.usage_label.setStyleSheet('color: #4f4134;')
		content_layout.addWidget(self.usage_label)

		content_layout.addWidget(create_dialog_section_label('Keyboard Shortcuts'))
		self.shortcuts_label = QLabel(
			'<b>Ctrl+N</b> New board<br>'
			'<b>Ctrl+Shift+O</b> Load board from folder<br>'
			'<b>Ctrl+Shift+S</b> Export current board<br>'
			'<b>Ctrl+O</b> Switch board<br>'
			'<b>F5</b> Refresh boards<br>'
			'<b>Ctrl+R</b> Rename current board<br>'
			'<b>Ctrl+Shift+D</b> Delete current board<br>'
			'<b>Ctrl+Shift+T</b> Due Date View<br>'
			'<b>Ctrl+I</b> Board statistics<br>'
			'<b>Ctrl+Shift+N</b> New card<br>'
			'<b>Ctrl+Shift+J</b> Add subcard to the selected card<br>'
			'<b>Ctrl+E</b> Edit selected card<br>'
			'<b>Ctrl+M</b> Move selected card<br>'
			'<b>Ctrl+D</b> Delete selected card<br>'
			'<b>Ctrl+Shift+K</b> Archive done cards<br>'
			'<b>Ctrl+Shift+C</b> New column<br>'
			'<b>Ctrl+Alt+R</b> Edit selected column<br>'
			'<b>Ctrl+Alt+O</b> Reorder columns<br>'
			'<b>Ctrl+Z</b> Undo current board action<br>'
			'<b>Ctrl+Y</b> Redo current board action<br>'
			'<b>Ctrl+Shift+Z</b> Undo board-management action<br>'
			'<b>Ctrl+Shift+Y</b> Redo board-management action<br>'
			'<b>F1</b> About Kanban'
		)
		self.shortcuts_label.setObjectName('AboutShortcuts')
		self.shortcuts_label.setWordWrap(True)
		self.shortcuts_label.setTextFormat(Qt.TextFormat.RichText)
		self.shortcuts_label.setStyleSheet('color: #4f4134;')
		content_layout.addWidget(self.shortcuts_label)

		content_layout.addWidget(create_dialog_hint_label('Tip: click a column title or card first to make the relevant card and column actions available.'))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


class ArchivedCardsDialog(QDialog):

	def _restore_selected_card(self):
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self, 'Restore Archived Card', 'Select an archived card first.')
			return
		# Extra safety: double-check card is archived and not deleted
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
		self.shortcuts_label = QLabel(
			'<b>Ctrl+N</b> New board<br>'
			'<b>Ctrl+Shift+O</b> Load board from folder<br>'
			'<b>Ctrl+Shift+S</b> Export current board<br>'
			'<b>Ctrl+O</b> Switch board<br>'
			'<b>F5</b> Refresh boards<br>'
			'<b>Ctrl+R</b> Rename current board<br>'
			'<b>Ctrl+Shift+D</b> Delete current board<br>'
			'<b>Ctrl+Shift+T</b> Due Date View<br>'
			'<b>Ctrl+I</b> Board statistics<br>'
			'<b>Ctrl+Shift+N</b> New card<br>'
			'<b>Ctrl+Shift+J</b> Add subcard to the selected card<br>'
			'<b>Ctrl+E</b> Edit selected card<br>'
			'<b>Ctrl+M</b> Move selected card<br>'
			'<b>Ctrl+D</b> Delete selected card<br>'
			'<b>Ctrl+Shift+K</b> Archive done cards<br>'
			'<b>Ctrl+Shift+C</b> New column<br>'
			'<b>Ctrl+Alt+R</b> Edit selected column<br>'
			'<b>Ctrl+Alt+O</b> Reorder columns<br>'
			'<b>Ctrl+Z</b> Undo current board action<br>'
			'<b>Ctrl+Y</b> Redo current board action<br>'
			'<b>Ctrl+Shift+Z</b> Undo board-management action<br>'
			'<b>Ctrl+Shift+Y</b> Redo board-management action<br>'
			'<b>F1</b> About Kanban'
		)
		self.shortcuts_label.setObjectName('AboutShortcuts')
		self.shortcuts_label.setWordWrap(True)
		self.shortcuts_label.setTextFormat(Qt.TextFormat.RichText)
		self.shortcuts_label.setStyleSheet('color: #4f4134;')
		content_layout.addWidget(self.shortcuts_label)

		content_layout.addWidget(create_dialog_hint_label('Tip: click a column title or card first to make the relevant card and column actions available.'))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


def build_command_line_guide_html() -> str:
	"""Return the HTML shown in the command-line guide dialog."""
	return (
		'<h3 style="margin: 0 0 8px 0; color: #6f3d1c;">Start From The Project Folder</h3>'
		'<p style="margin: 0 0 10px 0;">Open a terminal in the Kanban project directory. Both direct Python and <b>uv</b> commands work. The GUI is the default launch mode, and the CLI is enabled with <b>--cli</b>.</p>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'python main.py\n'
		'python main.py --cli\n'
		'python main.py list-boards\n'
		'python main.py create-board --name "Automation" --storage-backend sqlite --switch\n'
		'python main.py create-card --board "Automation" --title "Ship release" --priority high\n'
		'python main.py --boards-dir C:\\Boards\\Kanban\n\n'
		'uv run python main.py\n'
		'uv run python main.py --cli\n'
		'uv run python main.py list-boards\n'
		'uv run python main.py create-board --name "Automation" --storage-backend sqlite --switch\n'
		'uv run python main.py --boards-dir C:\\Boards\\Kanban\n'
		'</pre>'
		'<p style="margin: 10px 0 0 0;">Run <b>python main.py --help</b> or <b>uv run python main.py --help</b> to see the supported command-line options.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Top-Level CLI Options</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>--cli</b>: start the interactive multi-board command-line interface instead of the GUI.</li>'
		'<li><b>--boards-dir DIR</b>: use a different board storage directory for the session. This is useful when keeping work, demo, or archived boards in separate locations.</li>'
		'<li><b>--lock-action ACTION</b>: choose how direct commands respond to locked boards: <b>cancel</b>, <b>open_read_only</b>, or <b>delete_lock</b>.</li>'
		'<li><b>--help</b>: print the launcher help and exit.</li>'
		'</ul>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Direct-Action CLI Workflow</h3>'
		'<p style="margin: 0 0 10px 0;">Direct commands let one action run immediately without prompts. Use them for scripts, Task Scheduler jobs, or shell automation. Each action is its own subcommand.</p>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>list-boards</b>: print the registered boards, backends, and current-board marker.</li>'
		'<li><b>create-board</b>, <b>switch-board</b>, <b>rename-board</b>, <b>delete-board</b>: automate board management. Destructive commands require <b>--force</b>.</li>'
		'<li><b>convert-board</b>: switch an existing board between JSON and SQLite storage.</li>'
		'<li><b>show-board</b>, <b>create-card</b>, <b>edit-card</b>, <b>add-subcard</b>, <b>move-card</b>, <b>delete-card</b>, archive commands, and checklist item commands: automate current-board work without opening the menu CLI.</li>'
		'<li><b>search-cards</b>, <b>filter-priority</b>, <b>filter-assignee</b>, <b>add-tag</b>, and <b>card-details</b>: retrieve board information directly from scripts and targeted automation.</li>'
		'<li><b>create-column</b>, <b>rename-column</b>, <b>delete-column</b>, <b>reorder-columns</b>, <b>change-column-color</b>, <b>edit-column-flags</b>: automate column maintenance.</li>'
		'<li><b>create-card-type</b>, <b>edit-card-type</b>, <b>delete-card-type</b>, <b>create-backup</b>, <b>cleanup-orphaned-attachments</b>, <b>undo-current-board</b>, <b>redo-current-board</b>: cover the board-level maintenance actions.</li>'
		'</ul>'
		'<p style="margin: 10px 0 0 0;">Run <b>python main.py &lt;direct-command&gt; --help</b> to see the exact flags for one automation action.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Multi-Board CLI Workflow</h3>'
		'<p style="margin: 0 0 10px 0;">The first menu manages boards. If no boards exist, the CLI immediately prompts you to create one. When boards exist, the main menu exposes these actions:</p>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>1. Open current board</b>: enter the board-level card and column manager.</li>'
		'<li><b>2. Switch board</b>: change the active board.</li>'
		'<li><b>3. Create new board</b>: choose a name, optional description, storage backend, and target folder.</li>'
		'<li><b>4. Convert board backend</b>: switch a board between JSON and SQLite storage.</li>'
		'<li><b>5. Rename board</b> and <b>6. Delete board</b>: maintain existing boards.</li>'
		'<li><b>7. Board statistics</b>: review totals across every registered board.</li>'
		'<li><b>8. Export current board</b> and <b>9. Export all boards</b>: write portable board data for backup or migration.</li>'
		'<li><b>10. Import boards</b>: bring exported boards back into the manager.</li>'
		'<li><b>11. Load board from folder</b>: register boards stored outside the default directory.</li>'
		'<li><b>12. Undo</b> and <b>13. Redo</b>: reverse recent board-management operations.</li>'
		'</ul>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Creating Boards From The CLI</h3>'
		'<p style="margin: 0 0 10px 0;">When you create a board, the CLI asks which backend to use. Choose <b>1</b> for the current JSON file backend or <b>2</b> for the SQLite3 backend. It then asks for a storage folder. If you keep the default folder, the board is created under the application boards directory. If you choose another folder, the board is still registered in the manager and can be reopened later.</p>'
		'<p style="margin: 0 0 10px 0;">Load-board-from-folder works with a folder that contains <b>boards_metadata.json</b> or standalone board files. JSON board files and SQLite board files are both supported.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Board-Level CLI Workflow</h3>'
		'<p style="margin: 0 0 10px 0;">After choosing <b>Open current board</b>, the terminal switches to the per-board menu. This view prints the board state, current card statistics, and these actions:</p>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>Cards</b>: create, edit, move, delete, search, filter by priority, filter by assignee, add tags, manage checklists, view card details, archive done cards, manage archived cards, and add subcards.</li>'
		'<li><b>Columns</b>: create, rename, delete, reorder, recolor, edit flags, and inspect the current column setup.</li>'
		'<li><b>Card types</b>: view, create, edit, and delete reusable card type presets.</li>'
		'<li><b>Maintenance</b>: create a backup, clean orphaned attachment files, undo, and redo.</li>'
		'</ul>'
		'<p style="margin: 10px 0 0 0;">When the CLI requests dates, use <b>YYYY-MM-DD</b>. If a board is locked by another process, the terminal offers three responses: open read only, delete the lock, or cancel opening the board.</p>'
		'<p style="margin: 10px 0 0 0;">Checklist input accepts pipe-delimited items in the menu CLI, and direct commands can target individual checklist items by the ids printed in <b>card-details</b>.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Practical Notes</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li>Backups, imports, exports, and board loading work with both JSON and SQLite-backed boards.</li>'
		'<li>The CLI is useful when running on a machine without PySide6 or when you want to manage boards entirely from a terminal session.</li>'
		'<li>Press <b>Ctrl+C</b> to leave the CLI safely. The launcher handles this and exits cleanly.</li>'
		'</ul>'
	)


def build_direct_action_cli_options_html() -> str:
	"""Return the HTML shown in the direct-action CLI options dialog."""
	return (
		'<h3 style="margin: 0 0 8px 0; color: #6f3d1c;">Direct-Action CLI Options</h3>'
		'<p style="margin: 0 0 10px 0;">These commands run one action immediately without entering the interactive CLI. Use them for scripts, scheduled jobs, and automation. Run <b>python main.py &lt;command&gt; --help</b> to inspect the exact flag set for one command.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Global Options</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>--boards-dir DIR</b>: use a different board registry directory for the session.</li>'
		'<li><b>--lock-action ACTION</b>: choose <b>cancel</b>, <b>open_read_only</b>, or <b>delete_lock</b> when a direct command hits a locked board.</li>'
		'</ul>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Board Management Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'list-boards\n'
		'create-board --name NAME [--description TEXT] [--storage-backend json|sqlite] [--target-directory DIR] [--switch]\n'
		'switch-board --board BOARD\n'
		'rename-board --board BOARD --new-name NAME\n'
		'convert-board --board BOARD --storage-backend json|sqlite [--target-directory DIR]\n'
		'delete-board --board BOARD --force\n'
		'board-stats [--board BOARD]\n'
		'export-board [--board BOARD] --output FILE\n'
		'export-all-boards --output FILE\n'
		'import-boards --input FILE --force\n'
		'load-board-from-folder --path PATH [--board BOARD] [--name NAME] [--description TEXT] [--no-switch]\n'
		'undo-board-management\n'
		'redo-board-management\n'
		'show-board [--board BOARD]\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Card Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'create-card [--board BOARD] --title TITLE [--description TEXT] [--priority low|medium|high|critical] [--column COLUMN] [--project NAME] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--color VALUE] [--card-type TYPE] [--assignee NAME] [--tags tag1,tag2] [--todo TEXT]\n'
		'edit-card [--board BOARD] --card CARD [--title TITLE] [--description TEXT | --clear-description] [--priority low|medium|high|critical] [--assignee NAME | --clear-assignee] [--project NAME | --clear-project] [--start-date YYYY-MM-DD | --clear-start-date] [--end-date YYYY-MM-DD | --clear-end-date] [--color VALUE | --clear-color] [--card-type TYPE] [--tags tag1,tag2 | --clear-tags] [--todo TEXT | --clear-todo-list]\n'
		'add-subcard [--board BOARD] --parent-card CARD --title TITLE [--description TEXT] [--priority low|medium|high|critical] [--project NAME] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--color VALUE] [--card-type TYPE] [--assignee NAME] [--tags tag1,tag2] [--todo TEXT]\n'
		'move-card [--board BOARD] --card CARD --column COLUMN [--target-card CARD] [--insert-after]\n'
		'delete-card [--board BOARD] --card CARD --force\n'
		'search-cards [--board BOARD] --query TEXT\n'
		'filter-priority [--board BOARD] --priority low|medium|high|critical\n'
		'filter-assignee [--board BOARD] --assignee NAME\n'
		'add-tag [--board BOARD] --card CARD --tag TAG\n'
		'add-todo-item [--board BOARD] --card CARD --text TEXT [--completed]\n'
		'check-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'uncheck-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'toggle-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'remove-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'card-details [--board BOARD] --card CARD\n'
		'archive-done-cards [--board BOARD] --force\n'
		'list-archived-cards [--board BOARD]\n'
		'restore-archived-card [--board BOARD] --card CARD\n'
		'delete-archived-card [--board BOARD] --card CARD --force\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Column Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'create-column [--board BOARD] --name NAME [--position INDEX] [--color VALUE] [--completed] [--can-add-card]\n'
		'rename-column [--board BOARD] --column COLUMN --new-name NAME\n'
		'delete-column [--board BOARD] --column COLUMN [--move-cards-to COLUMN]\n'
		'reorder-columns [--board BOARD] --order COLUMN1 COLUMN2 COLUMN3\n'
		'change-column-color [--board BOARD] --column COLUMN --color VALUE\n'
		'edit-column-flags [--board BOARD] --column COLUMN [--completed | --not-completed] [--can-add-card | --cannot-add-card]\n'
		'list-columns [--board BOARD]\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Card Type And Maintenance Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'list-card-types [--board BOARD]\n'
		'create-card-type [--board BOARD] --name NAME [--description TEXT] [--default-project NAME] [--default-color VALUE]\n'
		'edit-card-type [--board BOARD] --card-type TYPE [--name NAME] [--description TEXT | --clear-description] [--default-project NAME | --clear-default-project] [--default-color VALUE | --clear-default-color]\n'
		'delete-card-type [--board BOARD] --card-type TYPE [--delete-cards] [--replacement-card-type TYPE]\n'
		'create-backup [--board BOARD] [--output FILE]\n'
		'cleanup-orphaned-attachments [--board BOARD]\n'
		'undo-current-board [--board BOARD]\n'
		'redo-current-board [--board BOARD]\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Notes</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li>Use a board id or an exact board name anywhere a command expects <b>BOARD</b>.</li>'
		'<li>Use exact names or ids for cards, checklist items, columns, and card types when there is any ambiguity.</li>'
		'<li>Destructive commands require <b>--force</b> where shown.</li>'
		'<li>Date values use <b>YYYY-MM-DD</b>.</li>'
		'<li><b>card-details</b> prints checklist item ids so single-item checklist commands can target them exactly.</li>'
		'<li>The Help menu in the GUI includes this reference alongside the About and Command Line Guide dialogs.</li>'
		'</ul>'
	)


class CommandLineGuideDialog(QDialog):
	"""Dedicated dialog for command-line usage documentation."""

	def __init__(self, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.setWindowTitle('Kanban Command Line Guide')
		self.resize(760, 760)

		content_layout = build_dialog_shell(
			self,
			'Command Line Guide',
			'Detailed terminal usage for starting Kanban, managing multiple boards, and operating a board entirely from the command line.',
			scrollable=False,
		)

		self.command_line_help = QTextBrowser()
		self.command_line_help.setObjectName('CommandLineGuideBrowser')
		self.command_line_help.setReadOnly(True)
		self.command_line_help.setOpenExternalLinks(False)
		self.command_line_help.setMinimumHeight(0)
		self.command_line_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.command_line_help.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		self.command_line_help.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.command_line_help.verticalScrollBar().setSingleStep(20)
		self.command_line_help.setStyleSheet(
			'QTextBrowser#CommandLineGuideBrowser {'
			'background: #fffaf2; color: #4f4134; border: 1px solid #d8c6ab; border-radius: 12px; padding: 8px;'
			'}'
		)
		self.command_line_help.setHtml(build_command_line_guide_html())
		content_layout.addWidget(self.command_line_help)

		content_layout.addWidget(create_dialog_hint_label('Tip: use the board-level CLI when you want backup, cleanup, and batch management tasks without opening the GUI.'))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


class DirectActionCliOptionsDialog(QDialog):
	"""Dedicated dialog for direct-action CLI option documentation."""

	def __init__(self, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.setWindowTitle('Kanban Direct-Action CLI Options')
		self.resize(860, 780)

		content_layout = build_dialog_shell(
			self,
			'Direct-Action CLI Options',
			'Command-by-command reference for the non-interactive automation interface.',
			scrollable=False,
		)

		self.direct_action_help = QTextBrowser()
		self.direct_action_help.setObjectName('DirectActionCliOptionsBrowser')
		self.direct_action_help.setReadOnly(True)
		self.direct_action_help.setOpenExternalLinks(False)
		self.direct_action_help.setMinimumHeight(0)
		self.direct_action_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.direct_action_help.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		self.direct_action_help.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.direct_action_help.verticalScrollBar().setSingleStep(20)
		self.direct_action_help.setStyleSheet(
			'QTextBrowser#DirectActionCliOptionsBrowser {'
			'background: #fffaf2; color: #4f4134; border: 1px solid #d8c6ab; border-radius: 12px; padding: 8px;'
			'}'
		)
		self.direct_action_help.setHtml(build_direct_action_cli_options_html())
		content_layout.addWidget(self.direct_action_help)

		content_layout.addWidget(create_dialog_hint_label('Tip: start with main.py <command> --help when you need the live argparse output for one action.'))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


class DueDateViewDialog(QDialog):
	def __init__(
		self,
		board: KanbanBoard,
		board_name: str,
		parent: Optional[QWidget] = None,
		on_focus_card=None,
		on_edit_card=None,
	):
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
				(entry['start_date'] or entry['end_date']) is None,
				entry['start_date'] or entry['end_date'] or date.max,
				entry['end_date'] or entry['start_date'] or date.max,
				str(entry['title']).lower(),
			),
		)

	def _timeline_bounds(self, rows: List[Dict[str, object]]) -> tuple[date, date]:
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
				if column_index == 3:
					item.setBackground(QColor(row_background))
					item.setForeground(QColor(row_foreground))
				self.table.setItem(row_index, column_index, item)
			self.table.setRowHeight(row_index, 56)

		self.table.clearSelection()
		self.selected_card_id = None
		self.selected_column_id = None

	def _update_selection_state(self):
		row = self.table.currentRow()
		if row < 0:
			self.selected_card_id = None
			self.selected_column_id = None
			return
		payload = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) or {}
		self.selected_card_id = payload.get('card_id')
		self.selected_column_id = payload.get('column_id')

	def _edit_selected_card(self):
		self._activate_selected_row('edit')



class ArchivedCardsDialog(QDialog):
	def _delete_selected_card(self):
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

	def _restore_selected_card(self):
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self, 'Restore Archived Card', 'Select an archived card first.')
			return
		# Extra safety: double-check card is archived and not deleted
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

	def __init__(self, board: KanbanBoard, board_name: str, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.board = board
		self.board_name = board_name
		self.selected_card_id: Optional[str] = None
		self.setWindowTitle(f'Archived Cards - {board_name}')
		self.resize(980, 640)
		self._build_ui()
		self._populate_table()

	def _build_ui(self):
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
		return sorted(
			self.board.get_archived_cards(),
			key=lambda card: (
				card.archived_at or datetime.min,
				(card.title or '').lower(),
			),
			reverse=True,
		)

	def _populate_table(self):
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
		row = self.table.currentRow()
		payload = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 and self.table.item(row, 0) else {}
		self.selected_card_id = (payload or {}).get('card_id')
		has_selection = bool(self.selected_card_id)
		self.details_button.setEnabled(has_selection)
		can_mutate = has_selection and not self.board.is_read_only()
		self.restore_button.setEnabled(can_mutate)
		self.delete_button.setEnabled(can_mutate)

	def _selected_card(self):
		if not self.selected_card_id:
			return None
		card = self.board.find_card(self.selected_card_id, include_archived=True)
		if card is None or not card.is_archived():
			return None
		return card

	def _view_selected_card(self):
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self, 'Archived Cards', 'Select an archived card first.')
			return
		dialog = ArchivedCardInfoDialog(card, self.board.get_card_location_label(card), self)
		dialog.exec()

# ...existing code...

# Modern, styled dialog for archived card info
class ArchivedCardInfoDialog(QDialog):
	def __init__(self, card, column_label, parent=None):
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

	def _restore_selected_card(self):
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self, 'Restore Archived Card', 'Select an archived card first.')
			return
		# Extra safety: double-check card is archived and not deleted
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
				"when that column allows adding cards; otherwise they start in the left-most column. "
				"Nested subcards are not supported."
			)

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
		content_layout.addWidget(create_dialog_section_label('Checklist'))
		content_layout.addWidget(self.checklist_frame)
		content_layout.addWidget(create_dialog_section_label('Attachments'))
		content_layout.addWidget(self.attachment_drop_frame)
		self.refresh_todo_list()
		self._set_attachment_drop_active(False)
		self.refresh_attachments_list()

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
			self.subcards_progress_label.setText(f'{completed} done' + ('' if completed == 1 else ''))
		if not self.subcards:
			placeholder = QListWidgetItem('No subcards yet.')
			placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
			placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.subcards_list.addItem(placeholder)
			return
		for subcard in self.subcards:
			tick = '[x]' if self.board.is_card_done(subcard) else '[ ]'
			location = self.board.get_card_location_label(subcard)
			item = QListWidgetItem(f'{tick} {subcard.title} ({location})')
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
			description_label = QLabel(subcard.description[:120] + ('...' if len(subcard.description) > 120 else ''))
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
