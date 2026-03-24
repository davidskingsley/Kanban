## @file
#  @brief Interactive command-line interface for managing multiple Kanban boards.
"""Multi-board command-line interface for the Kanban board application."""

import os

from .board_manager import BoardManager
from .cli import BoardCLI


## @brief Provide menu-driven multi-board management from the terminal.
class MultiBoardCLI:
    """Command line interface for managing multiple Kanban boards."""
    
    def __init__(self, board_manager: BoardManager):
        self.board_manager = board_manager
        self.board_manager.set_lock_handler(self.prompt_for_locked_board_action)
        self.running = True
        self.current_cli = None

    def prompt_for_locked_board_action(self, file_path: str, lock_details: dict) -> str:
        """Prompt for how to handle a locked board file."""
        print("\n--- BOARD LOCKED ---")
        print(f"Board file: {file_path}")
        if lock_details:
            print(f"Host: {lock_details.get('hostname', 'unknown')}")
            print(f"Opened: {lock_details.get('opened_at', 'unknown')}")

        while True:
            choice = input("Open read only, delete the lock, or cancel? [r/d/c]: ").strip().lower()
            if choice in ('r', 'ro', 'read', 'read-only', 'readonly'):
                return 'open_read_only'
            if choice in ('d', 'delete', 'del'):
                return 'delete_lock'
            if choice in ('c', 'cancel', ''):
                return 'cancel'
            print("Please enter 'r' to open read only, 'd' to delete the lock, or 'c' to cancel.")
    
    def run(self):
        """Main CLI loop."""
        self.show_welcome()
        
        # Check if any boards exist, if not, create one
        boards = self.board_manager.get_board_list()
        if not boards:
            print("No boards found. Let's create your first board!")
            self.create_board()
        
        while self.running:
            try:
                self.show_board_selector()
                choice = input("Enter your choice: ").strip()
                self.handle_main_choice(choice)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"Error: {e}")
    
    def show_welcome(self):
        """Show welcome message."""
        print("=" * 60)
        print("🗂️  WELCOME TO MULTI-BOARD KANBAN MANAGER  🗂️")
        print("=" * 60)
        print("Organize multiple projects with separate Kanban boards!")
        print()
    
    def show_board_selector(self):
        """Display board selection and management options."""
        boards = self.board_manager.get_board_list()
        
        if boards:
            print("📋 YOUR BOARDS:")
            print("-" * 40)
            for i, board in enumerate(boards, 1):
                current_marker = " 👈 (current)" if board['is_current'] else ""
                stats_info = ""
                if 'stats' in board:
                    stats = board['stats']
                    stats_info = f" | {stats['total_cards']} cards"
                
                print(f"{i}. {board['name']}{current_marker}{stats_info}")
                if board['description']:
                    print(f"   📝 {board['description']}")
            print()
        
        print("BOARD ACTIONS:")
        if boards:
            print("1. Open current board")
            print("2. Switch board")
            print("3. Create new board")
            print("4. Rename board")
            print("5. Delete board")
            print("6. Board statistics")
            print("7. Export all boards")
            print("8. Import boards")
            print("9. Load board from folder")
            print("10. Undo last board-management change")
            print("11. Redo last undone board-management change")
        else:
            print("3. Create new board")
            print("8. Import boards")
            print("9. Load board from folder")
            print("10. Undo last board-management change")
            print("11. Redo last undone board-management change")
        print("0. Exit")
        print()
    
    def handle_main_choice(self, choice: str):
        """Handle user's main menu choice."""
        boards = self.board_manager.get_board_list()
        
        handlers = {
            '1': self.open_current_board if boards else None,
            '2': self.switch_board if boards else None,
            '3': self.create_board,
            '4': self.rename_board if boards else None,
            '5': self.delete_board if boards else None,
            '6': self.show_board_statistics if boards else None,
            '7': self.export_all_boards if boards else None,
            '8': self.import_boards,
            '9': self.load_board_from_folder,
            '10': self.undo_last_change,
            '11': self.redo_last_change,
            '0': self.exit_app
        }
        
        if choice in handlers and handlers[choice]:
            handlers[choice]()
        elif choice in handlers:
            print("This option is not available (no boards found).")
        else:
            print("Invalid choice. Please try again.")
        
        if choice != '0' and choice != '1':  # Don't pause after opening board or exit
            input("\nPress Enter to continue...")
    
    def open_current_board(self):
        """Open the current board in the board command interface."""
        current_board = self.board_manager.get_current_board()
        if not current_board:
            if self.board_manager.current_board_id:
                print("Board open cancelled.")
            else:
                print("No current board selected!")
            return
        
        print("Opening board interface...")
        print()
        
        board_cli = BoardCLI(current_board)
        board_cli.run()
    
    def switch_board(self):
        """Switch to a different board."""
        boards = self.board_manager.get_board_list()
        if not boards:
            print("No boards available!")
            return
        
        print("\n--- SWITCH BOARD ---")
        print("Available boards:")
        for i, board in enumerate(boards, 1):
            current_marker = " (current)" if board['is_current'] else ""
            print(f"{i}. {board['name']}{current_marker}")
        
        try:
            choice = int(input(f"Select board (1-{len(boards)}): "))
            if 1 <= choice <= len(boards):
                board = boards[choice - 1]
                if self.board_manager.switch_board(board['id']):
                    print(f"✅ Switched to board '{board['name']}'!")
                else:
                    print("❌ Failed to switch board!")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def create_board(self):
        """Create a new board."""
        print("\n--- CREATE NEW BOARD ---")
        name = input("Board name: ").strip()
        if not name:
            print("Board name is required!")
            return
        
        description = input("Description (optional): ").strip()

        default_dir = self.board_manager.boards_directory
        storage_dir = input(f"Storage folder [{default_dir}]: ").strip() or default_dir

        board_id = self.board_manager.create_board(name, description, target_directory=storage_dir)
        if board_id:
            print(f"✅ Board '{name}' created successfully!")
            if os.path.abspath(storage_dir) != os.path.abspath(default_dir):
                print(f"📁 Stored at: {storage_dir}")
            
            # Ask if user wants to switch to the new board
            if len(self.board_manager.get_board_list()) > 1:
                switch = input("Switch to the new board now? (Y/n): ").strip().lower()
                if switch != 'n':
                    self.board_manager.switch_board(board_id)
                    print(f"Switched to board '{name}'!")
        else:
            print("❌ Failed to create board!")
    
    def rename_board(self):
        """Rename a board."""
        boards = self.board_manager.get_board_list()
        if not boards:
            print("No boards available!")
            return
        
        print("\n--- RENAME BOARD ---")
        print("Available boards:")
        for i, board in enumerate(boards, 1):
            print(f"{i}. {board['name']}")
        
        try:
            choice = int(input(f"Select board to rename (1-{len(boards)}): "))
            if 1 <= choice <= len(boards):
                board = boards[choice - 1]
                new_name = input(f"New name for '{board['name']}': ").strip()
                
                if new_name:
                    if self.board_manager.rename_board(board['id'], new_name):
                        print(f"✅ Board renamed to '{new_name}'!")
                    else:
                        print("❌ Failed to rename board!")
                else:
                    print("Board name cannot be empty!")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def delete_board(self):
        """Delete a board."""
        boards = self.board_manager.get_board_list()
        if not boards:
            print("No boards available!")
            return
        
        print("\n--- DELETE BOARD ---")
        print("Available boards:")
        for i, board in enumerate(boards, 1):
            current_marker = " (current)" if board['is_current'] else ""
            print(f"{i}. {board['name']}{current_marker}")
        
        try:
            choice = int(input(f"Select board to delete (1-{len(boards)}): "))
            if 1 <= choice <= len(boards):
                board = boards[choice - 1]
                
                print(f"\n⚠️  WARNING: This will permanently delete board '{board['name']}' and all its cards!")
                if len(boards) == 1:
                    print("Deleting the last board will return the app to an empty state.")
                confirm = input("Type 'DELETE' to confirm: ").strip()
                
                if confirm == 'DELETE':
                    if self.board_manager.delete_board(board['id']):
                        print(f"✅ Board '{board['name']}' deleted successfully!")
                    else:
                        print("❌ Failed to delete board!")
                else:
                    print("Deletion cancelled.")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def show_board_statistics(self):
        """Show statistics for all boards."""
        boards = self.board_manager.get_board_list()
        if not boards:
            print("No boards available!")
            return
        
        print("\n--- BOARD STATISTICS ---")
        
        total_cards = 0
        total_todos = 0
        total_in_progress = 0
        total_review = 0
        total_done = 0
        
        for board in boards:
            print(f"\n📋 Board: {board['name']}")
            if board['description']:
                print(f"   📝 {board['description']}")
            
            if 'stats' in board:
                stats = board['stats']
                print(f"   📊 Total cards: {stats['total_cards']}")
                print(f"   📝 To Do: {stats['todo']}")
                print(f"   ⚡ In Progress: {stats['in_progress']}")
                print(f"   🔍 Review: {stats['review']}")
                print(f"   ✅ Done: {stats['done']}")
                
                total_cards += stats['total_cards']
                total_todos += stats['todo']
                total_in_progress += stats['in_progress']
                total_review += stats['review']
                total_done += stats['done']
            else:
                print("   📊 (Board not loaded)")
        
        print(f"\n🌟 OVERALL STATISTICS:")
        print(f"   📋 Total boards: {len(boards)}")
        print(f"   📊 Total cards: {total_cards}")
        print(f"   📝 Total To Do: {total_todos}")
        print(f"   ⚡ Total In Progress: {total_in_progress}")
        print(f"   🔍 Total Review: {total_review}")
        print(f"   ✅ Total Done: {total_done}")
    
    def export_all_boards(self):
        """Export all boards to a backup file."""
        print("\n--- EXPORT ALL BOARDS ---")
        filename = input("Export filename (default: kanban_backup.json): ").strip()
        if not filename:
            filename = "kanban_backup.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        try:
            import json
            export_data = self.board_manager.export_all_boards()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ All boards exported to '{filename}'!")
        except Exception as e:
            print(f"❌ Failed to export boards: {e}")
    
    def import_boards(self):
        """Import boards from a backup file."""
        print("\n--- IMPORT BOARDS ---")
        filename = input("Import filename: ").strip()
        
        if not filename:
            print("Filename is required!")
            return
        
        try:
            import json
            import os
            
            if not os.path.exists(filename):
                print(f"File '{filename}' not found!")
                return
            
            with open(filename, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            print("⚠️  WARNING: This will replace all existing boards!")
            confirm = input("Type 'IMPORT' to confirm: ").strip()
            
            if confirm == 'IMPORT':
                if self.board_manager.import_boards(import_data):
                    print(f"✅ Boards imported from '{filename}'!")
                else:
                    print("❌ Failed to import boards!")
            else:
                print("Import cancelled.")
                
        except Exception as e:
            print(f"❌ Failed to import boards: {e}")

    def load_board_from_folder(self):
        """Load a specific board from an external folder."""
        import json
        import os

        print("\n--- LOAD BOARD FROM FOLDER ---")
        folder = input("Folder path: ").strip()
        if not folder:
            print("Folder path is required!")
            return

        if not os.path.isdir(folder):
            print("The provided folder does not exist.")
            return

        options = []
        option_map = {}
        metadata_path = os.path.join(folder, 'boards_metadata.json')

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
                    metadata = json.load(metadata_file)

                for board_id, board_info in metadata.get('boards', {}).items():
                    data_file = board_info.get('data_file')
                    if not data_file:
                        continue
                    if not os.path.isabs(data_file):
                        data_file = os.path.join(folder, data_file)

                    label = board_info.get('name', board_id)
                    option_map[label] = {
                        'data_file': data_file,
                        'name': board_info.get('name', label),
                        'description': board_info.get('description', ''),
                        'use_custom_columns': board_info.get('use_custom_columns'),
                    }
                    options.append(label)
            except Exception as error:
                print(f"❌ Failed to read board metadata: {error}")
                return
        else:
            for entry in sorted(os.listdir(folder)):
                if not entry.endswith('.json') or entry == 'boards_metadata.json' or entry.endswith('.backup.json'):
                    continue

                try:
                    inspected = self.board_manager.inspect_board_file(os.path.join(folder, entry))
                except FileNotFoundError:
                    continue

                label = inspected['name']
                if label in option_map:
                    label = f"{label} ({entry})"
                option_map[label] = {
                    'data_file': inspected['data_file'],
                    'name': inspected['name'],
                    'description': '',
                    'use_custom_columns': inspected['use_custom_columns'],
                }
                options.append(label)

        if not options:
            print("No board files were found in the selected folder.")
            return

        print("\nAvailable boards:")
        for index, option in enumerate(options, 1):
            print(f"{index}. {option}")

        try:
            choice = int(input(f"Select board (1-{len(options)}): "))
            if not 1 <= choice <= len(options):
                print("Invalid selection!")
                return
        except ValueError:
            print("Invalid input!")
            return

        board_choice = option_map[options[choice - 1]]
        try:
            board_id = self.board_manager.add_external_board(
                board_choice['data_file'],
                name=board_choice['name'],
                description=board_choice['description'],
                use_custom_columns=board_choice['use_custom_columns'],
                switch_to=True,
            )
            if not board_id:
                print("Board load cancelled.")
                return
            board = self.board_manager.get_current_board()
            print(f"✅ Loaded board '{board_choice['name']}'")
            if board and board.is_read_only():
                print(f"🔒 {board.get_read_only_message()}")
        except Exception as error:
            print(f"❌ Failed to load board: {error}")

    def undo_last_change(self):
        """Undo the most recent board-management change."""
        description = self.board_manager.undo_last_action()
        if not description:
            print("No board-management action is available to undo.")
            return

        print(f"↩ Undid: {description}")

    def redo_last_change(self):
        """Redo the most recently undone board-management change."""
        description = self.board_manager.redo_last_action()
        if not description:
            print("No board-management action is available to redo.")
            return

        print(f"↪ Redid: {description}")
    
    def exit_app(self):
        """Exit the application."""
        self.board_manager.close()
        print("\n👋 Goodbye! All your boards are automatically saved!")
        self.running = False