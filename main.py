#!/usr/bin/env python3
## @file
#  @brief Application entry point for the Kanban board project.
"""Kanban Board application launcher."""

import argparse
import sys
from kanban.cli import KanbanCLI
from kanban.multi_board_cli import MultiBoardCLI
from kanban.gui import KanbanGUI
from kanban.multi_board_gui import MultiBoardGUI
from kanban.board import KanbanBoard
from kanban.board_manager import BoardManager


## @brief Parse command-line options and launch the requested Kanban mode.
def main():
    """Main entry point of the Kanban application."""
    parser = argparse.ArgumentParser(description="Multi-Board Kanban Manager")
    parser.add_argument('--cli', action='store_true', 
                       help='Use command-line interface instead of GUI')
    parser.add_argument('--single-board', action='store_true',
                       help='Use legacy single-board mode')
    parser.add_argument('--data-file', type=str,
                       help='Specify custom data file path (single-board mode only)')
    parser.add_argument('--boards-dir', type=str,
                       help='Specify custom boards directory')
    
    args = parser.parse_args()
    
    try:
        if args.single_board:
            # Legacy single-board mode
            print("Starting in single-board mode...")
            board = KanbanBoard(args.data_file)
            
            if args.cli:
                cli = KanbanCLI(board)
                cli.run()
            else:
                try:
                    import tkinter
                    gui = KanbanGUI(board)
                    gui.run()
                except ImportError:
                    print("Tkinter not available. Falling back to CLI mode...")
                    cli = KanbanCLI(board)
                    cli.run()
                except Exception as e:
                    print(f"GUI error: {e}")
                    print("Falling back to CLI mode...")
                    cli = KanbanCLI(board)
                    cli.run()
        else:
            # Multi-board mode (default)
            print("Starting Multi-Board Kanban Manager...")
            board_manager = BoardManager(args.boards_dir)
            
            if args.cli:
                # Use multi-board CLI interface
                print("Using multi-board CLI mode...")
                multi_cli = MultiBoardCLI(board_manager)
                multi_cli.run()
            else:
                # Use GUI interface with multi-board support
                print("Starting multi-board GUI mode...")
                try:
                    import tkinter
                    multi_gui = MultiBoardGUI(board_manager)
                    multi_gui.run()
                except ImportError:
                    print("Tkinter not available. Using multi-board CLI mode...")
                    multi_cli = MultiBoardCLI(board_manager)
                    multi_cli.run()
                except Exception as e:
                    print(f"GUI error: {e}")
                    print("Falling back to multi-board CLI mode...")
                    multi_cli = MultiBoardCLI(board_manager)
                    multi_cli.run()
                
    except KeyboardInterrupt:
        print("\n\nGoodbye! Your work has been saved.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()