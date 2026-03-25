import os
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QMessageBox, QWidget, QVBoxLayout

from kanban.gui.pyside_app import CardDialog, CardListWidget, ColumnDialog, MultiBoardGUI, PropagatingListWidget, PropagatingScrollArea
from kanban.models import Priority
from gui_test_case import GuiTestCase


class GuiBoardRegressionTests(GuiTestCase):
    def test_custom_board_drag_drop_and_attachment_flow(self):
        self.board_manager.create_board('Regression Board')
        self.gui = MultiBoardGUI(self.board_manager)
        board = self.board_manager.get_current_board()

        columns = board.get_columns_ordered()
        first_column, second_column = columns[0], columns[1]
        card = board.create_card('Drag Target', 'drag me', Priority.MEDIUM, first_column.id)

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
                }

        with patch('kanban.gui.pyside_app.CardDialog', FakeCardDialog):
            self.gui.add_subcard_to_selected_card()

        subcards = board.get_subcards(parent_card.id)
        self.assertEqual(len(subcards), 1)
        self.assertEqual(subcards[0].title, 'Child Task')
        self.assertEqual(subcards[0].parent_id, parent_card.id)
        self.assertEqual(subcards[0].priority, Priority.HIGH)

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
