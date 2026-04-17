## @file
#  @brief Interactive command-line interface for operating one board inside the multi-board CLI.
"""!Board-level command-line interface for the Kanban board application."""

from datetime import date
from typing import Dict, List, Optional

from .board import KanbanBoard
from .board_manager import BoardManager
from .models import Priority

EMPTY_NOTE_LABEL = '(empty note)'


## @brief Provide menu-driven access to a selected board from the multi-board CLI.
class BoardCLI:
    """!Command line interface for an individual board."""
    
    def __init__(self, board: KanbanBoard, board_manager: Optional[BoardManager] = None):
        """!Init."""
        self.board = board
        self.board_manager = board_manager
        self.running = True

    def parse_optional_date(self, value: str, field_name: str) -> Optional[date]:
        """!Parse an optional ISO date string entered by the user."""
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from error

    def parse_todo_items(self, value: str) -> List[Dict[str, object]]:
        """!Parse a pipe-delimited checklist string into structured items."""
        items: List[Dict[str, object]] = []
        for raw_item in value.split('|'):
            text = raw_item.strip()
            if not text:
                continue
            completed = False
            lowered = text.lower()
            if lowered.startswith('[x]'):
                completed = True
                text = text[3:].strip()
            elif lowered.startswith('[ ]'):
                text = text[3:].strip()
            if text:
                items.append({'text': text, 'completed': completed})
        return items

    def note_preview(self, text: str, limit: int = 80) -> str:
        """!Return a compact single-line note preview for CLI listings."""
        preview = ' '.join((text or '').split()) or EMPTY_NOTE_LABEL
        if len(preview) <= limit:
            return preview
        return preview[: limit - 3] + '...'
    
    def run(self):
        """!Main CLI loop."""
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
        """!Show welcome message."""
        print("=" * 50)
        print("🗂️  WELCOME TO KANBAN BOARD MANAGER  🗂️")
        print("=" * 50)
        print("Organize your tasks efficiently!")
        actor_name = self.board.get_actor_name() or '(not set yet)'
        print(f"Action log user: {actor_name}")
        if self.board.is_read_only():
            print("🔒 This board is open in read-only mode.")
        print()

    def ensure_actor_name(self) -> bool:
        """!Prompt for and save the actor name when needed."""
        if self.board.get_actor_name():
            return True
        if self.board_manager is None:
            self.board.set_actor_name('Unknown User')
            return True

        while True:
            actor_name = input('Enter your name for the action log: ').strip()
            if actor_name:
                self.board_manager.set_actor_name(actor_name, persist=True)
                return True
            print('A user name is required to log board actions.')

    def ensure_board_writable(self) -> bool:
        """!Return False and explain why if the current board is read-only."""
        if not self.board.is_read_only():
            return self.ensure_actor_name()

        print(f"\n🔒 {self.board.get_read_only_message()}")
        return False
    
    def show_board(self):
        """!Display the current board state."""
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
        """!Display the main menu."""
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
        print("10. Manage card notes")
        print("11. Archive done cards")
        print("12. Manage archived cards")
        print("13. Add subcard")
        
        print("\nCOLUMN ACTIONS:")
        print("14. Create new column")
        print("15. Rename column")
        print("16. Delete column")
        print("17. Reorder columns")
        print("18. Change column color")
        print("19. Edit column flags")
        print("20. View columns")

        print("\nCARD TYPE ACTIONS:")
        print("21. View card types")
        print("22. Create card type")
        print("23. Edit card type")
        print("24. Delete card type")
        
        print("\nOTHER:")
        print("25. Create backup")
        print("26. Clean up orphaned attachment files")
        print("27. Undo last change")
        print("28. Redo last undone change")
        print("29. View action log")
        print("30. View card action log")
        print("0. Exit")
        print()
    
    def handle_choice(self, choice: str):
        """!Handle user's menu choice."""
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
            '10': self.manage_card_notes,
            '11': self.archive_done_cards,
            '12': self.manage_archived_cards,
            '13': self.add_subcard,
            '14': self.create_column,
            '15': self.rename_column,
            '16': self.delete_column,
            '17': self.reorder_columns,
            '18': self.change_column_color,
            '19': self.edit_column_flags,
            '20': self.view_columns,
            '21': self.view_card_types,
            '22': self.create_card_type,
            '23': self.edit_card_type,
            '24': self.delete_card_type,
            '25': self.create_backup,
            '26': self.cleanup_orphaned_attachment_files,
            '27': self.undo_last_change,
            '28': self.redo_last_change,
            '29': self.view_action_log,
            '30': self.view_card_action_log,
            '0': self.exit_app
        }
        
        if choice in handlers and handlers[choice]:
            handlers[choice]()
        else:
            print("Invalid choice. Please try again.")
        
        if choice != '0':
            input("\nPress Enter to continue...")
    
    def create_card(self):
        """!Create a new card."""
        if not self.ensure_board_writable():
            return

        print("\n--- CREATE NEW CARD ---")
        title = input("Card title: ").strip()
        if not title:
            print("Title is required!")
            return
        
        description = input("Description (optional): ").strip()
        card_type = self.select_card_type(default_type_id=self.board.get_last_used_card_type().id)
        if not card_type:
            return

        preset_project = card_type.default_project
        preset_color = card_type.default_color

        project = input(f"Project [{preset_project or 'none'}]: ").strip() or preset_project
        start_date_text = input("Start date (YYYY-MM-DD, optional): ").strip()
        end_date_text = input("End date (YYYY-MM-DD, optional): ").strip()
        color = input(f"Card color [{preset_color or 'default'}]: ").strip() or preset_color
        try:
            start_date = self.parse_optional_date(start_date_text, 'Start date')
            end_date = self.parse_optional_date(end_date_text, 'End date')
        except ValueError as error:
            print(f"❌ {error}")
            return

        if start_date and end_date and end_date < start_date:
            print("❌ End date cannot be earlier than start date.")
            return

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
        checklist_text = input("Checklist items (optional, separate with |, prefix completed items with [x]): ").strip()
        todo_items = self.parse_todo_items(checklist_text)
        
        column_id = None
        columns = self.board.get_columns_ordered()
        if columns:
            default_column_id = self.board.get_default_add_card_column_id()
            default_index = next((index for index, column in enumerate(columns) if column.id == default_column_id), 0)
            print("\nAvailable columns:")
            for i, column in enumerate(columns, 1):
                markers = []
                if getattr(column, 'can_add_card', False):
                    markers.append('add')
                if getattr(column, 'is_completed', False):
                    markers.append('done')
                suffix = f" [{' | '.join(markers)}]" if markers else ""
                print(f"{i}. {column.name}{suffix}")

            try:
                prompt_default = default_index + 1
                col_choice = input(f"Choose column (1-{len(columns)}, default={prompt_default}): ").strip()
                col_choice = int(col_choice) if col_choice else prompt_default
                if 1 <= col_choice <= len(columns):
                    column_id = columns[col_choice - 1].id
            except (ValueError, IndexError):
                column_id = columns[default_index].id
        
        try:
            self.board.create_card(
                title,
                description,
                priority,
                column_id,
                project,
                start_date,
                end_date,
                color=color,
                card_type_id=card_type.id,
                assignee=assignee,
                todo_items=todo_items,
            )
            
            print(f"✅ Card '{title}' created successfully!")
        except ValueError as e:
            print(f"❌ Error creating card: {e}")
    
    def edit_card(self):
        """!Edit an existing card."""
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

        new_card_type = self.select_card_type(default_type_id=card.card_type_id, allow_skip=True)
        if new_card_type is False:
            return

        new_project = input(f"Project [{card.project or 'none'}]: ").strip()
        if new_project == "":
            new_project = None

        start_default = card.start_date.isoformat() if card.start_date else 'none'
        start_input = input(f"Start date [{start_default}] (blank to keep, 'none' to clear): ").strip()
        end_default = card.end_date.isoformat() if card.end_date else 'none'
        end_input = input(f"End date [{end_default}] (blank to keep, 'none' to clear): ").strip()

        new_color = input(f"Color [{card.color or 'default'}]: ").strip()
        if card.todo_items:
            print("Current checklist:")
            for todo_item in card.todo_items:
                tick = '[x]' if todo_item.completed else '[ ]'
                print(f"  {tick} {todo_item.text}")
        checklist_input = input("Checklist items (blank to keep, 'none' to clear, separate with |, prefix completed items with [x]): ").strip()

        edit_kwargs = {}
        if start_input:
            if start_input.lower() == 'none':
                edit_kwargs['start_date'] = None
            else:
                try:
                    edit_kwargs['start_date'] = self.parse_optional_date(start_input, 'Start date')
                except ValueError as error:
                    print(f"❌ {error}")
                    return

        if end_input:
            if end_input.lower() == 'none':
                edit_kwargs['end_date'] = None
            else:
                try:
                    edit_kwargs['end_date'] = self.parse_optional_date(end_input, 'End date')
                except ValueError as error:
                    print(f"❌ {error}")
                    return

        effective_start = edit_kwargs.get('start_date', card.start_date)
        effective_end = edit_kwargs.get('end_date', card.end_date)
        if effective_start and effective_end and effective_end < effective_start:
            print("❌ End date cannot be earlier than start date.")
            return

        if new_color:
            edit_kwargs['color'] = new_color
        if new_card_type is not None:
            edit_kwargs['card_type_id'] = new_card_type.id
        if checklist_input:
            edit_kwargs['todo_items'] = [] if checklist_input.lower() == 'none' else self.parse_todo_items(checklist_input)

        self.board.edit_card(card_id, new_title, new_description, new_priority, new_assignee, new_project, **edit_kwargs)
        print("✅ Card updated successfully!")

    def add_subcard(self):
        """!Create a real child card under an existing top-level card."""
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
        card_type = self.select_card_type(default_type_id=parent_card.card_type_id or self.board.get_last_used_card_type().id)
        if not card_type:
            return

        project_default = parent_card.project if parent_card.project is not None else card_type.default_project
        color_default = parent_card.color if parent_card.color is not None else card_type.default_color
        project = input(f"Project [{project_default or 'none'}]: ").strip() or project_default
        start_date_text = input("Start date (YYYY-MM-DD, optional): ").strip()
        end_date_text = input("End date (YYYY-MM-DD, optional): ").strip()
        color = input(f"Card color [{color_default or 'default'}]: ").strip() or color_default

        try:
            start_date = self.parse_optional_date(start_date_text, 'Start date')
            end_date = self.parse_optional_date(end_date_text, 'End date')
        except ValueError as error:
            print(f"❌ {error}")
            return

        if start_date and end_date and end_date < start_date:
            print("❌ End date cannot be earlier than start date.")
            return

        print("\nPriority levels:")
        for i, priority in enumerate(Priority, 1):
            print(f"{i}. {priority.value}")

        try:
            priority_choice = int(input("Choose priority (1-4, default=2): ") or "2")
            priorities = list(Priority)
            priority = priorities[priority_choice - 1] if 1 <= priority_choice <= 4 else Priority.MEDIUM
        except (ValueError, IndexError):
            priority = Priority.MEDIUM

        checklist_text = input("Checklist items (optional, separate with |, prefix completed items with [x]): ").strip()
        todo_items = self.parse_todo_items(checklist_text)

        assignee = input("Assignee (optional): ").strip() or None
        tags_text = input("Tags (comma-separated, optional): ").strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []

        try:
            self.board.create_subcard(
                parent_id,
                title,
                description,
                priority,
                project,
                color,
                card_type.id,
                start_date,
                end_date,
                assignee,
                tags,
                todo_items,
            )
            print(f"✅ Subcard '{title}' created successfully!")
        except ValueError as error:
            print(f"❌ Error creating subcard: {error}")
    
    def move_card(self):
        """!Move a card to a different column."""
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
        
        ordered_columns = self.board.get_columns_ordered()
        current_column = next((column for column in ordered_columns if column.id == card.column_id), None)

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
    
    def delete_card(self):
        """!Delete a card."""
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
        """!Search for cards."""
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
            print(f"{i}. [{self.board.get_card_location_label(card)}] {card}")
    
    def filter_by_priority(self):
        """!Filter cards by priority."""
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
                    print(f"{i}. [{self.board.get_card_location_label(card)}] {card}")
            else:
                print("Invalid choice!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def filter_by_assignee(self):
        """!Filter cards by assignee."""
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
            print(f"{i}. [{self.board.get_card_location_label(card)}] {card}")
    
    def add_tag_to_card(self):
        """!Add a tag to a card."""
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
            if self.board.add_card_tag(card.id, tag):
                print(f"✅ Tag '{tag}' added to card!")
            else:
                print("Tag already exists or could not be added.")
        else:
            print("Tag name cannot be empty!")

    def undo_last_change(self):
        """!Undo the most recent board change."""
        if not self.ensure_board_writable():
            return

        description = self.board.undo_last_action()
        if not description:
            print("No board action is available to undo.")
            return

        print(f"↩ Undid: {description}")

    def redo_last_change(self):
        """!Redo the most recently undone board change."""
        if not self.ensure_board_writable():
            return

        description = self.board.redo_last_action()
        if not description:
            print("No board action is available to redo.")
            return

        print(f"↪ Redid: {description}")

    def view_action_log(self):
        """!Print the board action log on request."""
        print("\n--- ACTION LOG ---")
        print(self.board.export_action_log())

    def view_card_action_log(self):
        """!Print the audit log for one selected card."""
        print("\n--- CARD ACTION LOG ---")
        card_id = self.select_card()
        if not card_id:
            return

        card = self.board.find_card(card_id)
        if not card:
            print("Card not found!")
            return

        print(self.board.export_card_action_log(card.id, card_title=card.title))
    
    def show_card_details(self):
        """!Show detailed information about a card."""
        print("\n--- CARD DETAILS ---")
        card_id = self.select_card()
        if not card_id:
            return
        
        card = self.board.find_card(card_id)
        if not card:
            print("Card not found!")
            return
        
        print("\n📋 Card Details:")
        print(f"ID: {card.id}")
        print(f"Title: {card.title}")
        print(f"Description: {card.description or '(no description)'}")
        print(f"Column: {self.board.get_card_location_label(card)}")
        print(f"Priority: {card.priority.value}")
        card_type = self.board.get_card_type(card.card_type_id)
        print(f"Type: {card_type.name if card_type else self.board.get_default_card_type().name}")
        print(f"Project: {card.project or '(none)'}")
        print(f"Assignee: {card.assignee or '(unassigned)'}")
        print(f"Start Date: {card.start_date.isoformat() if card.start_date else '(none)'}")
        print(f"End Date: {card.end_date.isoformat() if card.end_date else '(none)'}")
        print(f"Late: {'yes' if card.has_past_end_date() and not self.board.is_card_done(card) else 'no'}")
        print(f"Color: {card.color or '(default)'}")
        print(f"Tags: {', '.join(card.tags) if card.tags else '(no tags)'}")
        todo_completed, todo_total = card.get_todo_progress()
        if todo_total:
            print(f"Checklist: {todo_completed}/{todo_total} done")
            for todo_item in card.todo_items:
                tick = '[x]' if todo_item.completed else '[ ]'
                print(f"  {tick} {todo_item.text}")
        else:
            print("Checklist: (none)")
        if card.notes:
            print(f"Notes: {len(card.notes)}")
            for note in sorted(card.notes, key=lambda item: item.created_at, reverse=True):
                created_label = note.created_at.strftime('%Y-%m-%d %H:%M:%S')
                print(f"  - {created_label}: {self.note_preview(note.text)}")
        else:
            print("Notes: (none)")

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

    def manage_card_notes(self):
        """!View, add, edit, and delete notes recorded on a card."""
        print("\n--- MANAGE CARD NOTES ---")
        card_id = self.select_card()
        if not card_id:
            return

        while True:
            card = self.board.find_card(card_id)
            if card is None:
                print("Card not found!")
                return

            print(f"\nNotes for: {card.title}")
            if card.notes:
                for index, note in enumerate(sorted(card.notes, key=lambda item: item.created_at, reverse=True), 1):
                    created_label = note.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{index}. {created_label} | {self.note_preview(note.text)}")
            else:
                print("No notes added yet.")

            print("\nActions:")
            print("1. View note")
            print("2. Add note")
            print("3. Edit note")
            print("4. Delete note")
            print("0. Back")

            action = input("Choose action: ").strip()
            if action == '0':
                return

            if action == '1':
                note = self.select_note(card)
                if note is not None:
                    self._print_note(note)
                continue

            if action == '2':
                if not self.ensure_board_writable():
                    continue
                note_text = self.prompt_note_text('Enter note text. Finish with a blank line:')
                if not note_text:
                    print('Note creation cancelled.')
                    continue
                note = self.board.add_card_note(card.id, note_text)
                if note is None:
                    print('❌ Failed to add note!')
                else:
                    print('✅ Note added successfully!')
                continue

            if action == '3':
                if not self.ensure_board_writable():
                    continue
                note = self.select_note(card)
                if note is None:
                    continue
                note_text = self.prompt_note_text('Enter replacement note text. Finish with a blank line:', existing_text=note.text)
                if not note_text:
                    print('Note update cancelled.')
                    continue
                updated = self.board.edit_card_note(card.id, note.id, note_text)
                if updated is None:
                    print('❌ Failed to update note!')
                else:
                    print('✅ Note updated successfully!')
                continue

            if action == '4':
                if not self.ensure_board_writable():
                    continue
                note = self.select_note(card)
                if note is None:
                    continue
                confirm = input('Delete this note? (y/N): ').strip().lower()
                if confirm != 'y':
                    print('Deletion cancelled.')
                    continue
                if self.board.delete_card_note(card.id, note.id):
                    print('✅ Note deleted successfully!')
                else:
                    print('❌ Failed to delete note!')
                continue

            print('Invalid choice. Please try again.')

    def prompt_note_text(self, prompt: str, existing_text: Optional[str] = None) -> Optional[str]:
        """!Prompt for note text, allowing multi-line input until a blank line is entered."""
        print(prompt)
        if existing_text is not None:
            print('Current note text:')
            for line in (existing_text.splitlines() or [EMPTY_NOTE_LABEL]):
                print(f'  {line}')
        print('(Press Enter on a blank line to finish.)')
        lines: List[str] = []
        while True:
            line = input()
            if line == '':
                break
            lines.append(line)
        note_text = '\n'.join(lines).strip()
        return note_text or None

    def select_note(self, card) -> Optional[object]:
        """!Prompt the user to select a note from a card."""
        ordered_notes = sorted(card.notes, key=lambda item: item.created_at, reverse=True)
        if not ordered_notes:
            print('No notes available!')
            return None

        print('\nAvailable notes:')
        for index, note in enumerate(ordered_notes, 1):
            created_label = note.created_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{index}. {created_label} | {self.note_preview(note.text)}")

        try:
            choice = int(input(f"Select note (1-{len(ordered_notes)}): "))
            if 1 <= choice <= len(ordered_notes):
                return ordered_notes[choice - 1]
        except ValueError:
            pass

        print('Invalid note selection!')
        return None

    def _print_note(self, note):
        """!Print one note with full text."""
        print(f"\n📝 Note {note.id}")
        print(f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print('Text:')
        for line in (note.text.splitlines() or [EMPTY_NOTE_LABEL]):
            print(f'  {line}')
    
    def archive_done_cards(self):
        """!Archive all active cards from completed columns."""
        if not self.ensure_board_writable():
            return

        print("\n--- ARCHIVE DONE CARDS ---")
        stats = self.board.get_board_stats()
        done_count = stats['done']
        
        if done_count == 0:
            print("No active cards in completed columns to archive.")
            return
        
        print(f"This will archive {done_count} card(s) from completed columns.")
        confirm = input("Are you sure? (y/N): ").strip().lower()
        
        if confirm == 'y':
            archived = self.board.archive_done_cards()
            print(f"✅ Archived {archived} card(s) from completed columns!")
        else:
            print("Operation cancelled.")

    def manage_archived_cards(self):
        """!List, restore, and permanently delete archived cards."""
        if not self.ensure_board_writable():
            return

        while True:
            archived_cards = self.board.get_archived_cards()
            print("\n--- MANAGE ARCHIVED CARDS ---")
            if not archived_cards:
                print("No archived cards found.")
                return

            for index, card in enumerate(archived_cards, 1):
                archived_label = card.archived_at.strftime('%Y-%m-%d %H:%M') if card.archived_at else 'unknown'
                print(f"{index}. [{self.board.get_card_location_label(card)}] {card.title} (archived {archived_label})")

            print("\nActions:")
            print("1. View archived card details")
            print("2. Restore archived card")
            print("3. Delete archived card permanently")
            print("0. Back")

            action = input("Choose action: ").strip()
            if action == '0':
                return

            card_id = self.select_card(archived_only=True)
            if not card_id:
                continue

            card = self.board.find_card(card_id, include_archived=True)
            if card is None or not card.is_archived():
                print("Archived card not found!")
                continue

            if action == '1':
                self._print_archived_card_details(card)
            elif action == '2':
                if self.board.restore_archived_card(card.id):
                    print(f"✅ Restored '{card.title}'.")
                else:
                    print("❌ Failed to restore archived card!")
            elif action == '3':
                confirm = input(f"Permanently delete archived card '{card.title}'? (y/N): ").strip().lower()
                if confirm == 'y':
                    if self.board.delete_card(card.id):
                        print(f"✅ Deleted archived card '{card.title}'.")
                    else:
                        print("❌ Failed to delete archived card!")
                else:
                    print("Deletion cancelled.")
            else:
                print("Invalid choice. Please try again.")

    def _print_archived_card_details(self, card):
        """!Print details for an archived card."""
        print("\n🗄️ Archived Card Details:")
        print(f"ID: {card.id}")
        print(f"Title: {card.title}")
        print(f"Column: {self.board.get_card_location_label(card)}")
        print(f"Archived: {card.archived_at.strftime('%Y-%m-%d %H:%M:%S') if card.archived_at else 'unknown'}")
        print(f"Description: {card.description or '(no description)'}")
        print(f"Priority: {card.priority.value}")
        print(f"Assignee: {card.assignee or '(unassigned)'}")
        print(f"Project: {card.project or '(none)'}")
        print(f"Tags: {', '.join(card.tags) if card.tags else '(no tags)'}")
        todo_completed, todo_total = card.get_todo_progress()
        if todo_total:
            print(f"Checklist: {todo_completed}/{todo_total} done")
            for todo_item in card.todo_items:
                tick = '[x]' if todo_item.completed else '[ ]'
                print(f"  {tick} {todo_item.text}")
        else:
            print("Checklist: (none)")
    
    def create_backup(self):
        """!Create a backup of the board data."""
        print("\n--- CREATE BACKUP ---")
        backup_path = self.board.storage.backup()
        if backup_path:
            print(f"✅ Backup created: {backup_path}")
        else:
            print("❌ Failed to create backup!")

    def cleanup_orphaned_attachment_files(self):
        """!Delete copied attachment files that are no longer referenced by the board or history."""
        if not self.ensure_board_writable():
            return

        print("\n--- CLEAN UP ORPHANED ATTACHMENTS ---")
        result = self.board.cleanup_orphaned_attachment_files()
        removed_files = result['removed_files']
        removed_directories = result['removed_directories']

        if removed_files == 0:
            print("No orphaned attachment files were found.")
            if removed_directories:
                print(f"Removed {removed_directories} empty attachment director{'y' if removed_directories == 1 else 'ies'}.")
            return

        print(
            f"✅ Removed {removed_files} orphaned attachment file(s) "
            f"and {removed_directories} empty director{'y' if removed_directories == 1 else 'ies'}."
        )

    def view_card_types(self):
        """!Display all configured card types."""
        print("\n--- CARD TYPES ---")
        default_type_id = self.board.get_default_card_type_id()
        last_used_id = self.board.get_last_used_card_type().id
        for index, card_type in enumerate(self.board.get_card_types_ordered(), start=1):
            flags = []
            if card_type.id == default_type_id:
                flags.append('default')
            if card_type.id == last_used_id:
                flags.append('last used')
            suffix = f" [{' | '.join(flags)}]" if flags else ""
            print(f"{index}. {card_type.name}{suffix}")
            if card_type.description:
                print(f"   Description: {card_type.description}")
            print(f"   Project preset: {card_type.default_project or '(none)'}")
            print(f"   Color preset: {card_type.default_color or '(default)'}")

    def create_card_type(self):
        """!Create a new card type."""
        if not self.ensure_board_writable():
            return

        print("\n--- CREATE CARD TYPE ---")
        name = input("Name: ").strip()
        if not name:
            print("Name is required!")
            return

        description = input("Description (optional): ").strip()
        default_project = input("Project preset (optional): ").strip() or None
        default_color = input("Color preset (optional): ").strip() or None

        try:
            self.board.create_card_type(name, description, default_project, default_color)
            print(f"✅ Card type '{name}' created successfully!")
        except ValueError as error:
            print(f"❌ {error}")

    def edit_card_type(self):
        """!Edit an existing card type."""
        if not self.ensure_board_writable():
            return

        print("\n--- EDIT CARD TYPE ---")
        card_type = self.select_card_type()
        if not card_type:
            return

        print("(Leave blank to keep current value)")
        new_name = input(f"Name [{card_type.name}]: ").strip() or None
        new_description = input(f"Description [{card_type.description or 'none'}]: ").strip()
        if new_description == '':
            new_description = None

        new_project = input(f"Project preset [{card_type.default_project or 'none'}]: ").strip()
        new_color = input(f"Color preset [{card_type.default_color or 'default'}]: ").strip()

        edit_kwargs = {}
        if new_project:
            edit_kwargs['default_project'] = new_project
        if new_color:
            edit_kwargs['default_color'] = new_color

        try:
            self.board.edit_card_type(card_type.id, new_name, new_description, **edit_kwargs)
            print(f"✅ Card type '{card_type.name}' updated successfully!")
        except ValueError as error:
            print(f"❌ {error}")

    def delete_card_type(self):
        """!Delete a card type and either delete or reassign its cards."""
        if not self.ensure_board_writable():
            return

        print("\n--- DELETE CARD TYPE ---")
        card_type = self.select_card_type(exclude_default=True)
        if not card_type:
            return

        cards_using_type = self.board.get_cards_by_type(card_type.id)
        print(f"Card type '{card_type.name}' is used by {len(cards_using_type)} card(s).")
        print("1. Delete all cards of this type")
        print("2. Change those cards to another type")
        choice = input("Choose action (1-2): ").strip()

        try:
            if choice == '1':
                self.board.delete_card_type(card_type.id, delete_cards=True)
                print(f"✅ Deleted card type '{card_type.name}' and its cards.")
                return
            if choice == '2':
                replacement = self.select_card_type(exclude_ids={card_type.id})
                if not replacement:
                    return
                self.board.delete_card_type(card_type.id, delete_cards=False, replacement_type_id=replacement.id)
                print(f"✅ Deleted card type '{card_type.name}' and reassigned cards to '{replacement.name}'.")
                return
            print("Invalid choice!")
        except ValueError as error:
            print(f"❌ {error}")

    def select_card_type(self, default_type_id: str = None, allow_skip: bool = False,
                         exclude_default: bool = False, exclude_ids=None):
        """!Select a card type from the board."""
        exclude_ids = set(exclude_ids or [])
        card_types = []
        for card_type in self.board.get_card_types_ordered():
            if exclude_default and card_type.id == self.board.get_default_card_type_id():
                continue
            if card_type.id in exclude_ids:
                continue
            card_types.append(card_type)

        if not card_types:
            print("No card types available!")
            return None

        print("\nAvailable card types:")
        default_index = 0
        for index, card_type in enumerate(card_types, start=1):
            flags = []
            if card_type.id == self.board.get_default_card_type_id():
                flags.append('default')
            if card_type.id == self.board.get_last_used_card_type().id:
                flags.append('last used')
            if card_type.id == default_type_id:
                default_index = index - 1
                flags.append('selected')
            suffix = f" [{' | '.join(flags)}]" if flags else ''
            print(f"{index}. {card_type.name}{suffix}")
            if card_type.description:
                print(f"   {card_type.description}")

        prompt = f"Choose card type (1-{len(card_types)}"
        if allow_skip:
            prompt += ", blank to keep current"
        else:
            prompt += f", default={default_index + 1}"
        prompt += "): "

        choice = input(prompt).strip()
        if not choice:
            if allow_skip:
                return None
            return card_types[default_index]

        try:
            index = int(choice) - 1
            if 0 <= index < len(card_types):
                return card_types[index]
        except ValueError:
            pass

        print("Invalid selection!")
        return False
    
    def select_card(self, top_level_only: bool = False, archived_only: bool = False) -> Optional[str]:
        """!Helper method to select a card from the board."""
        # Show all cards with indices
        all_cards = []
        
        for column in self.board.get_columns_ordered():
            for card in self.board.get_column_cards(column, include_archived=archived_only):
                if archived_only and not card.is_archived():
                    continue
                if top_level_only and card.parent_id:
                    continue
                all_cards.append((card, column.name))
        
        if not all_cards:
            print("No cards available!")
            return None
        
        print("\nAvailable cards:")
        for i, (card, column_name) in enumerate(all_cards, 1):
            parent_info = " <subcard>" if card.parent_id else ""
            archive_info = " <archived>" if card.is_archived() else ""
            print(f"{i}. [{column_name}] {card.title}{parent_info}{archive_info}")
        
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
        """!Exit the application."""
        print("\nSaving your work...")
        if not self.board.is_read_only():
            self.board.save_board()
        self.board.close()
        print("👋 Goodbye! Thanks for using Kanban Board Manager!")
        self.running = False
    
    # Column Management Methods
    def create_column(self):
        """!Create a new column."""
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

        is_completed = input("Treat this as a completed column? (y/N): ").strip().lower() == 'y'
        can_add_card = input("Show an Add Card action for this column? (y/N): ").strip().lower() == 'y'
        
        try:
            position = input("Position (leave blank for last): ").strip()
            position = int(position) if position else None
        except ValueError:
            position = None
        
        self.board.create_column(name, position, color, is_completed, can_add_card)
        print(f"✅ Column '{name}' created successfully!")
    
    def rename_column(self):
        """!Rename an existing column."""
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
        """!Delete a column."""
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
        """!Reorder columns."""
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
        print("Example: 2,1,3 (to move column 2 to first position)")
        
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
        """!Change column color."""
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

    def edit_column_flags(self):
        """!Edit the completed/add-card flags for an existing column."""
        if not self.ensure_board_writable():
            return

        print("\n--- EDIT COLUMN FLAGS ---")
        columns = self.board.get_columns_ordered()
        if not columns:
            print("No columns available!")
            return

        print("Available columns:")
        for i, column in enumerate(columns, 1):
            completed = 'yes' if getattr(column, 'is_completed', False) else 'no'
            add_card = 'yes' if getattr(column, 'can_add_card', False) else 'no'
            print(f"{i}. {column.name} (completed: {completed}, add card: {add_card})")

        try:
            choice = int(input(f"Select column (1-{len(columns)}): "))
            if not 1 <= choice <= len(columns):
                print("Invalid selection!")
                return

            column = columns[choice - 1]
            current_completed = getattr(column, 'is_completed', False)
            current_add_card = getattr(column, 'can_add_card', False)

            completed_text = input(
                f"Treat '{column.name}' as completed? (y/n, Enter keeps {'yes' if current_completed else 'no'}): "
            ).strip().lower()
            add_card_text = input(
                f"Show Add Card action for '{column.name}'? (y/n, Enter keeps {'yes' if current_add_card else 'no'}): "
            ).strip().lower()

            is_completed = current_completed if completed_text == '' else completed_text == 'y'
            can_add_card = current_add_card if add_card_text == '' else add_card_text == 'y'

            if self.board.update_column(
                column.id,
                is_completed=is_completed,
                can_add_card=can_add_card,
            ):
                print(f"✅ Updated flags for '{column.name}'!")
            else:
                print("❌ Failed to update column flags!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def view_columns(self):
        """!View all columns and their details."""
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
            print(f"   Completed column: {'yes' if getattr(column, 'is_completed', False) else 'no'}")
            print(f"   Add-card column: {'yes' if getattr(column, 'can_add_card', False) else 'no'}")
            active_cards = self.board.get_column_cards(column)
            archived_cards = [card for card in self.board.get_column_cards(column, include_archived=True) if card.is_archived()]
            print(f"   Cards: {len(active_cards)} active")
            if archived_cards:
                print(f"   Archived: {len(archived_cards)}")
            print(f"   Created: {column.created_at.strftime('%Y-%m-%d %H:%M')}")
            if active_cards:
                print("   Sample cards:")
                for j, card in enumerate(active_cards[:3], 1):
                    print(f"     {j}. {card}")
                if len(active_cards) > 3:
                    print(f"     ... and {len(active_cards) - 3} more")
            print()