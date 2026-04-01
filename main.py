#!/usr/bin/env python3
## @file
#  @brief Application entry point for the Kanban board project.
"""Kanban Board application launcher."""

import argparse
import sys
from typing import Optional, Sequence

from kanban.board_manager import BoardManager
from kanban.direct_cli import DirectActionCLI, add_direct_action_subcommands
from kanban.multi_board_cli import MultiBoardCLI


def build_parser() -> argparse.ArgumentParser:
    """Build the application argument parser."""
    parser = argparse.ArgumentParser(
        description="Multi-Board Kanban Manager with a desktop GUI, an interactive terminal UI, and direct-action automation commands.",
        epilog="Use --cli for the interactive terminal UI, or run '<command> --help' for direct-action automation details.",
    )
    parser.add_argument('--cli', action='store_true',
                       help='Use the interactive multi-board command-line interface instead of the desktop GUI')
    parser.add_argument('--boards-dir', type=str,
                       help='Specify a custom boards registry directory for this session')
    parser.add_argument(
        '--lock-action',
        choices=('cancel', 'open_read_only', 'delete_lock'),
        default='cancel',
        help='How direct-action commands should respond when a locked board is encountered',
    )

    subparsers = parser.add_subparsers(dest='command')
    add_direct_action_subcommands(subparsers)
    return parser


## @brief Parse command-line options and launch the requested Kanban mode.
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point of the Kanban application."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cli and args.command:
        parser.error('--cli cannot be used with direct-action subcommands.')
    
    try:
        board_manager = BoardManager(args.boards_dir)

        if args.command:
            direct_cli = DirectActionCLI(board_manager, lock_action=args.lock_action)
            return direct_cli.execute(args)

        print("Starting Multi-Board Kanban Manager...")

        if args.cli:
            # Use multi-board CLI interface
            print("Using multi-board CLI mode...")
            multi_cli = MultiBoardCLI(board_manager)
            multi_cli.run()
        else:
            # Use GUI interface with multi-board support
            print("Starting multi-board GUI mode...")
            try:
                from kanban.multi_board_gui import MultiBoardGUI
                multi_gui = MultiBoardGUI(board_manager)
                multi_gui.run()
            except ImportError:
                print("PySide6 not available. Falling back to interactive CLI mode...")
                multi_cli = MultiBoardCLI(board_manager)
                multi_cli.run()
            except Exception as e:
                print(f"GUI error: {e}")
                print("Falling back to interactive CLI mode...")
                multi_cli = MultiBoardCLI(board_manager)
                multi_cli.run()
        return 0
                
    except KeyboardInterrupt:
        print("\n\nGoodbye! Your work has been saved.")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())