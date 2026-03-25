## @file
#  @brief Shared PySide6 GUI helpers, styling, and utility widgets.
"""Shared helpers for the PySide6 GUI."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from typing import Dict, List, Optional

from PySide6.QtCore import QMimeData, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
	QAbstractItemView,
	QAbstractScrollArea,
	QApplication,
	QColorDialog,
	QComboBox,
	QDialog,
	QFileDialog,
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QScrollArea,
	QTableWidget,
	QTextEdit,
	QVBoxLayout,
	QWidget,
	QPushButton,
)

from ..board import KanbanBoard
from ..models import Priority, Status


WINDOW_STYLE = """
QMainWindow {
	background: #f5efe4;
}
QDialog, QMessageBox, QInputDialog {
	background: #fbf5ea;
}
QDialog#StandardDialog {
	background: #f6efe2;
}
QWidget {
	font-size: 10pt;
	color: #2d241c;
}
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
	color: #2d241c;
	background: transparent;
}
QDialog QLabel#DialogTitle {
	color: #2d241c;
	font-size: 16pt;
	font-weight: 700;
}
QDialog QLabel#DialogSubtitle {
	color: #6d5d4e;
	font-size: 10pt;
}
QDialog QLabel#DialogSectionLabel {
	color: #4f4134;
	font-size: 9pt;
	font-weight: 700;
	letter-spacing: 0.03em;
	text-transform: uppercase;
}
QDialog QLabel#DialogHint {
	color: #6d5d4e;
	font-size: 9pt;
}
QDialog QFrame#DialogHero,
QDialog QFrame#DialogCard {
	background: #fffaf2;
	border: 1px solid #d8c6ab;
	border-radius: 16px;
}
QDialog QFrame#DialogHero {
	background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
		stop:0 #f9efe1, stop:1 #efe3d1);
	border: 1px solid #d2ba97;
}
QDialog QGroupBox, QMessageBox QGroupBox, QInputDialog QGroupBox {
	background: #fbf5ea;
}
QScrollArea, QSplitter, QWidget#ColumnsContainer {
	background: #f5efe4;
	border: none;
}
QScrollArea > QWidget > QWidget {
	background: #f5efe4;
}
QToolBar#FilterToolbar {
	background: #efe4d3;
	border: 1px solid #d2be9d;
	border-radius: 12px;
	spacing: 6px;
	padding: 5px 8px;
}
QToolBar#FilterToolbar QLineEdit,
QToolBar#FilterToolbar QComboBox,
QToolBar#FilterToolbar QCheckBox {
	margin: 0 1px;
}
QLineEdit#CardSearchEntry {
	min-width: 180px;
	max-width: 220px;
	background: #fffdf9;
}
QComboBox#CardPriorityFilter,
QComboBox#CardAssigneeFilter,
QComboBox#CardTypeFilter,
QComboBox#CardTagFilter,
QComboBox#CardDueStateFilter,
QComboBox#DueFilterCombo {
	min-width: 108px;
	max-width: 126px;
	background: #fffdf9;
}
QPushButton#ClearCardFiltersButton {
	padding: 6px 10px;
	min-width: 58px;
}
QMenuBar {
	background: #eadfcf;
	color: #2d241c;
}
QMenuBar::item:selected {
	background: #d8c6ab;
}
QMenu {
	background: #fffaf2;
	border: 1px solid #d8c6ab;
}
QMenu::item:selected {
	background: #eadfcf;
}
QGroupBox {
	background: #fffaf2;
	border: 1px solid #d8c6ab;
	border-radius: 14px;
	margin-top: 18px;
	padding: 10px;
	font-weight: 700;
}
QGroupBox::title {
	subcontrol-origin: margin;
	left: 12px;
	padding: 0 6px;
}
QPushButton {
	background: #9c4d1f;
	color: #ffffff;
	border: 1px solid #7d3b14;
	border-radius: 10px;
	padding: 7px 14px;
}
QPushButton:hover {
	background: #b35d28;
}
QPushButton:pressed {
	background: #7d3b14;
}
QMessageBox QPushButton,
QInputDialog QPushButton {
	min-width: 90px;
}
QDialog QDialogButtonBox {
	border-top: 1px solid #eadcc6;
	padding-top: 10px;
}
QPushButton:disabled {
	background: #d9cfbf;
	color: #62574b;
	border-color: #c5baa9;
}
QLineEdit, QTextEdit, QComboBox, QDateEdit {
	background: #ffffff;
	color: #2d241c;
	border: 1px solid #ac9571;
	border-radius: 8px;
	padding: 7px 10px;
}
QTextEdit {
	min-height: 80px;
}
QComboBox {
	min-height: 18px;
}
QDateEdit {
	min-height: 18px;
}
QComboBox::drop-down {
	subcontrol-origin: padding;
	subcontrol-position: top right;
	width: 24px;
	border-left: 1px solid #d8c6ab;
	background: #f1e4d0;
	border-top-right-radius: 8px;
	border-bottom-right-radius: 8px;
}
QDateEdit::drop-down {
	subcontrol-origin: padding;
	subcontrol-position: top right;
	width: 24px;
	border-left: 1px solid #d8c6ab;
	background: #f1e4d0;
	border-top-right-radius: 8px;
	border-bottom-right-radius: 8px;
}
QComboBox::down-arrow {
	image: none;
	width: 0;
	height: 0;
	border-left: 5px solid transparent;
	border-right: 5px solid transparent;
	border-top: 7px solid #7d3b14;
	margin-right: 7px;
}
QDateEdit::down-arrow {
	image: none;
	width: 0;
	height: 0;
	border-left: 5px solid transparent;
	border-right: 5px solid transparent;
	border-top: 7px solid #7d3b14;
	margin-right: 7px;
}
QDateEdit:disabled {
	background: #efe4d3;
	color: #7a6c5f;
	border: 1px solid #cbb79a;
}
QDateEdit::drop-down:disabled {
	background: #e7d9c4;
	border-left: 1px solid #cfbea4;
}
QCalendarWidget QWidget {
	background: #fffaf2;
	color: #2d241c;
}
QCalendarWidget QToolButton {
	background: #efe4d3;
	color: #3f2f21;
	border: 1px solid #d5c3a6;
	border-radius: 8px;
	padding: 4px 8px;
}
QCalendarWidget QToolButton:hover {
	background: #e5d3bc;
}
QCalendarWidget QMenu {
	background: #fffaf2;
	color: #2d241c;
	border: 1px solid #d5c3a6;
}
QCalendarWidget QSpinBox {
	background: white;
	color: #2d241c;
	border: 1px solid #ac9571;
	border-radius: 6px;
	padding: 4px 6px;
}
QCalendarWidget QAbstractItemView:enabled {
	background: #fffdfa;
	color: #2d241c;
	selection-background-color: #9c4d1f;
	selection-color: white;
}
QCalendarWidget QTableView {
	alternate-background-color: #f8efe1;
	background: #fffdfa;
	color: #2d241c;
	outline: 0;
}
QCalendarWidget QHeaderView {
	background: #ead9c0;
}
QCalendarWidget QHeaderView::section {
	background: #ead9c0;
	color: #5a3417;
	border: none;
	border-bottom: 1px solid #d2ba97;
	padding: 6px 4px;
	font-weight: 700;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
	background: #f1e4d0;
	border-bottom: 1px solid #d5c3a6;
}
QComboBox QFrame,
QInputDialog QComboBox QFrame,
QComboBoxPrivateContainer,
QInputDialog QComboBoxPrivateContainer {
	background: #fffaf2;
	border: 1px solid #ac9571;
	border-radius: 10px;
	padding: 0;
}
QComboBox QAbstractItemView,
QInputDialog QComboBox QAbstractItemView {
	background: transparent;
	color: #2d241c;
	border: none;
	border-radius: 0;
	padding: 4px;
	selection-background-color: #7d3b14;
	selection-color: #ffffff;
}
QInputDialog QComboBox QAbstractItemView::item {
	min-height: 24px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
	border: 1px solid #8f4a1d;
}
QDialog QTableWidget,
QDialog QListWidget {
	background: #fffdfa;
	border: 1px solid #d5c3a6;
	border-radius: 12px;
	alternate-background-color: #fbf3e8;
}
QDialog QTableWidget::item,
QDialog QListWidget::item {
	padding: 8px 10px;
}
QDialog QHeaderView::section {
	background: #eadfcf;
	color: #3a2d22;
	border: none;
	border-bottom: 1px solid #d2b99a;
	padding: 10px 8px;
	font-weight: 700;
}
QCheckBox {
	color: #2d241c;
	spacing: 6px;
}
QCheckBox::indicator {
	width: 16px;
	height: 16px;
	border-radius: 4px;
	border: 1px solid #8f7654;
	background: #fffaf2;
}
QCheckBox::indicator:checked {
	background: #9c4d1f;
	border: 1px solid #7f3d16;
	border-radius: 4px;
}
"""


def priority_label(priority: Priority) -> str:
	return priority.value.replace('_', ' ').title()


def parse_tags(text: str) -> List[str]:
	tags: List[str] = []
	for raw_tag in (text or '').split(','):
		tag = raw_tag.strip().lstrip('#')
		if tag and tag not in tags:
			tags.append(tag)
	return tags


def create_project_name_combo(board: Optional[KanbanBoard], current_text: Optional[str] = None) -> QComboBox:
	combo = QComboBox()
	combo.setEditable(True)
	combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
	combo.addItem('')
	if board is not None:
		seen_names = set()
		for project in board.get_projects_ordered():
			key = project.name.strip().lower()
			if key in seen_names:
				continue
			seen_names.add(key)
			combo.addItem(project.name, project.id)
	combo.setCurrentIndex(0)
	combo.setEditText((current_text or '').strip())
	return combo


def color_to_rgb(color: str) -> tuple[float, float, float]:
	value = (color or '').strip().lstrip('#')
	if len(value) != 6:
		raise ValueError(f'Unsupported color value: {color!r}')
	return tuple(int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4))


def _linear_channel(channel: float) -> float:
	return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def contrast_ratio(color_a: str, color_b: str) -> float:
	def luminance(color: str) -> float:
		red, green, blue = color_to_rgb(color)
		return 0.2126 * _linear_channel(red) + 0.7152 * _linear_channel(green) + 0.0722 * _linear_channel(blue)

	light, dark = sorted((luminance(color_a), luminance(color_b)), reverse=True)
	return (light + 0.05) / (dark + 0.05)


def contrasting_text_color(background: str) -> str:
	dark_text = '#1f1812'
	light_text = '#ffffff'
	dark_contrast = contrast_ratio(background, dark_text)
	light_contrast = contrast_ratio(background, light_text)
	return dark_text if dark_contrast >= light_contrast else light_text


def resolve_hex_color(color: Optional[str], fallback: str) -> str:
	candidate = QColor((color or '').strip())
	if candidate.isValid():
		return candidate.name()
	return fallback


def secondary_text_color(background: str) -> str:
	return '#efe4d4' if contrasting_text_color(background) == '#ffffff' else '#66584b'


def rgba_color(color: str, alpha: float) -> str:
	qcolor = QColor(resolve_hex_color(color, '#000000'))
	clamped_alpha = max(0.0, min(alpha, 1.0))
	return f'rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {clamped_alpha:.3f})'


def priority_accent(priority: Priority) -> str:
	return {
		Priority.LOW: '#4f7f5c',
		Priority.MEDIUM: '#c67b2f',
		Priority.HIGH: '#c45f35',
		Priority.CRITICAL: '#a63c30',
	}.get(priority, '#c67b2f')


def schedule_summary(card) -> Optional[str]:
	if card.start_date and card.end_date:
		return f"{card.start_date.isoformat()} -> {card.end_date.isoformat()}"
	if card.start_date:
		return f"Starts {card.start_date.isoformat()}"
	if card.end_date:
		return f"Due {card.end_date.isoformat()}"
	return None


def due_state_label(board: KanbanBoard, card, today: Optional[date] = None) -> str:
	reference = today or date.today()
	if board.is_card_done(card):
		return 'Done'
	if card.end_date is None:
		return 'Start Date Only' if card.start_date else 'No Due Date'
	if card.end_date < reference:
		return 'Overdue'
	if card.end_date == reference:
		return 'Due Today'
	if (card.end_date - reference).days <= 7:
		return 'Due Soon'
	return 'Scheduled'


def display_date(value: Optional[date]) -> str:
	return value.isoformat() if value else '—'


def due_state_colors(state: str) -> tuple[str, str]:
	palette = {
		'Overdue': ('#f8ddd6', '#7f241b'),
		'Due Today': ('#f4e4c8', '#7a4b12'),
		'Due Soon': ('#e4efd9', '#456239'),
		'Scheduled': ('#e6ecf3', '#395067'),
		'Done': ('#dfe8dd', '#466040'),
		'Start Date Only': ('#ebe4f3', '#5b4a73'),
		'No Due Date': ('#ece7df', '#675a4d'),
	}
	return palette.get(state, ('#ece7df', '#675a4d'))


def clipped_description(text: str, limit: int = 180) -> str:
	compact = ' '.join((text or '').split())
	if len(compact) <= limit:
		return compact
	return compact[: limit - 3].rstrip() + '...'


def clipped_title(text: str, limit: int = 97) -> str:
	compact = ' '.join((text or '').split())
	if len(compact) <= limit:
		return compact
	return compact[: limit - 3].rstrip() + '...'


def wheel_delta(event: QWheelEvent) -> QPoint:
	return event.pixelDelta() if not event.pixelDelta().isNull() else event.angleDelta()


def scrollbar_can_consume_wheel(scroll_bar, delta: int) -> bool:
	if scroll_bar is None:
		return False
	if scroll_bar.maximum() <= scroll_bar.minimum():
		return False
	if delta > 0:
		return scroll_bar.value() > scroll_bar.minimum()
	if delta < 0:
		return scroll_bar.value() < scroll_bar.maximum()
	return False


def scrollable_widget_can_consume_wheel(widget: QAbstractItemView, event: QWheelEvent) -> bool:
	delta = wheel_delta(event)
	primary_vertical = abs(delta.y()) >= abs(delta.x())
	if primary_vertical:
		return scrollbar_can_consume_wheel(widget.verticalScrollBar(), delta.y())
	return scrollbar_can_consume_wheel(widget.horizontalScrollBar(), delta.x())


def forward_wheel_event_to_ancestor_scroll_area(widget: QWidget, event: QWheelEvent) -> bool:
	ancestor = widget.parentWidget()
	while ancestor is not None:
		if isinstance(ancestor, QAbstractScrollArea):
			target = ancestor.viewport() or ancestor
			local_position = QPointF(target.mapFromGlobal(event.globalPosition().toPoint()))
			forwarded_event = QWheelEvent(
				local_position,
				event.globalPosition(),
				event.pixelDelta(),
				event.angleDelta(),
				event.buttons(),
				event.modifiers(),
				event.phase(),
				event.inverted(),
				event.source(),
			)
			QApplication.sendEvent(target, forwarded_event)
			if forwarded_event.isAccepted():
				event.accept()
			else:
				event.ignore()
			return True
		ancestor = ancestor.parentWidget()
	return False


def handle_scrollable_wheel_event(widget: QWidget, event: QWheelEvent, default_handler) -> None:
	if scrollable_widget_can_consume_wheel(widget, event):
		default_handler()
		return
	if forward_wheel_event_to_ancestor_scroll_area(widget, event):
		return
	default_handler()


class PropagatingScrollArea(QScrollArea):
	def wheelEvent(self, event):
		handle_scrollable_wheel_event(self, event, lambda: super(PropagatingScrollArea, self).wheelEvent(event))


class PropagatingListWidget(QListWidget):
	def wheelEvent(self, event):
		handle_scrollable_wheel_event(self, event, lambda: super(PropagatingListWidget, self).wheelEvent(event))


class PropagatingTableWidget(QTableWidget):
	def wheelEvent(self, event):
		handle_scrollable_wheel_event(self, event, lambda: super(PropagatingTableWidget, self).wheelEvent(event))


class PropagatingTextEdit(QTextEdit):
	def wheelEvent(self, event):
		handle_scrollable_wheel_event(self, event, lambda: super(PropagatingTextEdit, self).wheelEvent(event))


def build_dialog_shell(dialog: QDialog, title: str, subtitle: str) -> QVBoxLayout:
	dialog.setObjectName('StandardDialog')
	outer_layout = QVBoxLayout(dialog)
	outer_layout.setContentsMargins(18, 18, 18, 18)
	outer_layout.setSpacing(14)

	hero = QFrame()
	hero.setObjectName('DialogHero')
	hero_layout = QVBoxLayout(hero)
	hero_layout.setContentsMargins(18, 16, 18, 16)
	hero_layout.setSpacing(6)

	title_label = QLabel(title)
	title_label.setObjectName('DialogTitle')
	hero_layout.addWidget(title_label)

	subtitle_label = QLabel(subtitle)
	subtitle_label.setObjectName('DialogSubtitle')
	subtitle_label.setWordWrap(True)
	hero_layout.addWidget(subtitle_label)
	outer_layout.addWidget(hero)

	scroll_area = PropagatingScrollArea()
	scroll_area.setObjectName('DialogScrollArea')
	scroll_area.setWidgetResizable(True)
	scroll_area.setFrameShape(QFrame.Shape.NoFrame)
	scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
	outer_layout.addWidget(scroll_area, 1)

	scroll_contents = QWidget()
	scroll_area.setWidget(scroll_contents)
	scroll_layout = QVBoxLayout(scroll_contents)
	scroll_layout.setContentsMargins(0, 0, 0, 0)
	scroll_layout.setSpacing(0)

	card = QFrame()
	card.setObjectName('DialogCard')
	card_layout = QVBoxLayout(card)
	card_layout.setContentsMargins(18, 18, 18, 18)
	card_layout.setSpacing(14)
	scroll_layout.addWidget(card)
	scroll_layout.addStretch(1)
	return card_layout


def configure_form_layout(layout: QFormLayout):
	layout.setContentsMargins(0, 0, 0, 0)
	layout.setSpacing(12)
	layout.setHorizontalSpacing(14)
	layout.setVerticalSpacing(12)
	layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
	layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)


def create_dialog_section_label(text: str) -> QLabel:
	label = QLabel(text)
	label.setObjectName('DialogSectionLabel')
	return label


def create_dialog_hint_label(text: str) -> QLabel:
	label = QLabel(text)
	label.setObjectName('DialogHint')
	label.setWordWrap(True)
	return label


class ColorSelectionField(QWidget):
	def __init__(self, initial_color: Optional[str] = None, allow_clear: bool = False,
				 default_label: str = 'Default', selected_label: str = 'Color selected',
				 parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.allow_clear = allow_clear
		self.default_label = default_label
		self.selected_label = selected_label
		self._color_value = (initial_color or '').strip() or None

		self.swatch = QFrame()
		self.swatch.setFixedSize(22, 22)

		self.label = QLabel()
		self.label.setObjectName('DialogHint')

		self.pick_button = QPushButton('Pick Color')
		self.pick_button.clicked.connect(self.pick_color)

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(8)
		layout.addWidget(self.swatch)
		layout.addWidget(self.label, 1)
		layout.addWidget(self.pick_button)

		self.clear_button: Optional[QPushButton] = None
		if self.allow_clear:
			self.clear_button = QPushButton('Clear')
			self.clear_button.clicked.connect(self.clear_color)
			layout.addWidget(self.clear_button)

		self._refresh_display()

	def _refresh_display(self):
		if self._color_value:
			resolved = resolve_hex_color(self._color_value, '#ddd4c6')
			self.swatch.setStyleSheet(f'background: {resolved}; border: 1px solid #b8a17f; border-radius: 6px;')
			self.label.setText(self.selected_label)
		else:
			self.swatch.setStyleSheet('background: #efe6d8; border: 1px dashed #b8a17f; border-radius: 6px;')
			self.label.setText(self.default_label)
		if self.clear_button is not None:
			self.clear_button.setEnabled(self._color_value is not None)

	def pick_color(self):
		initial = self._color_value or '#ffffff'
		color = choose_color_dialog(self, 'Choose Color', initial)
		if color is not None:
			self._color_value = color.name()
			self._refresh_display()

	def clear_color(self):
		self._color_value = None
		self._refresh_display()

	def color(self) -> Optional[str]:
		return self._color_value


def choose_color_dialog(parent: QWidget, title: str, initial_color: str) -> Optional[QColor]:
	dialog = QColorDialog(QColor(initial_color or '#ffffff'), parent)
	dialog.setWindowTitle(title)
	dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
	if dialog.exec() != QDialog.DialogCode.Accepted:
		return None
	color = dialog.currentColor()
	return color if color.isValid() else None


def choose_existing_directory_dialog(parent: QWidget, title: str, directory: str = '') -> str:
	dialog = QFileDialog(parent, title, directory or '')
	dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
	dialog.setFileMode(QFileDialog.FileMode.Directory)
	dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
	if dialog.exec() != QDialog.DialogCode.Accepted:
		return ''
	selected_files = dialog.selectedFiles()
	return selected_files[0] if selected_files else ''


def choose_open_file_dialog(parent: QWidget, title: str, directory: str = '', filter_text: str = '') -> str:
	dialog = QFileDialog(parent, title, directory or '')
	dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
	dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
	if filter_text:
		dialog.setNameFilter(filter_text)
	if dialog.exec() != QDialog.DialogCode.Accepted:
		return ''
	selected_files = dialog.selectedFiles()
	return selected_files[0] if selected_files else ''


def choose_open_files_dialog(parent: QWidget, title: str, directory: str = '', filter_text: str = '') -> List[str]:
	dialog = QFileDialog(parent, title, directory or '')
	dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
	dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
	if filter_text:
		dialog.setNameFilter(filter_text)
	if dialog.exec() != QDialog.DialogCode.Accepted:
		return []
	return dialog.selectedFiles()


def choose_save_file_dialog(parent: QWidget, title: str, directory: str = '', filter_text: str = '') -> str:
	dialog = QFileDialog(parent, title, directory or '')
	dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
	dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
	dialog.setFileMode(QFileDialog.FileMode.AnyFile)
	if filter_text:
		dialog.setNameFilter(filter_text)
	if dialog.exec() != QDialog.DialogCode.Accepted:
		return ''
	selected_files = dialog.selectedFiles()
	return selected_files[0] if selected_files else ''


def open_path_with_default_app(path: str):
	absolute_path = os.path.abspath(path)
	if os.name == 'nt':
		os.startfile(absolute_path)
		return
	command = ['open', absolute_path] if sys.platform == 'darwin' else ['xdg-open', absolute_path]
	subprocess.Popen(command)


def file_paths_from_mime_data(mime_data: QMimeData) -> List[str]:
	if mime_data is None or not mime_data.hasUrls():
		return []
	paths: List[str] = []
	for url in mime_data.urls():
		if not url.isLocalFile():
			continue
		local_path = os.path.abspath(url.toLocalFile())
		if os.path.exists(local_path) and local_path not in paths:
			paths.append(local_path)
	return paths


def format_card_text(board: KanbanBoard, card) -> str:
	parts = [card.title, f'[{priority_label(card.priority)}]']
	if card.project:
		parts.append(f'[{card.project}]')
	if card.assignee:
		parts.append(f'@{card.assignee}')
	if card.tags:
		parts.append(' '.join(f'#{tag}' for tag in card.tags))
	completed, total = board.get_subcard_progress(card.id)
	if total:
		parts.append(f'subcards {completed}/{total}')
	return ' '.join(parts)


def column_identifier(column) -> str:
	if hasattr(column, 'id'):
		return column.id
	status = getattr(column, 'status', None)
	return status.value if status is not None else ''


def column_label(column) -> str:
	if hasattr(column, 'name'):
		return column.name
	status = getattr(column, 'status', None)
	return status.value if status is not None else 'Column'


def column_color(column) -> Optional[str]:
	return getattr(column, 'color', None)


def column_is_completed(column) -> bool:
	if hasattr(column, 'is_completed'):
		return bool(column.is_completed)
	return getattr(column, 'status', None) == Status.DONE


def column_can_add_card(column) -> bool:
	if hasattr(column, 'can_add_card'):
		return bool(column.can_add_card)
	return getattr(column, 'status', None) == Status.TODO


def column_target_value(column):
	if hasattr(column, 'id'):
		return column.id
	return getattr(column, 'status', None)


def resolve_column_target(board: KanbanBoard, column_token: Optional[str]):
	if not column_token:
		return None
	return column_token


def clamp_drag_hotspot(point: QPoint, size: QSize) -> QPoint:
	max_x = max(0, size.width() - 1)
	max_y = max(0, size.height() - 1)
	return QPoint(min(max(point.x(), 0), max_x), min(max(point.y(), 0), max_y))


def create_drag_preview(source: QPixmap, opacity: float = 0.88) -> QPixmap:
	if source.isNull():
		return source
	preview = QPixmap(source.size())
	preview.fill(Qt.GlobalColor.transparent)
	preview.setDevicePixelRatio(source.devicePixelRatio())

	painter = QPainter(preview)
	painter.setOpacity(opacity)
	painter.drawPixmap(0, 0, source)
	painter.end()
	return preview


__all__ = [
	'WINDOW_STYLE',
	'ColorSelectionField',
	'PropagatingListWidget',
	'PropagatingScrollArea',
	'PropagatingTableWidget',
	'PropagatingTextEdit',
	'build_dialog_shell',
	'choose_color_dialog',
	'choose_existing_directory_dialog',
	'choose_open_file_dialog',
	'choose_open_files_dialog',
	'choose_save_file_dialog',
	'clamp_drag_hotspot',
	'clipped_description',
	'clipped_title',
	'column_can_add_card',
	'column_color',
	'column_identifier',
	'column_is_completed',
	'column_label',
	'column_target_value',
	'configure_form_layout',
	'contrasting_text_color',
	'create_dialog_hint_label',
	'create_dialog_section_label',
	'create_drag_preview',
	'create_project_name_combo',
	'display_date',
	'due_state_colors',
	'due_state_label',
	'file_paths_from_mime_data',
	'format_card_text',
	'handle_scrollable_wheel_event',
	'open_path_with_default_app',
	'parse_tags',
	'priority_accent',
	'priority_label',
	'resolve_column_target',
	'resolve_hex_color',
	'rgba_color',
	'schedule_summary',
	'secondary_text_color',
]
