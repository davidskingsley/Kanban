## @file
#  @brief PySide6-based multi-board GUI for the Kanban application.
"""PySide6 GUI implementation for the multi-board Kanban manager."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from typing import Dict, List, Optional

from PySide6.QtCore import QDate, QMimeData, QPoint, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QDrag, QKeySequence, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from ..board import KanbanBoard
from ..board_manager import BoardManager
from ..models import CardType, CustomColumn, Priority, Project, Status


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
QCheckBox#ToolbarLateOnlyCheckbox {
    background: rgba(125, 59, 20, 0.08);
    border: 1px solid rgba(125, 59, 20, 0.12);
    border-radius: 10px;
    padding: 6px 8px;
    font-weight: 600;
}
QPushButton#ClearCardFiltersButton {
    padding: 6px 10px;
    min-width: 58px;
}
QMenuBar {
    background: #eadfcf;
    color: #2d241c;
    border-bottom: 1px solid #b59c77;
}
QMenuBar::item {
    background: transparent;
    color: #2d241c;
    padding: 8px 12px;
    margin: 2px 4px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #d8c2a3;
    color: #2d241c;
}
QMenuBar::item:pressed {
    background: #caa781;
    color: #2d241c;
}
QMenu {
    background: #fffaf2;
    color: #2d241c;
    border: 1px solid #b59c77;
    padding: 6px;
}
QMenu::item {
    background: transparent;
    color: #2d241c;
    padding: 8px 24px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: #7d3b14;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #d9c8b0;
    margin: 6px 10px;
}
QListWidget {
    background: #fffdf9;
    border: 1px solid #ac9571;
    border-radius: 10px;
    padding: 4px;
    outline: 0;
}
QListWidget::item {
    border-radius: 6px;
    padding: 6px;
}
QListWidget::item:selected {
    background: #734117;
    color: #ffffff;
}
QGroupBox {
    background: #fbf5ea;
    border: 1px solid #b59c77;
    border-radius: 12px;
    margin-top: 14px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #3f2f21;
}
QPushButton {
    background: #9c4d1f;
    color: white;
    border: 1px solid #7f3d16;
    border-radius: 8px;
    padding: 6px 12px;
}
QPushButton:hover {
    background: #7d3b14;
}
QDialogButtonBox QPushButton,
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
    border: 1px solid #bcad95;
}
QLineEdit, QTextEdit, QComboBox, QDateEdit {
    background: white;
    color: #2d241c;
    border: 1px solid #ac9571;
    border-radius: 8px;
    padding: 6px 32px 6px 10px;
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
QComboBox QAbstractItemView::item,
QInputDialog QComboBox QAbstractItemView::item {
    min-height: 24px;
    padding: 6px 10px;
    border-radius: 6px;
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
}
QCheckBox::indicator:unchecked {
    background: #fffaf2;
    border: 1px solid #ac9571;
    border-radius: 4px;
}
QCheckBox::indicator:checked {
    background: #9c4d1f;
    border: 1px solid #7f3d16;
    border-radius: 4px;
}
"""


def priority_label(priority: Priority) -> str:
    """Return a user-facing label for a priority enum."""
    return priority.value.replace('_', ' ').title()


def parse_tags(text: str) -> List[str]:
    """Return a normalized tag list from a comma-separated string."""
    tags: List[str] = []
    for raw_tag in (text or '').split(','):
        tag = raw_tag.strip().lstrip('#')
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def create_project_name_combo(board: Optional[KanbanBoard], current_text: Optional[str] = None) -> QComboBox:
    """Return an editable project picker populated from the board registry."""
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
    """Return an RGB tuple normalized to 0..1 from a hex color."""
    value = (color or '').strip().lstrip('#')
    if len(value) != 6:
        raise ValueError(f'Unsupported color value: {color!r}')
    return tuple(int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4))


def _linear_channel(channel: float) -> float:
    """Return the relative luminance contribution of a channel."""
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def contrast_ratio(color_a: str, color_b: str) -> float:
    """Return the WCAG contrast ratio between two hex colors."""
    def luminance(color: str) -> float:
        red, green, blue = color_to_rgb(color)
        return (
            0.2126 * _linear_channel(red)
            + 0.7152 * _linear_channel(green)
            + 0.0722 * _linear_channel(blue)
        )

    light, dark = sorted((luminance(color_a), luminance(color_b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def contrasting_text_color(background: str) -> str:
    """Return the better of dark or light text for a background color."""
    dark_text = '#1f1812'
    light_text = '#ffffff'
    dark_contrast = contrast_ratio(background, dark_text)
    light_contrast = contrast_ratio(background, light_text)
    return dark_text if dark_contrast >= light_contrast else light_text


def resolve_hex_color(color: Optional[str], fallback: str) -> str:
    """Return a valid hex color name or the provided fallback."""
    candidate = QColor((color or '').strip())
    if candidate.isValid():
        return candidate.name()
    return fallback


def secondary_text_color(background: str) -> str:
    """Return a softer text color that still fits the card background."""
    return '#efe4d4' if contrasting_text_color(background) == '#ffffff' else '#66584b'


def rgba_color(color: str, alpha: float) -> str:
    """Return a CSS rgba string for the provided color and alpha value."""
    qcolor = QColor(resolve_hex_color(color, '#000000'))
    clamped_alpha = max(0.0, min(alpha, 1.0))
    return f'rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {clamped_alpha:.3f})'


def priority_accent(priority: Priority) -> str:
    """Return a stable accent color for a priority level."""
    return {
        Priority.LOW: '#4f7f5c',
        Priority.MEDIUM: '#c67b2f',
        Priority.HIGH: '#c45f35',
        Priority.CRITICAL: '#a63c30',
    }.get(priority, '#c67b2f')


def schedule_summary(card) -> Optional[str]:
    """Return a compact schedule summary for a card."""
    if card.start_date and card.end_date:
        return f"{card.start_date.isoformat()} -> {card.end_date.isoformat()}"
    if card.start_date:
        return f"Starts {card.start_date.isoformat()}"
    if card.end_date:
        return f"Due {card.end_date.isoformat()}"
    return None


def due_state_label(board: KanbanBoard, card, today: Optional[date] = None) -> str:
    """Return a readable due-date status label for a card."""
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
    """Return a display value for an optional date."""
    return value.isoformat() if value else '—'


def due_state_colors(state: str) -> tuple[str, str]:
    """Return background and foreground colors for a due-date state."""
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
    """Return a single-paragraph preview of card text."""
    compact = ' '.join((text or '').split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + '...'


def clipped_title(text: str, limit: int = 97) -> str:
    """Return a clipped card-title preview with trailing full stops when truncated."""
    compact = ' '.join((text or '').split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + '...'


def wheel_delta(event: QWheelEvent) -> QPoint:
    """Return the effective wheel delta for the event."""
    return event.pixelDelta() if not event.pixelDelta().isNull() else event.angleDelta()


def scrollbar_can_consume_wheel(scroll_bar, delta: int) -> bool:
    """Return whether the given scroll bar can move in response to the wheel delta."""
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
    """Return whether a scrollable widget can use the incoming wheel event."""
    delta = wheel_delta(event)
    primary_vertical = abs(delta.y()) >= abs(delta.x())
    if primary_vertical:
        return scrollbar_can_consume_wheel(widget.verticalScrollBar(), delta.y())
    return scrollbar_can_consume_wheel(widget.horizontalScrollBar(), delta.x())


def forward_wheel_event_to_ancestor_scroll_area(widget: QWidget, event: QWheelEvent) -> bool:
    """Forward a wheel event to the nearest ancestor scroll area."""
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
    """Handle wheel events locally when possible, otherwise bubble them to an ancestor scroll area."""
    if scrollable_widget_can_consume_wheel(widget, event):
        default_handler()
        return
    if forward_wheel_event_to_ancestor_scroll_area(widget, event):
        return
    default_handler()


class PropagatingScrollArea(QScrollArea):
    """Scroll area that bubbles unused wheel input to ancestor scroll areas."""

    def wheelEvent(self, event):
        handle_scrollable_wheel_event(self, event, lambda: super(PropagatingScrollArea, self).wheelEvent(event))


class PropagatingListWidget(QListWidget):
    """List widget that bubbles unused wheel input to ancestor scroll areas."""

    def wheelEvent(self, event):
        handle_scrollable_wheel_event(self, event, lambda: super(PropagatingListWidget, self).wheelEvent(event))


class PropagatingTableWidget(QTableWidget):
    """Table widget that bubbles unused wheel input to ancestor scroll areas."""

    def wheelEvent(self, event):
        handle_scrollable_wheel_event(self, event, lambda: super(PropagatingTableWidget, self).wheelEvent(event))


class PropagatingTextEdit(QTextEdit):
    """Text edit that bubbles unused wheel input to ancestor scroll areas."""

    def wheelEvent(self, event):
        handle_scrollable_wheel_event(self, event, lambda: super(PropagatingTextEdit, self).wheelEvent(event))


def build_dialog_shell(dialog: QDialog, title: str, subtitle: str) -> QVBoxLayout:
    """Create a consistent dialog shell and return the content-card layout."""
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
    """Apply consistent spacing and growth settings to a form layout."""
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    layout.setHorizontalSpacing(14)
    layout.setVerticalSpacing(12)
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)


def create_dialog_section_label(text: str) -> QLabel:
    """Create a section label for dialog content."""
    label = QLabel(text)
    label.setObjectName('DialogSectionLabel')
    return label


def create_dialog_hint_label(text: str) -> QLabel:
    """Create a hint label for dialog content."""
    label = QLabel(text)
    label.setObjectName('DialogHint')
    label.setWordWrap(True)
    return label


class ColorSelectionField(QWidget):
    """Compact swatch-first color selection control."""

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
        """Refresh the swatch and descriptive label."""
        if self._color_value:
            resolved = resolve_hex_color(self._color_value, '#ddd4c6')
            self.swatch.setStyleSheet(
                f'background: {resolved}; border: 1px solid #b8a17f; border-radius: 6px;'
            )
            self.label.setText(self.selected_label)
        else:
            self.swatch.setStyleSheet(
                'background: #efe6d8; border: 1px dashed #b8a17f; border-radius: 6px;'
            )
            self.label.setText(self.default_label)
        if self.clear_button is not None:
            self.clear_button.setEnabled(self._color_value is not None)

    def pick_color(self):
        """Open the themed color picker and store the result."""
        initial = self._color_value or '#ffffff'
        color = choose_color_dialog(self, 'Choose Color', initial)
        if color is not None:
            self._color_value = color.name()
            self._refresh_display()

    def clear_color(self):
        """Reset to the default color state."""
        self._color_value = None
        self._refresh_display()

    def color(self) -> Optional[str]:
        """Return the selected color value."""
        return self._color_value


def choose_color_dialog(parent: QWidget, title: str, initial_color: str) -> Optional[QColor]:
    """Show a themed non-native color dialog and return the selected color."""
    dialog = QColorDialog(QColor(initial_color or '#ffffff'), parent)
    dialog.setWindowTitle(title)
    dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    color = dialog.currentColor()
    return color if color.isValid() else None


def choose_existing_directory_dialog(parent: QWidget, title: str, directory: str = '') -> str:
    """Show a themed non-native directory picker."""
    dialog = QFileDialog(parent, title, directory or '')
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return ''
    selected_files = dialog.selectedFiles()
    return selected_files[0] if selected_files else ''


def choose_open_file_dialog(parent: QWidget, title: str, directory: str = '', filter_text: str = '') -> str:
    """Show a themed non-native open-file dialog."""
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
    """Show a themed non-native multi-file open dialog."""
    dialog = QFileDialog(parent, title, directory or '')
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    if filter_text:
        dialog.setNameFilter(filter_text)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return []
    return dialog.selectedFiles()


def choose_save_file_dialog(parent: QWidget, title: str, directory: str = '', filter_text: str = '') -> str:
    """Show a themed non-native save-file dialog."""
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
    """Open a file path with the operating system default application."""
    absolute_path = os.path.abspath(path)
    if os.name == 'nt':
        os.startfile(absolute_path)
        return
    command = ['open', absolute_path] if sys.platform == 'darwin' else ['xdg-open', absolute_path]
    subprocess.Popen(command)


def file_paths_from_mime_data(mime_data: QMimeData) -> List[str]:
    """Return local file paths from dropped mime data."""
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
    """Return a compact display string for a card."""
    parts = [card.title, f"[{priority_label(card.priority)}]"]
    if card.project:
        parts.append(f"[{card.project}]")
    if card.assignee:
        parts.append(f"@{card.assignee}")
    if card.tags:
        parts.append(' '.join(f"#{tag}" for tag in card.tags))
    completed, total = board.get_subcard_progress(card.id)
    if total:
        parts.append(f"subcards {completed}/{total}")
    return ' '.join(parts)


def column_identifier(column) -> str:
    """Return a stable string identifier for custom or legacy columns."""
    if hasattr(column, 'id'):
        return column.id
    status = getattr(column, 'status', None)
    return status.value if status is not None else ''


def column_label(column) -> str:
    """Return the user-facing label for a custom or legacy column."""
    if hasattr(column, 'name'):
        return column.name
    status = getattr(column, 'status', None)
    return status.value if status is not None else 'Column'


def column_color(column) -> Optional[str]:
    """Return the configured color for a custom column, if any."""
    return getattr(column, 'color', None)


def column_is_completed(column) -> bool:
    """Return whether the column represents completed work."""
    if hasattr(column, 'is_completed'):
        return bool(column.is_completed)
    return getattr(column, 'status', None) == Status.DONE


def column_can_add_card(column) -> bool:
    """Return whether the column should offer card creation from the UI."""
    if hasattr(column, 'can_add_card'):
        return bool(column.can_add_card)
    return getattr(column, 'status', None) == Status.TODO


def column_target_value(column):
    """Return the board move/create target for the column."""
    if hasattr(column, 'id'):
        return column.id
    return getattr(column, 'status', None)


def resolve_column_target(board: KanbanBoard, column_token: Optional[str]):
    """Resolve a drag-drop column token to the value expected by the board API."""
    if not column_token:
        return None
    return column_token


def clamp_drag_hotspot(point: QPoint, size: QSize) -> QPoint:
    """Clamp a drag hotspot so it always stays within the preview pixmap."""
    max_x = max(0, size.width() - 1)
    max_y = max(0, size.height() - 1)
    return QPoint(
        min(max(point.x(), 0), max_x),
        min(max(point.y(), 0), max_y),
    )


def create_drag_preview(source: QPixmap, opacity: float = 0.88) -> QPixmap:
    """Return a softened drag preview that remains easy to align under the cursor."""
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
        """Synchronize the editor state with the checkbox."""
        self.editor.setEnabled(checked)
        self.clear_button.setEnabled(checked)
        if checked:
            if not self.editor.date().isValid():
                self.editor.setDate(QDate.currentDate())
            self.editor.setFocus(Qt.FocusReason.TabFocusReason)
            self.editor.selectAll()

    def clear(self):
        """Disable the field and drop its value from the dialog state."""
        self.checkbox.setChecked(False)
        self.editor.setDate(QDate.currentDate())

    def value(self) -> Optional[date]:
        """Return the selected date, if enabled."""
        if not self.checkbox.isChecked():
            return None
        selected = self.editor.date()
        return date(selected.year(), selected.month(), selected.day())


class CardTile(QFrame):
    """Structured card widget used inside each column list."""

    def __init__(self, board: KanbanBoard, card, selected: bool = False,
                 file_drop_callback=None, select_callback=None,
                 edit_callback=None, context_action_callback=None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.board = board
        self.card = card
        self.selected = selected
        self.file_drop_callback = file_drop_callback
        self.select_callback = select_callback
        self.edit_callback = edit_callback
        self.context_action_callback = context_action_callback
        self._drop_highlight = False

        self.background = resolve_hex_color(card.color, '#fffaf3')
        self.foreground = contrasting_text_color(self.background)
        self.muted = secondary_text_color(self.background)
        self.priority_color = priority_accent(card.priority)
        self.border_color = '#7d3b14' if selected else ('#a63c30' if card.has_past_end_date() and not board.is_card_done(card) else '#d7c4aa')

        self.setObjectName('CardTile')
        self.setAcceptDrops(True)
        self._build_ui()
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(64, 39, 21, 38))
        self.setGraphicsEffect(shadow)
        self._apply_style()

    def _create_badge(self, text: str, background: str, foreground: str, border: Optional[str] = None) -> QLabel:
        """Create a compact badge label for card metadata."""
        label = QLabel(text)
        label.setFixedHeight(24)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"""
            background: {background};
            color: {foreground};
            border: 1px solid {border or background};
            border-radius: 9px;
            padding: 3px 8px;
            font-size: 6.5pt;
            font-weight: 700;
            """
        )
        return label

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        priority_bar = QFrame()
        priority_bar.setFixedHeight(6)
        priority_bar.setStyleSheet(f'background: {self.priority_color}; border-radius: 3px;')
        layout.addWidget(priority_bar)

        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        header_layout.addWidget(
            self._create_badge(
                priority_label(self.card.priority).upper(),
                rgba_color(self.priority_color, 0.14),
                self.priority_color,
                rgba_color(self.priority_color, 0.30),
            )
        )

        card_type = self.board.get_card_type(self.card.card_type_id)
        if card_type is None:
            card_type = self.board.get_default_card_type()
        if card_type is not None:
            header_layout.addWidget(
                self._create_badge(
                    card_type.name,
                    rgba_color(self.foreground, 0.08),
                    self.foreground,
                    rgba_color(self.foreground, 0.12),
                )
            )

        if self.card.has_past_end_date() and not self.board.is_card_done(self.card):
            header_layout.addWidget(
                self._create_badge('LATE', 'rgba(166, 60, 48, 0.14)', '#a63c30', 'rgba(166, 60, 48, 0.28)')
            )
        header_layout.addStretch(1)
        if self.card.assignee:
            header_layout.addWidget(
                self._create_badge(
                    f'@{self.card.assignee}',
                    rgba_color(self.foreground, 0.08),
                    self.foreground,
                    rgba_color(self.foreground, 0.12),
                )
            )
        layout.addWidget(header_row)

        title_label = QLabel(clipped_title(self.card.title))
        title_label.setWordWrap(True)
        title_label.setStyleSheet(
            f'font-size: 9pt; font-weight: 700; color: {self.foreground}; background: transparent;'
        )
        layout.addWidget(title_label)

        meta_parts = []
        if self.card.project:
            meta_parts.append(self.card.project)
        parent_card = self.board.get_parent_card(self.card)
        if parent_card is not None:
            meta_parts.append(f'Subcard of {parent_card.title}')
        if meta_parts:
            meta_label = QLabel(' | '.join(meta_parts))
            meta_label.setWordWrap(True)
            meta_label.setStyleSheet(f'color: {self.muted}; background: transparent; font-size: 7pt; font-weight: 600;')
            layout.addWidget(meta_label)

        description = clipped_description(self.card.description)
        if description:
            description_label = QLabel(description)
            description_label.setWordWrap(True)
            description_label.setStyleSheet(
                f'color: {self.muted}; background: transparent; font-size: 7.5pt;'
            )
            layout.addWidget(description_label)

        schedule_parts = []
        schedule_text = schedule_summary(self.card)
        if schedule_text:
            schedule_parts.append(schedule_text)
        if self.card.has_past_end_date() and not self.board.is_card_done(self.card):
            schedule_parts.append('Late')
        if parent_card is None:
            completed, total = self.board.get_subcard_progress(self.card.id)
            if total:
                schedule_parts.append(f'Subcards {completed}/{total}')
        if schedule_parts:
            schedule_label = QLabel(' | '.join(schedule_parts))
            schedule_label.setWordWrap(True)
            schedule_label.setStyleSheet(
                f'color: {self.foreground}; background: {rgba_color(self.foreground, 0.055)}; '
                f'border: 1px solid {rgba_color(self.foreground, 0.08)}; border-radius: 10px; padding: 7px 9px; font-size: 7.5pt;'
            )
            layout.addWidget(schedule_label)

        if self.card.tags:
            tags_label = QLabel(' '.join(f'#{tag}' for tag in self.card.tags))
            tags_label.setWordWrap(True)
            tags_label.setStyleSheet(
                f'color: {self.foreground}; background: {rgba_color(self.priority_color, 0.08)}; '
                f'border-radius: 10px; padding: 6px 8px; font-weight: 600; font-size: 8pt;'
            )
            layout.addWidget(tags_label)

        footer_badges = []
        if self.card.notes:
            footer_badges.append(
                self._create_badge(
                    f'{len(self.card.notes)} note' + ('' if len(self.card.notes) == 1 else 's'),
                    rgba_color(self.foreground, 0.06),
                    self.muted,
                    rgba_color(self.foreground, 0.09),
                )
            )
        if self.card.attachments:
            footer_badges.append(
                self._create_badge(
                    f'{len(self.card.attachments)} attachment' + ('' if len(self.card.attachments) == 1 else 's'),
                    rgba_color(self.foreground, 0.06),
                    self.muted,
                    rgba_color(self.foreground, 0.09),
                )
            )
        if footer_badges:
            footer_row = QWidget()
            footer_layout = QHBoxLayout(footer_row)
            footer_layout.setContentsMargins(0, 0, 0, 0)
            footer_layout.setSpacing(6)
            for badge in footer_badges:
                footer_layout.addWidget(badge)
            footer_layout.addStretch(1)
            layout.addWidget(footer_row)

    def _apply_style(self):
        active_border = '#3e7a5e' if self._drop_highlight else self.border_color
        soft_top = QColor(self.background).lighter(104).name()
        soft_bottom = QColor(self.background).darker(102).name()
        self.setStyleSheet(
            f"""
            QFrame#CardTile {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {soft_top}, stop:1 {soft_bottom});
                border: 2px solid {active_border};
                border-radius: 14px;
            }}
            """
        )

    def dragEnterEvent(self, event):
        """Accept dropped files for attachment creation."""
        if self.file_drop_callback is None:
            event.ignore()
            return
        paths = file_paths_from_mime_data(event.mimeData())
        if not paths:
            event.ignore()
            return
        self._drop_highlight = True
        self._apply_style()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Clear file-drop highlight state."""
        self._drop_highlight = False
        self._apply_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        """Handle dropped files on a card tile."""
        paths = file_paths_from_mime_data(event.mimeData())
        self._drop_highlight = False
        self._apply_style()
        if not paths or self.file_drop_callback is None:
            event.ignore()
            return
        self.file_drop_callback(self.card.id, paths)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        """Let the parent item view handle left-button selection and drag initiation."""
        if event.button() == Qt.MouseButton.LeftButton:
            event.ignore()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Edit the card from a normal left double-click on the embedded tile."""
        if event.button() == Qt.MouseButton.LeftButton and self.edit_callback is not None:
            self.edit_callback(self.card.id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        """Show card actions for the current tile."""
        menu = QMenu(self)
        edit_action = menu.addAction('Edit Card')
        add_subcard_action = None
        if self.context_action_callback is not None and not self.card.parent_id:
            add_subcard_action = menu.addAction('Add Subcard')
        chosen_action = menu.exec(event.globalPos())
        if chosen_action == edit_action and self.edit_callback is not None:
            self.edit_callback(self.card.id)
            event.accept()
            return
        if chosen_action == add_subcard_action and self.context_action_callback is not None:
            self.context_action_callback(self.card.id, 'add_subcard')
            event.accept()
            return
        super().contextMenuEvent(event)

    def sizeHint(self) -> QSize:
        width = self.width() if self.width() > 0 else super().sizeHint().width()
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        width = self.width() if self.width() > 0 else max(hint.width(), super().sizeHint().width())
        return QSize(width, self.heightForWidth(width))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        layout = self.layout()
        if layout is None:
            return max(super().sizeHint().height(), 156)
        constrained_width = max(width, 120)
        return max(layout.totalHeightForWidth(constrained_width), 156)


class CardListWidget(QListWidget):
    """List widget that keeps custom card tiles sized to the column width."""

    CARD_MIME_TYPE = 'application/x-kanban-card'

    def __init__(self, column_id: Optional[str] = None, board_view=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.column_id = column_id
        self.board_view = board_view
        self._drop_highlight = False
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(False)

    def _apply_drop_style(self):
        border_style = '2px solid #3e7a5e' if self._drop_highlight else 'none'
        background = '#eef7f0' if self._drop_highlight else 'transparent'
        padding = '8px' if self._drop_highlight else '0'
        self.setStyleSheet(
            f"""
            QListWidget {{
                background: {background};
                border: {border_style};
                border-radius: 14px;
                padding: {padding};
                outline: 0;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                padding: 0;
                margin: 0 0 10px 0;
            }}
            QListWidget::item:selected {{
                background: transparent;
                border: none;
            }}
            """
        )

    def startDrag(self, supported_actions):
        """Start a drag carrying the selected card metadata."""
        item = self.currentItem()
        if item is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole) or {}
        card_id = payload.get('card_id')
        if not card_id:
            return
        mime_data = QMimeData()
        mime_payload = {
            'card_id': card_id,
            'source_column_id': payload.get('column_id') or self.column_id,
        }
        mime_data.setData(self.CARD_MIME_TYPE, json.dumps(mime_payload).encode('utf-8'))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        widget = self.itemWidget(item)
        if widget is not None:
            preview = create_drag_preview(widget.grab())
            drag.setPixmap(preview)
            drag.setHotSpot(clamp_drag_hotspot(widget.mapFromGlobal(QCursor.pos()), preview.size()))
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        """Accept card drags into a target column list."""
        if event.mimeData().hasFormat(self.CARD_MIME_TYPE):
            self._drop_highlight = True
            self._apply_drop_style()
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        """Keep accepting valid card drags over the column list."""
        if event.mimeData().hasFormat(self.CARD_MIME_TYPE):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Clear target highlighting when a drag leaves the list."""
        self._drop_highlight = False
        self._apply_drop_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        """Move a dragged card into this column."""
        self._drop_highlight = False
        self._apply_drop_style()
        if not event.mimeData().hasFormat(self.CARD_MIME_TYPE) or self.board_view is None:
            event.ignore()
            return
        payload = json.loads(bytes(event.mimeData().data(self.CARD_MIME_TYPE)).decode('utf-8'))
        self.board_view.handle_card_drop(payload.get('card_id'), payload.get('source_column_id'), self.column_id)
        event.acceptProposedAction()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_card_sizes()

    def wheelEvent(self, event):
        handle_scrollable_wheel_event(self, event, lambda: super(CardListWidget, self).wheelEvent(event))

    def refresh_card_sizes(self):
        """Resize card widgets to the available viewport width and refresh item heights."""
        available_width = self.viewport().width() - 12
        if available_width <= 0:
            return
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget is None:
                continue
            widget.setFixedWidth(available_width)
            widget.updateGeometry()
            if widget.hasHeightForWidth():
                height = widget.heightForWidth(available_width)
            else:
                height = widget.sizeHint().height()
            widget.setMinimumHeight(height)
            item.setSizeHint(QSize(available_width, height))


class ColumnTitleButton(QPushButton):
    """Header title control used to select or edit a column."""

    def __init__(self, text: str, click_callback=None, double_click_callback=None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._double_click_callback = double_click_callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        if click_callback is not None:
            self.clicked.connect(click_callback)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._double_click_callback is not None:
            self._double_click_callback()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class ColumnAddButton(QPushButton):
    """Circular add-card button with a painted plus icon."""

    def __init__(self, accent_color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.accent_color = resolve_hex_color(accent_color, '#8f4a1d')
        self.setObjectName('ColumnAddButton')
        self.setToolTip('Add card')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(28, 28)
        self.setStyleSheet(
            f"QPushButton#ColumnAddButton {{ background: {rgba_color(self.accent_color, 0.14)}; border: 1px solid {rgba_color(self.accent_color, 0.28)}; border-radius: 14px; }}"
            f"QPushButton#ColumnAddButton:hover {{ background: {rgba_color(self.accent_color, 0.22)}; border-color: {rgba_color(self.accent_color, 0.40)}; }}"
            f"QPushButton#ColumnAddButton:pressed {{ background: {rgba_color(self.accent_color, 0.30)}; }}"
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(self.accent_color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        center_x = self.width() / 2
        center_y = self.height() / 2
        arm = 5
        painter.drawLine(QPointF(center_x - arm, center_y), QPointF(center_x + arm, center_y))
        painter.drawLine(QPointF(center_x, center_y - arm), QPointF(center_x, center_y + arm))
        painter.end()


class ColumnGroupBox(QGroupBox):
    """Column widget that supports drag reordering."""

    COLUMN_MIME_TYPE = 'application/x-kanban-column'
    DRAG_HANDLE_HEIGHT = 56

    def __init__(self, title: str, column_id: str, board_view, selected: bool, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self.column_id = column_id
        self.board_view = board_view
        self.selected = selected
        self._drop_highlight = False
        self._press_pos = None
        self.setAcceptDrops(True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(74, 49, 30, 26))
        self.setGraphicsEffect(shadow)
        self._apply_style()

    def _apply_style(self):
        border_color = '#3e7a5e' if self._drop_highlight else ('#7d3b14' if self.selected else '#ccb391')
        title_background = 'rgba(125, 59, 20, 0.12)' if self.selected else 'rgba(98, 76, 58, 0.08)'
        self.setStyleSheet(
            f"""
            QGroupBox {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fdf7ed, stop:1 #f3e6d5);
                border: 2px solid {border_color};
                border-radius: 18px;
                margin-top: 12px;
                padding-top: 0px;
            }}
            """
        )

    def mousePressEvent(self, event):
        """Record a potential header drag start."""
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= self.DRAG_HANDLE_HEIGHT:
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Start a column drag when the header is dragged."""
        if self._press_pos is None:
            super().mouseMoveEvent(event)
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self._press_pos).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
        mime_data = QMimeData()
        mime_data.setData(self.COLUMN_MIME_TYPE, self.column_id.encode('utf-8'))
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        preview = create_drag_preview(self.grab())
        drag.setPixmap(preview)
        drag.setHotSpot(clamp_drag_hotspot(self._press_pos, preview.size()))
        self._press_pos = None
        drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Clear any pending drag state."""
        self._press_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Open column editing when the header is double-clicked."""
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 34:
            self.board_view.handle_column_double_click(self.column_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        """Accept column drags so the user can reorder columns."""
        if event.mimeData().hasFormat(self.COLUMN_MIME_TYPE):
            self._drop_highlight = True
            self._apply_style()
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        """Continue accepting valid column drags."""
        if event.mimeData().hasFormat(self.COLUMN_MIME_TYPE):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Clear highlight when a column drag leaves."""
        self._drop_highlight = False
        self._apply_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        """Reorder columns relative to this target column."""
        self._drop_highlight = False
        self._apply_style()
        if not event.mimeData().hasFormat(self.COLUMN_MIME_TYPE):
            event.ignore()
            return
        dragged_column_id = bytes(event.mimeData().data(self.COLUMN_MIME_TYPE)).decode('utf-8')
        insert_after = event.position().x() > (self.width() / 2)
        self.board_view.handle_column_drop(dragged_column_id, self.column_id, insert_after)
        event.acceptProposedAction()


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
        """Create a compact stat card for the dialog header."""
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
        """Build the due-date rows for the current board."""
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
        """Return rows matching the selected filter."""
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
        """Refresh the table rows for the selected filter."""
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
        """Track the currently selected row."""
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
        """Accept the dialog using the selected card."""
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
        """Choose a storage directory."""
        directory = choose_existing_directory_dialog(self, 'Select Board Storage Folder', self.directory_edit.text())
        if directory:
            self.directory_edit.setText(directory)

    def values(self) -> Dict[str, str]:
        """Return dialog values."""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'storage_dir': self.directory_edit.text().strip(),
        }

    def accept(self):
        """Validate before closing."""
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
        """Return dialog values."""
        return {
            'name': self.name_edit.text().strip(),
            'color': self.color_field.color() or '#2196F3',
            'is_completed': self.completed_check.isChecked(),
            'can_add_card': self.add_card_check.isChecked(),
        }

    def accept(self):
        """Validate before closing."""
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
        """Refresh the list content."""
        self.list_widget.clear()
        for column in self.columns:
            self.list_widget.addItem(column.name)
        if self.columns:
            self.list_widget.setCurrentRow(0)

    def move_up(self):
        """Move the selected column up."""
        row = self.list_widget.currentRow()
        if row <= 0:
            return
        self.columns[row - 1], self.columns[row] = self.columns[row], self.columns[row - 1]
        self.refresh_items()
        self.list_widget.setCurrentRow(row - 1)

    def move_down(self):
        """Move the selected column down."""
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.columns) - 1:
            return
        self.columns[row + 1], self.columns[row] = self.columns[row], self.columns[row + 1]
        self.refresh_items()
        self.list_widget.setCurrentRow(row + 1)

    def ordered_ids(self) -> List[str]:
        """Return the reordered column IDs."""
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
        """Return the dialog values."""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'default_project': self.project_edit.currentText().strip() or None,
            'default_color': self.color_field.color(),
        }

    def accept(self):
        """Validate before closing."""
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
        """Return a compact swatch widget for a preset color value."""
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
        """Populate the browser rows."""
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
        """Accept the dialog with the currently selected card type."""
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
        """Return the dialog values."""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
        }

    def accept(self):
        """Validate before closing."""
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
        """Populate the browser rows."""
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
        """Accept the dialog with the currently selected project."""
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
        """Return whether the dialog should expose subcard management."""
        return self.card is not None and not self.card.parent_id

    def _set_attachment_drop_active(self, active: bool):
        """Update the attachment drop target styling."""
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
        """Accept dropped files for existing cards."""
        if self.card is None:
            event.ignore()
            return
        if not file_paths_from_mime_data(event.mimeData()):
            event.ignore()
            return
        self._set_attachment_drop_active(True)
        event.acceptProposedAction()

    def _attachment_drag_leave_event(self, event):
        """Clear attachment drop highlighting."""
        self._set_attachment_drop_active(False)
        QFrame.dragLeaveEvent(self.attachment_drop_frame, event)

    def _attachment_drop_event(self, event):
        """Attach dropped files to the current card."""
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
        """Reload the dialog attachment list."""
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
        """Return the selected attachment identifier."""
        item = self.attachments_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def add_attachments_via_picker(self):
        """Select files and attach them to the card."""
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
        """Attach files to the current card and refresh the list."""
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
        """Open the selected attachment in the system default application."""
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
        """Remove the selected attachment from the card."""
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
        """Reload the dialog subcard list."""
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
        """Return the subcard currently selected in the list."""
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
        """Open a nested dialog to create a subcard for the current card."""
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
        """Edit the currently selected subcard from the list."""
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
        """Delete the currently selected subcard."""
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
        """Return dialog values."""
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
        """Validate before closing."""
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, 'Missing Title', 'Card title is required.')
            return
        super().accept()


class MultiBoardGUI:
    """PySide6 multi-board GUI wrapper."""

    def __init__(self, board_manager: BoardManager):
        self.board_manager = board_manager
        self.board_manager.set_lock_handler(self.prompt_for_locked_board_action)
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName('Kanban')
        self.app.setStyle('Fusion')
        self.app.setStyleSheet(WINDOW_STYLE)

        self.window = QMainWindow()
        self.window.setWindowTitle('Multi-Board Kanban Manager')
        self.window.resize(1480, 860)

        self.selected_card_id: Optional[str] = None
        self.selected_column_id: Optional[str] = None
        self.recent_board_ids: List[str] = []
        self.max_recent_boards = 5
        self.board_filter_states: Dict[str, Dict[str, object]] = {}
        self._updating_filter_controls = False

        self._build_ui()
        self.refresh_ui()

    def _build_ui(self):
        """Create the main window widgets."""
        self._build_menu()
        self._build_filter_toolbar()

        central = QWidget()
        self.window.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        self.summary_label = QLabel('No board selected')
        self.summary_label.setWordWrap(True)
        root_layout.addWidget(self.summary_label)

        self.scroll_area = PropagatingScrollArea()
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.columns_container = QWidget()
        self.columns_container.setObjectName('ColumnsContainer')
        self.columns_layout = QHBoxLayout(self.columns_container)
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(10)
        self.scroll_area.setWidget(self.columns_container)
        root_layout.addWidget(self.scroll_area, 1)

    def _build_filter_toolbar(self):
        """Create the card search and filter toolbar."""
        toolbar = QToolBar('Card Filters')
        toolbar.setObjectName('FilterToolbar')
        toolbar.setMovable(False)
        self.window.addToolBar(toolbar)

        self.toolbar_search_entry = QLineEdit()
        self.toolbar_search_entry.setObjectName('CardSearchEntry')
        self.toolbar_search_entry.setPlaceholderText('Search cards')
        self.toolbar_search_entry.setClearButtonEnabled(True)
        self.toolbar_search_entry.setFixedWidth(190)
        self.toolbar_search_entry.setToolTip('Search title and description')
        self.toolbar_search_entry.textChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_search_entry)

        self.toolbar_priority_combo = QComboBox()
        self.toolbar_priority_combo.setObjectName('CardPriorityFilter')
        self.toolbar_priority_combo.setFixedWidth(118)
        self.toolbar_priority_combo.setToolTip('Filter by priority')
        self.toolbar_priority_combo.addItem('Priority', '')
        for priority in Priority:
            self.toolbar_priority_combo.addItem(priority_label(priority), priority.value)
        self.toolbar_priority_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_priority_combo)

        self.toolbar_assignee_combo = QComboBox()
        self.toolbar_assignee_combo.setObjectName('CardAssigneeFilter')
        self.toolbar_assignee_combo.setFixedWidth(120)
        self.toolbar_assignee_combo.setToolTip('Filter by assignee')
        self.toolbar_assignee_combo.addItem('Assignee', '')
        self.toolbar_assignee_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_assignee_combo)

        self.toolbar_card_type_combo = QComboBox()
        self.toolbar_card_type_combo.setObjectName('CardTypeFilter')
        self.toolbar_card_type_combo.setFixedWidth(112)
        self.toolbar_card_type_combo.setToolTip('Filter by card type')
        self.toolbar_card_type_combo.addItem('Type', '')
        self.toolbar_card_type_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_card_type_combo)

        self.toolbar_tag_combo = QComboBox()
        self.toolbar_tag_combo.setObjectName('CardTagFilter')
        self.toolbar_tag_combo.setFixedWidth(108)
        self.toolbar_tag_combo.setToolTip('Filter by tag')
        self.toolbar_tag_combo.addItem('Tag', '')
        self.toolbar_tag_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_tag_combo)

        self.toolbar_due_state_combo = QComboBox()
        self.toolbar_due_state_combo.setObjectName('CardDueStateFilter')
        self.toolbar_due_state_combo.setFixedWidth(118)
        self.toolbar_due_state_combo.setToolTip('Filter by due-date state')
        self.toolbar_due_state_combo.addItem('Due', '')
        for due_state in ['Overdue', 'Due Today', 'Due Soon', 'Scheduled', 'Done', 'Start Date Only', 'No Due Date']:
            self.toolbar_due_state_combo.addItem(due_state, due_state)
        self.toolbar_due_state_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_due_state_combo)

        self.toolbar_overdue_checkbox = QCheckBox('Late only')
        self.toolbar_overdue_checkbox.setObjectName('ToolbarLateOnlyCheckbox')
        self.toolbar_overdue_checkbox.setToolTip('Only show overdue cards')
        self.toolbar_overdue_checkbox.toggled.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_overdue_checkbox)

        self.toolbar_clear_filters_button = QPushButton('Clear')
        self.toolbar_clear_filters_button.setObjectName('ClearCardFiltersButton')
        self.toolbar_clear_filters_button.clicked.connect(self.clear_toolbar_filters)
        toolbar.addWidget(self.toolbar_clear_filters_button)

    def _build_menu(self):
        """Create the menu bar."""
        menu_bar = self.window.menuBar()

        self.edit_menu = menu_bar.addMenu('Edit')
        self.edit_menu.addSection('History')
        self.undo_current_board_qaction = self._action('Undo Current Board Action', self.undo_current_board_action, 'Ctrl+Z')
        self.redo_current_board_qaction = self._action('Redo Current Board Action', self.redo_current_board_action, 'Ctrl+Y')
        self.undo_board_management_qaction = self._action('Undo Board Management Action', self.undo_board_management_action, 'Ctrl+Shift+Z')
        self.redo_board_management_qaction = self._action('Redo Board Management Action', self.redo_board_management_action, 'Ctrl+Shift+Y')
        self.edit_menu.addAction(self.undo_current_board_qaction)
        self.edit_menu.addAction(self.redo_current_board_qaction)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.undo_board_management_qaction)
        self.edit_menu.addAction(self.redo_board_management_qaction)

        self.board_menu = menu_bar.addMenu('Boards')
        self.board_menu.addSection('Open')
        self.board_menu.addAction(self._action('New Board', self.create_board, 'Ctrl+N'))
        self.board_menu.addAction(self._action('Switch Board', self.switch_board_prompt, 'Ctrl+O'))
        self.recent_board_menu = self.board_menu.addMenu('Recent Boards')
        self.switch_board_menu = self.board_menu.addMenu('Switch To')
        self.board_menu.addSection('Current Board')
        self.board_menu.addAction(self._action('Refresh Boards', self.refresh_ui, 'F5'))
        self.board_menu.addAction(self._action('Rename Current Board', self.rename_current_board, 'Ctrl+R'))
        self.board_menu.addAction(self._action('Delete Current Board', self.delete_current_board, 'Ctrl+Shift+D'))
        self.board_menu.addSection('Import / Export')
        self.board_menu.addAction(self._action('Load Board From Folder', self.load_board_from_folder, 'Ctrl+Shift+O'))
        self.board_menu.addAction(self._action('Export All Boards', self.export_all_boards, 'Ctrl+Shift+E'))
        self.board_menu.addAction(self._action('Import Boards', self.import_boards, 'Ctrl+Shift+I'))
        self.board_menu.addSection('Overview')
        self.board_menu.addAction(self._action('Due Date View', self.show_due_date_view, 'Ctrl+Shift+T'))
        self.board_menu.addAction(self._action('Board Statistics', self.show_board_statistics, 'Ctrl+I'))
        self.board_menu.addSection('Application')
        self.board_menu.addAction(self._action('Quit', self.window.close, QKeySequence.Quit))

        self.filters_menu = menu_bar.addMenu('Filters')
        self.filters_menu.addSection('Toolbar Filters')
        self.filters_menu.addAction(self._action('Search Cards', self.focus_search_filter, 'Ctrl+F'))
        self.filters_menu.addAction(self._action('Filter by Priority', self.show_priority_filter_popup, 'Ctrl+Shift+P'))
        self.filters_menu.addAction(self._action('Filter by Assignee', self.show_assignee_filter_popup, 'Ctrl+Shift+A'))
        self.filters_menu.addAction(self._action('Filter by Due State', self.show_due_state_filter_popup, 'Ctrl+Shift+L'))
        self.filters_menu.addAction(self._action('Filter by Card Type', self.show_card_type_filter_popup, 'Ctrl+Shift+Y'))
        self.filters_menu.addAction(self._action('Filter by Tag', self.show_tag_filter_popup, 'Ctrl+Shift+G'))
        self.filters_menu.addAction(self._action('Toggle Late Only', self.toggle_late_only_filter, 'Ctrl+Alt+L'))
        self.filters_menu.addSeparator()
        self.filters_menu.addAction(self._action('Clear Filters', self.clear_toolbar_filters, 'Ctrl+Shift+F'))

        card_menu = menu_bar.addMenu('Cards')
        card_menu.addSection('Selected Card')
        card_menu.addAction(self._action('New Card', self.create_card, 'Ctrl+Shift+N'))
        card_menu.addAction(self._action('Add Subcard', self.add_subcard_to_selected_card, 'Ctrl+Shift+J'))
        card_menu.addAction(self._action('Edit Selected Card', self.edit_selected_card, 'Ctrl+E'))
        card_menu.addAction(self._action('Move Selected Card', self.move_selected_card, 'Ctrl+M'))
        card_menu.addAction(self._action('Delete Selected Card', self.delete_selected_card, 'Ctrl+D'))
        card_menu.addSection('Cleanup')
        card_menu.addAction(self._action('Clear Done Cards', self.clear_done_cards, 'Ctrl+Shift+K'))
        card_menu.addSection('Card Types')
        card_menu.addAction(self._action('View Card Types', self.show_card_types_browser))
        card_menu.addAction(self._action('Create Card Type', self.create_card_type))
        card_menu.addAction(self._action('Edit Card Type', self.edit_card_type))
        card_menu.addAction(self._action('Delete Card Type', self.delete_card_type))
        card_menu.addSection('Projects')
        card_menu.addAction(self._action('View Projects', self.show_projects_browser))
        card_menu.addAction(self._action('Create Project', self.create_project))
        card_menu.addAction(self._action('Edit Project', self.edit_project))
        card_menu.addAction(self._action('Delete Project', self.delete_project))

        column_menu = menu_bar.addMenu('Columns')
        column_menu.addSection('Structure')
        column_menu.addAction(self._action('New Column', self.create_column, 'Ctrl+Shift+C'))
        column_menu.addAction(self._action('Edit Selected Column', self.edit_selected_column, 'Ctrl+Alt+R'))
        column_menu.addAction(self._action('Delete Selected Column', self.delete_selected_column, 'Ctrl+Alt+D'))
        column_menu.addSection('Layout')
        column_menu.addAction(self._action('Reorder Columns', self.reorder_columns, 'Ctrl+Alt+O'))

    def _action(self, title: str, callback, shortcut=None) -> QAction:
        """Create a QAction helper."""
        action = QAction(title, self.window)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        return action

    def _history_action_text(self, base_title: str, description: Optional[str]) -> str:
        """Return a menu label for a history action."""
        if not description:
            return base_title
        return f'{base_title}: {description}'

    def _refresh_history_actions(self, board: Optional[KanbanBoard] = None):
        """Sync the history actions with the available undo and redo stacks."""
        current_board = board if board is not None else self.current_board()
        board_can_undo = bool(current_board and not current_board.is_read_only() and current_board.can_undo())
        board_can_redo = bool(current_board and not current_board.is_read_only() and current_board.can_redo())

        undo_board_description = current_board.get_next_undo_description() if board_can_undo else None
        redo_board_description = current_board.get_next_redo_description() if board_can_redo else None
        undo_manager_description = self.board_manager.get_next_undo_description()
        redo_manager_description = self.board_manager.get_next_redo_description()

        self.undo_current_board_qaction.setText(self._history_action_text('Undo Current Board Action', undo_board_description))
        self.redo_current_board_qaction.setText(self._history_action_text('Redo Current Board Action', redo_board_description))
        self.undo_board_management_qaction.setText(self._history_action_text('Undo Board Management Action', undo_manager_description))
        self.redo_board_management_qaction.setText(self._history_action_text('Redo Board Management Action', redo_manager_description))

        self.undo_current_board_qaction.setEnabled(board_can_undo)
        self.redo_current_board_qaction.setEnabled(board_can_redo)
        self.undo_board_management_qaction.setEnabled(self.board_manager.can_undo())
        self.redo_board_management_qaction.setEnabled(self.board_manager.can_redo())

        self.undo_current_board_qaction.setStatusTip(undo_board_description or 'Undo the most recent change on the current board')
        self.redo_current_board_qaction.setStatusTip(redo_board_description or 'Redo the most recently undone change on the current board')
        self.undo_board_management_qaction.setStatusTip(undo_manager_description or 'Undo the most recent board-management change')
        self.redo_board_management_qaction.setStatusTip(redo_manager_description or 'Redo the most recently undone board-management change')

    def _show_history_feedback(self, message: str, timeout_ms: int = 4000):
        """Show transient feedback for history actions."""
        self.window.statusBar().showMessage(message, timeout_ms)

    def _run_current_board_history_action(self, method_name: str, unavailable_message: str, success_prefix: str):
        """Invoke an undo or redo action on the current board."""
        board = self.ensure_writable_board()
        if board is None:
            return

        action = getattr(board, method_name, None)
        if action is None:
            QMessageBox.warning(self.window, 'History Unavailable', 'That action is not available for the current board.')
            return

        description = action()
        if not description:
            self._show_history_feedback(unavailable_message)
            self.refresh_ui()
            return

        self.refresh_ui()
        self._show_history_feedback(f'{success_prefix}: {description}')

    def undo_current_board_action(self):
        """Undo the most recent change on the current board."""
        self._run_current_board_history_action('undo_last_action', 'No board action is available to undo.', 'Undid')

    def redo_current_board_action(self):
        """Redo the most recently undone change on the current board."""
        self._run_current_board_history_action('redo_last_action', 'No board action is available to redo.', 'Redid')

    def _run_board_management_history_action(self, method_name: str, unavailable_message: str, success_prefix: str):
        """Invoke an undo or redo action on the board manager."""
        action = getattr(self.board_manager, method_name)
        description = action()
        if not description:
            self._show_history_feedback(unavailable_message)
            self.refresh_ui()
            return

        current_board_id = self.board_manager.current_board_id
        if current_board_id:
            self._remember_recent_board(current_board_id)
        self.refresh_ui()
        self._show_history_feedback(f'{success_prefix}: {description}')

    def undo_board_management_action(self):
        """Undo the most recent board-management action."""
        self._run_board_management_history_action('undo_last_action', 'No board-management action is available to undo.', 'Undid')

    def redo_board_management_action(self):
        """Redo the most recently undone board-management action."""
        self._run_board_management_history_action('redo_last_action', 'No board-management action is available to redo.', 'Redid')

    def _default_filter_state(self) -> Dict[str, object]:
        """Return the default filter state."""
        return {
            'search': '',
            'priority': '',
            'assignee': '',
            'card_type': '',
            'tag': '',
            'due_state': '',
            'overdue': False,
            'column_search': {},
        }

    def _get_current_filter_state(self) -> Dict[str, object]:
        """Return the filter state for the current board."""
        board_id = self.board_manager.current_board_id
        if not board_id:
            return self._default_filter_state()
        state = self.board_filter_states.get(board_id)
        if state is None:
            state = self._default_filter_state()
            self.board_filter_states[board_id] = state
        return state

    def _filters_active(self) -> bool:
        """Return whether any current board filter is active."""
        state = self._get_current_filter_state()
        return any([
            state['search'],
            state['priority'],
            state['assignee'],
            state['card_type'],
            state['tag'],
            state['due_state'],
            state['overdue'],
        ])

    def _column_search_text(self, column_id: str) -> str:
        """Return the saved in-column search text for the given column."""
        state = self._get_current_filter_state()
        column_search = state.get('column_search') or {}
        return str(column_search.get(column_id, ''))

    def _set_column_search_text(self, column_id: str, value: str):
        """Persist the in-column search text for the given column."""
        state = self._get_current_filter_state()
        column_search = dict(state.get('column_search') or {})
        normalized = value.strip()
        if normalized:
            column_search[column_id] = normalized
        else:
            column_search.pop(column_id, None)
        state['column_search'] = column_search

    def _card_matches_column_search(self, card, search_text: str) -> bool:
        """Return whether a card matches a column-local search string."""
        needle = search_text.lower().strip()
        if not needle:
            return True
        haystacks = [card.title or '', card.description or '', card.project or '', card.assignee or '']
        haystacks.extend(card.tags or [])
        return any(needle in text.lower() for text in haystacks)

    def _set_filter_toolbar_enabled(self, enabled: bool):
        """Enable or disable the filter controls."""
        self.toolbar_search_entry.setEnabled(enabled)
        self.toolbar_priority_combo.setEnabled(enabled)
        self.toolbar_assignee_combo.setEnabled(enabled)
        self.toolbar_card_type_combo.setEnabled(enabled)
        self.toolbar_tag_combo.setEnabled(enabled)
        self.toolbar_due_state_combo.setEnabled(enabled)
        self.toolbar_overdue_checkbox.setEnabled(enabled)
        self.toolbar_clear_filters_button.setEnabled(enabled and self._filters_active())

    def _sync_filter_toolbar(self, board: Optional[KanbanBoard]):
        """Sync the toolbar widgets with the current board's filter state."""
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
                self.toolbar_overdue_checkbox.setChecked(False)
                self._set_filter_toolbar_enabled(False)
                return

            state = self._get_current_filter_state()
            self.toolbar_search_entry.setText(str(state['search']))
            self._set_combo_to_data(self.toolbar_priority_combo, state['priority'])
            self._set_combo_to_data(self.toolbar_assignee_combo, state['assignee'])
            self._set_combo_to_data(self.toolbar_card_type_combo, state['card_type'])
            self._set_combo_to_data(self.toolbar_tag_combo, state['tag'])
            self._set_combo_to_data(self.toolbar_due_state_combo, state['due_state'])
            self.toolbar_overdue_checkbox.setChecked(bool(state['overdue']))
            self._set_filter_toolbar_enabled(True)
        finally:
            self._updating_filter_controls = False

    def _set_combo_to_data(self, combo_box: QComboBox, target_data):
        """Select the combo-box row matching the provided item data."""
        for index in range(combo_box.count()):
            if combo_box.itemData(index) == target_data:
                combo_box.setCurrentIndex(index)
                return
        combo_box.setCurrentIndex(0)

    def _refresh_assignee_filter_options(self, board: Optional[KanbanBoard]):
        """Refresh assignee choices from the current board."""
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
        """Refresh card-type choices from the current board."""
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
        """Refresh tag choices from the current board."""
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
        """Apply the toolbar filter values to the current board."""
        if self._updating_filter_controls or self.board_manager.current_board_id is None:
            return
        self.board_filter_states[self.board_manager.current_board_id] = {
            'search': self.toolbar_search_entry.text().strip(),
            'priority': self.toolbar_priority_combo.currentData() or '',
            'assignee': self.toolbar_assignee_combo.currentData() or '',
            'card_type': self.toolbar_card_type_combo.currentData() or '',
            'tag': self.toolbar_tag_combo.currentData() or '',
            'due_state': self.toolbar_due_state_combo.currentData() or '',
            'overdue': self.toolbar_overdue_checkbox.isChecked(),
        }
        self.selected_card_id = None
        self.refresh_ui()

    def clear_toolbar_filters(self):
        """Clear the active board's search and filter controls."""
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
            self.toolbar_overdue_checkbox.setChecked(False)
        finally:
            self._updating_filter_controls = False
        self.board_filter_states[self.board_manager.current_board_id] = self._default_filter_state()
        self.selected_card_id = None
        self.refresh_ui()

    def focus_search_filter(self):
        """Focus the search control in the filter toolbar."""
        self.toolbar_search_entry.setFocus()
        self.toolbar_search_entry.selectAll()

    def show_priority_filter_popup(self):
        """Open the priority filter dropdown."""
        self.toolbar_priority_combo.setFocus()
        self.toolbar_priority_combo.showPopup()

    def show_assignee_filter_popup(self):
        """Open the assignee filter dropdown."""
        self.toolbar_assignee_combo.setFocus()
        self.toolbar_assignee_combo.showPopup()

    def show_card_type_filter_popup(self):
        """Open the card-type filter dropdown."""
        self.toolbar_card_type_combo.setFocus()
        self.toolbar_card_type_combo.showPopup()

    def show_tag_filter_popup(self):
        """Open the tag filter dropdown."""
        self.toolbar_tag_combo.setFocus()
        self.toolbar_tag_combo.showPopup()

    def show_due_state_filter_popup(self):
        """Open the due-state filter dropdown."""
        self.toolbar_due_state_combo.setFocus()
        self.toolbar_due_state_combo.showPopup()

    def toggle_late_only_filter(self):
        """Toggle the late-only checkbox from the Filters menu."""
        if not self.toolbar_overdue_checkbox.isEnabled():
            return
        self.toolbar_overdue_checkbox.setChecked(not self.toolbar_overdue_checkbox.isChecked())

    def _card_matches_filters(self, board: KanbanBoard, card) -> bool:
        """Return whether a card matches the active board filters."""
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
        if state['overdue'] and not (card.has_past_end_date() and not board.is_card_done(card)):
            return False
        return True

    def _filter_cards(self, board: KanbanBoard, cards: List[object]) -> List[object]:
        """Return the subset of cards matching the active filters."""
        return [card for card in cards if self._card_matches_filters(board, card)]

    def _filter_summary_suffix(self) -> str:
        """Return a readable summary of the current active filters."""
        state = self._get_current_filter_state()
        if not any([state['search'], state['priority'], state['assignee'], state['card_type'], state['tag'], state['due_state'], state['overdue']]):
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
        if state['overdue']:
            parts.append('late only')
        return f" | filtered: {', '.join(parts)}"

    def run(self):
        """Run the application event loop."""
        self.window.show()
        return self.app.exec()

    def prompt_for_locked_board_action(self, file_path: str, lock_details: dict) -> str:
        """Prompt for how to handle a locked board."""
        dialog = QMessageBox(self.window)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle('Board Locked')
        message = ['This board is locked.', '', f'File: {file_path}']
        if lock_details:
            message.append(f"Host: {lock_details.get('hostname', 'unknown')}")
            message.append(f"Opened: {lock_details.get('opened_at', 'unknown')}")
        message.extend(['', 'Choose how to continue.'])
        dialog.setText('\n'.join(message))
        read_only_button = dialog.addButton('Open Read Only', QMessageBox.ButtonRole.AcceptRole)
        delete_button = dialog.addButton('Delete Lock', QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked == read_only_button:
            return 'open_read_only'
        if clicked == delete_button:
            return 'delete_lock'
        return 'cancel'

    def current_board(self) -> Optional[KanbanBoard]:
        """Return the active board if available."""
        return self.board_manager.get_current_board()

    def ensure_board(self) -> Optional[KanbanBoard]:
        """Return the current board or show a warning."""
        board = self.current_board()
        if board is None:
            QMessageBox.warning(self.window, 'No Board Selected', 'Select or create a board first.')
        return board

    def ensure_writable_board(self) -> Optional[KanbanBoard]:
        """Return the current board if it is writable."""
        board = self.ensure_board()
        if board is None:
            return None
        if board.is_read_only():
            QMessageBox.warning(self.window, 'Read Only Board', board.get_read_only_message())
            return None
        return board

    def refresh_ui(self):
        """Refresh the board list, summary, and column view."""
        boards = self.board_manager.get_board_list()
        current_board = self.board_manager.get_current_board()

        self._refresh_board_menus(boards)
        self._sync_filter_toolbar(current_board)

        self._clear_columns()
        if current_board is None:
            if boards and self.board_manager.current_board_id is None:
                if self.board_manager.switch_board(boards[0]['id']):
                    self._remember_recent_board(boards[0]['id'])
                current_board = self.board_manager.get_current_board()
                self._sync_filter_toolbar(current_board)
            else:
                self.selected_card_id = None
                self.selected_column_id = None

        if current_board is None:
            self.summary_label.setText('No board selected')
            self._refresh_history_actions(None)
            return

        stats = current_board.get_board_stats()
        completed_cards = sum(1 for card in current_board.get_all_cards() if current_board.is_card_done(card))
        read_only_suffix = ' | read only' if current_board.is_read_only() else ''
        self.summary_label.setText(
            f"Board: {self._current_board_name()} | {stats['total_cards']} cards | {completed_cards} completed"
            f"{self._filter_summary_suffix()}{read_only_suffix}"
        )
        self._populate_columns(current_board)
        self._refresh_history_actions(current_board)

    def _current_board_name(self) -> str:
        """Return the current board name."""
        for board in self.board_manager.get_board_list():
            if board['is_current']:
                return board['name']
        return 'Unknown'

    def _clear_columns(self):
        """Clear the rendered column widgets."""
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _populate_columns(self, board: KanbanBoard):
        """Render the current board columns."""
        for column in board.get_columns_ordered():
            self.columns_layout.addWidget(self._create_column_widget(board, column))
        self.columns_layout.addStretch(1)

    def _create_column_widget(self, board: KanbanBoard, column: CustomColumn) -> QWidget:
        """Create a widget for a board column."""
        column_id = column_identifier(column)
        accent_color = resolve_hex_color(column_color(column), '#8f4a1d')
        column_box = ColumnGroupBox(
            '',
            column_id,
            self,
            selected=column_id == self.selected_column_id,
        )
        layout = QVBoxLayout(column_box)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(10)

        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        title_button = ColumnTitleButton(
            column_label(column),
            click_callback=lambda _checked=False, cid=column_id: self.select_column(cid),
            double_click_callback=lambda cid=column_id: self.handle_column_double_click(cid),
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
            filtered_cards = [
                card for card in self._filter_cards(board, list(column.cards))
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
                )
                item.setSizeHint(card_widget.sizeHint())
                list_widget.addItem(item)
                list_widget.setItemWidget(item, card_widget)
                if card.id == self.selected_card_id:
                    item.setSelected(True)
            count_text = f"{len(filtered_cards)} card" + ('' if len(filtered_cards) == 1 else 's')
            if search_text.strip() or (self._filters_active() and len(filtered_cards) != len(column.cards)):
                count_text = f"{len(filtered_cards)} of {len(column.cards)} cards"
            card_count_label.setText(count_text)
            QTimer.singleShot(0, lambda lw=list_widget: lw.refresh_card_sizes() if isValid(lw) else None)

        column_search_edit.textChanged.connect(lambda value, cid=column_id: self._set_column_search_text(cid, value))
        column_search_edit.textChanged.connect(populate_cards)
        populate_cards(column_search_edit.text())
        layout.addWidget(list_widget, 1)
        column_box.setMinimumWidth(280)
        return column_box

    def on_card_clicked(self, column_id: str, item: QListWidgetItem):
        """Track the selected card and column."""
        payload = item.data(Qt.ItemDataRole.UserRole) or {}
        self.selected_column_id = column_id
        self.selected_card_id = payload.get('card_id')
        self.refresh_ui()

    def handle_column_double_click(self, column_id: str):
        """Select a column and open its edit dialog from a double-click."""
        self.selected_column_id = column_id
        self.selected_card_id = None
        self.edit_selected_column()

    def select_card_from_tile(self, column_id: str, card_id: str):
        """Track the selected card from a direct card-tile click."""
        self.selected_column_id = column_id
        self.selected_card_id = card_id
        self.refresh_ui()

    def edit_card_from_tile(self, column_id: str, card_id: str):
        """Edit a card from a direct card-tile double-click."""
        self.selected_column_id = column_id
        self.selected_card_id = card_id
        self.edit_selected_card()

    def handle_card_tile_action(self, column_id: str, card_id: str, action: str):
        """Run a context-menu action requested from a card tile."""
        self.selected_column_id = column_id
        self.selected_card_id = card_id
        if action == 'add_subcard':
            self.add_subcard_to_selected_card()

    def select_column(self, column_id: str):
        """Track the selected column."""
        self.selected_column_id = column_id
        self.selected_card_id = None
        self.refresh_ui()

    def handle_card_drop(self, card_id: Optional[str], source_column_id: Optional[str], target_column_id: Optional[str]):
        """Move a card between columns from a drag-drop gesture."""
        if not card_id or not target_column_id:
            return
        board = self.ensure_writable_board()
        if board is None:
            return
        target_value = resolve_column_target(board, target_column_id)
        if target_value is None:
            return
        if source_column_id == target_column_id:
            self.selected_column_id = target_column_id
            self.selected_card_id = card_id
            self.refresh_ui()
            return
        board.move_card(card_id, target_value)
        self.selected_column_id = target_column_id
        self.selected_card_id = card_id
        self.refresh_ui()

    def handle_column_drop(self, dragged_column_id: Optional[str], target_column_id: Optional[str], insert_after: bool):
        """Reorder columns from a drag-drop gesture."""
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
        """Attach dropped files to a card."""
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
        """Refresh the dynamic board menus."""
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
        """Refresh the recent-boards submenu."""
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
        """Track recently opened boards for menu access."""
        if not board_id:
            return
        self.recent_board_ids = [existing_id for existing_id in self.recent_board_ids if existing_id != board_id]
        self.recent_board_ids.insert(0, board_id)
        self.recent_board_ids = self.recent_board_ids[:self.max_recent_boards]

    def _switch_board_by_id(self, board_id: str):
        """Switch to a board by ID and refresh the UI."""
        if board_id and board_id != self.board_manager.current_board_id:
            if self.board_manager.switch_board(board_id):
                self._remember_recent_board(board_id)
                self.refresh_ui()

    def switch_board_prompt(self):
        """Prompt for a board to switch to."""
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

    def create_board(self):
        """Create a new board."""
        dialog = BoardDialog(self.board_manager.boards_directory, self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        board_id = self.board_manager.create_board(values['name'], values['description'], target_directory=values['storage_dir'])
        self._switch_board_by_id(board_id)

    def rename_current_board(self):
        """Rename the current board."""
        boards = self.board_manager.get_board_list()
        current = next((board for board in boards if board['is_current']), None)
        if current is None:
            return
        new_name, ok = QInputDialog.getText(self.window, 'Rename Board', 'New name', text=current['name'])
        if ok and new_name.strip():
            self.board_manager.rename_board(current['id'], new_name.strip())
            self.refresh_ui()

    def delete_current_board(self):
        """Delete the current board."""
        boards = self.board_manager.get_board_list()
        current = next((board for board in boards if board['is_current']), None)
        if current is None:
            return
        result = QMessageBox.question(
            self.window,
            'Delete Board',
            f"Delete board '{current['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self.board_manager.delete_board(current['id'])
            self.refresh_ui()

    def show_board_statistics(self):
        """Show overall board statistics."""
        boards = self.board_manager.get_board_list()
        if not boards:
            QMessageBox.information(self.window, 'Statistics', 'No boards available.')
            return
        total_cards = 0
        lines = []
        for board_info in boards:
            board = self.board_manager.boards.get(board_info['id'])
            if board is None and board_info['is_current']:
                board = self.board_manager.get_current_board()
            if board is not None:
                stats = board.get_board_stats()
                total_cards += stats['total_cards']
                lines.append(f"{board_info['name']}: {stats['total_cards']} cards")
            else:
                lines.append(f"{board_info['name']}: not loaded")
        lines.append('')
        lines.append(f'Total boards: {len(boards)}')
        lines.append(f'Total cards: {total_cards}')
        QMessageBox.information(self.window, 'Board Statistics', '\n'.join(lines))

    def _choose_card_type(self, board: KanbanBoard, title: str, prompt: str,
                          exclude_default: bool = False, exclude_ids: Optional[set[str]] = None) -> Optional[CardType]:
        """Prompt the user to select a card type from the current board."""
        exclude_ids = set(exclude_ids or set())
        card_types = [
            card_type
            for card_type in board.get_card_types_ordered()
            if (not exclude_default or card_type.id != board.get_default_card_type_id()) and card_type.id not in exclude_ids
        ]
        if not card_types:
            QMessageBox.information(self.window, title, 'No card types available.')
            return None

        option_map: Dict[str, CardType] = {}
        for card_type in card_types:
            label = card_type.name
            if card_type.id == board.get_default_card_type_id():
                label += ' [default]'
            if card_type.id == board.get_last_used_card_type().id:
                label += ' [last used]'
            option_map[label] = card_type

        selected, ok = QInputDialog.getItem(self.window, title, prompt, list(option_map.keys()), editable=False)
        if not ok or not selected:
            return None
        return option_map[selected]

    def show_card_types_browser(self):
        """Show the current board card types and presets."""
        board = self.ensure_board()
        if board is None:
            return
        dialog = CardTypesBrowserDialog(board, self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_card_type_id:
            self.edit_card_type_by_id(dialog.selected_card_type_id)

    def create_card_type(self):
        """Create a new card type for the current board."""
        board = self.ensure_writable_board()
        if board is None:
            return
        dialog = CardTypeDialog(board=board, parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            board.create_card_type(
                values['name'],
                values['description'],
                values['default_project'],
                values['default_color'],
            )
        except ValueError as error:
            QMessageBox.warning(self.window, 'Create Card Type', str(error))
            return
        self.refresh_ui()

    def edit_card_type(self):
        """Edit an existing card type on the current board."""
        board = self.ensure_writable_board()
        if board is None:
            return
        card_type = self._choose_card_type(board, 'Edit Card Type', 'Card type')
        if card_type is None:
            return
        self._edit_card_type(board, card_type)

    def edit_card_type_by_id(self, card_type_id: str):
        """Edit a specific card type by identifier."""
        board = self.ensure_writable_board()
        if board is None:
            return
        card_type = next((item for item in board.get_card_types_ordered() if item.id == card_type_id), None)
        if card_type is None:
            QMessageBox.information(self.window, 'Card Type', 'The selected card type no longer exists.')
            return
        self._edit_card_type(board, card_type)

    def _edit_card_type(self, board: KanbanBoard, card_type: CardType):
        """Edit the provided card type."""
        is_default = card_type.id == board.get_default_card_type_id()
        dialog = CardTypeDialog(card_type=card_type, is_default=is_default, board=board, parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            board.edit_card_type(
                card_type.id,
                None if is_default else values['name'],
                values['description'],
                default_project=values['default_project'],
                default_color=values['default_color'],
            )
        except ValueError as error:
            QMessageBox.warning(self.window, 'Edit Card Type', str(error))
            return
        self.refresh_ui()

    def delete_card_type(self):
        """Delete a card type, optionally reassigning or deleting its cards."""
        board = self.ensure_writable_board()
        if board is None:
            return
        card_type = self._choose_card_type(board, 'Delete Card Type', 'Card type', exclude_default=True)
        if card_type is None:
            return

        cards_using_type = board.get_cards_by_type(card_type.id)
        if not cards_using_type:
            result = QMessageBox.question(
                self.window,
                'Delete Card Type',
                f"Delete card type '{card_type.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return
            try:
                board.delete_card_type(card_type.id, delete_cards=False)
            except ValueError as error:
                QMessageBox.warning(self.window, 'Delete Card Type', str(error))
                return
            self.refresh_ui()
            return

        dialog = QMessageBox(self.window)
        dialog.setWindowTitle('Delete Card Type')
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText(
            f"Card type '{card_type.name}' is used by {len(cards_using_type)} card(s). Choose what to do with those cards."
        )
        reassign_button = dialog.addButton('Reassign Cards', QMessageBox.ButtonRole.AcceptRole)
        delete_cards_button = dialog.addButton('Delete Cards', QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked == reassign_button:
            replacement = self._choose_card_type(
                board,
                'Replacement Card Type',
                'Reassign cards to',
                exclude_ids={card_type.id},
            )
            if replacement is None:
                return
            try:
                board.delete_card_type(card_type.id, delete_cards=False, replacement_type_id=replacement.id)
            except ValueError as error:
                QMessageBox.warning(self.window, 'Delete Card Type', str(error))
                return
            self.refresh_ui()
            return

        if clicked == delete_cards_button:
            confirm = QMessageBox.question(
                self.window,
                'Delete Cards',
                f"Delete card type '{card_type.name}' and all {len(cards_using_type)} card(s) using it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            try:
                board.delete_card_type(card_type.id, delete_cards=True)
            except ValueError as error:
                QMessageBox.warning(self.window, 'Delete Card Type', str(error))
                return
            self.refresh_ui()

    def _choose_project(self, board: KanbanBoard, title: str, prompt: str,
                        exclude_ids: Optional[set[str]] = None) -> Optional[Project]:
        """Prompt the user to select a managed project from the current board."""
        exclude_ids = set(exclude_ids or set())
        projects = [project for project in board.get_projects_ordered() if project.id not in exclude_ids]
        if not projects:
            QMessageBox.information(self.window, title, 'No projects available.')
            return None

        option_map: Dict[str, Project] = {}
        for project in projects:
            option_map[project.name] = project

        selected, ok = QInputDialog.getItem(self.window, title, prompt, list(option_map.keys()), editable=False)
        if not ok or not selected:
            return None
        return option_map[selected]

    def show_projects_browser(self):
        """Show the current board's managed projects."""
        board = self.ensure_board()
        if board is None:
            return
        dialog = ProjectsBrowserDialog(board, self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_project_id:
            self.edit_project_by_id(dialog.selected_project_id)

    def create_project(self):
        """Create a managed project for the current board."""
        board = self.ensure_writable_board()
        if board is None:
            return
        dialog = ProjectDialog(parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            board.create_project(values['name'], values['description'])
        except ValueError as error:
            QMessageBox.warning(self.window, 'Create Project', str(error))
            return
        self.refresh_ui()

    def edit_project(self):
        """Edit a managed project on the current board."""
        board = self.ensure_writable_board()
        if board is None:
            return
        project = self._choose_project(board, 'Edit Project', 'Project')
        if project is None:
            return
        self._edit_project(board, project)

    def edit_project_by_id(self, project_id: str):
        """Edit a specific managed project by identifier."""
        board = self.ensure_writable_board()
        if board is None:
            return
        project = board.get_project(project_id)
        if project is None:
            QMessageBox.information(self.window, 'Project', 'The selected project no longer exists.')
            return
        self._edit_project(board, project)

    def _edit_project(self, board: KanbanBoard, project: Project):
        """Edit the provided managed project."""
        dialog = ProjectDialog(project=project, parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            board.edit_project(project.id, values['name'], values['description'])
        except ValueError as error:
            QMessageBox.warning(self.window, 'Edit Project', str(error))
            return
        self.refresh_ui()

    def delete_project(self):
        """Delete a project, optionally reassigning or deleting referenced cards."""
        board = self.ensure_writable_board()
        if board is None:
            return
        project = self._choose_project(board, 'Delete Project', 'Project')
        if project is None:
            return

        cards_using_project = board.get_cards_by_project(project.id)
        card_types_using_project = board.get_card_types_by_project(project.id)
        if not cards_using_project and not card_types_using_project:
            result = QMessageBox.question(
                self.window,
                'Delete Project',
                f"Delete project '{project.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return
            try:
                board.delete_project(project.id, delete_cards=False)
            except ValueError as error:
                QMessageBox.warning(self.window, 'Delete Project', str(error))
                return
            self.refresh_ui()
            return

        dialog = QMessageBox(self.window)
        dialog.setWindowTitle('Delete Project')
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText(
            f"Project '{project.name}' is used by {len(cards_using_project)} card(s) and {len(card_types_using_project)} card type preset(s). Choose what to do with those references."
        )
        reassign_button = dialog.addButton('Reassign References', QMessageBox.ButtonRole.AcceptRole)
        clear_references_button = dialog.addButton('Clear References', QMessageBox.ButtonRole.ActionRole)
        delete_cards_button = dialog.addButton('Delete Cards', QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked == reassign_button:
            replacement = self._choose_project(
                board,
                'Replacement Project',
                'Reassign references to',
                exclude_ids={project.id},
            )
            if replacement is None:
                return
            try:
                board.delete_project(project.id, delete_cards=False, replacement_project_id=replacement.id)
            except ValueError as error:
                QMessageBox.warning(self.window, 'Delete Project', str(error))
                return
            self.refresh_ui()
            return

        if clicked == clear_references_button:
            try:
                board.delete_project(project.id, delete_cards=False)
            except ValueError as error:
                QMessageBox.warning(self.window, 'Delete Project', str(error))
                return
            self.refresh_ui()
            return

        if clicked == delete_cards_button:
            confirm = QMessageBox.question(
                self.window,
                'Delete Cards',
                f"Delete project '{project.name}' and all {len(cards_using_project)} card(s) using it? Card type presets will be cleared.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            try:
                board.delete_project(project.id, delete_cards=True)
            except ValueError as error:
                QMessageBox.warning(self.window, 'Delete Project', str(error))
                return
            self.refresh_ui()

    def show_due_date_view(self):
        """Show the active board's due-date overview dialog."""
        board = self.ensure_board()
        if board is None:
            return

        dialog = DueDateViewDialog(board, self._current_board_name(), self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not dialog.selected_card_id:
            return

        self.selected_column_id = dialog.selected_column_id
        self.selected_card_id = dialog.selected_card_id
        self.refresh_ui()

    def export_all_boards(self):
        """Export all boards to a JSON backup file."""
        file_name = choose_save_file_dialog(self.window, 'Export All Boards', 'kanban_backup.json', 'JSON Files (*.json)')
        if not file_name:
            return
        export_data = self.board_manager.export_all_boards()
        with open(file_name, 'w', encoding='utf-8') as output_file:
            json.dump(export_data, output_file, indent=2, ensure_ascii=False)
        QMessageBox.information(self.window, 'Export Complete', f'Exported boards to {file_name}.')

    def import_boards(self):
        """Import boards from a JSON backup file."""
        file_name = choose_open_file_dialog(self.window, 'Import Boards', '', 'JSON Files (*.json)')
        if not file_name:
            return
        result = QMessageBox.question(
            self.window,
            'Import Boards',
            'Importing will replace the current board registry. Continue?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        with open(file_name, 'r', encoding='utf-8') as input_file:
            import_data = json.load(input_file)
        if self.board_manager.import_boards(import_data):
            self.refresh_ui()

    def _discover_boards_in_folder(self, folder: str) -> Dict[str, Dict[str, object]]:
        """Return available board files from a folder."""
        option_map: Dict[str, Dict[str, object]] = {}
        metadata_path = os.path.join(folder, 'boards_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
                metadata = json.load(metadata_file)
            for board_id, board_info in metadata.get('boards', {}).items():
                if board_info.get('use_custom_columns') is False:
                    continue
                data_file = board_info.get('data_file')
                if not data_file:
                    continue
                if not os.path.isabs(data_file):
                    data_file = os.path.join(folder, data_file)
                label = board_info.get('name', board_id)
                option_map[label] = {
                    'data_file': data_file,
                    'name': board_info.get('name', label),
                    'description': board_info.get('description', ''),
                }
        else:
            for entry in sorted(os.listdir(folder)):
                if not entry.endswith('.json') or entry == 'boards_metadata.json' or entry.endswith('.backup.json'):
                    continue
                try:
                    inspected = self.board_manager.inspect_board_file(os.path.join(folder, entry))
                except ValueError:
                    continue
                label = inspected['name']
                if label in option_map:
                    label = f"{label} ({entry})"
                option_map[label] = {
                    'data_file': inspected['data_file'],
                    'name': inspected['name'],
                    'description': '',
                }
        return option_map

    def load_board_from_folder(self):
        """Load a board file from an external folder."""
        folder = choose_existing_directory_dialog(self.window, 'Select Folder Containing a Board')
        if not folder:
            return
        option_map = self._discover_boards_in_folder(folder)
        if not option_map:
            QMessageBox.information(self.window, 'No Boards Found', 'No board files were found in the selected folder.')
            return
        options = list(option_map.keys())
        selected, ok = QInputDialog.getItem(self.window, 'Load Board From Folder', 'Board', options, editable=False)
        if not ok or not selected:
            return
        board_choice = option_map[selected]
        board_id = self.board_manager.add_external_board(
            board_choice['data_file'],
            name=board_choice['name'],
            description=board_choice['description'],
            switch_to=True,
        )
        if board_id:
            self.refresh_ui()

    def create_card(self, column_id: Optional[str] = None):
        """Create a card on the current board."""
        board = self.ensure_writable_board()
        if board is None:
            return
        target_column = column_id or self.selected_column_id or board.get_default_add_card_column_id()
        dialog = CardDialog(board, target_column_id=target_column, parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        board.create_card(
            values['title'],
            values['description'],
            values['priority'],
            values['column_id'],
            values['project'] or None,
            values['start_date'],
            values['end_date'],
            None,
            values['color'],
            values['card_type_id'],
            values['assignee'] or None,
            values['tags'],
        )
        self.refresh_ui()

    def add_subcard_to_selected_card(self):
        """Create a subcard under the currently selected top-level card."""
        board = self.ensure_writable_board()
        if board is None:
            return
        parent_card = self._selected_card()
        if parent_card is None:
            QMessageBox.information(self.window, 'No Card Selected', 'Select a parent card first.')
            return
        if parent_card.parent_id:
            QMessageBox.information(self.window, 'Add Subcard', 'Nested subcards are not supported.')
            return

        dialog = CardDialog(
            board,
            target_column_id=parent_card.column_id,
            parent_card=parent_card,
            parent=self.window,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            if dialog.did_mutate_board:
                self.refresh_ui()
            return
        values = dialog.values()
        try:
            created = board.create_subcard(
                parent_card.id,
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
            QMessageBox.warning(self.window, 'Add Subcard', str(error))
            return
        self.selected_card_id = created.id
        self.refresh_ui()

    def _selected_card(self):
        """Return the selected card from the current board."""
        board = self.current_board()
        if board is None or not self.selected_card_id:
            return None
        return board.find_card(self.selected_card_id)

    def edit_selected_card(self):
        """Edit the selected card."""
        board = self.ensure_writable_board()
        if board is None:
            return
        card = self._selected_card()
        if card is None:
            QMessageBox.information(self.window, 'No Card Selected', 'Select a card first.')
            return
        original_column_id = card.column_id
        dialog = CardDialog(board, card=card, parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            if dialog.did_mutate_board:
                self.refresh_ui()
            return
        values = dialog.values()
        board.edit_card(
            card.id,
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
            board.move_card(card.id, values['column_id'])
        self.refresh_ui()

    def delete_selected_card(self):
        """Delete the selected card."""
        board = self.ensure_writable_board()
        if board is None:
            return
        card = self._selected_card()
        if card is None:
            QMessageBox.information(self.window, 'No Card Selected', 'Select a card first.')
            return
        result = QMessageBox.question(
            self.window,
            'Delete Card',
            f"Delete '{card.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            board.delete_card(card.id)
            self.refresh_ui()

    def move_selected_card(self):
        """Move the selected card to a different column."""
        board = self.ensure_writable_board()
        if board is None:
            return
        card = self._selected_card()
        if card is None:
            QMessageBox.information(self.window, 'No Card Selected', 'Select a card first.')
            return
        current_column_token = card.column_id
        choices = [column_label(column) for column in board.get_columns_ordered() if column_identifier(column) != current_column_token]
        if not choices:
            return
        selected, ok = QInputDialog.getItem(self.window, 'Move Card', 'Target Column', choices, editable=False)
        if not ok or not selected:
            return
        for column in board.get_columns_ordered():
            if column_label(column) == selected:
                board.move_card(card.id, column_target_value(column))
                self.refresh_ui()
                return

    def clear_done_cards(self):
        """Clear cards from completed columns."""
        board = self.ensure_writable_board()
        if board is None:
            return
        removed_count = board.clear_done_cards()
        QMessageBox.information(self.window, 'Clear Done Cards', f'Removed {removed_count} cards.')
        self.refresh_ui()

    def _selected_column(self) -> Optional[CustomColumn]:
        """Return the selected column from the current board."""
        board = self.current_board()
        if board is None:
            return None
        if self.selected_column_id:
            return board.get_column_by_id(self.selected_column_id)
        ordered_columns = board.get_columns_ordered()
        return ordered_columns[0] if ordered_columns else None

    def create_column(self):
        """Create a new column."""
        board = self.ensure_writable_board()
        if board is None:
            return
        dialog = ColumnDialog(parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        column_id = board.create_column(
            values['name'],
            color=values['color'],
            is_completed=values['is_completed'],
            can_add_card=values['can_add_card'],
        )
        self.selected_column_id = column_id
        self.refresh_ui()

    def edit_selected_column(self):
        """Edit the selected column."""
        board = self.ensure_writable_board()
        if board is None:
            return
        column = self._selected_column()
        if column is None:
            return
        dialog = ColumnDialog(column, self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        board.update_column(
            column.id,
            name=values['name'],
            color=values['color'],
            is_completed=values['is_completed'],
            can_add_card=values['can_add_card'],
        )
        self.refresh_ui()

    def delete_selected_column(self):
        """Delete the selected column."""
        board = self.ensure_writable_board()
        if board is None:
            return
        column = self._selected_column()
        if column is None:
            return
        if len(board.get_columns_ordered()) <= 1:
            QMessageBox.warning(self.window, 'Cannot Delete Column', 'A board must keep at least one column.')
            return
        move_target = None
        if column.cards:
            choices = [other.name for other in board.get_columns_ordered() if other.id != column.id]
            selected, ok = QInputDialog.getItem(self.window, 'Delete Column', 'Move cards to', choices, editable=False)
            if not ok or not selected:
                return
            move_target = next(other.id for other in board.get_columns_ordered() if other.name == selected)
        result = QMessageBox.question(
            self.window,
            'Delete Column',
            f"Delete column '{column.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            board.delete_column(column.id, move_cards_to=move_target)
            self.selected_column_id = None
            self.refresh_ui()

    def reorder_columns(self):
        """Reorder board columns."""
        board = self.ensure_writable_board()
        if board is None:
            return
        dialog = ReorderColumnsDialog(board.get_columns_ordered(), self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        board.reorder_columns(dialog.ordered_ids())
        self.refresh_ui()
