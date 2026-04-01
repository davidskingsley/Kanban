## @file
#  @brief PySide6-based multi-board GUI for the Kanban application.
"""PySide6 GUI implementation for the multi-board Kanban manager."""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..board import KanbanBoard
from ..board_manager import BoardManager
from ..models import Priority
from .board_actions import BoardActionsMixin
from .board_filters import BoardFiltersMixin
from .board_navigation import BoardNavigationMixin
from .common import (
    WINDOW_STYLE,
    PropagatingListWidget,
    PropagatingScrollArea,
    choose_existing_directory_dialog,
    choose_open_file_dialog,
    choose_save_file_dialog,
    clamp_drag_hotspot,
    clipped_description,
    clipped_title,
    create_drag_preview,
    priority_label,
)
from .dialogs import (
    AboutDialog,
    ArchivedCardsDialog,
    BoardDialog,
    CardDialog,
    CardTypeDialog,
    CardTypesBrowserDialog,
    ColumnDialog,
    CommandLineGuideDialog,
    DirectActionCliOptionsDialog,
    DueDateViewDialog,
    OptionalDateField,
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

__all__ = [
    'AboutDialog',
    'ArchivedCardsDialog',
    'BoardDialog',
    'CardDialog',
    'CardListItemContainer',
    'CardListWidget',
    'CardTile',
    'CardTypeDialog',
    'CardTypesBrowserDialog',
    'ColumnAddButton',
    'ColumnDialog',
    'ColumnGroupBox',
    'ColumnTitleButton',
    'CommandLineGuideDialog',
    'DirectActionCliOptionsDialog',
    'DueDateViewDialog',
    'MultiBoardGUI',
    'OptionalDateField',
    'ProjectDialog',
    'ProjectsBrowserDialog',
    'PropagatingListWidget',
    'PropagatingScrollArea',
    'QInputDialog',
    'QMessageBox',
    'ReorderColumnsDialog',
    'choose_existing_directory_dialog',
    'choose_open_file_dialog',
    'choose_save_file_dialog',
    'clamp_drag_hotspot',
    'clipped_description',
    'clipped_title',
    'create_drag_preview',
    'priority_label',
    'resolve_app_asset_path',
]


def resolve_app_asset_path(*parts: str) -> str:
    """Return an absolute path to an application asset for source and bundled runs."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, *parts)


class MultiBoardGUI(BoardActionsMixin, BoardFiltersMixin, BoardNavigationMixin):
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
        self.board_menu.addAction(self._action('Convert Current Board Backend', self.convert_current_board_backend))
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
        card_menu.addAction(self._action('Archive Done Cards', self.archive_done_cards, 'Ctrl+Shift+K'))
        card_menu.addAction(self._action('Manage Archived Cards', self.manage_archived_cards))
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
        help_menu.addAction(self._action('Command Line Guide', self.show_command_line_guide_dialog))
        help_menu.addAction(self._action('Direct-Action CLI Options', self.show_direct_action_cli_options_dialog))

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

    def run(self):
        """Run the application event loop."""
        self.window.show()
        return self.app.exec()

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
