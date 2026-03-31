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
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='kanban-direct-cli-')

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def invoke_direct(self, argv):
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

    def test_edit_card_can_clear_optional_fields_directly(self):
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
        self.invoke_direct(['create-board', '--name', 'Protected Board'])

        with self.assertRaisesRegex(ValueError, 'requires --force'):
            self.invoke_direct(['delete-board', '--board', 'Protected Board'])

    def test_create_column_and_move_card_directly(self):
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
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(['--boards-dir', self.temp_dir, 'create-board', '--name', 'Main Entry Board'])

        self.assertEqual(exit_code, 0)
        self.assertIn("Created board 'Main Entry Board'", output.getvalue())
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'boards_metadata.json')))

    def test_board_stats_reports_backend_type(self):
        self.invoke_direct(['create-board', '--name', 'Stats Board', '--storage-backend', 'sqlite'])

        exit_code, output = self.invoke_direct(['board-stats', '--board', 'Stats Board'])

        self.assertEqual(exit_code, 0)
        self.assertIn('Backend: sqlite', output)


if __name__ == '__main__':
    unittest.main()