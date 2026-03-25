import os
import shutil
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QScrollArea, QToolBar

from kanban.gui.pyside_app import (
    BoardDialog,
    CardDialog,
    CardTile,
    CardTypeDialog,
    CardTypesBrowserDialog,
    ColumnAddButton,
    ColumnDialog,
    ColumnTitleButton,
    MultiBoardGUI,
    OptionalDateField,
    ProjectsBrowserDialog,
    clamp_drag_hotspot,
    clipped_description,
    clipped_title,
    create_drag_preview,
    priority_label,
)
from kanban.gui.board_statistics import BoardStatisticsDialog
from kanban.models import Priority
from gui_test_case import GuiTestCase


class GuiDialogRegressionTests(GuiTestCase):
    def test_legacy_board_files_are_rejected_and_skipped_in_folder_discovery(self):
        legacy_board_path = Path(self.temp_dir) / 'legacy_board.json'
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'example_kanban.json', legacy_board_path)

        self.gui = MultiBoardGUI(self.board_manager)

        with self.assertRaisesRegex(ValueError, 'Legacy boards are no longer supported'):
            self.board_manager.add_external_board(str(legacy_board_path), name='Legacy Board', switch_to=True)

        self.assertEqual(self.gui._discover_boards_in_folder(self.temp_dir), {})

    def test_large_dialogs_are_scrollable(self):
        self.board_manager.create_board('Scrollable Dialog Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        board.create_card('Scroll Card', 'dialog content', Priority.MEDIUM, board.get_columns_ordered()[0].id)
        card = board.get_all_cards()[0]
        card_type = board.get_card_types_ordered()[0]

        dialogs = [
            BoardDialog(self.temp_dir, parent=self.gui.window),
            CardTypeDialog(card_type=card_type, parent=self.gui.window),
            CardDialog(board, card=card, parent=self.gui.window),
        ]

        for dialog in dialogs:
            scroll_areas = dialog.findChildren(QScrollArea, 'DialogScrollArea')
            self.assertTrue(scroll_areas, f'{type(dialog).__name__} should include a scroll area')

    def test_drag_hotspot_is_clamped_to_preview_bounds(self):
        self.assertEqual(clamp_drag_hotspot(QPoint(12, 18), QSize(100, 80)), QPoint(12, 18))
        self.assertEqual(clamp_drag_hotspot(QPoint(-5, 18), QSize(100, 80)), QPoint(0, 18))
        self.assertEqual(clamp_drag_hotspot(QPoint(120, 90), QSize(100, 80)), QPoint(99, 79))

    def test_drag_preview_preserves_size_and_adds_transparency(self):
        source = QPixmap(20, 20)
        source.fill(QColor('#336699'))

        preview = create_drag_preview(source)

        self.assertEqual(preview.size(), source.size())
        self.assertEqual(preview.toImage().pixelColor(10, 10).alpha(), int(round(0.88 * 255)))
        self.assertEqual(preview.toImage().pixelColor(10, 10).rgb(), QColor('#336699').rgb())

    def test_clipped_description_uses_three_trailing_full_stops(self):
        text = 'A' * 200

        clipped = clipped_description(text, limit=20)

        self.assertEqual(clipped, ('A' * 17) + '...')

    def test_clipped_title_uses_ninety_seven_character_limit(self):
        text = 'A' * 120

        clipped = clipped_title(text)

        self.assertEqual(clipped, ('A' * 94) + '...')
        self.assertEqual(len(clipped), 97)

    def test_card_type_browser_double_click_selects_card_type(self):
        self.board_manager.create_board('Card Type Browser Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        created_id = board.create_card_type('Bug', 'Bug preset', 'Project A', '#336699')

        dialog = CardTypesBrowserDialog(board, parent=self.gui.window)
        target_row = next(
            row for row in range(dialog.table.rowCount())
            if dialog.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == created_id
        )
        dialog.table.setCurrentCell(target_row, 0)

        dialog._activate_selected_card_type()

        self.assertEqual(dialog.selected_card_type_id, created_id)
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)

    def test_project_browser_double_click_selects_project(self):
        self.board_manager.create_board('Project Browser Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        created_id = board.create_project('Platform', 'Shared platform work')

        dialog = ProjectsBrowserDialog(board, parent=self.gui.window)
        target_row = next(
            row for row in range(dialog.table.rowCount())
            if dialog.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == created_id
        )
        dialog.table.setCurrentCell(target_row, 0)

        dialog._activate_selected_project()

        self.assertEqual(dialog.selected_project_id, created_id)
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)

    def test_card_dialog_project_picker_lists_managed_projects(self):
        self.board_manager.create_board('Project Picker Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        board.create_project('Operations', 'Ops work')
        board.create_project('Roadmap', 'Planning')

        dialog = CardDialog(board, parent=self.gui.window)
        project_options = {dialog.project_edit.itemText(index) for index in range(dialog.project_edit.count())}

        self.assertIn('Operations', project_options)
        self.assertIn('Roadmap', project_options)
        self.assertTrue(dialog.project_edit.isEditable())

    def test_optional_date_field_enables_editor_when_checked(self):
        field = OptionalDateField('Start Date')

        self.assertFalse(field.checkbox.isChecked())
        self.assertFalse(field.editor.isEnabled())
        self.assertFalse(field.clear_button.isEnabled())
        self.assertIsNone(field.value())

        field.checkbox.setChecked(True)

        self.assertTrue(field.editor.isEnabled())
        self.assertTrue(field.clear_button.isEnabled())
        self.assertIsNotNone(field.value())

    def test_optional_date_field_clear_button_resets_to_none(self):
        field = OptionalDateField('End Date')

        field.checkbox.setChecked(True)
        self.assertIsNotNone(field.value())

        field.clear_button.click()

        self.assertFalse(field.checkbox.isChecked())
        self.assertFalse(field.editor.isEnabled())
        self.assertFalse(field.clear_button.isEnabled())
        self.assertIsNone(field.value())

    def test_window_style_includes_date_edit_dropdown_rules(self):
        from kanban.gui.pyside_app import WINDOW_STYLE

        self.assertIn('QDateEdit::drop-down', WINDOW_STYLE)
        self.assertIn('QDateEdit::down-arrow', WINDOW_STYLE)
        self.assertIn('QCalendarWidget', WINDOW_STYLE)
        self.assertIn('QCalendarWidget QHeaderView::section', WINDOW_STYLE)
        self.assertIn('QCalendarWidget QWidget#qt_calendar_navigationbar', WINDOW_STYLE)

    def test_filter_toolbar_uses_compact_single_row_controls(self):
        self.board_manager.create_board('Compact Toolbar Board')
        self.gui = MultiBoardGUI(self.board_manager)

        toolbar = self.gui.window.findChild(QToolBar, 'FilterToolbar')
        toolbar_labels = {label.text() for label in toolbar.findChildren(QLabel)}

        self.assertNotIn('Card Filters', toolbar_labels)
        self.assertNotIn('Priority', toolbar_labels)
        self.assertNotIn('Assignee', toolbar_labels)
        self.assertNotIn('Type', toolbar_labels)
        self.assertNotIn('Tag', toolbar_labels)
        self.assertNotIn('Due State', toolbar_labels)
        self.assertEqual(self.gui.toolbar_search_entry.width(), 190)
        self.assertEqual(self.gui.toolbar_priority_combo.width(), 118)
        self.assertEqual(self.gui.toolbar_assignee_combo.width(), 120)
        self.assertEqual(self.gui.toolbar_card_type_combo.width(), 112)
        self.assertEqual(self.gui.toolbar_tag_combo.width(), 108)
        self.assertEqual(self.gui.toolbar_due_state_combo.width(), 118)

    def test_board_summary_moves_to_title_bar(self):
        self.board_manager.create_board('Title Summary Board')
        self.gui = MultiBoardGUI(self.board_manager)

        self.assertFalse(hasattr(self.gui, 'summary_label'))
        self.assertEqual(self.gui.window.windowTitle(), 'Multi-Board Kanban Manager - Title Summary Board | 0 cards | 0 completed')

    def test_board_statistics_dialog_shows_current_board_breakdown(self):
        self.board_manager.create_board('Statistics Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        columns = board.get_columns_ordered()
        todo_column = columns[0].id
        done_column = columns[-1].id
        urgent = board.create_card('Urgent Fix', 'Patch issue', Priority.CRITICAL, todo_column)
        board.create_card('Review Work', 'Check flow', Priority.MEDIUM, columns[1].id)
        board.create_card('Completed Task', 'Finished', Priority.LOW, done_column)
        board.move_card(urgent.id, done_column)

        dialog = BoardStatisticsDialog(self.board_manager.get_board_list(), self.board_manager.boards, self.gui.window)

        self.assertEqual(dialog.boards_table.rowCount(), 1)
        self.assertEqual(dialog.columns_table.rowCount(), len(columns))
        self.assertEqual(dialog.priority_table.rowCount(), 4)
        self.assertGreaterEqual(dialog.due_state_table.rowCount(), 1)
        self.assertEqual(dialog.stat_cards['cards']['value'].text(), '3')
        self.assertEqual(dialog.stat_cards['completed']['value'].text(), '2')

    def test_card_dialog_restores_subcard_management_for_top_level_cards(self):
        self.board_manager.create_board('Subcard Dialog Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, column_id)
        subcard = board.create_subcard(parent_card.id, 'Child', 'subcard desc')

        dialog = CardDialog(board, card=parent_card)

        self.assertTrue(hasattr(dialog, 'subcards_list'))
        self.assertEqual(dialog.subcards_list.count(), 1)
        self.assertIn('Child', dialog.subcards_list.item(0).text())

        dialog.subcards_list.setCurrentRow(0)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            dialog.delete_selected_subcard()

        self.assertIsNone(board.find_card(subcard.id))
        self.assertTrue(dialog.did_mutate_board)
        self.assertEqual(dialog.subcards_list.count(), 1)
        self.assertEqual(dialog.subcards_list.item(0).text(), 'No subcards yet.')

    def test_subcard_list_double_click_edit_updates_selected_subcard(self):
        self.board_manager.create_board('Subcard Double Click Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, column_id)
        subcard = board.create_subcard(parent_card.id, 'Child', 'subcard desc')
        dialog = CardDialog(board, card=parent_card)
        dialog.subcards_list.setCurrentRow(0)

        class FakeCardDialog:
            def __init__(self, *_args, **_kwargs):
                self.did_mutate_board = False

            def exec(self):
                return CardDialog.DialogCode.Accepted

            def values(self):
                return {
                    'title': 'Child Edited',
                    'description': 'edited',
                    'priority': Priority.CRITICAL,
                    'column_id': column_id,
                    'assignee': 'sam',
                    'project': '',
                    'tags': ['edited'],
                    'color': None,
                    'card_type_id': board.get_default_card_type_id(),
                    'start_date': None,
                    'end_date': None,
                }

        with patch('kanban.gui.dialogs.CardDialog', FakeCardDialog):
            dialog.edit_selected_subcard()

        updated = board.find_card(subcard.id)
        self.assertEqual(updated.title, 'Child Edited')
        self.assertEqual(updated.priority, Priority.CRITICAL)
        self.assertEqual(updated.assignee, 'sam')
        self.assertTrue(dialog.did_mutate_board)

    def test_card_tile_context_menu_add_subcard_routes_through_callback(self):
        self.board_manager.create_board('Card Tile Context Menu Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, column_id)
        calls = []
        tile = CardTile(
            board,
            parent_card,
            context_action_callback=lambda card_id, action: calls.append((card_id, action)),
        )
        event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(10, 10))

        edit_action = object()
        add_subcard_action = object()

        class FakeMenu:
            def __init__(self, *_args, **_kwargs):
                pass

            def addAction(self, label):
                if label == 'Edit Card':
                    return edit_action
                if label == 'Add Subcard':
                    return add_subcard_action
                return object()

            def exec(self, *_args, **_kwargs):
                return add_subcard_action

        with patch('kanban.gui.embedded_board.QMenu', FakeMenu):
            tile.contextMenuEvent(event)

        self.assertEqual(calls, [(parent_card.id, 'add_subcard')])

    def test_card_tile_uses_left_double_click_for_edit(self):
        self.board_manager.create_board('Card Tile Double Click Board')
        board = self.board_manager.get_current_board()
        card = board.create_card('Tile Card', 'desc', Priority.MEDIUM, board.get_columns_ordered()[0].id)

        edited = []
        tile = CardTile(
            board,
            card,
            edit_callback=lambda card_id: edited.append(card_id),
        )

        left_double_click = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        tile.mouseDoubleClickEvent(left_double_click)

        right_double_click = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            QPointF(10, 10),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        tile.mouseDoubleClickEvent(right_double_click)

        self.assertEqual(edited, [card.id])

    def test_card_tile_ignores_left_press_for_parent_drag_handling(self):
        self.board_manager.create_board('Card Tile Press Board')
        board = self.board_manager.get_current_board()
        card = board.create_card('Tile Card', 'desc', Priority.MEDIUM, board.get_columns_ordered()[0].id)

        tile = CardTile(board, card)
        left_press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        tile.mousePressEvent(left_press)

        self.assertFalse(left_press.isAccepted())

    def test_card_tile_text_labels_do_not_use_line_height_styling(self):
        self.board_manager.create_board('Card Tile Text Style Board')
        board = self.board_manager.get_current_board()
        card = board.create_card(
            'Very Long Title ' * 6,
            'Very long description content ' * 30,
            Priority.MEDIUM,
            board.get_columns_ordered()[0].id,
        )

        tile = CardTile(board, card)
        text_labels = [label for label in tile.findChildren(QLabel) if label.text() in {clipped_title(card.title), clipped_description(card.description)}]

        self.assertTrue(text_labels)
        for label in text_labels:
            self.assertNotIn('line-height', label.styleSheet())

    def test_card_tile_height_expands_for_wrapped_content(self):
        self.board_manager.create_board('Card Tile Height Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        short_card = board.create_card('Short title', 'short text', Priority.MEDIUM, column_id)
        long_card = board.create_card('Long title ' * 8, 'Long description ' * 80, Priority.MEDIUM, column_id)

        short_tile = CardTile(board, short_card)
        long_tile = CardTile(board, long_card)

        constrained_width = 260
        short_height = short_tile.heightForWidth(constrained_width)
        long_height = long_tile.heightForWidth(constrained_width)

        self.assertGreater(long_height, short_height)

    def test_card_tile_header_badges_use_fixed_height(self):
        self.board_manager.create_board('Card Tile Badge Height Board')
        board = self.board_manager.get_current_board()
        card = board.create_card('Tile Card', 'desc', Priority.MEDIUM, board.get_columns_ordered()[0].id)
        card.assignee = 'alex'

        tile = CardTile(board, card)
        badge_texts = {priority_label(card.priority).upper(), board.get_default_card_type().name, f'@{card.assignee}'}
        badges = [label for label in tile.findChildren(QLabel) if label.text() in badge_texts]

        self.assertTrue(badges)
        for badge in badges:
            self.assertEqual(badge.height(), 24)

    def test_column_header_uses_title_selection_and_plus_add_button(self):
        self.board_manager.create_board('Column Header Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column = board.get_columns_ordered()[0]

        widget = self.gui._create_column_widget(board, column)
        title_button = next(button for button in widget.findChildren(ColumnTitleButton) if button.text() == column.name)
        plus_buttons = widget.findChildren(ColumnAddButton)
        legacy_buttons = [button for button in widget.findChildren(QPushButton) if button.text() in {'Select', 'Add Card'}]

        title_button.click()

        self.assertEqual(self.gui.selected_column_id, column.id)
        self.assertTrue(plus_buttons)
        self.assertFalse(legacy_buttons)
