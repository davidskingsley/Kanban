## @file
#  @brief PySide6-based multi-board GUI for the Kanban application.
"""PySide6 GUI implementation for the multi-board Kanban manager."""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from ..board import KanbanBoard
from ..board_manager import BoardManager
from ..models import CardType, CustomColumn, Priority, Project
from .board_statistics import BoardStatisticsDialog
from .common import (
    WINDOW_STYLE,
    PropagatingListWidget,  # noqa: F401
    PropagatingScrollArea,
    choose_existing_directory_dialog,
    choose_open_file_dialog,
    choose_save_file_dialog,
    clamp_drag_hotspot,  # noqa: F401
    clipped_description,  # noqa: F401
    clipped_title,  # noqa: F401
    column_can_add_card,
    column_color,
    column_identifier,
    column_label,
    column_target_value,
    create_drag_preview,  # noqa: F401
    due_state_label,
    priority_label,
    resolve_column_target,
    resolve_hex_color,
)
from .dialogs import (
    AboutDialog,
    BoardDialog,
    CardDialog,
    CardTypeDialog,
    CardTypesBrowserDialog,
    ColumnDialog,
    DueDateViewDialog,
    OptionalDateField,  # noqa: F401
    ProjectDialog,
    ProjectsBrowserDialog,
    ReorderColumnsDialog,
)
from .embedded_board import (
    CardListItemContainer,
    CardListWidget,
    CardTile,
    ColumnAddButton,
    ColumnGroupBox,
    ColumnTitleButton,
)


def resolve_app_asset_path(*parts: str) -> str:
    """Return an absolute path to an application asset for source and bundled runs."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, *parts)


class MultiBoardGUI:
    """PySide6 multi-board GUI wrapper."""

    def __init__(self, board_manager: BoardManager):
        self.board_manager = board_manager
        self.board_manager.set_lock_handler(self.prompt_for_locked_board_action)
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName('Kanban')
        self.app.setStyle('Fusion')
        self.app.setStyleSheet(WINDOW_STYLE)
        app_icon = QIcon(resolve_app_asset_path('assets', 'kanban_icon.png'))
        if not app_icon.isNull():
            self.app.setWindowIcon(app_icon)
        self.base_window_title = 'Multi-Board Kanban Manager'

        self.window = QMainWindow()
        self.window.setWindowTitle(self.base_window_title)
        self.window.resize(1480, 860)
        if not self.app.windowIcon().isNull():
            self.window.setWindowIcon(self.app.windowIcon())

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

        self.toolbar_clear_filters_button = QPushButton('Clear')
        self.toolbar_clear_filters_button.setObjectName('ClearCardFiltersButton')
        self.toolbar_clear_filters_button.clicked.connect(self.clear_toolbar_filters)
        toolbar.addWidget(self.toolbar_clear_filters_button)

    def _build_menu(self):
        """Create the menu bar."""
        menu_bar = self.window.menuBar()

        self.file_menu = menu_bar.addMenu('File')
        self.file_menu.addAction(self._action('Exit', self.window.close, QKeySequence.Quit))

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
        self.board_menu.addAction(self._action('Export Current Board', self.export_current_board, 'Ctrl+Shift+S'))
        self.board_menu.addSection('Import / Export')
        self.board_menu.addAction(self._action('Load Board From Folder', self.load_board_from_folder, 'Ctrl+Shift+O'))
        self.board_menu.addAction(self._action('Export All Boards', self.export_all_boards, 'Ctrl+Shift+E'))
        self.board_menu.addAction(self._action('Import Boards', self.import_boards, 'Ctrl+Shift+I'))
        self.board_menu.addSection('Overview')
        self.board_menu.addAction(self._action('Due Date View', self.show_due_date_view, 'Ctrl+Shift+T'))
        self.board_menu.addAction(self._action('Board Statistics', self.show_board_statistics, 'Ctrl+I'))

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

        help_menu = menu_bar.addMenu('Help')
        help_menu.addAction(self._action('About Kanban', self.show_about_dialog, 'F1'))

    def _set_window_title_summary(self, board_name: str, stats_text: str = ''):
        """Update the native window title with board summary details."""
        if board_name == 'No board selected' and not stats_text:
            self.window.setWindowTitle(self.base_window_title)
            return
        suffix = f' - {board_name}'
        if stats_text:
            suffix += f' | {stats_text}'
        self.window.setWindowTitle(f'{self.base_window_title}{suffix}')

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

    def show_about_dialog(self):
        """Show the application about and help dialog."""
        dialog = AboutDialog(parent=self.window, version='2.0')
        dialog.exec()

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
                self._set_filter_toolbar_enabled(False)
                return

            state = self._get_current_filter_state()
            self.toolbar_search_entry.setText(str(state['search']))
            self._set_combo_to_data(self.toolbar_priority_combo, state['priority'])
            self._set_combo_to_data(self.toolbar_assignee_combo, state['assignee'])
            self._set_combo_to_data(self.toolbar_card_type_combo, state['card_type'])
            self._set_combo_to_data(self.toolbar_tag_combo, state['tag'])
            self._set_combo_to_data(self.toolbar_due_state_combo, state['due_state'])
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
        finally:
            self._updating_filter_controls = False
        self.board_filter_states[self.board_manager.current_board_id] = self._default_filter_state()
        self.selected_card_id = None
        self.refresh_ui()

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
        return True

    def _filter_cards(self, board: KanbanBoard, cards: List[object]) -> List[object]:
        """Return the subset of cards matching the active filters."""
        return [card for card in cards if self._card_matches_filters(board, card)]

    def _filter_summary_suffix(self) -> str:
        """Return a readable summary of the current active filters."""
        state = self._get_current_filter_state()
        if not any([state['search'], state['priority'], state['assignee'], state['card_type'], state['tag'], state['due_state']]):
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
            self._set_window_title_summary('No board selected')
            self._refresh_history_actions(None)
            return

        stats = current_board.get_board_stats()
        completed_cards = sum(1 for card in current_board.get_all_cards() if current_board.is_card_done(card))
        read_only_suffix = ' | read only' if current_board.is_read_only() else ''
        self._set_window_title_summary(
            self._current_board_name(),
            f"{stats['total_cards']} cards | {completed_cards} completed"
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
                row_widget = CardListItemContainer(card_widget)
                item.setSizeHint(row_widget.sizeHint())
                list_widget.addItem(item)
                list_widget.setItemWidget(item, row_widget)
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

    def handle_card_drop(
        self,
        card_id: Optional[str],
        source_column_id: Optional[str],
        target_column_id: Optional[str],
        target_card_id: Optional[str] = None,
        insert_after: bool = False,
    ):
        """Move a card between columns from a drag-drop gesture."""
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
        board_id = self.board_manager.create_board(
            values['name'],
            values['description'],
            target_directory=values['storage_dir'],
            storage_backend=values['storage_backend'],
        )
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
        dialog = BoardStatisticsDialog(boards, self.board_manager.boards, self.window)
        dialog.exec()

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

        dialog = DueDateViewDialog(
            board,
            self._current_board_name(),
            self.window,
            on_focus_card=self._focus_card_from_due_date_view,
            on_edit_card=self._edit_card_from_due_date_view,
        )
        dialog.exec()

    def _focus_card_from_due_date_view(self, card_id: str, column_id: Optional[str]):
        """Focus a card selected from the due date dialog without closing it."""
        self.selected_column_id = column_id
        self.selected_card_id = card_id
        self.refresh_ui()

    def _edit_card_from_due_date_view(self, card_id: str, column_id: Optional[str]):
        """Open the selected due date dialog card in the editor without dismissing the dialog."""
        self.selected_column_id = column_id
        self.selected_card_id = card_id
        self.edit_selected_card()

    def export_all_boards(self):
        """Export all boards to a JSON backup file."""
        file_name = choose_save_file_dialog(self.window, 'Export All Boards', 'kanban_backup.json', 'JSON Files (*.json)')
        if not file_name:
            return
        export_data = self.board_manager.export_all_boards()
        with open(file_name, 'w', encoding='utf-8') as output_file:
            json.dump(export_data, output_file, indent=2, ensure_ascii=False)
        QMessageBox.information(self.window, 'Export Complete', f'Exported boards to {file_name}.')

    def export_current_board(self):
        """Export the current board to a standalone JSON file."""
        board = self.ensure_board()
        if board is None:
            return

        suggested_name = ''.join(c.lower() if c.isalnum() else '_' for c in self._current_board_name()).strip('_') or 'board'
        file_name = choose_save_file_dialog(
            self.window,
            'Export Current Board',
            f'{suggested_name}.json',
            'JSON Files (*.json)',
        )
        if not file_name:
            return

        export_data = self.board_manager.export_board_data(self.board_manager.current_board_id)
        with open(file_name, 'w', encoding='utf-8') as output_file:
            json.dump(export_data, output_file, indent=2, ensure_ascii=False)
        QMessageBox.information(self.window, 'Export Complete', f'Exported current board to {file_name}.')

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
                    'storage_backend': board_info.get('storage_backend'),
                }
        else:
            for entry in sorted(os.listdir(folder)):
                candidate_path = os.path.join(folder, entry)
                if entry == 'boards_metadata.json' or os.path.isdir(candidate_path) or '.backup.' in entry.lower():
                    continue
                try:
                    inspected = self.board_manager.inspect_board_file(candidate_path)
                except ValueError:
                    continue
                label = inspected['name']
                if label in option_map:
                    label = f"{label} ({entry})"
                option_map[label] = {
                    'data_file': inspected['data_file'],
                    'name': inspected['name'],
                    'description': '',
                    'storage_backend': inspected.get('storage_backend'),
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
            target_column_id=board.get_subcard_target(parent_card),
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
