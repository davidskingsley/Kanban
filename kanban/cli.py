## @file
#  @brief Interactive command-line interface for operating a single Kanban board.
"""Command Line Interface for the Kanban board application."""

from typing import Optional

from .board import KanbanBoard
from .models import Priority, Status


## @brief Provide menu-driven access to single-board Kanban operations.
class KanbanCLI:
    """Command line interface for the Kanban board."""
    
    def __init__(self, board: KanbanBoard):
        self.board = board
        self.running = True
    
    def run(self):
        """Main CLI loop."""
        self.show_welcome()
        
        while self.running:
            try:
                self.show_board()
                self.show_menu()
                choice = input("Enter your choice: ").strip()
                self.handle_choice(choice)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"Error: {e}")
    
    def show_welcome(self):
        """Show welcome message."""
        print("=" * 50)
        print("🗂️  WELCOME TO KANBAN BOARD MANAGER  🗂️")
        print("=" * 50)
        print("Organize your tasks efficiently!")
        if self.board.is_read_only():
            print("🔒 This board is open in read-only mode.")
        print()

    def ensure_board_writable(self) -> bool:
        """Return False and explain why if the current board is read-only."""
        if not self.board.is_read_only():
            return True

        print(f"\n🔒 {self.board.get_read_only_message()}")
        return False
    
    def show_board(self):
        """Display the current board state."""
        print(self.board.export_board())
        print()
        
        # Show board statistics
        stats = self.board.get_board_stats()
        print(f"📊 Board Stats: {stats['total_cards']} total cards | "
              f"🟢 {stats['priority_counts'][Priority.LOW]} low | "
              f"🟡 {stats['priority_counts'][Priority.MEDIUM]} medium | "
              f"🟠 {stats['priority_counts'][Priority.HIGH]} high | "
              f"🔴 {stats['priority_counts'][Priority.CRITICAL]} critical")
        print()
    
    def show_menu(self):
        """Display the main menu."""
        print("CARD ACTIONS:")
        print("1. Create new card")
        print("2. Edit card")
        print("3. Move card")
        print("4. Delete card")
        print("5. Search cards")
        print("6. Filter by priority")
        print("7. Filter by assignee")
        print("8. Add tag to card")
        print("9. Card details")
        print("10. Clear done cards")
        print("11. Add subcard")
        
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            print("\nCOLUMN ACTIONS:")
            print("12. Create new column")
            print("13. Rename column")
            print("14. Delete column")
            print("15. Reorder columns")
            print("16. Change column color")
            print("17. View columns")
        
        print("\nOTHER:")
        print("18. Create backup")
        print("0. Exit")
        print()
    
    def handle_choice(self, choice: str):
        """Handle user's menu choice."""
        handlers = {
            '1': self.create_card,
            '2': self.edit_card,
            '3': self.move_card,
            '4': self.delete_card,
            '5': self.search_cards,
            '6': self.filter_by_priority,
            '7': self.filter_by_assignee,
            '8': self.add_tag_to_card,
            '9': self.show_card_details,
            '10': self.clear_done_cards,
            '11': self.add_subcard,
            '12': self.create_column if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns else None,
            '13': self.rename_column if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns else None,
            '14': self.delete_column if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns else None,
            '15': self.reorder_columns if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns else None,
            '16': self.change_column_color if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns else None,
            '17': self.view_columns if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns else None,
            '18': self.create_backup,
            '0': self.exit_app
        }
        
        if choice in handlers and handlers[choice]:
            handlers[choice]()
        else:
            print("Invalid choice. Please try again.")
        
        if choice != '0':
            input("\nPress Enter to continue...")
    
    def create_card(self):
        """Create a new card."""
        if not self.ensure_board_writable():
            return

        print("\n--- CREATE NEW CARD ---")
        title = input("Card title: ").strip()
        if not title:
            print("Title is required!")
            return
        
        description = input("Description (optional): ").strip()
        project = input("Project (optional): ").strip() or None
        print("\nPriority levels:")
        for i, priority in enumerate(Priority, 1):
            print(f"{i}. {priority.value}")
        
        try:
            priority_choice = int(input("Choose priority (1-4, default=2): ") or "2")
            priorities = list(Priority)
            priority = priorities[priority_choice - 1] if 1 <= priority_choice <= 4 else Priority.MEDIUM
        except (ValueError, IndexError):
            priority = Priority.MEDIUM
        
        assignee = input("Assignee (optional): ").strip() or None
        
        # Handle column selection for custom columns
        column_id = None
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            columns = self.board.get_columns_ordered()
            if columns:
                print("\nAvailable columns:")
                for i, column in enumerate(columns, 1):
                    print(f"{i}. {column.name}")
                
                try:
                    col_choice = input(f"Choose column (1-{len(columns)}, default=1): ").strip()
                    col_choice = int(col_choice) if col_choice else 1
                    if 1 <= col_choice <= len(columns):
                        column_id = columns[col_choice - 1].id
                except (ValueError, IndexError):
                    column_id = columns[0].id  # Default to first column
        
        try:
            card = self.board.create_card(title, description, priority, column_id, project)
            if assignee:
                self.board.edit_card(card.id, assignee=assignee)
            
            print(f"✅ Card '{title}' created successfully!")
        except ValueError as e:
            print(f"❌ Error creating card: {e}")
    
    def edit_card(self):
        """Edit an existing card."""
        if not self.ensure_board_writable():
            return

        print("\n--- EDIT CARD ---")
        card_id = self.select_card()
        if not card_id:
            return
        
        card = self.board.find_card(card_id)
        if not card:
            print("Card not found!")
            return
        
        print(f"\nEditing card: {card.title}")
        print("(Leave blank to keep current value)")
        
        new_title = input(f"Title [{card.title}]: ").strip() or None
        new_description = input(f"Description [{card.description}]: ").strip()
        if new_description == "":
            new_description = None
        
        print("\nPriority levels:")
        for i, priority in enumerate(Priority, 1):
            current = " (current)" if priority == card.priority else ""
            print(f"{i}. {priority.value}{current}")
        
        new_priority = None
        try:
            priority_choice = input("Choose priority (1-4, blank to keep current): ").strip()
            if priority_choice:
                priorities = list(Priority)
                new_priority = priorities[int(priority_choice) - 1]
        except (ValueError, IndexError):
            pass
        
        new_assignee = input(f"Assignee [{card.assignee or 'none'}]: ").strip()
        if new_assignee == "":
            new_assignee = None

        new_project = input(f"Project [{card.project or 'none'}]: ").strip()
        if new_project == "":
            new_project = None

        self.board.edit_card(card_id, new_title, new_description, new_priority, new_assignee, new_project)
        print("✅ Card updated successfully!")

    def add_subcard(self):
        """Create a real child card under an existing top-level card."""
        if not self.ensure_board_writable():
            return

        print("\n--- ADD SUBCARD ---")
        parent_id = self.select_card(top_level_only=True)
        if not parent_id:
            return

        parent_card = self.board.find_card(parent_id)
        if not parent_card:
            print("Parent card not found!")
            return

        print(f"Creating subcard for: {parent_card.title}")
        title = input("Subcard title: ").strip()
        if not title:
            print("Title is required!")
            return

        description = input("Description (optional): ").strip()
        project = input(f"Project [{parent_card.project or 'none'}]: ").strip() or parent_card.project

        print("\nPriority levels:")
        for i, priority in enumerate(Priority, 1):
            print(f"{i}. {priority.value}")

        try:
            priority_choice = int(input("Choose priority (1-4, default=2): ") or "2")
            priorities = list(Priority)
            priority = priorities[priority_choice - 1] if 1 <= priority_choice <= 4 else Priority.MEDIUM
        except (ValueError, IndexError):
            priority = Priority.MEDIUM

        assignee = input("Assignee (optional): ").strip() or None
        tags_text = input("Tags (comma-separated, optional): ").strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []

        try:
            subcard = self.board.create_subcard(parent_id, title, description, priority, project)
            if assignee:
                self.board.edit_card(subcard.id, assignee=assignee)
            for tag in tags:
                subcard.add_tag(tag)
            self.board.save_board()
            print(f"✅ Subcard '{title}' created successfully!")
        except ValueError as error:
            print(f"❌ Error creating subcard: {error}")
    
    def move_card(self):
        """Move a card to a different column."""
        if not self.ensure_board_writable():
            return

        print("\n--- MOVE CARD ---")
        card_id = self.select_card()
        if not card_id:
            return
        
        card = self.board.find_card(card_id)
        if not card:
            print("Card not found!")
            return
        
        print(f"\nMoving card: {card.title}")
        
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            # Custom columns mode
            ordered_columns = self.board.get_columns_ordered()
            current_column = None
            
            for column in ordered_columns:
                if column.id == card.column_id:
                    current_column = column
                    break
            
            print(f"Current column: {current_column.name if current_column else 'Unknown'}")
            
            print("\nAvailable columns:")
            for i, column in enumerate(ordered_columns, 1):
                current = " (current)" if column.id == card.column_id else ""
                print(f"{i}. {column.name}{current}")
            
            try:
                choice = int(input(f"Choose new column (1-{len(ordered_columns)}): "))
                if 1 <= choice <= len(ordered_columns):
                    new_column = ordered_columns[choice - 1]
                    if new_column.id != card.column_id:
                        self.board.move_card(card_id, new_column.id)
                        print(f"✅ Card moved to {new_column.name}!")
                    else:
                        print("Card is already in that column.")
                else:
                    print("Invalid choice!")
            except (ValueError, IndexError):
                print("Invalid input!")
        else:
            # Legacy mode
            print(f"Current status: {card.status.value}")
            
            print("\nAvailable statuses:")
            statuses = list(Status)
            for i, status in enumerate(statuses, 1):
                current = " (current)" if status == card.status else ""
                print(f"{i}. {status.value}{current}")
            
            try:
                choice = int(input("Choose new status (1-4): "))
                if 1 <= choice <= 4:
                    new_status = statuses[choice - 1]
                    if new_status != card.status:
                        self.board.move_card(card_id, new_status)
                        print(f"✅ Card moved to {new_status.value}!")
                    else:
                        print("Card is already in that status.")
                else:
                    print("Invalid choice!")
            except (ValueError, IndexError):
                print("Invalid input!")
    
    def delete_card(self):
        """Delete a card."""
        if not self.ensure_board_writable():
            return

        print("\n--- DELETE CARD ---")
        card_id = self.select_card()
        if not card_id:
            return
        
        card = self.board.find_card(card_id)
        if not card:
            print("Card not found!")
            return
        
        print(f"\nCard to delete: {card.title}")
        confirm = input("Are you sure you want to delete this card? (y/N): ").strip().lower()
        
        if confirm == 'y':
            if self.board.delete_card(card_id):
                print("✅ Card deleted successfully!")
            else:
                print("❌ Failed to delete card!")
        else:
            print("Deletion cancelled.")
    
    def search_cards(self):
        """Search for cards."""
        print("\n--- SEARCH CARDS ---")
        query = input("Enter search query: ").strip()
        if not query:
            print("Search query cannot be empty!")
            return
        
        results = self.board.search_cards(query)
        if not results:
            print("No cards found matching your query.")
            return
        
        print(f"\nFound {len(results)} card(s):")
        for i, card in enumerate(results, 1):
            print(f"{i}. [{card.status.value}] {card}")
    
    def filter_by_priority(self):
        """Filter cards by priority."""
        print("\n--- FILTER BY PRIORITY ---")
        print("Priority levels:")
        priorities = list(Priority)
        for i, priority in enumerate(priorities, 1):
            print(f"{i}. {priority.value}")
        
        try:
            choice = int(input("Choose priority (1-4): "))
            if 1 <= choice <= 4:
                priority = priorities[choice - 1]
                results = self.board.get_cards_by_priority(priority)
                
                if not results:
                    print(f"No cards found with {priority.value} priority.")
                    return
                
                print(f"\nCards with {priority.value} priority:")
                for i, card in enumerate(results, 1):
                    print(f"{i}. [{card.status.value}] {card}")
            else:
                print("Invalid choice!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def filter_by_assignee(self):
        """Filter cards by assignee."""
        print("\n--- FILTER BY ASSIGNEE ---")
        assignee = input("Enter assignee name: ").strip()
        if not assignee:
            print("Assignee name cannot be empty!")
            return
        
        results = self.board.get_cards_by_assignee(assignee)
        if not results:
            print(f"No cards found assigned to '{assignee}'.")
            return
        
        print(f"\nCards assigned to '{assignee}':")
        for i, card in enumerate(results, 1):
            print(f"{i}. [{card.status.value}] {card}")
    
    def add_tag_to_card(self):
        """Add a tag to a card."""
        if not self.ensure_board_writable():
            return

        print("\n--- ADD TAG TO CARD ---")
        card_id = self.select_card()
        if not card_id:
            return
        
        card = self.board.find_card(card_id)
        if not card:
            print("Card not found!")
            return
        
        print(f"\nAdding tag to card: {card.title}")
        if card.tags:
            print(f"Current tags: {', '.join(card.tags)}")
        
        tag = input("Enter tag name: ").strip()
        if tag:
            card.add_tag(tag)
            self.board.save_board()
            print(f"✅ Tag '{tag}' added to card!")
        else:
            print("Tag name cannot be empty!")
    
    def show_card_details(self):
        """Show detailed information about a card."""
        print("\n--- CARD DETAILS ---")
        card_id = self.select_card()
        if not card_id:
            return
        
        card = self.board.find_card(card_id)
        if not card:
            print("Card not found!")
            return
        
        print(f"\n📋 Card Details:")
        print(f"ID: {card.id}")
        print(f"Title: {card.title}")
        print(f"Description: {card.description or '(no description)'}")
        print(f"Status: {card.status.value}")
        print(f"Priority: {card.priority.value}")
        print(f"Project: {card.project or '(none)'}")
        print(f"Assignee: {card.assignee or '(unassigned)'}")
        print(f"Tags: {', '.join(card.tags) if card.tags else '(no tags)'}")

        parent_card = self.board.get_parent_card(card)
        if parent_card:
            print(f"Parent Card: {parent_card.title}")

        completed, total = self.board.get_subcard_progress(card.id)
        if total:
            print(f"Subcards: {completed}/{total} done")
            for subcard in self.board.get_subcards(card.id):
                tick = "[x]" if self.board.is_card_done(subcard) else "[ ]"
                print(f"  {tick} {subcard.title} ({self.board.get_card_location_label(subcard)})")

        print(f"Created: {card.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Updated: {card.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def clear_done_cards(self):
        """Clear all cards from the Done column."""
        if not self.ensure_board_writable():
            return

        print("\n--- CLEAR DONE CARDS ---")
        stats = self.board.get_board_stats()
        done_count = stats['done']
        
        if done_count == 0:
            print("No cards in Done column to clear.")
            return
        
        print(f"This will delete {done_count} card(s) from the Done column.")
        confirm = input("Are you sure? (y/N): ").strip().lower()
        
        if confirm == 'y':
            cleared = self.board.clear_done_cards()
            print(f"✅ Cleared {cleared} card(s) from Done column!")
        else:
            print("Operation cancelled.")
    
    def create_backup(self):
        """Create a backup of the board data."""
        print("\n--- CREATE BACKUP ---")
        backup_path = self.board.storage.backup()
        if backup_path:
            print(f"✅ Backup created: {backup_path}")
        else:
            print("❌ Failed to create backup!")
    
    def select_card(self, top_level_only: bool = False) -> Optional[str]:
        """Helper method to select a card from the board."""
        # Show all cards with indices
        all_cards = []
        
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            # Custom columns mode
            for column in self.board.custom_columns.values():
                for card in column:
                    if top_level_only and card.parent_id:
                        continue
                    all_cards.append((card, column.name))
        else:
            # Legacy mode
            for column in self.board.columns.values():
                for card in column:
                    if top_level_only and card.parent_id:
                        continue
                    all_cards.append((card, card.status.value))
        
        if not all_cards:
            print("No cards available!")
            return None
        
        print("\nAvailable cards:")
        for i, (card, column_name) in enumerate(all_cards, 1):
            parent_info = " <subcard>" if card.parent_id else ""
            print(f"{i}. [{column_name}] {card.title}{parent_info}")
        
        try:
            choice = int(input(f"Select card (1-{len(all_cards)}): "))
            if 1 <= choice <= len(all_cards):
                return all_cards[choice - 1][0].id
            else:
                print("Invalid selection!")
                return None
        except (ValueError, IndexError):
            print("Invalid input!")
            return None
    
    def exit_app(self):
        """Exit the application."""
        print("\nSaving your work...")
        if not self.board.is_read_only():
            self.board.save_board()
        self.board.close()
        print("👋 Goodbye! Thanks for using Kanban Board Manager!")
        self.running = False
    
    # Column Management Methods
    def create_column(self):
        """Create a new column."""
        if not self.ensure_board_writable():
            return

        print("\n--- CREATE NEW COLUMN ---")
        name = input("Column name: ").strip()
        if not name:
            print("Column name is required!")
            return
        
        colors = {
            "1": "#FF9800",  # Orange
            "2": "#2196F3",  # Blue
            "3": "#4CAF50",  # Green
            "4": "#F44336",  # Red
            "5": "#9C27B0",  # Purple
            "6": "#FF5722",  # Deep Orange
            "7": "#607D8B",  # Blue Grey
            "8": "#795548",  # Brown
        }
        
        print("\nAvailable colors:")
        print("1. Orange   2. Blue     3. Green    4. Red")
        print("5. Purple   6. D.Orange 7. B.Grey   8. Brown")
        
        color_choice = input("Choose color (1-8, default=2): ").strip() or "2"
        color = colors.get(color_choice, colors["2"])
        
        try:
            position = input("Position (leave blank for last): ").strip()
            position = int(position) if position else None
        except ValueError:
            position = None
        
        column_id = self.board.create_column(name, position, color)
        print(f"✅ Column '{name}' created successfully!")
    
    def rename_column(self):
        """Rename an existing column."""
        if not self.ensure_board_writable():
            return

        print("\n--- RENAME COLUMN ---")
        columns = self.board.get_columns_ordered()
        if not columns:
            print("No columns available!")
            return
        
        print("Available columns:")
        for i, column in enumerate(columns, 1):
            print(f"{i}. {column.name}")
        
        try:
            choice = int(input(f"Select column to rename (1-{len(columns)}): "))
            if 1 <= choice <= len(columns):
                column = columns[choice - 1]
                new_name = input(f"New name for '{column.name}': ").strip()
                
                if new_name:
                    if self.board.rename_column(column.id, new_name):
                        print(f"✅ Column renamed to '{new_name}'!")
                    else:
                        print("❌ Failed to rename column!")
                else:
                    print("Column name cannot be empty!")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def delete_column(self):
        """Delete a column."""
        if not self.ensure_board_writable():
            return

        print("\n--- DELETE COLUMN ---")
        columns = self.board.get_columns_ordered()
        if len(columns) <= 1:
            print("Cannot delete the last remaining column!")
            return
        
        print("Available columns:")
        for i, column in enumerate(columns, 1):
            print(f"{i}. {column.name} ({len(column)} cards)")
        
        try:
            choice = int(input(f"Select column to delete (1-{len(columns)}): "))
            if 1 <= choice <= len(columns):
                column = columns[choice - 1]
                
                if len(column) > 0:
                    print(f"\nThis column contains {len(column)} card(s).")
                    print("Where should these cards be moved?")
                    
                    other_columns = [col for col in columns if col.id != column.id]
                    for i, col in enumerate(other_columns, 1):
                        print(f"{i}. {col.name}")
                    
                    move_choice = input(f"Select destination column (1-{len(other_columns)}): ").strip()
                    try:
                        move_idx = int(move_choice) - 1
                        if 0 <= move_idx < len(other_columns):
                            move_to_column = other_columns[move_idx].id
                        else:
                            print("Invalid choice! Cards will be moved to the first available column.")
                            move_to_column = other_columns[0].id
                    except (ValueError, IndexError):
                        print("Invalid choice! Cards will be moved to the first available column.")
                        move_to_column = other_columns[0].id
                else:
                    move_to_column = None
                
                confirm = input(f"⚠️  Delete column '{column.name}'? (y/N): ").strip().lower()
                
                if confirm == 'y':
                    if self.board.delete_column(column.id, move_to_column):
                        print(f"✅ Column '{column.name}' deleted!")
                    else:
                        print("❌ Failed to delete column!")
                else:
                    print("Deletion cancelled.")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def reorder_columns(self):
        """Reorder columns."""
        if not self.ensure_board_writable():
            return

        print("\n--- REORDER COLUMNS ---")
        columns = self.board.get_columns_ordered()
        if len(columns) <= 1:
            print("Need at least 2 columns to reorder!")
            return
        
        print("Current column order:")
        for i, column in enumerate(columns, 1):
            print(f"{i}. {column.name}")
        
        print("\nEnter new order by typing column numbers separated by commas.")
        print(f"Example: 2,1,3 (to move column 2 to first position)")
        
        try:
            order_input = input("New order: ").strip()
            order_indices = [int(x.strip()) - 1 for x in order_input.split(',')]
            
            if len(order_indices) != len(columns) or not all(0 <= i < len(columns) for i in order_indices):
                print("Invalid order! Must include all columns exactly once.")
                return
            
            if len(set(order_indices)) != len(order_indices):
                print("Invalid order! Each column can only appear once.")
                return
            
            new_order = [columns[i].id for i in order_indices]
            
            if self.board.reorder_columns(new_order):
                print("✅ Columns reordered successfully!")
            else:
                print("❌ Failed to reorder columns!")
                
        except (ValueError, IndexError):
            print("Invalid input! Use numbers separated by commas.")
    
    def change_column_color(self):
        """Change column color."""
        if not self.ensure_board_writable():
            return

        print("\n--- CHANGE COLUMN COLOR ---")
        columns = self.board.get_columns_ordered()
        if not columns:
            print("No columns available!")
            return
        
        print("Available columns:")
        for i, column in enumerate(columns, 1):
            print(f"{i}. {column.name} (Current: {column.color})")
        
        try:
            choice = int(input(f"Select column (1-{len(columns)}): "))
            if 1 <= choice <= len(columns):
                column = columns[choice - 1]
                
                colors = {
                    "1": "#FF9800",  # Orange
                    "2": "#2196F3",  # Blue
                    "3": "#4CAF50",  # Green
                    "4": "#F44336",  # Red
                    "5": "#9C27B0",  # Purple
                    "6": "#FF5722",  # Deep Orange
                    "7": "#607D8B",  # Blue Grey
                    "8": "#795548",  # Brown
                }
                
                print("\nAvailable colors:")
                print("1. Orange   2. Blue     3. Green    4. Red")
                print("5. Purple   6. D.Orange 7. B.Grey   8. Brown")
                
                color_choice = input(f"Choose color for '{column.name}' (1-8): ").strip()
                
                if color_choice in colors:
                    new_color = colors[color_choice]
                    if self.board.change_column_color(column.id, new_color):
                        print(f"✅ Color changed for '{column.name}'!")
                    else:
                        print("❌ Failed to change color!")
                else:
                    print("Invalid color choice!")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def view_columns(self):
        """View all columns and their details."""
        print("\n--- COLUMN OVERVIEW ---")
        columns = self.board.get_columns_ordered()
        if not columns:
            print("No columns available!")
            return
        
        print(f"Total columns: {len(columns)}")
        print()
        
        for i, column in enumerate(columns):
            print(f"{i + 1}. {column.name}")
            print(f"   Color: {column.color}")
            print(f"   Position: {column.position}")
            print(f"   Cards: {len(column)} cards")
            print(f"   Created: {column.created_at.strftime('%Y-%m-%d %H:%M')}")
            if column.cards:
                print("   Sample cards:")
                for j, card in enumerate(column.cards[:3], 1):
                    print(f"     {j}. {card}")
                if len(column.cards) > 3:
                    print(f"     ... and {len(column.cards) - 3} more")
            print()