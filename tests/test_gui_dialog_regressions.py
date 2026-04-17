import os
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QToolBar,
)

from gui_test_case import GuiTestCase
from kanban import __version__
from kanban.gui.board_statistics import BoardStatisticsDialog
from kanban.gui.common import WINDOW_STYLE
from kanban.gui.dialogs import ArchivedCardInfoDialog
from kanban.gui.pyside_app import (
    AboutDialog,
    ActionLogDialog,
    ArchivedCardsDialog,
    BoardDialog,
    CardDialog,
    CardTile,
    CardTypeDialog,
    CardTypesBrowserDialog,
    ColumnAddButton,
    ColumnTitleButton,
    CommandLineGuideDialog,
    DirectActionCliOptionsDialog,
    DueDateViewDialog,
    MultiBoardGUI,
    OptionalDateField,
    ProjectsBrowserDialog,
    clamp_drag_hotspot,
    clipped_description,
    clipped_title,
    create_drag_preview,
    priority_label,
)
from kanban.models import Priority


class GuiDialogRegressionTests(GuiTestCase):
    """!Gui Dialog Regression Tests."""
    def test_board_dialog_exposes_json_and_sqlite_backends(self):
        """!Test board dialog exposes json and sqlite backends."""
        dialog = BoardDialog(self.temp_dir)

        backend_values = [dialog.backend_combo.itemData(index) for index in range(dialog.backend_combo.count())]

        self.assertEqual(backend_values, ['json', 'sqlite'])
        dialog.name_edit.setText('SQLite Board')
        dialog.backend_combo.setCurrentIndex(1)
        self.assertEqual(dialog.values()['storage_backend'], 'sqlite')

    def test_legacy_board_files_are_rejected_and_skipped_in_folder_discovery(self):
        """!Test legacy board files are rejected and skipped in folder discovery."""
        legacy_board_path = Path(self.temp_dir) / 'legacy_board.json'
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'example_kanban.json', legacy_board_path)

        self.gui = MultiBoardGUI(self.board_manager)

        with self.assertRaisesRegex(ValueError, 'Legacy boards are no longer supported'):
            self.board_manager.add_external_board(str(legacy_board_path), name='Legacy Board', switch_to=True)

        self.assertEqual(self.gui._discover_boards_in_folder(self.temp_dir), {})

    def test_large_dialogs_are_scrollable(self):
        """!Test large dialogs are scrollable."""
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
            self.assertEqual(dialog.layout().spacing(), 8)
            self.assertEqual(scroll_areas[0].sizePolicy().verticalPolicy(), QSizePolicy.Policy.Expanding)
            self.assertEqual(scroll_areas[0].widget().sizePolicy().verticalPolicy(), QSizePolicy.Policy.Preferred)
            self.assertEqual(scroll_areas[0].widget().layout().count(), 1)
            dialog.resize(520, 360)
            dialog.show()
            QApplication.processEvents()
            self.assertGreater(scroll_areas[0].verticalScrollBar().maximum(), 0)
            dialog.close()

    def test_dialog_action_buttons_stay_outside_scroll_content(self):
        """!Test dialog action buttons stay outside scroll content."""
        self.board_manager.create_board('Pinned Footer Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card('Pinned Footer Card', 'dialog content', Priority.MEDIUM, column_id)
        card_type = board.get_card_types_ordered()[0]

        dialogs = [
            AboutDialog(version='3.0', parent=self.gui.window),
            BoardDialog(self.temp_dir, parent=self.gui.window),
            CardTypeDialog(card_type=card_type, parent=self.gui.window),
            CardDialog(board, card=card, parent=self.gui.window),
        ]

        for dialog in dialogs:
            scroll_area = dialog.findChild(QScrollArea, 'DialogScrollArea')
            self.assertIsNotNone(scroll_area, f'{type(dialog).__name__} should include a scroll area')
            button_box = dialog.findChild(QDialogButtonBox)
            self.assertIsNotNone(button_box, f'{type(dialog).__name__} should include a button box')
            self.assertIsNot(button_box.parentWidget(), scroll_area.widget())
            self.assertNotIn(button_box, scroll_area.widget().findChildren(QDialogButtonBox))

    def test_action_log_dialog_shows_actor_timestamp_and_messages(self):
        """!Test action log dialog shows actor timestamp and messages."""
        self.board_manager.create_board('Audit Dialog Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        card = board.create_card('Logged Card', 'dialog content', Priority.MEDIUM, board.get_columns_ordered()[0].id)
        board.add_card_note(card.id, 'Audit note')

        dialog = ActionLogDialog(board, 'Audit Dialog Board', parent=self.gui.window)
        log_text = dialog.log_browser.toPlainText()

        self.assertIn('Test User', log_text)
        self.assertIn("Added note to card 'Logged Card'.", log_text)
        self.assertRegex(log_text, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| Test User \|')

    def test_action_log_dialog_can_filter_to_one_card(self):
        """!Test action log dialog can filter to one card."""
        self.board_manager.create_board('Filtered Audit Dialog Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        first_card = board.create_card('Logged Card', 'dialog content', Priority.MEDIUM, board.get_columns_ordered()[0].id)
        second_card = board.create_card('Other Card', 'dialog content', Priority.MEDIUM, board.get_columns_ordered()[0].id)
        board.add_card_note(first_card.id, 'Show only this card')
        board.add_card_note(second_card.id, 'Do not show this card')

        dialog = ActionLogDialog(board, 'Filtered Audit Dialog Board', parent=self.gui.window, card=first_card)
        log_text = dialog.log_browser.toPlainText()

        self.assertIn("Added note to card 'Logged Card'.", log_text)
        self.assertNotIn("Added note to card 'Other Card'.", log_text)

    def test_drag_hotspot_is_clamped_to_preview_bounds(self):
        """!Test drag hotspot is clamped to preview bounds."""
        self.assertEqual(clamp_drag_hotspot(QPoint(12, 18), QSize(100, 80)), QPoint(12, 18))
        self.assertEqual(clamp_drag_hotspot(QPoint(-5, 18), QSize(100, 80)), QPoint(0, 18))
        self.assertEqual(clamp_drag_hotspot(QPoint(120, 90), QSize(100, 80)), QPoint(99, 79))

    def test_drag_preview_preserves_size_and_adds_transparency(self):
        """!Test drag preview preserves size and adds transparency."""
        source = QPixmap(20, 20)
        source.fill(QColor('#336699'))

        preview = create_drag_preview(source)

        self.assertEqual(preview.size(), source.size())
        self.assertEqual(preview.toImage().pixelColor(10, 10).alpha(), int(round(0.88 * 255)))
        self.assertEqual(preview.toImage().pixelColor(10, 10).rgb(), QColor('#336699').rgb())

    def test_clipped_description_uses_three_trailing_full_stops(self):
        """!Test clipped description uses three trailing full stops."""
        text = 'A' * 200

        clipped = clipped_description(text, limit=20)

        self.assertEqual(clipped, ('A' * 17) + '...')

    def test_clipped_title_uses_ninety_seven_character_limit(self):
        """!Test clipped title uses ninety seven character limit."""
        text = 'A' * 120

        clipped = clipped_title(text)

        self.assertEqual(clipped, ('A' * 94) + '...')
        self.assertEqual(len(clipped), 97)

    def test_card_type_browser_double_click_selects_card_type(self):
        """!Test card type browser double click selects card type."""
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
        """!Test project browser double click selects project."""
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
        """!Test card dialog project picker lists managed projects."""
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

    def test_card_dialog_collects_checklist_values(self):
        """!Test card dialog collects checklist values."""
        self.board_manager.create_board('Checklist Dialog Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        dialog = CardDialog(board, parent=self.gui.window)

        self.assertEqual(dialog.todo_list.count(), 1)
        self.assertEqual(dialog.todo_list.item(0).text(), 'No checklist items yet.')

        dialog.todo_entry.setText('Draft release notes')
        dialog.add_todo_item()
        dialog.todo_entry.setText('Share build with QA')
        dialog.add_todo_item()
        dialog.todo_list.item(1).setCheckState(Qt.CheckState.Checked)

        values = dialog.values()

        self.assertEqual(len(values['todo_items']), 2)
        self.assertEqual(values['todo_items'][0]['text'], 'Draft release notes')
        self.assertFalse(values['todo_items'][0]['completed'])
        self.assertEqual(values['todo_items'][1]['text'], 'Share build with QA')
        self.assertTrue(values['todo_items'][1]['completed'])

    def test_card_dialog_can_add_edit_and_delete_notes_for_existing_card(self):
        """!Test card dialog can add edit and delete notes for existing card."""
        self.board_manager.create_board('Card Notes Dialog Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card('Notes Card', 'desc', Priority.MEDIUM, column_id)

        dialog = CardDialog(board, card=card, parent=self.gui.window)

        self.assertEqual(dialog.notes_list.count(), 1)
        self.assertEqual(dialog.notes_list.item(0).text(), 'No notes added yet.')

        dialog.note_entry.setPlainText('First release note')
        dialog.save_note()

        reloaded = board.find_card(card.id)
        self.assertTrue(dialog.did_mutate_board)
        self.assertEqual(len(reloaded.notes), 1)
        self.assertEqual(reloaded.notes[0].text, 'First release note')

        dialog.notes_list.setCurrentRow(0)
        dialog.edit_selected_note()
        self.assertEqual(dialog.note_entry.toPlainText(), 'First release note')

        dialog.note_entry.setPlainText('Updated release note')
        dialog.save_note()

        reloaded = board.find_card(card.id)
        self.assertEqual(len(reloaded.notes), 1)
        self.assertEqual(reloaded.notes[0].text, 'Updated release note')

        dialog.notes_list.setCurrentRow(0)
        with patch('kanban.gui.dialogs.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            dialog.delete_selected_note()

        reloaded = board.find_card(card.id)
        self.assertEqual(reloaded.notes, [])
        self.assertEqual(dialog.notes_list.count(), 1)
        self.assertEqual(dialog.notes_list.item(0).text(), 'No notes added yet.')

    def test_card_dialog_uses_matching_section_borders_for_checklist_attachments_and_subcards(self):
        """!Test card dialog uses matching section borders for checklist attachments and subcards."""
        self.board_manager.create_board('Matching Section Borders Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, column_id)
        board.create_subcard(parent_card.id, 'Child', 'subcard desc')

        dialog = CardDialog(board, card=parent_card, parent=self.gui.window)
        expected_border = 'border: 1px solid #dcc7a7;'

        self.assertIn(expected_border, dialog.checklist_frame.styleSheet())
        self.assertIn(expected_border, dialog.attachment_drop_frame.styleSheet())
        subcards_frame = dialog.subcards_list.parentWidget()
        self.assertIsNotNone(subcards_frame)
        self.assertIn(expected_border, subcards_frame.styleSheet())

    def test_card_tile_shows_checklist_progress_and_preview(self):
        """!Test card tile shows checklist progress and preview."""
        self.board_manager.create_board('Checklist Tile Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card(
            'Release prep',
            'desc',
            Priority.HIGH,
            column_id,
            todo_items=[
                {'text': 'Draft notes', 'completed': True},
                {'text': 'Validate migrations', 'completed': False},
            ],
        )

        tile = CardTile(board, card)
        todo_checkboxes = tile.findChildren(QCheckBox)

        self.assertEqual(tile.schedule_label.text(), 'Checklist 1/2')
        self.assertEqual(len(todo_checkboxes), 2)
        self.assertEqual(todo_checkboxes[0].text(), 'Draft notes')
        self.assertTrue(todo_checkboxes[0].isChecked())
        self.assertEqual(todo_checkboxes[1].text(), 'Validate migrations')
        self.assertFalse(todo_checkboxes[1].isChecked())

    def test_card_tile_checkbox_toggle_routes_through_callback(self):
        """!Test card tile checkbox toggle routes through callback."""
        self.board_manager.create_board('Checklist Callback Tile Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card(
            'Toggle inline',
            'desc',
            Priority.MEDIUM,
            column_id,
            todo_items=[{'text': 'Flip me', 'completed': False}],
        )
        calls = []

        tile = CardTile(
            board,
            card,
            todo_toggle_callback=lambda card_id, todo_item_id, completed: calls.append((card_id, todo_item_id, completed)),
        )
        checkbox = tile.findChild(QCheckBox)

        self.assertIsNotNone(checkbox)
        checkbox.setChecked(True)

        self.assertEqual(calls, [(card.id, card.todo_items[0].id, True)])

    def test_optional_date_field_enables_editor_when_checked(self):
        """!Test optional date field enables editor when checked."""
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
        """!Test optional date field clear button resets to none."""
        field = OptionalDateField('End Date')

        field.checkbox.setChecked(True)
        self.assertIsNotNone(field.value())

        field.clear_button.click()

        self.assertFalse(field.checkbox.isChecked())
        self.assertFalse(field.editor.isEnabled())
        self.assertFalse(field.clear_button.isEnabled())
        self.assertIsNone(field.value())

    def test_window_style_includes_date_edit_dropdown_rules(self):
        """!Test window style includes date edit dropdown rules."""
        from kanban.gui.pyside_app import WINDOW_STYLE

        self.assertIn('QDateEdit::drop-down', WINDOW_STYLE)
        self.assertIn('QDateEdit::down-arrow', WINDOW_STYLE)
        self.assertIn('QCalendarWidget', WINDOW_STYLE)
        self.assertIn('QCalendarWidget QHeaderView::section', WINDOW_STYLE)
        self.assertIn('QCalendarWidget QWidget#qt_calendar_navigationbar', WINDOW_STYLE)

    def test_filter_toolbar_uses_compact_single_row_controls(self):
        """!Test filter toolbar uses compact single row controls."""
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

    def test_menu_bar_does_not_include_filters_menu(self):
        """!Test menu bar does not include filters menu."""
        self.board_manager.create_board('No Filters Menu Board')
        self.gui = MultiBoardGUI(self.board_manager)

        menu_titles = [action.text().replace('&', '') for action in self.gui.window.menuBar().actions()]

        self.assertNotIn('Filters', menu_titles)

    def test_menu_bar_includes_help_menu_actions(self):
        """!Test menu bar includes help menu actions."""
        self.board_manager.create_board('Help Menu Board')
        self.gui = MultiBoardGUI(self.board_manager)

        menu_bar = self.gui.window.menuBar()
        menu_titles = [action.text().replace('&', '') for action in menu_bar.actions()]
        help_action = next(action for action in menu_bar.actions() if action.text().replace('&', '') == 'Help')
        help_menu = help_action.menu()
        help_titles = [action.text().replace('&', '') for action in help_menu.actions() if action.text()]

        self.assertIn('Help', menu_titles)
        self.assertIn('About Kanban', help_titles)
        self.assertIn('Command Line Guide', help_titles)
        self.assertIn('Direct-Action CLI Options', help_titles)

    def test_main_window_uses_project_icon(self):
        """!Test main window uses project icon."""
        self.board_manager.create_board('Icon Board')
        self.gui = MultiBoardGUI(self.board_manager)

        self.assertFalse(self.gui.window.windowIcon().isNull())

    def test_about_dialog_shows_version_usage_and_shortcuts(self):
        """!Test about dialog shows version usage and shortcuts."""
        dialog = AboutDialog(version=__version__)
        scroll_area = dialog.findChildren(QScrollArea, 'DialogScrollArea')[0]

        self.assertEqual(dialog.windowTitle(), 'About Kanban')
        self.assertEqual(dialog.version_label.text(), f'Kanban Version {__version__}')
        self.assertIn('Create or switch to a board', dialog.usage_label.text())
        self.assertIn('Ctrl+Shift+J', dialog.shortcuts_label.text())
        self.assertIn('Ctrl+Shift+O', dialog.shortcuts_label.text())
        self.assertIn('Ctrl+Shift+Z', dialog.shortcuts_label.text())
        self.assertIn('Archive done cards', dialog.shortcuts_label.text())
        self.assertIn('Undo current board action', dialog.shortcuts_label.text())
        self.assertTrue(dialog.findChildren(QScrollArea, 'DialogScrollArea'))
        self.assertIs(dialog.button_box.parentWidget(), dialog)
        self.assertIsNot(dialog.button_box.parentWidget(), scroll_area.widget())

    def test_command_line_guide_dialog_shows_detailed_cli_help(self):
        """!Test command line guide dialog shows detailed cli help."""
        dialog = CommandLineGuideDialog()
        guide_text = dialog.command_line_help.toPlainText()

        self.assertEqual(dialog.windowTitle(), 'Kanban Command Line Guide')
        self.assertIn('python main.py --cli', guide_text)
        self.assertIn('--boards-dir DIR', guide_text)
        self.assertIn('Convert board backend', guide_text)
        self.assertIn('manage checklists', guide_text)
        self.assertIn('add-subcard', guide_text)
        self.assertIn('card-details', guide_text)
        self.assertIn('archive done cards', guide_text)
        self.assertIn('manage archived cards', guide_text)
        self.assertIn('Open current board', guide_text)
        self.assertIn('YYYY-MM-DD', guide_text)
        self.assertIn('SQLite3 backend', guide_text)
        self.assertFalse(dialog.findChildren(QScrollArea, 'DialogScrollArea'))
        self.assertTrue(dialog.findChildren(QTextBrowser, 'CommandLineGuideBrowser'))
        self.assertEqual(dialog.command_line_help.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.assertNotIn('QScrollBar::handle:vertical', dialog.command_line_help.styleSheet())
        self.assertIn('QScrollBar::handle:vertical', WINDOW_STYLE)
        dialog.resize(620, 420)
        dialog.show()
        QApplication.processEvents()
        self.assertGreater(dialog.command_line_help.verticalScrollBar().maximum(), 0)
        dialog.close()
        self.assertIs(dialog.button_box.parentWidget(), dialog)

    def test_direct_action_cli_options_dialog_shows_command_reference(self):
        """!Test direct action cli options dialog shows command reference."""
        dialog = DirectActionCliOptionsDialog()
        guide_text = dialog.direct_action_help.toPlainText()

        self.assertEqual(dialog.windowTitle(), 'Kanban Direct-Action CLI Options')
        self.assertIn('Direct-Action CLI Options', guide_text)
        self.assertIn('create-board --name NAME', guide_text)
        self.assertIn('convert-board --board BOARD --storage-backend json|sqlite', guide_text)
        self.assertIn('delete-board --board BOARD --force', guide_text)
        self.assertIn('create-card', guide_text)
        self.assertIn('add-todo-item [--board BOARD] --card CARD --text TEXT [--completed]', guide_text)
        self.assertIn('toggle-todo-item [--board BOARD] --card CARD --item ITEM', guide_text)
        self.assertIn('archive-done-cards [--board BOARD] --force', guide_text)
        self.assertIn('list-archived-cards [--board BOARD]', guide_text)
        self.assertIn('card-details prints checklist item ids', guide_text)
        self.assertIn('About and Command Line Guide dialogs', guide_text)
        self.assertIn('edit-column-flags', guide_text)
        self.assertIn('cleanup-orphaned-attachments', guide_text)
        self.assertIn('YYYY-MM-DD', guide_text)
        self.assertFalse(dialog.findChildren(QScrollArea, 'DialogScrollArea'))
        self.assertTrue(dialog.findChildren(QTextBrowser, 'DirectActionCliOptionsBrowser'))
        self.assertEqual(dialog.direct_action_help.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        dialog.resize(680, 460)
        dialog.show()
        QApplication.processEvents()
        self.assertGreater(dialog.direct_action_help.verticalScrollBar().maximum(), 0)
        dialog.close()

    def test_archived_cards_dialog_lists_and_restores_archived_cards(self):
        """!Test archived cards dialog lists and restores archived cards."""
        self.board_manager.create_board('Archived Dialog Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        done_column_id = next(column.id for column in board.get_columns_ordered() if column.is_completed)
        card = board.create_card('Archive Candidate', 'desc', Priority.HIGH, done_column_id)
        board.archive_done_cards()

        dialog = ArchivedCardsDialog(board, 'Archived Dialog Board', parent=self.gui.window)
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertIn('hidden from normal board views', dialog.summary_label.text())
        dialog.table.setCurrentCell(0, 0)

        with patch('kanban.gui.dialogs.QMessageBox.information') as information_mock:
            dialog._restore_selected_card()

        self.assertIsNotNone(board.find_card(card.id))
        self.assertEqual(dialog.table.rowCount(), 0)
        information_mock.assert_called_once()
        self.assertIs(dialog.button_box.parentWidget(), dialog)

    def test_archived_card_info_dialog_uses_styled_shell_and_sections(self):
        """!Test archived card info dialog uses styled shell and sections."""
        self.board_manager.create_board('Archived Info Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        done_column_id = next(column.id for column in board.get_columns_ordered() if column.is_completed)
        card = board.create_card('Archived Snapshot', 'Investigate the failed sync before restoring.', Priority.CRITICAL, done_column_id)
        card.assignee = 'Taylor'
        card.project = 'Stability'
        card.tags = ['incident', 'sync']
        board.archive_done_cards()

        archived_card = board.find_card(card.id, include_archived=True)
        dialog = ArchivedCardInfoDialog(archived_card, board.get_card_location_label(archived_card), parent=self.gui.window)

        self.assertEqual(dialog.objectName(), 'StandardDialog')
        self.assertEqual(dialog.findChild(QLabel, 'DialogTitle').text(), 'Archived Snapshot')
        self.assertFalse(dialog.findChildren(QScrollArea, 'DialogScrollArea'))

        badge_text = {label.text() for label in dialog.findChildren(QLabel, 'ArchivedInfoBadge')}
        self.assertIn('Archived', badge_text)
        self.assertIn('Critical Priority', badge_text)
        self.assertIn('Checklist 0/0', badge_text)

        description = dialog.findChild(QTextBrowser, 'ArchivedInfoDescription')
        self.assertIsNotNone(description)
        self.assertEqual(description.toPlainText(), 'Investigate the failed sync before restoring.')

    def test_board_summary_moves_to_title_bar(self):
        """!Test board summary moves to title bar."""
        self.board_manager.create_board('Title Summary Board')
        self.gui = MultiBoardGUI(self.board_manager)

        self.assertFalse(hasattr(self.gui, 'summary_label'))
        self.assertEqual(self.gui.window.windowTitle(), 'Multi-Board Kanban Manager - Title Summary Board | 0 cards | 0 completed')

    def test_board_statistics_dialog_shows_current_board_breakdown(self):
        """!Test board statistics dialog shows current board breakdown."""
        self.board_manager.create_board('Statistics Board', storage_backend='sqlite')
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
        self.assertEqual(dialog.boards_table.columnCount(), 10)
        self.assertEqual(dialog.columns_table.rowCount(), len(columns))
        self.assertEqual(dialog.priority_table.rowCount(), 4)
        self.assertGreaterEqual(dialog.due_state_table.rowCount(), 1)
        self.assertEqual(dialog.stat_cards['cards']['value'].text(), '3')
        self.assertEqual(dialog.stat_cards['completed']['value'].text(), '2')
        self.assertEqual(dialog.boards_table.item(0, 2).text(), 'SQLITE')
        self.assertIn('SQLITE storage', dialog.current_board_hint.text())
        self.assertFalse(dialog.findChildren(QScrollArea, 'DialogScrollArea'))
        self.assertIs(dialog.button_box.parentWidget(), dialog)

    def test_due_date_dialog_uses_timeline_column_for_gantt_style_view(self):
        """!Test due date dialog uses timeline column for gantt style view."""
        self.board_manager.create_board('Timeline Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        board.create_card(
            'Scheduled Work',
            'Timeline entry',
            Priority.HIGH,
            column_id,
            start_date=date(2026, 3, 24),
            end_date=date(2026, 3, 28),
        )

        dialog = DueDateViewDialog(board, 'Timeline Board', self.gui.window)

        self.assertEqual(dialog.table.columnCount(), 6)
        self.assertIn('Timeline', dialog.table.horizontalHeaderItem(2).text())
        self.assertTrue(dialog.timeline_hint_label.text())
        timeline_payload = dialog.table.item(0, 2).data(Qt.ItemDataRole.UserRole)
        self.assertEqual(timeline_payload['label'], 'Scheduled Work')
        self.assertEqual(timeline_payload['start_date'], date(2026, 3, 24))
        self.assertEqual(timeline_payload['end_date'], date(2026, 3, 28))

    def test_due_date_dialog_filter_popup_has_explicit_readable_styling(self):
        """!Test due date dialog filter popup has explicit readable styling."""
        self.board_manager.create_board('Readable Due Filter Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()

        dialog = DueDateViewDialog(board, 'Readable Due Filter Board', self.gui.window)
        popup_style = dialog.filter_combo.view().styleSheet()

        self.assertIn('background: #fffaf2;', popup_style)
        self.assertIn('color: #2d241c;', popup_style)
        self.assertIn('selection-background-color: #7d3b14;', popup_style)
        self.assertIn('selection-color: #ffffff;', popup_style)

    def test_due_date_dialog_edit_action_is_selected_on_double_click(self):
        """!Test due date dialog edit action is selected on double click."""
        self.board_manager.create_board('Due Edit Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card('Editable Scheduled Work', 'Timeline entry', Priority.HIGH, column_id, end_date=date(2026, 3, 28))
        callback_calls = []

        dialog = DueDateViewDialog(
            board,
            'Due Edit Board',
            self.gui.window,
            on_edit_card=lambda card_id, selected_column_id: callback_calls.append((card_id, selected_column_id)),
        )
        dialog.table.setCurrentCell(0, 0)

        dialog._edit_selected_card()

        self.assertEqual(dialog.selected_action, 'edit')
        self.assertEqual(dialog.selected_card_id, card.id)
        self.assertEqual(callback_calls, [(card.id, column_id)])
        self.assertEqual(dialog.result(), dialog.DialogCode.Rejected)

    def test_due_date_dialog_has_no_open_card_button(self):
        """!Test due date dialog has no open card button."""
        self.board_manager.create_board('Due Focus Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        board.create_card('Focused Scheduled Work', 'Timeline entry', Priority.MEDIUM, column_id, end_date=date(2026, 3, 28))

        dialog = DueDateViewDialog(
            board,
            'Due Focus Board',
            self.gui.window,
        )

        self.assertFalse(hasattr(dialog, 'open_button'))

    def test_card_dialog_restores_subcard_management_for_top_level_cards(self):
        """!Test card dialog restores subcard management for top level cards."""
        self.board_manager.create_board('Subcard Dialog Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, column_id)
        subcard = board.create_subcard(parent_card.id, 'Child', 'subcard desc')

        dialog = CardDialog(board, card=parent_card)

        self.assertTrue(hasattr(dialog, 'subcards_list'))
        self.assertEqual(dialog.subcards_list.verticalScrollMode(), QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.assertEqual(dialog.subcards_list.verticalScrollBar().singleStep(), 20)
        self.assertEqual(dialog.subcards_list.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.assertEqual(dialog.subcards_summary_label.text(), '1 subcard')
        self.assertEqual(dialog.subcards_progress_label.text(), '0 done')
        self.assertEqual(dialog.subcards_list.count(), 1)
        self.assertIn('Child', dialog.subcards_list.item(0).text())
        row_container = dialog.subcards_list.itemWidget(dialog.subcards_list.item(0))
        self.assertIsNotNone(row_container)
        self.assertEqual(row_container.layout().contentsMargins().bottom(), 5)
        row_widget = row_container.row_widget
        title_label = row_widget.findChild(QLabel, 'SubcardRowTitle')
        self.assertIsNotNone(title_label)
        self.assertNotIn('padding:', title_label.styleSheet())
        header_widget = row_widget.layout().itemAt(0).widget()
        self.assertIsNotNone(header_widget)
        self.assertEqual(header_widget.layout().contentsMargins().bottom(), 3)
        badge_row = header_widget.layout().itemAt(0).widget()
        self.assertIsNotNone(badge_row)
        self.assertGreaterEqual(header_widget.layout().count(), 2)
        self.assertTrue(row_widget.hasHeightForWidth())
        self.assertTrue(row_container.hasHeightForWidth())
        dialog.subcards_list.resize(320, 220)
        dialog.subcards_list.refresh_item_sizes()
        self.assertEqual(dialog.subcards_list.item(0).sizeHint().height(), row_container.heightForWidth(row_container.width()))

        dialog.subcards_list.setCurrentRow(0)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            dialog.delete_selected_subcard()

        self.assertIsNone(board.find_card(subcard.id))
        self.assertTrue(dialog.did_mutate_board)
        self.assertEqual(dialog.subcards_summary_label.text(), '0 subcards')
        self.assertEqual(dialog.subcards_progress_label.text(), '0 done')
        self.assertEqual(dialog.subcards_list.count(), 1)
        self.assertEqual(dialog.subcards_list.item(0).text(), 'No subcards yet.')

    def test_add_subcard_uses_leftmost_column_when_parent_column_disables_add_card(self):
        """!Test add subcard uses leftmost column when parent column disables add card."""
        self.board_manager.create_board('Subcard Target Board')
        board = self.board_manager.get_current_board()
        ordered_columns = board.get_columns_ordered()
        leftmost_column = ordered_columns[0]
        parent_column = ordered_columns[1]
        board.update_column(leftmost_column.id, can_add_card=False)
        board.update_column(parent_column.id, can_add_card=False)
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, parent_column.id)

        dialog = CardDialog(board, parent_card=parent_card)

        self.assertFalse(dialog.column_combo.isEnabled())
        self.assertEqual(dialog.column_combo.currentData(), leftmost_column.id)
        self.assertIn('left-most column', dialog.findChild(QLabel, 'DialogSubtitle').text())

        subcard = board.create_subcard(parent_card.id, 'Child', 'subcard desc')

        self.assertEqual(subcard.column_id, leftmost_column.id)

    def test_subcard_list_double_click_edit_updates_selected_subcard(self):
        """!Test subcard list double click edit updates selected subcard."""
        self.board_manager.create_board('Subcard Double Click Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, column_id)
        subcard = board.create_subcard(parent_card.id, 'Child', 'subcard desc')
        dialog = CardDialog(board, card=parent_card)
        dialog.subcards_list.setCurrentRow(0)

        class FakeCardDialog:
            """!Fake Card Dialog."""
            def __init__(self, *_args, **_kwargs):
                """!Init."""
                self.did_mutate_board = False

            def exec(self):
                """!Exec."""
                return CardDialog.DialogCode.Accepted

            def values(self):
                """!Values."""
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
                    'todo_items': [],
                }

        with patch('kanban.gui.dialogs.CardDialog', FakeCardDialog):
            dialog.edit_selected_subcard()

        updated = board.find_card(subcard.id)
        self.assertEqual(updated.title, 'Child Edited')
        self.assertEqual(updated.priority, Priority.CRITICAL)
        self.assertEqual(updated.assignee, 'sam')
        self.assertTrue(dialog.did_mutate_board)

    def test_card_tile_context_menu_add_subcard_routes_through_callback(self):
        """!Test card tile context menu add subcard routes through callback."""
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
            """!Fake Menu."""
            def __init__(self, *_args, **_kwargs):
                """!Init."""
                pass

            def addAction(self, label):
                """!Add action."""
                if label == 'Edit Card':
                    return edit_action
                if label == 'Add Subcard':
                    return add_subcard_action
                return object()

            def exec(self, *_args, **_kwargs):
                """!Exec."""
                return add_subcard_action

        with patch('kanban.gui.embedded_board.QMenu', FakeMenu):
            tile.contextMenuEvent(event)

        self.assertEqual(calls, [(parent_card.id, 'add_subcard')])

    def test_card_tile_uses_left_double_click_for_edit(self):
        """!Test card tile uses left double click for edit."""
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
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        tile.mouseDoubleClickEvent(left_double_click)

        right_double_click = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            QPointF(10, 10),
            QPointF(10, 10),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        tile.mouseDoubleClickEvent(right_double_click)

        self.assertEqual(edited, [card.id])

    def test_card_tile_ignores_left_press_for_parent_drag_handling(self):
        """!Test card tile ignores left press for parent drag handling."""
        self.board_manager.create_board('Card Tile Press Board')
        board = self.board_manager.get_current_board()
        card = board.create_card('Tile Card', 'desc', Priority.MEDIUM, board.get_columns_ordered()[0].id)

        tile = CardTile(board, card)
        left_press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        tile.mousePressEvent(left_press)

        self.assertFalse(left_press.isAccepted())

    def test_card_tile_text_labels_do_not_use_line_height_styling(self):
        """!Test card tile text labels do not use line height styling."""
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
        """!Test card tile height expands for wrapped content."""
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
        """!Test card tile header badges use fixed height."""
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

    def test_selected_card_tile_uses_more_obvious_selected_styling(self):
        """!Test selected card tile uses more obvious selected styling."""
        self.board_manager.create_board('Selected Card Tile Board')
        board = self.board_manager.get_current_board()
        card = board.create_card('Tile Card', 'desc', Priority.MEDIUM, board.get_columns_ordered()[0].id)
        card.color = '#4f7ec9'

        tile = CardTile(board, card, selected=True)
        labels = [label.text() for label in tile.findChildren(QLabel)]

        self.assertIn('SELECTED', labels)
        self.assertNotEqual(tile.selection_color, '#7d3b14')
        self.assertIn(f'border: 3px solid {tile.selection_color};', tile.styleSheet())

    def test_column_header_uses_title_selection_and_plus_add_button(self):
        """!Test column header uses title selection and plus add button."""
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

    def test_column_cards_use_more_of_column_width(self):
        """!Test column cards use more of column width."""
        self.board_manager.create_board('Column Card Width Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column = board.get_columns_ordered()[0]
        board.create_card('Width Test Card', 'desc', Priority.MEDIUM, column.id)

        widget = self.gui._create_column_widget(board, column)
        margins = widget.layout().contentsMargins()
        list_widget = widget.findChild(QListWidget)

        self.assertEqual(margins.left(), 6)
        self.assertEqual(margins.right(), 6)

        list_widget.resize(320, 400)
        list_widget.refresh_card_sizes()

        item = list_widget.item(0)
        row_widget = list_widget.itemWidget(item)
        card_widget = row_widget.card_widget
        self.assertEqual(row_widget.width(), list_widget.viewport().width())
        self.assertEqual(row_widget.layout().contentsMargins().left(), 0)
        self.assertEqual(card_widget.width(), list_widget.viewport().width() - 2 - list_widget._card_content_clearance_width())

    def test_column_card_list_uses_larger_vertical_spacing(self):
        """!Test column card list uses larger vertical spacing."""
        self.board_manager.create_board('Column Card Spacing Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column = board.get_columns_ordered()[0]

        widget = self.gui._create_column_widget(board, column)
        list_widget = widget.findChild(QListWidget)

        self.assertEqual(list_widget.spacing(), 0)

        board.create_card('Spacing Card', 'desc', Priority.MEDIUM, column.id)
        widget = self.gui._create_column_widget(board, column)
        list_widget = widget.findChild(QListWidget)
        row_widget = list_widget.itemWidget(list_widget.item(0))
        self.assertEqual(row_widget.layout().contentsMargins().bottom(), 14)

    def test_column_card_list_uses_per_pixel_scrolling(self):
        """!Test column card list uses per pixel scrolling."""
        self.board_manager.create_board('Column Smooth Scrolling Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column = board.get_columns_ordered()[0]

        widget = self.gui._create_column_widget(board, column)
        list_widget = widget.findChild(QListWidget)

        self.assertEqual(list_widget.verticalScrollMode(), QListWidget.ScrollMode.ScrollPerPixel)
        self.assertEqual(list_widget.verticalScrollBar().singleStep(), 24)

    def test_column_card_list_reserves_scrollbar_clearance(self):
        """!Test column card list reserves scrollbar clearance."""
        self.board_manager.create_board('Column Scrollbar Clearance Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column = board.get_columns_ordered()[0]

        widget = self.gui._create_column_widget(board, column)
        list_widget = widget.findChild(QListWidget)

        self.assertEqual(list_widget.viewportMargins().right(), 0)
        self.assertEqual(list_widget._card_content_clearance_width(), 6)

        for index in range(12):
            board.create_card(f'Card {index}', 'desc', Priority.MEDIUM, column.id)

        widget = self.gui._create_column_widget(board, column)
        list_widget = widget.findChild(QListWidget)
        list_widget.resize(320, 220)
        list_widget.refresh_card_sizes()

        self.assertEqual(list_widget._card_content_clearance_width(), 14)

    def test_scrollable_column_cards_use_compact_text_sizes(self):
        """!Test scrollable column cards use compact text sizes."""
        self.board_manager.create_board('Compact Scroll Text Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column = board.get_columns_ordered()[0]

        for index in range(12):
            board.create_card('Long title ' * 4, 'Long description ' * 12, Priority.MEDIUM, column.id)

        widget = self.gui._create_column_widget(board, column)
        list_widget = widget.findChild(QListWidget)
        list_widget.resize(320, 220)
        list_widget.refresh_card_sizes()

        row_widget = list_widget.itemWidget(list_widget.item(0))
        card_widget = row_widget.card_widget

        self.assertTrue(card_widget.compact_text)
        self.assertIn('font-size: 8.5pt;', card_widget.title_label.styleSheet())
