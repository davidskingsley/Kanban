import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

from main import build_parser, main

from kanban.board_manager import BoardManager
from kanban.direct_cli import DirectActionCLI


class DirectCliRegressionTests(unittest.TestCase):
    """!Direct Cli Regression Tests."""
    def setUp(self):
        """!Set up."""
        self.temp_dir = tempfile.mkdtemp(prefix='kanban-direct-cli-')

    def tearDown(self):
        """!Tear down."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def invoke_direct(self, argv):
        """!Invoke direct."""
        parser = build_parser()
        args = parser.parse_args(['--boards-dir', self.temp_dir, *argv])
        manager = BoardManager(self.temp_dir)
        cli = DirectActionCLI(manager, lock_action='cancel')
        output = io.StringIO()
        try:
            with redirect_stdout(output):
                exit_code = cli.execute(args)
        finally:
            manager.close()
        return exit_code, output.getvalue()

    def test_create_and_list_boards_directly(self):
        """!Test create and list boards directly."""
        exit_code, output = self.invoke_direct([
            'create-board',
            '--name', 'Automation Board',
            '--description', 'Created by a script',
            '--storage-backend', 'sqlite',
            '--switch',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Created board 'Automation Board'", output)

        _, output = self.invoke_direct(['list-boards'])

        self.assertIn('Automation Board', output)
        self.assertIn('backend=sqlite', output)
        self.assertIn('current', output)

    def test_create_search_and_show_card_details_directly(self):
        """!Test create search and show card details directly."""
        self.invoke_direct(['create-board', '--name', 'Automation Board'])
        exit_code, output = self.invoke_direct([
            'create-card',
            '--board', 'Automation Board',
            '--title', 'Ship direct CLI',
            '--description', 'Add an automation-friendly command line',
            '--priority', 'high',
            '--assignee', 'Alex',
            '--tags', 'cli,automation',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Created card 'Ship direct CLI'", output)

        _, search_output = self.invoke_direct([
            'search-cards',
            '--board', 'Automation Board',
            '--query', 'Ship direct CLI',
        ])
        self.assertIn('Ship direct CLI', search_output)

        _, detail_output = self.invoke_direct([
            'card-details',
            '--board', 'Automation Board',
            '--card', 'Ship direct CLI',
        ])
        self.assertIn('Assignee: Alex', detail_output)
        self.assertIn('Tags: cli, automation', detail_output)

    def test_direct_cli_can_create_and_replace_card_checklists(self):
        """!Test direct cli can create and replace card checklists."""
        self.invoke_direct(['create-board', '--name', 'Checklist Board'])
        exit_code, output = self.invoke_direct([
            'create-card',
            '--board', 'Checklist Board',
            '--title', 'Ship release',
            '--todo', 'Write release notes',
            '--todo', '[x] Cut release candidate',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Created card 'Ship release'", output)

        _, detail_output = self.invoke_direct([
            'card-details',
            '--board', 'Checklist Board',
            '--card', 'Ship release',
        ])
        self.assertIn('Checklist: 1/2 done', detail_output)
        self.assertIn('[ ] Write release notes', detail_output)
        self.assertIn('[x] Cut release candidate', detail_output)

        exit_code, output = self.invoke_direct([
            'edit-card',
            '--board', 'Checklist Board',
            '--card', 'Ship release',
            '--todo', '[x] Write release notes',
            '--todo', 'Publish announcement',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Updated card 'Ship release'", output)

        _, detail_output = self.invoke_direct([
            'card-details',
            '--board', 'Checklist Board',
            '--card', 'Ship release',
        ])
        self.assertIn('Checklist: 1/2 done', detail_output)
        self.assertIn('[x] Write release notes', detail_output)
        self.assertIn('[ ] Publish announcement', detail_output)

    def test_direct_cli_can_mutate_single_checklist_items(self):
        """!Test direct cli can mutate single checklist items."""
        self.invoke_direct(['create-board', '--name', 'Item Commands Board'])
        self.invoke_direct([
            'create-card',
            '--board', 'Item Commands Board',
            '--title', 'Operate checklist',
            '--todo', 'Initial task',
        ])

        exit_code, output = self.invoke_direct([
            'add-todo-item',
            '--board', 'Item Commands Board',
            '--card', 'Operate checklist',
            '--text', 'Follow-up task',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Added checklist item 'Follow-up task'", output)

        manager = BoardManager(self.temp_dir)
        try:
            board_info = next(board for board in manager.get_board_list() if board['name'] == 'Item Commands Board')
            manager.switch_board(board_info['id'])
            board = manager.get_current_board()
            card = next(card for card in board.get_all_cards() if card.title == 'Operate checklist')
            follow_up_id = next(item.id for item in card.todo_items if item.text == 'Follow-up task')
        finally:
            manager.close()

        exit_code, output = self.invoke_direct([
            'check-todo-item',
            '--board', 'Item Commands Board',
            '--card', 'Operate checklist',
            '--item', 'Initial task',
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("Marked checklist item 'Initial task'", output)

        exit_code, output = self.invoke_direct([
            'toggle-todo-item',
            '--board', 'Item Commands Board',
            '--card', 'Operate checklist',
            '--item', follow_up_id,
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("Toggled checklist item 'Follow-up task'", output)

        exit_code, output = self.invoke_direct([
            'remove-todo-item',
            '--board', 'Item Commands Board',
            '--card', 'Operate checklist',
            '--item', 'Initial task',
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("Removed checklist item 'Initial task'", output)

        _, detail_output = self.invoke_direct([
            'card-details',
            '--board', 'Item Commands Board',
            '--card', 'Operate checklist',
        ])
        self.assertIn('Checklist: 1/1 done', detail_output)
        self.assertIn('[x] Follow-up task', detail_output)
        self.assertNotIn('Initial task', detail_output)

    def test_direct_cli_can_add_edit_list_and_delete_notes(self):
        """!Test direct cli can add edit list and delete notes."""
        self.invoke_direct(['create-board', '--name', 'Notes Board'])
        self.invoke_direct([
            'create-card',
            '--board', 'Notes Board',
            '--title', 'Document release',
        ])

        exit_code, output = self.invoke_direct([
            'add-note',
            '--board', 'Notes Board',
            '--card', 'Document release',
            '--text', 'Drafted the release notes',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Added note (", output)

        manager = BoardManager(self.temp_dir)
        try:
            board_info = next(board for board in manager.get_board_list() if board['name'] == 'Notes Board')
            manager.switch_board(board_info['id'])
            board = manager.get_current_board()
            card = next(card for card in board.get_all_cards() if card.title == 'Document release')
            note_id = card.notes[0].id
        finally:
            manager.close()

        _, list_output = self.invoke_direct([
            'list-notes',
            '--board', 'Notes Board',
            '--card', 'Document release',
        ])
        self.assertIn('Drafted the release notes', list_output)
        self.assertIn(note_id, list_output)

        exit_code, output = self.invoke_direct([
            'edit-note',
            '--board', 'Notes Board',
            '--card', 'Document release',
            '--note', note_id,
            '--text', 'Updated release notes draft',
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn('Updated note', output)

        _, detail_output = self.invoke_direct([
            'card-details',
            '--board', 'Notes Board',
            '--card', 'Document release',
        ])
        self.assertIn('Notes: 1', detail_output)
        self.assertIn('Updated release notes draft', detail_output)

        exit_code, output = self.invoke_direct([
            'delete-note',
            '--board', 'Notes Board',
            '--card', 'Document release',
            '--note', note_id,
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn('Deleted note', output)

        _, list_output = self.invoke_direct([
            'list-notes',
            '--board', 'Notes Board',
            '--card', 'Document release',
        ])
        self.assertIn('Notes: (none)', list_output)

    def test_direct_cli_can_archive_restore_and_delete_archived_cards(self):
        """!Test direct cli can archive restore and delete archived cards."""
        self.invoke_direct(['create-board', '--name', 'Archive Automation'])

        manager = BoardManager(self.temp_dir)
        try:
            board_info = next(board for board in manager.get_board_list() if board['name'] == 'Archive Automation')
            manager.switch_board(board_info['id'])
            board = manager.get_current_board()
            done_column_id = next(column.id for column in board.get_columns_ordered() if column.is_completed)
        finally:
            manager.close()

        self.invoke_direct([
            'create-card',
            '--board', 'Archive Automation',
            '--title', 'Ship archive flow',
            '--column', done_column_id,
            '--assignee', 'Alex',
        ])

        exit_code, output = self.invoke_direct([
            'archive-done-cards',
            '--board', 'Archive Automation',
            '--force',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Archived 1 done card(s) from board 'Archive Automation'.", output)

        _, archived_output = self.invoke_direct(['list-archived-cards', '--board', 'Archive Automation'])
        self.assertIn('Ship archive flow', archived_output)
        self.assertIn('archived=', archived_output)

        exit_code, output = self.invoke_direct([
            'restore-archived-card',
            '--board', 'Archive Automation',
            '--card', 'Ship archive flow',
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("Restored archived card 'Ship archive flow' on board 'Archive Automation'.", output)

        _, board_output = self.invoke_direct(['show-board', '--board', 'Archive Automation'])
        self.assertIn('Ship archive flow', board_output)

        self.invoke_direct([
            'archive-done-cards',
            '--board', 'Archive Automation',
            '--force',
        ])
        exit_code, output = self.invoke_direct([
            'delete-archived-card',
            '--board', 'Archive Automation',
            '--card', 'Ship archive flow',
            '--force',
        ])
        self.assertEqual(exit_code, 0)
        self.assertIn("Deleted archived card 'Ship archive flow' from board 'Archive Automation'.", output)

        _, archived_output = self.invoke_direct(['list-archived-cards', '--board', 'Archive Automation'])
        self.assertIn('No archived cards found.', archived_output)

    def test_edit_card_can_clear_optional_fields_directly(self):
        """!Test edit card can clear optional fields directly."""
        self.invoke_direct(['create-board', '--name', 'Automation Board'])
        self.invoke_direct([
            'create-card',
            '--board', 'Automation Board',
            '--title', 'Card To Clear',
            '--description', 'Temporary description',
            '--assignee', 'Alex',
            '--project', 'Platform',
        ])

        exit_code, output = self.invoke_direct([
            'edit-card',
            '--board', 'Automation Board',
            '--card', 'Card To Clear',
            '--clear-description',
            '--clear-assignee',
            '--clear-project',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Updated card 'Card To Clear'", output)

        _, detail_output = self.invoke_direct([
            'card-details',
            '--board', 'Automation Board',
            '--card', 'Card To Clear',
        ])
        self.assertIn('Description: (no description)', detail_output)
        self.assertIn('Assignee: (unassigned)', detail_output)
        self.assertIn('Project: (none)', detail_output)

    def test_delete_board_requires_force(self):
        """!Test delete board requires force."""
        self.invoke_direct(['create-board', '--name', 'Protected Board'])

        with self.assertRaisesRegex(ValueError, 'requires --force'):
            self.invoke_direct(['delete-board', '--board', 'Protected Board'])

    def test_create_column_and_move_card_directly(self):
        """!Test create column and move card directly."""
        self.invoke_direct(['create-board', '--name', 'Column Automation'])
        self.invoke_direct(['create-column', '--board', 'Column Automation', '--name', 'Blocked', '--can-add-card'])
        self.invoke_direct(['create-card', '--board', 'Column Automation', '--title', 'Waiting on review'])

        exit_code, output = self.invoke_direct([
            'move-card',
            '--board', 'Column Automation',
            '--card', 'Waiting on review',
            '--column', 'Blocked',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Moved card 'Waiting on review'", output)

        _, board_output = self.invoke_direct(['show-board', '--board', 'Column Automation'])
        self.assertIn('Blocked', board_output)
        self.assertIn('Waiting on review', board_output)

    def test_load_board_from_folder_directly(self):
        """!Test load board from folder directly."""
        external_dir = tempfile.mkdtemp(prefix='kanban-external-board-')
        try:
            external_manager = BoardManager(external_dir)
            try:
                external_manager.create_board('External Board', 'Stored elsewhere')
            finally:
                external_manager.close()

            exit_code, output = self.invoke_direct([
                'load-board-from-folder',
                '--path', external_dir,
                '--board', 'External Board',
            ])

            self.assertEqual(exit_code, 0)
            self.assertIn("Registered board 'External Board'", output)

            _, list_output = self.invoke_direct(['list-boards'])
            self.assertIn('External Board', list_output)
            self.assertIn('external', list_output)
        finally:
            shutil.rmtree(external_dir, ignore_errors=True)

    def test_convert_board_between_json_and_sqlite_directly(self):
        """!Test convert board between json and sqlite directly."""
        self.invoke_direct(['create-board', '--name', 'Convertible Board'])
        self.invoke_direct([
            'create-card',
            '--board', 'Convertible Board',
            '--title', 'Preserved Card',
        ])

        exit_code, output = self.invoke_direct([
            'convert-board',
            '--board', 'Convertible Board',
            '--storage-backend', 'sqlite',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Converted board 'Convertible Board' from json to sqlite", output)

        manager = BoardManager(self.temp_dir)
        try:
            boards = manager.get_board_list()
            board_info = next(board for board in boards if board['name'] == 'Convertible Board')
            self.assertEqual(board_info['storage_backend'], 'sqlite')
            self.assertTrue(manager.load_metadata()['boards'][board_info['id']]['data_file'].endswith('.sqlite3'))
        finally:
            manager.close()

        exit_code, output = self.invoke_direct([
            'convert-board',
            '--board', 'Convertible Board',
            '--storage-backend', 'json',
        ])

        self.assertEqual(exit_code, 0)
        self.assertIn("Converted board 'Convertible Board' from sqlite to json", output)

        _, detail_output = self.invoke_direct([
            'card-details',
            '--board', 'Convertible Board',
            '--card', 'Preserved Card',
        ])
        self.assertIn('Title: Preserved Card', detail_output)

    def test_main_executes_direct_action_subcommand(self):
        """!Test main executes direct action subcommand."""
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(['--boards-dir', self.temp_dir, 'create-board', '--name', 'Main Entry Board'])

        self.assertEqual(exit_code, 0)
        self.assertIn("Created board 'Main Entry Board'", output.getvalue())
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'boards_metadata.json')))

    def test_board_stats_reports_backend_type(self):
        """!Test board stats reports backend type."""
        self.invoke_direct(['create-board', '--name', 'Stats Board', '--storage-backend', 'sqlite'])

        exit_code, output = self.invoke_direct(['board-stats', '--board', 'Stats Board'])

        self.assertEqual(exit_code, 0)
        self.assertIn('Backend: sqlite', output)


if __name__ == '__main__':
    unittest.main()