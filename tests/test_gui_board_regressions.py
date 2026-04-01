import json
import os
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QVBoxLayout, QWidget

from gui_test_case import GuiTestCase
from kanban.board_manager import BoardManager
from kanban.gui.pyside_app import (
    CardDialog,
    CardListItemContainer,
    CardListWidget,
    CardTile,
    ColumnDialog,
    ColumnGroupBox,
    ColumnTitleButton,
    MultiBoardGUI,
    PropagatingListWidget,
    PropagatingScrollArea,
)
from kanban.models import Priority


class GuiBoardRegressionTests(GuiTestCase):
    def test_sqlite_board_backend_round_trips_and_creates_backups(self):
        board_id = self.board_manager.create_board('SQLite Board', storage_backend='sqlite')
        metadata = self.board_manager.load_metadata()
        board_info = metadata['boards'][board_id]

        self.assertEqual(board_info['storage_backend'], 'sqlite')
        self.assertTrue(board_info['data_file'].endswith('.sqlite3'))

        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        created_card = board.create_card('SQLite Card', 'stored in sqlite', Priority.HIGH, column_id)

        backup_path = board.storage.backup()
        export_data = self.board_manager.export_board_data(board_id)

        self.assertTrue(os.path.exists(backup_path))
        self.assertEqual(export_data['cards'][0]['id'], created_card.id)

    def test_import_boards_preserves_sqlite_backend_payloads(self):
        board_id = self.board_manager.create_board('SQLite Import Board', storage_backend='sqlite')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        board.create_card('Imported SQLite Card', 'sqlite export', Priority.MEDIUM, column_id)

        export_snapshot = self.board_manager.export_all_boards()
        imported_manager = BoardManager(os.path.join(self.temp_dir, 'sqlite_import_target'))

        try:
            self.assertTrue(imported_manager.import_boards(export_snapshot))
            imported_metadata = imported_manager.load_metadata()
            imported_info = imported_metadata['boards'][board_id]
            imported_data = imported_manager.export_board_data(board_id)

            self.assertEqual(imported_info['storage_backend'], 'sqlite')
            self.assertEqual(imported_data['cards'][0]['title'], 'Imported SQLite Card')
        finally:
            imported_manager.close()

    def test_folder_discovery_includes_sqlite_board_files(self):
        external_dir = os.path.join(self.temp_dir, 'sqlite_folder_board')
        os.makedirs(external_dir, exist_ok=True)
        self.board_manager.create_board(
            'SQLite Folder Board',
            target_directory=external_dir,
            storage_backend='sqlite',
        )
        self.gui = MultiBoardGUI(self.board_manager)

        option_map = self.gui._discover_boards_in_folder(external_dir)

        self.assertEqual(len(option_map), 1)
        discovered_board = next(iter(option_map.values()))
        self.assertEqual(discovered_board['storage_backend'], 'sqlite')
        self.assertTrue(discovered_board['data_file'].endswith('.sqlite3'))

    def test_board_manager_converts_board_between_json_and_sqlite(self):
        board_id = self.board_manager.create_board('Convertible Board', storage_backend='json')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card('Convert Me', 'persist across backend changes', Priority.MEDIUM, column_id)
        json_path = self.board_manager.load_metadata()['boards'][board_id]['data_file']

        sqlite_path = self.board_manager.convert_board_storage_backend(board_id, 'sqlite')
        converted_metadata = self.board_manager.load_metadata()['boards'][board_id]

        self.assertEqual(converted_metadata['storage_backend'], 'sqlite')
        self.assertTrue(sqlite_path.endswith('.sqlite3'))
        self.assertTrue(os.path.exists(sqlite_path))
        self.assertFalse(os.path.exists(json_path))
        self.assertEqual(self.board_manager.export_board_data(board_id)['cards'][0]['id'], card.id)

        json_path = self.board_manager.convert_board_storage_backend(board_id, 'json')
        converted_metadata = self.board_manager.load_metadata()['boards'][board_id]

        self.assertEqual(converted_metadata['storage_backend'], 'json')
        self.assertTrue(json_path.endswith('.json'))
        self.assertTrue(os.path.exists(json_path))
        self.assertEqual(self.board_manager.export_board_data(board_id)['cards'][0]['title'], 'Convert Me')

    def test_gui_can_convert_current_board_backend(self):
        board_id = self.board_manager.create_board('GUI Convertible Board', storage_backend='json')
        self.gui = MultiBoardGUI(self.board_manager)
        original_path = self.board_manager.load_metadata()['boards'][board_id]['data_file']

        with patch('kanban.gui.pyside_app.QInputDialog.getItem', return_value=('SQLite3 Backend', True)), patch(
            'kanban.gui.pyside_app.QMessageBox.information'
        ) as information_mock:
            self.gui.convert_current_board_backend()

        converted_metadata = self.board_manager.load_metadata()['boards'][board_id]
        self.assertEqual(converted_metadata['storage_backend'], 'sqlite')
        self.assertTrue(converted_metadata['data_file'].endswith('.sqlite3'))
        self.assertFalse(os.path.exists(original_path))
        information_mock.assert_called_once()

    def test_card_list_drag_preview_uses_card_widget_not_row_container(self):
        self.board_manager.create_board('Drag Preview Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card('Drag Card', 'desc', Priority.MEDIUM, column_id)

        list_widget = CardListWidget(column_id=column_id)
        list_widget.resize(320, 240)
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, {'card_id': card.id, 'column_id': column_id})
        card_widget = CardTile(board, card)
        row_widget = CardListItemContainer(card_widget)
        list_widget.addItem(item)
        list_widget.setItemWidget(item, row_widget)
        list_widget.setCurrentItem(item)
        list_widget.show()
        self.app.processEvents()
        list_widget.refresh_card_sizes()

        captured = {}

        class FakeDrag:
            def __init__(self, _source):
                self.mime_data = None

            def setMimeData(self, mime_data):
                self.mime_data = mime_data

            def setPixmap(self, pixmap):
                captured['pixmap_size'] = pixmap.size()

            def setHotSpot(self, hotspot):
                captured['hotspot'] = hotspot

            def exec(self, _action):
                captured['exec_called'] = True

        def fake_create_drag_preview(pixmap):
            captured['grabbed_size'] = pixmap.size()
            return QPixmap(pixmap)

        with patch('kanban.gui.embedded_board.QDrag', FakeDrag), patch('kanban.gui.embedded_board.create_drag_preview', fake_create_drag_preview):
            list_widget.startDrag(Qt.DropAction.MoveAction)

        self.assertEqual(captured['grabbed_size'], card_widget.size())
        self.assertEqual(captured['pixmap_size'], card_widget.size())
        self.assertTrue(captured['exec_called'])

    def test_dismissing_subcard_context_menu_does_not_trigger_add_subcard(self):
        self.board_manager.create_board('Subcard Context Menu Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'parent card', Priority.MEDIUM, column_id)
        subcard = board.create_subcard(parent_card.id, 'Child', 'subcard card', Priority.LOW, column_id)
        callback_calls = []
        tile = CardTile(board, subcard, context_action_callback=lambda card_id, action: callback_calls.append((card_id, action)))

        class FakeContextEvent:
            def __init__(self):
                self.ignored = False

            def globalPos(self):
                return QPoint(5, 5)

            def ignore(self):
                self.ignored = True

        class FakeMenu:
            def __init__(self, _parent=None):
                self.actions = []

            def addAction(self, label):
                self.actions.append(label)
                return label

            def exec(self, _global_pos):
                return None

        with patch('kanban.gui.embedded_board.QMenu', FakeMenu):
            event = FakeContextEvent()
            tile.contextMenuEvent(event)

        self.assertEqual(callback_calls, [])
        self.assertTrue(event.ignored)

    def test_card_list_drop_indicator_tracks_item_insertion_position(self):
        list_widget = CardListWidget()
        list_widget.resize(220, 240)

        for label in ('First', 'Second'):
            item = QListWidgetItem(label)
            item.setSizeHint(QSize(180, 40))
            list_widget.addItem(item)

        list_widget.show()
        self.app.processEvents()

        first_rect = list_widget.visualItemRect(list_widget.item(0))
        second_rect = list_widget.visualItemRect(list_widget.item(1))

        list_widget._update_drop_indicator(QPoint(first_rect.center().x(), first_rect.center().y() + 1))
        self.assertEqual(list_widget._drop_indicator_y, first_rect.bottom() + list_widget.DROP_INDICATOR_SPACING)
        self.assertTrue(list_widget._drop_indicator_line.isVisible())
        self.assertIs(list_widget._drop_indicator_line.parentWidget(), list_widget.viewport())

        list_widget._update_drop_indicator(QPoint(second_rect.center().x(), second_rect.center().y() - 1))
        self.assertEqual(list_widget._drop_indicator_y, second_rect.top() - list_widget.DROP_INDICATOR_SPACING)

        list_widget._clear_drop_indicator()
        self.assertIsNone(list_widget._drop_indicator_y)
        self.assertFalse(list_widget._drop_indicator_line.isVisible())

    def test_column_group_box_drop_indicator_tracks_left_and_right_edges(self):
        column_box = ColumnGroupBox('', 'column-1', board_view=None, selected=False)
        column_box.resize(260, 200)
        column_box.show()
        self.app.processEvents()

        column_box._update_drop_indicator(20)
        self.assertEqual(column_box._drop_indicator_x, column_box.DROP_INDICATOR_MARGIN)
        self.assertTrue(column_box._drop_indicator_line.isVisible())
        self.assertIs(column_box._drop_indicator_line.parentWidget(), column_box)

        column_box._update_drop_indicator(240)
        self.assertEqual(column_box._drop_indicator_x, column_box.width() - column_box.DROP_INDICATOR_MARGIN)

        column_box._clear_drop_indicator()
        self.assertIsNone(column_box._drop_indicator_x)
        self.assertFalse(column_box._drop_indicator_line.isVisible())

    def test_column_title_button_can_trigger_drag_callback(self):
        drag_calls = []
        drag_target = QWidget()
        button = ColumnTitleButton('Backlog', drag_callback=drag_calls.append, drag_target=drag_target, parent=drag_target)
        button._press_pos = QPoint(8, 9)

        did_start_drag = button._maybe_start_drag(
            QPoint(8 + self.app.startDragDistance(), 9),
            Qt.MouseButton.LeftButton,
        )

        self.assertTrue(did_start_drag)
        self.assertEqual(drag_calls, [button.mapTo(drag_target, QPoint(8, 9))])
        self.assertIsNone(button._press_pos)

    def test_file_menu_exposes_exit_action(self):
        self.board_manager.create_board('File Menu Board')
        self.gui = MultiBoardGUI(self.board_manager)

        menu_actions = self.gui.window.menuBar().actions()
        self.assertTrue(menu_actions)
        self.assertEqual(menu_actions[0].text().replace('&', ''), 'File')

        file_menu = menu_actions[0].menu()
        file_action_texts = [action.text().replace('&', '') for action in file_menu.actions()]
        self.assertIn('Exit', file_action_texts)

    def test_cards_menu_exposes_archive_management_actions(self):
        self.board_manager.create_board('Archive Menu Board')
        self.gui = MultiBoardGUI(self.board_manager)

        cards_action = next(action for action in self.gui.window.menuBar().actions() if action.text().replace('&', '') == 'Cards')
        cards_menu = cards_action.menu()
        card_action_texts = [action.text().replace('&', '') for action in cards_menu.actions() if action.text()]

        self.assertIn('Archive Done Cards', card_action_texts)
        self.assertIn('Manage Archived Cards', card_action_texts)

    def test_gui_archive_done_cards_moves_cards_out_of_active_board_view(self):
        self.board_manager.create_board('Archive Done GUI Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        done_column_id = next(column.id for column in board.get_columns_ordered() if column.is_completed)
        card = board.create_card('Archive Me', 'completed work', Priority.MEDIUM, done_column_id)
        self.gui.selected_card_id = card.id

        with patch('kanban.gui.pyside_app.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes), patch(
            'kanban.gui.pyside_app.QMessageBox.information'
        ) as information_mock:
            self.gui.archive_done_cards()

        self.assertIsNone(board.find_card(card.id))
        archived = board.find_card(card.id, include_archived=True)
        self.assertIsNotNone(archived)
        self.assertTrue(archived.is_archived())
        self.assertIsNone(self.gui.selected_card_id)
        information_mock.assert_called_once()

    def test_export_current_board_writes_standalone_board_json(self):
        self.board_manager.create_board('Exportable Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        board.create_card('Standalone Export', 'card data', Priority.HIGH, column_id)
        export_path = os.path.join(self.temp_dir, 'exported_board.json')

        with patch('kanban.gui.pyside_app.choose_save_file_dialog', return_value=export_path), patch(
            'kanban.gui.pyside_app.QMessageBox.information'
        ) as information_mock:
            self.gui.export_current_board()

        self.assertTrue(os.path.exists(export_path))
        with open(export_path, 'r', encoding='utf-8') as input_file:
            export_data = json.load(input_file)

        self.assertIn('columns', export_data)
        self.assertIn('cards', export_data)
        self.assertNotIn('metadata', export_data)
        self.assertEqual(export_data['cards'][0]['title'], 'Standalone Export')
        information_mock.assert_called_once()

    def test_custom_board_drag_drop_and_attachment_flow(self):
        self.board_manager.create_board('Regression Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()

        columns = board.get_columns_ordered()
        first_column, second_column = columns[0], columns[1]
        first_card = board.create_card('First', 'top card', Priority.LOW, first_column.id)
        second_card = board.create_card('Second', 'middle card', Priority.MEDIUM, first_column.id)
        card = board.create_card('Drag Target', 'drag me', Priority.MEDIUM, first_column.id)

        self.gui.handle_card_drop(card.id, first_column.id, first_column.id, target_card_id=first_card.id, insert_after=False)
        reordered_ids = [entry.id for entry in board.custom_columns[first_column.id].cards]
        self.assertEqual(reordered_ids, [card.id, first_card.id, second_card.id])

        self.gui.handle_card_drop(card.id, first_column.id, second_column.id)
        moved_card = board.find_card(card.id)
        self.assertEqual(moved_card.column_id, second_column.id)

        self.gui.handle_column_drop(second_column.id, first_column.id, insert_after=False)
        reordered_ids = [column.id for column in board.get_columns_ordered()]
        self.assertEqual(reordered_ids[0], second_column.id)

        attachment_path = f'{self.temp_dir}/attachment.txt'
        with open(attachment_path, 'w', encoding='utf-8') as handle:
            handle.write('attachment regression')

        dialog = CardDialog(board, card=moved_card, parent=self.gui.window)
        dialog.add_attachments_from_drop([attachment_path])

        moved_card = board.find_card(card.id)
        self.assertEqual(len(moved_card.attachments), 1)
        self.assertEqual(moved_card.attachments[0].name, 'attachment.txt')

    def test_column_double_click_routes_to_column_edit(self):
        self.board_manager.create_board('Column Double Click Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id

        calls = []

        def fake_edit_selected_column():
            calls.append(self.gui.selected_column_id)

        self.gui.edit_selected_column = fake_edit_selected_column
        self.gui.handle_column_double_click(column_id)

        self.assertEqual(calls, [column_id])
        self.assertEqual(self.gui.selected_column_id, column_id)
        self.assertIsNone(self.gui.selected_card_id)

    def test_project_crud_updates_cards_and_card_type_presets(self):
        self.board_manager.create_board('Project Crud Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id

        alpha_id = board.create_project('Alpha', 'First project')
        beta_id = board.create_project('Beta', 'Second project')
        card_type_id = board.create_card_type('Bug', 'Defect preset', 'Alpha', '#336699')
        card = board.create_card('Fix auth', 'Investigate', Priority.HIGH, column_id, project='Alpha')

        board.edit_project(alpha_id, 'Alpha Prime', 'Renamed project')

        updated_card = board.find_card(card.id)
        updated_card_type = board.get_card_type(card_type_id)
        renamed_project = board.get_project(alpha_id)
        self.assertEqual(updated_card.project, 'Alpha Prime')
        self.assertEqual(updated_card_type.default_project, 'Alpha Prime')
        self.assertEqual(renamed_project.name, 'Alpha Prime')

        board.delete_project(alpha_id, replacement_project_id=beta_id)

        reassigned_card = board.find_card(card.id)
        reassigned_card_type = board.get_card_type(card_type_id)
        self.assertIsNone(board.get_project(alpha_id))
        self.assertEqual(reassigned_card.project, 'Beta')
        self.assertEqual(reassigned_card_type.default_project, 'Beta')

    def test_add_subcard_action_creates_child_for_selected_top_level_card(self):
        self.board_manager.create_board('Selected Subcard Action Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        parent_card = board.create_card('Parent', 'desc', Priority.MEDIUM, column_id)
        self.gui.selected_card_id = parent_card.id

        class FakeCardDialog:
            def __init__(self, *_args, **_kwargs):
                self.did_mutate_board = False

            def exec(self):
                return CardDialog.DialogCode.Accepted

            def values(self):
                return {
                    'title': 'Child Task',
                    'description': 'nested work',
                    'priority': Priority.HIGH,
                    'column_id': column_id,
                    'assignee': 'alex',
                    'project': '',
                    'tags': ['nested'],
                    'color': None,
                    'card_type_id': board.get_default_card_type_id(),
                    'start_date': None,
                    'end_date': None,
                    'todo_items': [],
                }

        with patch('kanban.gui.pyside_app.CardDialog', FakeCardDialog):
            self.gui.add_subcard_to_selected_card()

        subcards = board.get_subcards(parent_card.id)
        self.assertEqual(len(subcards), 1)
        self.assertEqual(subcards[0].title, 'Child Task')
        self.assertEqual(subcards[0].parent_id, parent_card.id)
        self.assertEqual(subcards[0].priority, Priority.HIGH)

    def test_board_card_checklist_persists_through_create_and_edit(self):
        self.board_manager.create_board('Checklist Persistence Board')
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id

        card = board.create_card(
            'Checklist Card',
            'desc',
            Priority.MEDIUM,
            column_id,
            todo_items=[
                {'text': 'Draft copy', 'completed': False},
                {'text': 'Review with QA', 'completed': True},
            ],
        )

        created = board.find_card(card.id)
        self.assertEqual(created.get_todo_progress(), (1, 2))

        board.edit_card(
            card.id,
            todo_items=[
                {'text': 'Draft copy', 'completed': True},
                {'text': 'Ship to production', 'completed': False},
            ],
        )

        updated = board.find_card(card.id)
        self.assertEqual(updated.get_todo_progress(), (1, 2))
        self.assertEqual([item.text for item in updated.todo_items], ['Draft copy', 'Ship to production'])
        exported_card = next(item for item in board.export_data()['cards'] if item['id'] == card.id)
        self.assertEqual(len(exported_card['todo_items']), 2)

    def test_gui_can_toggle_card_checklist_item_inline(self):
        self.board_manager.create_board('Inline Checklist Toggle Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id
        card = board.create_card(
            'Inline toggle',
            'desc',
            Priority.MEDIUM,
            column_id,
            todo_items=[{'text': 'Flip me', 'completed': False}],
        )
        todo_item = card.todo_items[0]

        self.gui.handle_card_tile_todo_toggle(column_id, card.id, todo_item.id, True)

        updated = board.find_card(card.id)
        self.assertTrue(updated.todo_items[0].completed)
        self.assertEqual(self.gui.selected_column_id, column_id)
        self.assertEqual(self.gui.selected_card_id, card.id)

    def test_card_list_has_no_default_container_frame(self):
        list_widget = CardListWidget()
        list_widget._apply_drop_style()

        self.assertIn('background: transparent;', list_widget.styleSheet())
        self.assertIn('border: none;', list_widget.styleSheet())

    def test_history_actions_track_current_board_undo_and_redo(self):
        self.board_manager.create_board('Board History Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column_id = board.get_columns_ordered()[0].id

        created_card = board.create_card('Undo Me', 'desc', Priority.MEDIUM, column_id)
        self.gui.refresh_ui()

        self.assertTrue(self.gui.undo_current_board_qaction.isEnabled())
        self.assertIn('Create card', self.gui.undo_current_board_qaction.text())

        self.gui.undo_current_board_action()

        self.assertIsNone(board.find_card(created_card.id))
        self.assertTrue(self.gui.redo_current_board_qaction.isEnabled())
        self.assertIn('Create card', self.gui.redo_current_board_qaction.text())

        self.gui.redo_current_board_action()

        self.assertIsNotNone(board.find_card(created_card.id))
        self.assertTrue(self.gui.undo_current_board_qaction.isEnabled())

    def test_history_actions_track_board_management_undo_and_redo(self):
        first_board_id = self.board_manager.create_board('Primary Board')
        self.gui = MultiBoardGUI(self.board_manager)

        created_board_id = self.board_manager.create_board('Second Board')
        self.gui.refresh_ui()

        self.assertTrue(self.gui.undo_board_management_qaction.isEnabled())
        self.assertIn("Create board 'Second Board'", self.gui.undo_board_management_qaction.text())
        self.assertEqual(len(self.board_manager.get_board_list()), 2)

        self.gui.undo_board_management_action()

        board_ids_after_undo = [board_info['id'] for board_info in self.board_manager.get_board_list()]
        self.assertEqual(board_ids_after_undo, [first_board_id])
        self.assertTrue(self.gui.redo_board_management_qaction.isEnabled())
        self.assertIn("Create board 'Second Board'", self.gui.redo_board_management_qaction.text())

        self.gui.redo_board_management_action()

        board_ids_after_redo = [board_info['id'] for board_info in self.board_manager.get_board_list()]
        self.assertIn(created_board_id, board_ids_after_redo)
        self.assertTrue(self.gui.undo_board_management_qaction.isEnabled())

    def test_column_dialog_prefills_existing_column_values(self):
        self.board_manager.create_board('Column Prefill Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()
        column = board.get_columns_ordered()[1]

        dialog = ColumnDialog(column, self.gui.window)

        self.assertEqual(dialog.name_edit.text(), column.name)
        self.assertEqual(dialog.color_field.color(), column.color)
        self.assertEqual(dialog.completed_check.isChecked(), column.is_completed)
        self.assertEqual(dialog.add_card_check.isChecked(), column.can_add_card)

    def test_scroll_wheel_bubbles_to_parent_when_child_cannot_scroll(self):
        parent_scroll = PropagatingScrollArea()
        parent_scroll.resize(260, 150)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        child_list = PropagatingListWidget(parent=content)
        child_list.setFixedHeight(80)
        child_list.addItem('Only item')
        layout.addWidget(child_list)

        filler = QWidget()
        filler.setFixedHeight(800)
        layout.addWidget(filler)

        parent_scroll.setWidget(content)
        parent_scroll.show()
        self.app.processEvents()

        self.assertEqual(child_list.verticalScrollBar().maximum(), 0)
        self.assertGreater(parent_scroll.verticalScrollBar().maximum(), 0)
        self.assertEqual(parent_scroll.verticalScrollBar().value(), 0)

        local_pos = QPointF(child_list.rect().center())
        global_pos = QPointF(child_list.mapToGlobal(child_list.rect().center()))
        wheel_event = QWheelEvent(
            local_pos,
            global_pos,
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate,
            False,
        )
        child_list.wheelEvent(wheel_event)
        self.app.processEvents()

        self.assertGreater(parent_scroll.verticalScrollBar().value(), 0)

    def test_scroll_wheel_stays_on_child_when_child_can_scroll(self):
        parent_scroll = PropagatingScrollArea()
        parent_scroll.resize(260, 180)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        child_list = PropagatingListWidget(parent=content)
        child_list.setFixedHeight(120)
        for index in range(40):
            child_list.addItem(f'Item {index}')
        layout.addWidget(child_list)

        filler = QWidget()
        filler.setFixedHeight(800)
        layout.addWidget(filler)

        parent_scroll.setWidget(content)
        parent_scroll.show()
        self.app.processEvents()

        self.assertGreater(child_list.verticalScrollBar().maximum(), 0)
        self.assertEqual(child_list.verticalScrollBar().value(), 0)
        self.assertEqual(parent_scroll.verticalScrollBar().value(), 0)

        local_pos = QPointF(child_list.rect().center())
        global_pos = QPointF(child_list.mapToGlobal(child_list.rect().center()))
        wheel_event = QWheelEvent(
            local_pos,
            global_pos,
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate,
            False,
        )
        child_list.wheelEvent(wheel_event)
        self.app.processEvents()

        self.assertGreater(child_list.verticalScrollBar().value(), 0)
        self.assertEqual(parent_scroll.verticalScrollBar().value(), 0)
