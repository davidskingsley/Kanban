## @file
#  @brief Board-management commands for the direct-action CLI.
"""!Board-management commands for the direct-action CLI."""

from __future__ import annotations

import argparse
import json


class DirectCliBoardCommandsMixin:
    """!Board-management commands for the direct CLI."""

    def cmd_list_boards(self, args: argparse.Namespace):
        """!Cmd list boards."""
        boards = self.board_manager.get_board_list()
        if not boards:
            print('No boards found.')
            return

        for board in boards:
            markers = []
            if board.get('is_current'):
                markers.append('current')
            if board.get('external'):
                markers.append('external')
            marker_text = f" [{' | '.join(markers)}]" if markers else ''
            print(f"{board['name']} ({board['id']}){marker_text} backend={board.get('storage_backend', 'json')}")
            if board.get('description'):
                print(f"  {board['description']}")

    def cmd_create_board(self, args: argparse.Namespace):
        """!Cmd create board."""
        board_id = self.board_manager.create_board(
            args.name,
            args.description,
            target_directory=args.target_directory,
            storage_backend=args.storage_backend,
        )
        if args.switch and self.board_manager.current_board_id != board_id:
            self.board_manager.switch_board(board_id)
        print(f"Created board '{args.name}' ({board_id}) using {args.storage_backend} backend.")

    def cmd_switch_board(self, args: argparse.Namespace):
        """!Cmd switch board."""
        board_id, board_info = self._resolve_board_reference(args.board)
        if not self.board_manager.switch_board(board_id):
            raise ValueError(f"Unable to switch to board '{board_info['name']}'.")
        print(f"Switched to board '{board_info['name']}'.")

    def cmd_rename_board(self, args: argparse.Namespace):
        """!Cmd rename board."""
        board_id, board_info = self._resolve_board_reference(args.board)
        if not self.board_manager.rename_board(board_id, args.new_name):
            raise ValueError(f"Unable to rename board '{board_info['name']}'.")
        print(f"Renamed board '{board_info['name']}' to '{args.new_name}'.")

    def cmd_convert_board(self, args: argparse.Namespace):
        """!Cmd convert board."""
        board_id, board_info = self._resolve_board_reference(args.board)
        current_backend = board_info.get('storage_backend', 'json')
        target_file = self.board_manager.convert_board_storage_backend(
            board_id,
            args.storage_backend,
            target_directory=args.target_directory,
        )
        print(
            f"Converted board '{board_info['name']}' from {current_backend} to {args.storage_backend}. "
            f"New file: '{target_file}'."
        )

    def cmd_delete_board(self, args: argparse.Namespace):
        """!Cmd delete board."""
        self._require_force(args.force, 'Deleting a board requires --force.')
        board_id, board_info = self._resolve_board_reference(args.board)
        if not self.board_manager.delete_board(board_id):
            raise ValueError(f"Unable to delete board '{board_info['name']}'.")
        print(f"Deleted board '{board_info['name']}'.")

    def cmd_board_stats(self, args: argparse.Namespace):
        """!Cmd board stats."""
        if args.board:
            board_id, board_info, board = self._load_board(args.board)
            stats = board.get_board_stats()
            print(f"Board: {board_info['name']} ({board_id})")
            print(f"Backend: {board_info.get('storage_backend', 'json')}")
            print(f"Total cards: {stats['total_cards']}")
            for label in self._format_board_stat_lines(stats):
                print(label)
            return

        boards = self.board_manager.get_board_list()
        if not boards:
            print('No boards found.')
            return

        for board in boards:
            print(f"{board['name']} ({board['id']})")
            stats = board.get('stats')
            if stats is None:
                _, _, loaded_board = self._load_board(board['id'])
                stats = loaded_board.get_board_stats()
            summary = ' | '.join(self._format_board_stat_lines(stats))
            print(f"  backend={board.get('storage_backend', 'json')} cards={stats['total_cards']} | {summary}")

    def cmd_export_board(self, args: argparse.Namespace):
        """!Cmd export board."""
        board_id, board_info = self._resolve_board_reference(args.board)
        export_data = self.board_manager.export_board_data(board_id)
        self._write_json(args.output, export_data)
        print(f"Exported board '{board_info['name']}' to '{args.output}'.")

    def cmd_export_all_boards(self, args: argparse.Namespace):
        """!Cmd export all boards."""
        export_data = self.board_manager.export_all_boards()
        self._write_json(args.output, export_data)
        print(f"Exported all boards to '{args.output}'.")

    def cmd_import_boards(self, args: argparse.Namespace):
        """!Cmd import boards."""
        self._require_force(args.force, 'Importing boards requires --force because it replaces the current registry.')
        with open(args.input, 'r', encoding='utf-8') as input_file:
            import_data = json.load(input_file)
        if not self.board_manager.import_boards(import_data):
            raise ValueError('Board import failed.')
        print(f"Imported boards from '{args.input}'.")

    def cmd_load_board_from_folder(self, args: argparse.Namespace):
        """!Cmd load board from folder."""
        chosen = self._select_external_board(args.path, args.board)
        board_id = self.board_manager.add_external_board(
            chosen['data_file'],
            name=args.name or chosen['name'],
            description=args.description or chosen.get('description', ''),
            switch_to=args.switch,
        )
        if not board_id:
            raise ValueError('Board load cancelled.')
        print(f"Registered board '{args.name or chosen['name']}' from '{chosen['data_file']}'.")

    def cmd_undo_board_management(self, args: argparse.Namespace):
        """!Cmd undo board management."""
        description = self.board_manager.undo_last_action()
        if not description:
            raise ValueError('No board-management action is available to undo.')
        print(f'Undid board-management action: {description}')

    def cmd_redo_board_management(self, args: argparse.Namespace):
        """!Cmd redo board management."""
        description = self.board_manager.redo_last_action()
        if not description:
            raise ValueError('No board-management action is available to redo.')
        print(f'Redid board-management action: {description}')

    def cmd_show_board(self, args: argparse.Namespace):
        """!Cmd show board."""
        _, board_info, board = self._load_board(args.board)
        print(f"Board: {board_info['name']}")
        print(board.export_board())