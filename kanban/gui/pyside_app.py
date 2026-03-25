## @file
#  @brief PySide6-based multi-board GUI for the Kanban application.
"""PySide6 GUI implementation for the multi-board Kanban manager."""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from typing import Dict, List, Optional

from PySide6.QtCore import QDate, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from ..board import KanbanBoard
from ..board_manager import BoardManager
from ..models import CardType, CustomColumn, Priority


WINDOW_STYLE = """
QMainWindow {
    background: #f5efe4;
}
QDialog, QMessageBox, QInputDialog {
    background: #fbf5ea;
}
QWidget {
    font-size: 10pt;
    color: #2d241c;
}
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #2d241c;
    background: transparent;
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
    spacing: 8px;
    padding: 6px 10px;
}
QToolBar#FilterToolbar QLabel {
    color: #4c3f33;
    font-weight: 600;
    background: transparent;
}
QToolBar#FilterToolbar QLineEdit,
QToolBar#FilterToolbar QComboBox,
QToolBar#FilterToolbar QCheckBox {
    margin: 0 2px;
}
QLineEdit#CardSearchEntry {
    min-width: 220px;
    background: #fffdf9;
}
QComboBox#CardPriorityFilter,
QComboBox#CardAssigneeFilter,
QComboBox#CardTypeFilter,
QComboBox#CardTagFilter,
QComboBox#CardDueStateFilter,
QComboBox#DueFilterCombo {
    min-width: 150px;
    background: #fffdf9;
}
QPushButton#ClearCardFiltersButton {
    padding: 6px 10px;
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
QComboBox::drop-down {
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
QComboBox QAbstractItemView,
QInputDialog QComboBox QAbstractItemView {
    background: #fffaf2;
    color: #2d241c;
    border: 1px solid #ac9571;
    border-radius: 10px;
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
    return compact[: limit - 1].rstrip() + '…'


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


class OptionalDateField(QWidget):
    """A checkbox-controlled date input."""

    def __init__(self, label: str, initial_value: Optional[date] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.checkbox = QCheckBox(label)
        self.editor = QDateEdit()
        self.editor.setCalendarPopup(True)
        self.editor.setDisplayFormat('yyyy-MM-dd')
        self.editor.setEnabled(initial_value is not None)

        initial_qdate = QDate.currentDate()
        if initial_value is not None:
            initial_qdate = QDate(initial_value.year, initial_value.month, initial_value.day)
            self.checkbox.setChecked(True)
        self.editor.setDate(initial_qdate)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.editor)
        self.checkbox.toggled.connect(self.editor.setEnabled)

    def value(self) -> Optional[date]:
        """Return the selected date, if enabled."""
        if not self.checkbox.isChecked():
            return None
        selected = self.editor.date()
        return date(selected.year(), selected.month(), selected.day())


class CardTile(QFrame):
    """Structured card widget used inside each column list."""

    def __init__(self, board: KanbanBoard, card, selected: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.board = board
        self.card = card
        self.selected = selected

        self.background = resolve_hex_color(card.color, '#fffaf3')
        self.foreground = contrasting_text_color(self.background)
        self.muted = secondary_text_color(self.background)
        self.priority_color = priority_accent(card.priority)
        self.border_color = '#7d3b14' if selected else ('#a63c30' if card.has_past_end_date() and not board.is_card_done(card) else '#d7c4aa')

        self.setObjectName('CardTile')
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        priority_bar = QFrame()
        priority_bar.setFixedHeight(5)
        priority_bar.setStyleSheet(f'background: {self.priority_color}; border-radius: 2px;')
        layout.addWidget(priority_bar)

        title_label = QLabel(self.card.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f'font-size: 11pt; font-weight: 700; color: {self.foreground}; background: transparent;')
        layout.addWidget(title_label)

        description = clipped_description(self.card.description)
        if description:
            description_label = QLabel(description)
            description_label.setWordWrap(True)
            description_label.setStyleSheet(f'color: {self.muted}; background: transparent; line-height: 1.3;')
            layout.addWidget(description_label)

        details = []
        card_type = self.board.get_card_type(self.card.card_type_id)
        if card_type is None:
            card_type = self.board.get_default_card_type()
        details.append(priority_label(self.card.priority))
        if card_type is not None:
            details.append(card_type.name)
        if self.card.project:
            details.append(self.card.project)
        if self.card.assignee:
            details.append(f'@{self.card.assignee}')
        if details:
            details_label = QLabel(' | '.join(details))
            details_label.setWordWrap(True)
            details_label.setStyleSheet(f'color: {self.muted}; background: transparent; font-weight: 600;')
            layout.addWidget(details_label)

        schedule_parts = []
        schedule_text = schedule_summary(self.card)
        if schedule_text:
            schedule_parts.append(schedule_text)
        if self.card.has_past_end_date() and not self.board.is_card_done(self.card):
            schedule_parts.append('Late')
        parent_card = self.board.get_parent_card(self.card)
        if parent_card is not None:
            schedule_parts.append(f'Subcard of {parent_card.title}')
        else:
            completed, total = self.board.get_subcard_progress(self.card.id)
            if total:
                schedule_parts.append(f'Subcards {completed}/{total}')
        if schedule_parts:
            schedule_label = QLabel(' | '.join(schedule_parts))
            schedule_label.setWordWrap(True)
            schedule_label.setStyleSheet(f'color: {self.muted}; background: transparent;')
            layout.addWidget(schedule_label)

        if self.card.tags:
            tags_label = QLabel(' '.join(f'#{tag}' for tag in self.card.tags))
            tags_label.setWordWrap(True)
            tags_label.setStyleSheet(f'color: {self.foreground}; background: transparent; font-weight: 600;')
            layout.addWidget(tags_label)

        extras = []
        if self.card.notes:
            extras.append(f'{len(self.card.notes)} note' + ('' if len(self.card.notes) == 1 else 's'))
        if self.card.attachments:
            extras.append(f'{len(self.card.attachments)} attachment' + ('' if len(self.card.attachments) == 1 else 's'))
        if extras:
            extras_label = QLabel(' | '.join(extras))
            extras_label.setWordWrap(True)
            extras_label.setStyleSheet(f'color: {self.muted}; background: transparent;')
            layout.addWidget(extras_label)

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QFrame#CardTile {{
                background: {self.background};
                border: 2px solid {self.border_color};
                border-radius: 12px;
            }}
            """
        )

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), max(hint.height(), 132))


class CardListWidget(QListWidget):
    """List widget that keeps custom card tiles sized to the column width."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_card_sizes()

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
            item.setSizeHint(QSize(available_width, widget.sizeHint().height()))


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

        self.table = QTableWidget(0, 7)
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
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(90)
        self.directory_edit = QLineEdit(default_directory)
        browse_button = QPushButton('Browse')
        browse_button.clicked.connect(self.choose_directory)

        directory_row = QWidget()
        directory_layout = QHBoxLayout(directory_row)
        directory_layout.setContentsMargins(0, 0, 0, 0)
        directory_layout.addWidget(self.directory_edit)
        directory_layout.addWidget(browse_button)

        form = QFormLayout(self)
        form.addRow('Name', self.name_edit)
        form.addRow('Description', self.description_edit)
        form.addRow('Storage Folder', directory_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def choose_directory(self):
        """Choose a storage directory."""
        directory = QFileDialog.getExistingDirectory(self, 'Select Board Storage Folder', self.directory_edit.text())
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
        self.name_edit = QLineEdit(column.name if column else '')
        self.color_edit = QLineEdit(column.color if column else '#2196F3')
        self.completed_check = QCheckBox('Completed column')
        self.completed_check.setChecked(bool(column and column.is_completed))
        self.add_card_check = QCheckBox('Show add-card action')
        self.add_card_check.setChecked(bool(column and column.can_add_card))
        color_button = QPushButton('Pick Color')
        color_button.clicked.connect(self.choose_color)

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self.color_edit)
        color_layout.addWidget(color_button)

        form = QFormLayout(self)
        form.addRow('Name', self.name_edit)
        form.addRow('Color', color_row)
        form.addRow('', self.completed_check)
        form.addRow('', self.add_card_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def choose_color(self):
        """Choose a column color."""
        color = QColorDialog.getColor(QColor(self.color_edit.text() or '#2196F3'), self, 'Choose Column Color')
        if color.isValid():
            self.color_edit.setText(color.name())

    def values(self) -> Dict[str, object]:
        """Return dialog values."""
        return {
            'name': self.name_edit.text().strip(),
            'color': self.color_edit.text().strip() or '#2196F3',
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
        self.columns = list(columns)
        self.list_widget = QListWidget()
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

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addWidget(button_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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

    def __init__(self, card_type: Optional[CardType] = None, is_default: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.card_type = card_type
        self.is_default = is_default
        self.setWindowTitle('Edit Card Type' if card_type else 'Create Card Type')

        self.name_edit = QLineEdit(card_type.name if card_type else '')
        self.name_edit.setEnabled(not is_default)
        self.description_edit = QTextEdit(card_type.description if card_type else '')
        self.description_edit.setFixedHeight(100)
        self.project_edit = QLineEdit(card_type.default_project or '' if card_type else '')
        self.color_edit = QLineEdit(card_type.default_color or '' if card_type else '')
        color_button = QPushButton('Pick Color')
        color_button.clicked.connect(self.choose_color)
        clear_color_button = QPushButton('Clear')
        clear_color_button.clicked.connect(lambda: self.color_edit.clear())

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self.color_edit)
        color_layout.addWidget(color_button)
        color_layout.addWidget(clear_color_button)

        info_label = QLabel('Card types can define reusable project and color presets. The default type cannot be renamed or deleted.')
        info_label.setWordWrap(True)

        layout = QFormLayout(self)
        layout.addRow('Name', self.name_edit)
        layout.addRow('Description', self.description_edit)
        layout.addRow('Project Preset', self.project_edit)
        layout.addRow('Color Preset', color_row)
        layout.addRow('', info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def choose_color(self):
        """Choose a preset color."""
        initial = self.color_edit.text().strip() or '#ffffff'
        color = QColorDialog.getColor(QColor(initial), self, 'Choose Card Type Color')
        if color.isValid():
            self.color_edit.setText(color.name())

    def values(self) -> Dict[str, Optional[str]]:
        """Return the dialog values."""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'default_project': self.project_edit.text().strip() or None,
            'default_color': self.color_edit.text().strip() or None,
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
        self.setWindowTitle('Card Types')
        self.resize(860, 520)

        layout = QVBoxLayout(self)

        intro = QLabel('Browse the reusable card types configured for this board, including project presets, color presets, and usage counts.')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Name', 'Description', 'Project Preset', 'Color Preset', 'Cards', 'Flags'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
            label.setText(resolved)
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


class CardDialog(QDialog):
    """Dialog for creating or editing a card."""

    def __init__(self, board: KanbanBoard, card=None, target_column_id: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.board = board
        self.card = card
        self.setWindowTitle('Edit Card' if card else 'Create Card')

        self.title_edit = QLineEdit(card.title if card else '')
        self.description_edit = QTextEdit(card.description if card else '')
        self.description_edit.setFixedHeight(120)

        self.priority_combo = QComboBox()
        for priority in Priority:
            self.priority_combo.addItem(priority_label(priority), priority)
        if card:
            self.priority_combo.setCurrentIndex(list(Priority).index(card.priority))

        self.column_combo = QComboBox()
        for column in board.get_columns_ordered():
            self.column_combo.addItem(column.name, column.id)
        desired_column = target_column_id or (card.column_id if card else board.get_default_add_card_column_id())
        if desired_column:
            for index in range(self.column_combo.count()):
                if self.column_combo.itemData(index) == desired_column:
                    self.column_combo.setCurrentIndex(index)
                    break

        self.assignee_edit = QLineEdit(card.assignee or '' if card else '')
        self.project_edit = QLineEdit(card.project or '' if card else '')
        self.tags_edit = QLineEdit(', '.join(card.tags) if card else '')
        self.color_edit = QLineEdit(card.color or '' if card else '')
        color_button = QPushButton('Pick Color')
        color_button.clicked.connect(self.choose_color)
        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self.color_edit)
        color_layout.addWidget(color_button)

        self.start_date = OptionalDateField('Start Date', card.start_date if card else None)
        self.end_date = OptionalDateField('End Date', card.end_date if card else None)

        self.card_type_combo = QComboBox()
        for card_type in board.get_card_types_ordered():
            self.card_type_combo.addItem(card_type.name, card_type.id)
        selected_type_id = None
        if card and card.card_type_id:
            selected_type_id = card.card_type_id
        elif not card:
            selected_type_id = board.get_last_used_card_type().id
        if selected_type_id:
            for index in range(self.card_type_combo.count()):
                if self.card_type_combo.itemData(index) == selected_type_id:
                    self.card_type_combo.setCurrentIndex(index)
                    break

        info_label = QLabel('Existing notes and attachments are preserved. Use the CLI for advanced note and attachment maintenance.')
        info_label.setWordWrap(True)

        layout = QFormLayout(self)
        layout.addRow('Title', self.title_edit)
        layout.addRow('Description', self.description_edit)
        layout.addRow('Priority', self.priority_combo)
        layout.addRow('Column', self.column_combo)
        layout.addRow('Assignee', self.assignee_edit)
        layout.addRow('Project', self.project_edit)
        layout.addRow('Tags', self.tags_edit)
        layout.addRow('Color', color_row)
        layout.addRow('Card Type', self.card_type_combo)
        layout.addRow('', self.start_date)
        layout.addRow('', self.end_date)
        layout.addRow('', info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def choose_color(self):
        """Choose a card color."""
        initial = self.color_edit.text().strip() or '#ffffff'
        color = QColorDialog.getColor(QColor(initial), self, 'Choose Card Color')
        if color.isValid():
            self.color_edit.setText(color.name())

    def values(self) -> Dict[str, object]:
        """Return dialog values."""
        return {
            'title': self.title_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'priority': self.priority_combo.currentData(),
            'column_id': self.column_combo.currentData(),
            'assignee': self.assignee_edit.text().strip(),
            'project': self.project_edit.text().strip(),
            'tags': parse_tags(self.tags_edit.text()),
            'color': self.color_edit.text().strip() or None,
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

        self.scroll_area = QScrollArea()
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

        title_label = QLabel('Card Filters')
        toolbar.addWidget(title_label)

        self.toolbar_search_entry = QLineEdit()
        self.toolbar_search_entry.setObjectName('CardSearchEntry')
        self.toolbar_search_entry.setPlaceholderText('Search title or description')
        self.toolbar_search_entry.textChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_search_entry)

        priority_label_widget = QLabel('Priority')
        toolbar.addWidget(priority_label_widget)
        self.toolbar_priority_combo = QComboBox()
        self.toolbar_priority_combo.setObjectName('CardPriorityFilter')
        self.toolbar_priority_combo.addItem('All Priorities', '')
        for priority in Priority:
            self.toolbar_priority_combo.addItem(priority_label(priority), priority.value)
        self.toolbar_priority_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_priority_combo)

        assignee_label_widget = QLabel('Assignee')
        toolbar.addWidget(assignee_label_widget)
        self.toolbar_assignee_combo = QComboBox()
        self.toolbar_assignee_combo.setObjectName('CardAssigneeFilter')
        self.toolbar_assignee_combo.addItem('All Assignees', '')
        self.toolbar_assignee_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_assignee_combo)

        type_label_widget = QLabel('Type')
        toolbar.addWidget(type_label_widget)
        self.toolbar_card_type_combo = QComboBox()
        self.toolbar_card_type_combo.setObjectName('CardTypeFilter')
        self.toolbar_card_type_combo.addItem('All Types', '')
        self.toolbar_card_type_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_card_type_combo)

        tag_label_widget = QLabel('Tag')
        toolbar.addWidget(tag_label_widget)
        self.toolbar_tag_combo = QComboBox()
        self.toolbar_tag_combo.setObjectName('CardTagFilter')
        self.toolbar_tag_combo.addItem('All Tags', '')
        self.toolbar_tag_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_tag_combo)

        due_state_label_widget = QLabel('Due State')
        toolbar.addWidget(due_state_label_widget)
        self.toolbar_due_state_combo = QComboBox()
        self.toolbar_due_state_combo.setObjectName('CardDueStateFilter')
        self.toolbar_due_state_combo.addItem('All States', '')
        for due_state in ['Overdue', 'Due Today', 'Due Soon', 'Scheduled', 'Done', 'Start Date Only', 'No Due Date']:
            self.toolbar_due_state_combo.addItem(due_state, due_state)
        self.toolbar_due_state_combo.currentIndexChanged.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_due_state_combo)

        self.toolbar_overdue_checkbox = QCheckBox('Late only')
        self.toolbar_overdue_checkbox.toggled.connect(self.apply_toolbar_filters)
        toolbar.addWidget(self.toolbar_overdue_checkbox)

        self.toolbar_clear_filters_button = QPushButton('Clear')
        self.toolbar_clear_filters_button.setObjectName('ClearCardFiltersButton')
        self.toolbar_clear_filters_button.clicked.connect(self.clear_toolbar_filters)
        toolbar.addWidget(self.toolbar_clear_filters_button)

    def _build_menu(self):
        """Create the menu bar."""
        menu_bar = self.window.menuBar()

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
            return

        stats = current_board.get_board_stats()
        completed_cards = sum(1 for card in current_board.get_all_cards() if current_board.is_card_done(card))
        read_only_suffix = ' | read only' if current_board.is_read_only() else ''
        self.summary_label.setText(
            f"Board: {self._current_board_name()} | {stats['total_cards']} cards | {completed_cards} completed"
            f"{self._filter_summary_suffix()}{read_only_suffix}"
        )
        self._populate_columns(current_board)

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
        column_box = QGroupBox(column.name)
        column_border = '#7d3b14' if column.id == self.selected_column_id else '#b59c77'
        column_box.setStyleSheet(
            f"""
            QGroupBox {{
                background: #fbf5ea;
                border: 2px solid {column_border};
                border-radius: 12px;
                margin-top: 14px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #3f2f21;
            }}
            """
        )
        layout = QVBoxLayout(column_box)
        layout.setSpacing(8)

        color_strip = QFrame()
        color_strip.setFixedHeight(8)
        color_strip.setStyleSheet(f"background: {resolve_hex_color(column.color, '#8f4a1d')}; border-radius: 4px;")
        layout.addWidget(color_strip)

        meta = []
        if column.is_completed:
            meta.append('completed')
        if column.can_add_card:
            meta.append('add enabled')
        filtered_cards = self._filter_cards(board, list(column.cards))
        if self._filters_active() and len(filtered_cards) != len(column.cards):
            meta.append(f'{len(filtered_cards)} of {len(column.cards)} shown')
        elif column.cards:
            meta.append(f'{len(column.cards)} card' + ('' if len(column.cards) == 1 else 's'))
        meta_label = QLabel(' | '.join(meta) if meta else 'active column')
        layout.addWidget(meta_label)

        list_widget = CardListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        list_widget.setStyleSheet(
            """
            QListWidget {
                background: #f3eadc;
                border: 1px solid #d5c3a6;
                border-radius: 10px;
                padding: 6px;
                outline: 0;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 0;
                margin: 0 0 8px 0;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
            }
            """
        )
        list_widget.itemClicked.connect(lambda item, cid=column.id: self.on_card_clicked(cid, item))
        list_widget.itemDoubleClicked.connect(lambda _item: self.edit_selected_card())
        for card in filtered_cards:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, {'card_id': card.id, 'column_id': column.id})
            card_widget = CardTile(board, card, selected=card.id == self.selected_card_id)
            item.setSizeHint(card_widget.sizeHint())
            list_widget.addItem(item)
            list_widget.setItemWidget(item, card_widget)
            if card.id == self.selected_card_id:
                item.setSelected(True)
        QTimer.singleShot(0, list_widget.refresh_card_sizes)
        layout.addWidget(list_widget, 1)

        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        select_button = QPushButton('Select')
        select_button.clicked.connect(lambda _checked=False, cid=column.id: self.select_column(cid))
        button_layout.addWidget(select_button)
        if column.can_add_card:
            add_button = QPushButton('Add Card')
            add_button.clicked.connect(lambda _checked=False, cid=column.id: self.create_card(cid))
            button_layout.addWidget(add_button)
        layout.addWidget(button_row)
        column_box.setMinimumWidth(280)
        return column_box

    def on_card_clicked(self, column_id: str, item: QListWidgetItem):
        """Track the selected card and column."""
        payload = item.data(Qt.ItemDataRole.UserRole) or {}
        self.selected_column_id = column_id
        self.selected_card_id = payload.get('card_id')
        self.refresh_ui()

    def select_column(self, column_id: str):
        """Track the selected column."""
        self.selected_column_id = column_id
        self.selected_card_id = None
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
        dialog.exec()

    def create_card_type(self):
        """Create a new card type for the current board."""
        board = self.ensure_writable_board()
        if board is None:
            return
        dialog = CardTypeDialog(parent=self.window)
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
        is_default = card_type.id == board.get_default_card_type_id()
        dialog = CardTypeDialog(card_type=card_type, is_default=is_default, parent=self.window)
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
        file_name, _ = QFileDialog.getSaveFileName(self.window, 'Export All Boards', 'kanban_backup.json', 'JSON Files (*.json)')
        if not file_name:
            return
        export_data = self.board_manager.export_all_boards()
        with open(file_name, 'w', encoding='utf-8') as output_file:
            json.dump(export_data, output_file, indent=2, ensure_ascii=False)
        QMessageBox.information(self.window, 'Export Complete', f'Exported boards to {file_name}.')

    def import_boards(self):
        """Import boards from a JSON backup file."""
        file_name, _ = QFileDialog.getOpenFileName(self.window, 'Import Boards', '', 'JSON Files (*.json)')
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
                    'use_custom_columns': board_info.get('use_custom_columns'),
                }
        else:
            for entry in sorted(os.listdir(folder)):
                if not entry.endswith('.json') or entry == 'boards_metadata.json' or entry.endswith('.backup.json'):
                    continue
                inspected = self.board_manager.inspect_board_file(os.path.join(folder, entry))
                label = inspected['name']
                if label in option_map:
                    label = f"{label} ({entry})"
                option_map[label] = {
                    'data_file': inspected['data_file'],
                    'name': inspected['name'],
                    'description': '',
                    'use_custom_columns': inspected['use_custom_columns'],
                }
        return option_map

    def load_board_from_folder(self):
        """Load a board file from an external folder."""
        folder = QFileDialog.getExistingDirectory(self.window, 'Select Folder Containing a Board')
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
            use_custom_columns=board_choice['use_custom_columns'],
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
        choices = [column.name for column in board.get_columns_ordered() if column.id != card.column_id]
        if not choices:
            return
        selected, ok = QInputDialog.getItem(self.window, 'Move Card', 'Target Column', choices, editable=False)
        if not ok or not selected:
            return
        for column in board.get_columns_ordered():
            if column.name == selected:
                board.move_card(card.id, column.id)
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
