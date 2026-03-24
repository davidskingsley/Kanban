## @file
#  @brief Board domain logic for cards, columns, persistence, and read-only guards.
"""Main Kanban board implementation with custom column support."""

from datetime import date
from typing import List, Optional, Dict, Union
from .models import Card, Column, CustomColumn, Status, Priority, CardType, UNSET
from .storage import DataStorage, get_default_single_board_file
import os
import uuid


## @brief Encapsulates the state and operations of a single Kanban board.
class KanbanBoard:
    """Main Kanban board class for managing cards and columns."""
    DEFAULT_CARD_TYPE_NAME = 'Default'
    
    def __init__(self, data_file: str = None, use_custom_columns: bool = True):
        if data_file is None:
            data_file = get_default_single_board_file()
        
        self.storage = DataStorage(data_file)
        self.use_custom_columns = use_custom_columns
        self.card_types: Dict[str, CardType] = {}
        self.last_used_card_type_id = None
        
        # Initialize columns based on mode
        if use_custom_columns:
            self.custom_columns: Dict[str, CustomColumn] = {}
            self.columns = None  # Legacy columns not used
        else:
            # Legacy mode
            self.columns: Dict[Status, Column] = {
                Status.TODO: Column(Status.TODO),
                Status.IN_PROGRESS: Column(Status.IN_PROGRESS),
                Status.REVIEW: Column(Status.REVIEW),
                Status.DONE: Column(Status.DONE)
            }
            self.custom_columns = None
        
        # Load existing data
        self.load_board()

    def is_read_only(self) -> bool:
        """Return whether the board is opened read-only."""
        return self.storage.is_read_only()

    def get_read_only_message(self) -> str:
        """Return a user-facing explanation for read-only access."""
        return self.storage.get_read_only_message()

    def close(self):
        """Release any resources associated with the board."""
        self.storage.release_lock()

    def _ensure_writable(self):
        """Raise if the board is currently read-only."""
        if self.is_read_only():
            raise PermissionError(self.get_read_only_message())
    
    # Column Management Methods
    def create_column(self, name: str, position: int = None, color: str = "#2196F3") -> str:
        """Create a new custom column."""
        self._ensure_writable()

        if not self.use_custom_columns:
            raise ValueError("Custom columns not enabled for this board")
        
        if position is None:
            position = len(self.custom_columns)
        
        column_id = str(uuid.uuid4())
        column = CustomColumn(column_id, name, position, color)
        self.custom_columns[column_id] = column
        
        # Adjust positions of other columns if needed
        self._adjust_column_positions()
        
        self.save_board()
        return column_id
    
    def rename_column(self, column_id: str, new_name: str) -> bool:
        """Rename a custom column."""
        self._ensure_writable()

        if not self.use_custom_columns or column_id not in self.custom_columns:
            return False
        
        self.custom_columns[column_id].rename(new_name)
        self.save_board()
        return True
    
    def delete_column(self, column_id: str, move_cards_to: str = None) -> bool:
        """Delete a custom column."""
        self._ensure_writable()

        if not self.use_custom_columns or column_id not in self.custom_columns:
            return False
        
        if len(self.custom_columns) <= 1:
            return False  # Cannot delete the last column
        
        column = self.custom_columns[column_id]
        
        # Move cards to another column if specified
        if move_cards_to and move_cards_to in self.custom_columns:
            target_column = self.custom_columns[move_cards_to]
            for card in column.cards:
                card.move_to_column(move_cards_to)
                target_column.add_card(card)
        elif column.cards:
            # Move cards to the first available column
            first_column_id = next(iter(self.custom_columns.keys()))
            if first_column_id != column_id:
                target_column = self.custom_columns[first_column_id]
                for card in column.cards:
                    card.move_to_column(first_column_id)
                    target_column.add_card(card)
        
        # Remove the column
        del self.custom_columns[column_id]
        
        # Adjust positions
        self._adjust_column_positions()
        
        self.save_board()
        return True
    
    def reorder_columns(self, column_order: List[str]) -> bool:
        """Reorder columns by providing a list of column IDs in the desired order."""
        self._ensure_writable()

        if not self.use_custom_columns:
            return False
        
        # Validate that all column IDs exist
        if set(column_order) != set(self.custom_columns.keys()):
            return False
        
        # Update positions
        for index, column_id in enumerate(column_order):
            self.custom_columns[column_id].reposition(index)
        
        self.save_board()
        return True
    
    def change_column_color(self, column_id: str, color: str) -> bool:
        """Change the color of a custom column."""
        self._ensure_writable()

        if not self.use_custom_columns or column_id not in self.custom_columns:
            return False
        
        self.custom_columns[column_id].change_color(color)
        self.save_board()
        return True
    
    def get_columns_ordered(self) -> List[Union[CustomColumn, Column]]:
        """Get columns in order (by position for custom columns, fixed order for legacy)."""
        if self.use_custom_columns:
            return sorted(self.custom_columns.values(), key=lambda col: col.position)
        else:
            return [self.columns[status] for status in Status]
    
    def get_column_by_id(self, column_id: str) -> Optional[CustomColumn]:
        """Get a custom column by ID."""
        if not self.use_custom_columns:
            return None
        return self.custom_columns.get(column_id)
    
    def _adjust_column_positions(self):
        """Ensure column positions are sequential starting from 0."""
        if not self.use_custom_columns:
            return
        
        ordered_columns = sorted(self.custom_columns.values(), key=lambda col: col.position)
        for index, column in enumerate(ordered_columns):
            column.position = index
    
    def _get_first_column_id(self) -> Optional[str]:
        """Get the ID of the first column."""
        if self.use_custom_columns:
            if not self.custom_columns:
                return None
            return min(self.custom_columns.keys(), key=lambda cid: self.custom_columns[cid].position)
        else:
            return None  # Legacy mode uses Status enum

    def _ensure_default_card_type(self):
        """Ensure the board always has a non-deletable default card type."""
        default_type = next((card_type for card_type in self.card_types.values()
                             if card_type.name == self.DEFAULT_CARD_TYPE_NAME), None)
        if default_type is None:
            default_type = CardType(self.DEFAULT_CARD_TYPE_NAME, "Standard card type")
            self.card_types[default_type.id] = default_type
        return default_type

    def get_default_card_type(self) -> CardType:
        """Return the default card type."""
        return self._ensure_default_card_type()

    def get_default_card_type_id(self) -> str:
        """Return the ID of the default card type."""
        return self.get_default_card_type().id

    def get_card_type(self, card_type_id: str) -> Optional[CardType]:
        """Return a card type by ID."""
        return self.card_types.get(card_type_id)

    def get_card_types_ordered(self) -> List[CardType]:
        """Return card types with the default type first and the rest by name."""
        default_type = self.get_default_card_type()
        other_types = [card_type for card_type in self.card_types.values() if card_type.id != default_type.id]
        other_types.sort(key=lambda card_type: card_type.name.lower())
        return [default_type] + other_types

    def get_last_used_card_type(self) -> CardType:
        """Return the last used card type, or the default type if unavailable."""
        card_type = self.get_card_type(self.last_used_card_type_id)
        if card_type is None:
            card_type = self.get_default_card_type()
            self.last_used_card_type_id = card_type.id
        return card_type

    def _resolve_card_type(self, card_type_id: str = None) -> CardType:
        """Resolve a requested card type, falling back to last-used or default."""
        if card_type_id:
            card_type = self.get_card_type(card_type_id)
            if card_type is None:
                raise ValueError("Card type does not exist")
            return card_type
        return self.get_last_used_card_type()

    def create_card_type(self, name: str, description: str = '', default_project: str = None,
                         default_color: str = None) -> str:
        """Create a new reusable card type."""
        self._ensure_writable()

        name = (name or '').strip()
        if not name:
            raise ValueError("Card type name is required")
        if any(card_type.name.lower() == name.lower() for card_type in self.card_types.values()):
            raise ValueError("A card type with that name already exists")

        card_type = CardType(name, description, default_project, default_color)
        self.card_types[card_type.id] = card_type
        self.last_used_card_type_id = card_type.id
        self.save_board()
        return card_type.id

    def edit_card_type(self, card_type_id: str, name: str = None, description: str = None,
                       default_project=UNSET, default_color=UNSET) -> Optional[CardType]:
        """Edit an existing card type."""
        self._ensure_writable()

        card_type = self.get_card_type(card_type_id)
        if card_type is None:
            return None

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Card type name is required")
            duplicate = next((existing for existing in self.card_types.values()
                              if existing.id != card_type_id and existing.name.lower() == name.lower()), None)
            if duplicate is not None:
                raise ValueError("A card type with that name already exists")
            if card_type_id == self.get_default_card_type_id() and name != self.DEFAULT_CARD_TYPE_NAME:
                raise ValueError("The default card type name cannot be changed")

        card_type.update(name, description, default_project, default_color)
        self.save_board()
        return card_type

    def get_cards_by_type(self, card_type_id: str) -> List[Card]:
        """Return all cards using the given card type."""
        return [card for card in self.get_all_cards() if card.card_type_id == card_type_id]

    def delete_card_type(self, card_type_id: str, delete_cards: bool = False,
                         replacement_type_id: str = None) -> bool:
        """Delete a card type and either remove or reassign its cards."""
        self._ensure_writable()

        card_type = self.get_card_type(card_type_id)
        if card_type is None:
            return False
        if card_type_id == self.get_default_card_type_id():
            raise ValueError("The default card type cannot be deleted")

        cards = self.get_cards_by_type(card_type_id)
        if delete_cards:
            top_level_cards = [card for card in cards if not card.parent_id]
            nested_cards = [card for card in cards if card.parent_id]
            for card in top_level_cards + nested_cards:
                if self.find_card(card.id):
                    self.delete_card(card.id)
        else:
            replacement_type = self._resolve_card_type(replacement_type_id or self.get_default_card_type_id())
            if replacement_type.id == card_type_id:
                raise ValueError("Replacement card type must be different")
            for card in cards:
                card.update(card_type_id=replacement_type.id)

        del self.card_types[card_type_id]
        if self.last_used_card_type_id == card_type_id:
            self.last_used_card_type_id = replacement_type.id if not delete_cards else self.get_default_card_type_id()
        self.save_board()
        return True
    
    # Card Management Methods
    def create_card(self, title: str, description: str = "", priority: Priority = Priority.MEDIUM,
                   column_id: str = None, project: str = None, start_date: date = None,
                   end_date: date = None, parent_id: str = None, color: str = None,
                   card_type_id: str = None) -> Card:
        """Create a new card and add it to the specified column (or first column if none specified)."""
        self._ensure_writable()
        card_type = self._resolve_card_type(card_type_id)
        effective_project = project if project is not None else card_type.default_project
        effective_color = color if color is not None else card_type.default_color

        if self.use_custom_columns:
            if not column_id:
                column_id = self._get_first_column_id()
                if not column_id:
                    raise ValueError("No columns available. Create a column first.")
            
            if column_id not in self.custom_columns:
                raise ValueError(f"Column {column_id} does not exist")
            
            card = Card(title, description, priority, column_id)
            card.project = effective_project
            card.start_date = start_date
            card.end_date = end_date
            if parent_id is not None:
                card.parent_id = parent_id
            card.color = effective_color
            card.card_type_id = card_type.id
            self.custom_columns[column_id].add_card(card)
        else:
            # Legacy mode
            card = Card(title, description, priority)
            card.project = effective_project
            card.start_date = start_date
            card.end_date = end_date
            if parent_id is not None:
                card.parent_id = parent_id
            card.color = effective_color
            card.card_type_id = card_type.id
            self.columns[Status.TODO].add_card(card)

        self.last_used_card_type_id = card_type.id
        self.save_board()
        return card
    
    def edit_card(self, card_id: str, title: str = None, description: str = None, 
                  priority: Priority = None, assignee: str = None, project: str = None,
                  start_date=UNSET, end_date=UNSET, parent_id: str = None, color=UNSET,
                  card_type_id=UNSET) -> Optional[Card]:
        """Edit an existing card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if card:
            resolved_type_id = card_type_id
            if card_type_id is not UNSET:
                resolved_type = self._resolve_card_type(card_type_id)
                resolved_type_id = resolved_type.id
                self.last_used_card_type_id = resolved_type.id
            card.update(title, description, priority, assignee, project, start_date, end_date, parent_id, color, resolved_type_id)
            self.save_board()
            return card
        return None

    def get_all_cards(self) -> List[Card]:
        """Return every card currently on the board."""
        cards = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        for column in columns:
            cards.extend(list(column))
        return cards

    def get_parent_card(self, card: Card) -> Optional[Card]:
        """Return the direct parent card for the given card, if any."""
        if not card.parent_id:
            return None
        return self.find_card(card.parent_id)

    def get_subcards(self, parent_id: str) -> List[Card]:
        """Return the direct child cards of the given parent card."""
        return [card for card in self.get_all_cards() if card.parent_id == parent_id]

    def add_card_note(self, card_id: str, text: str = ""):
        """Add a timestamped note to an existing card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return None

        note = card.add_note(text)
        self.save_board()
        return note

    def delete_card_note(self, card_id: str, note_id: str) -> bool:
        """Delete a note from an existing card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return False

        removed = card.remove_note(note_id)
        if removed:
            self.save_board()
        return removed

    def edit_card_note(self, card_id: str, note_id: str, text: str = ""):
        """Edit an existing note on a card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return None

        note = card.update_note(note_id, text)
        if note is not None:
            self.save_board()
        return note

    def get_subcard_progress(self, parent_id: str) -> tuple[int, int]:
        """Return completed and total counts for a parent card's direct subcards."""
        subcards = self.get_subcards(parent_id)
        completed = sum(1 for card in subcards if self.is_card_done(card))
        return completed, len(subcards)

    def is_card_done(self, card: Card) -> bool:
        """Return whether the given card is currently in the done column."""
        if self.use_custom_columns:
            ordered_columns = self.get_columns_ordered()
            if not ordered_columns:
                return False
            return card.column_id == ordered_columns[-1].id
        return card.status == Status.DONE

    def get_card_location_label(self, card: Card) -> str:
        """Return the display label for the card's current column or status."""
        if self.use_custom_columns:
            column = self.get_column_by_id(card.column_id)
            return column.name if column else 'Unknown'
        return card.status.value if card.status else 'Unknown'

    def create_subcard(self, parent_id: str, title: str, description: str = "",
                       priority: Priority = Priority.MEDIUM, project: str = None,
                       color: str = None, card_type_id: str = None, start_date: date = None,
                       end_date: date = None) -> Card:
        """Create a child card under an existing parent card."""
        parent_card = self.find_card(parent_id)
        if not parent_card:
            raise ValueError("Parent card does not exist")
        if parent_card.parent_id:
            raise ValueError("Nested subcards are not supported")

        target = parent_card.column_id if self.use_custom_columns else parent_card.status
        return self.create_card(
            title,
            description,
            priority,
            target,
            project or parent_card.project,
            start_date,
            end_date,
            parent_id,
            color if color is not None else parent_card.color,
            card_type_id if card_type_id is not None else parent_card.card_type_id,
        )
    
    def delete_card(self, card_id: str) -> bool:
        """Delete a card from the board."""
        self._ensure_writable()

        for subcard in list(self.get_subcards(card_id)):
            self.delete_card(subcard.id)

        if self.use_custom_columns:
            for column in self.custom_columns.values():
                removed_card = column.remove_card(card_id)
                if removed_card:
                    self.save_board()
                    return True
        else:
            for column in self.columns.values():
                removed_card = column.remove_card(card_id)
                if removed_card:
                    self.save_board()
                    return True
        return False
    
    def move_card(self, card_id: str, to_column: Union[str, Status]) -> bool:
        """Move a card to a different column."""
        self._ensure_writable()

        card = None
        
        if self.use_custom_columns:
            # Find and remove the card from its current column
            for column in self.custom_columns.values():
                card = column.remove_card(card_id)
                if card:
                    break
            
            if card and isinstance(to_column, str) and to_column in self.custom_columns:
                card.move_to_column(to_column)
                self.custom_columns[to_column].add_card(card)
                self.save_board()
                return True
        else:
            # Legacy mode
            for column in self.columns.values():
                card = column.remove_card(card_id)
                if card:
                    break
            
            if card and isinstance(to_column, Status):
                card.move_to_status(to_column)
                self.columns[to_column].add_card(card)
                self.save_board()
                return True
        
        return False
    
    def find_card(self, card_id: str) -> Optional[Card]:
        """Find a card by its ID."""
        if self.use_custom_columns:
            for column in self.custom_columns.values():
                card = column.get_card(card_id)
                if card:
                    return card
        else:
            for column in self.columns.values():
                card = column.get_card(card_id)
                if card:
                    return card
        return None
    
    def search_cards(self, query: str) -> List[Card]:
        """Search for cards by title, description, project, tags, and child-card titles."""
        results = []
        query_lower = query.lower()
        
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        
        for column in columns:
            for card in column:
                if (query_lower in card.title.lower() or 
                    query_lower in card.description.lower() or
                    (card.project and query_lower in card.project.lower()) or
                    any(query_lower in subcard.title.lower() for subcard in self.get_subcards(card.id)) or
                    any(query_lower in tag.lower() for tag in card.tags)):
                    results.append(card)
        
        return results
    
    def get_cards_by_priority(self, priority: Priority) -> List[Card]:
        """Get all cards with a specific priority."""
        results = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        
        for column in columns:
            for card in column:
                if card.priority == priority:
                    results.append(card)
        return results
    
    def get_cards_by_assignee(self, assignee: str) -> List[Card]:
        """Get all cards assigned to a specific person."""
        results = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        
        for column in columns:
            for card in column:
                if card.assignee and card.assignee.lower() == assignee.lower():
                    results.append(card)
        return results
    
    def get_board_stats(self) -> Dict:
        """Get statistics about the board."""
        if self.use_custom_columns:
            total_cards = sum(len(column) for column in self.custom_columns.values())
            column_stats = {column.name: len(column) for column in self.custom_columns.values()}
        else:
            total_cards = sum(len(column) for column in self.columns.values())
            column_stats = {
                'todo': len(self.columns[Status.TODO]),
                'in_progress': len(self.columns[Status.IN_PROGRESS]),
                'review': len(self.columns[Status.REVIEW]),
                'done': len(self.columns[Status.DONE])
            }
        
        priority_counts = {priority: 0 for priority in Priority}
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        
        for column in columns:
            for card in column:
                priority_counts[card.priority] += 1
        
        stats = {
            'total_cards': total_cards,
            'priority_counts': priority_counts,
            'use_custom_columns': self.use_custom_columns
        }
        stats.update(column_stats)
        
        return stats
    
    def clear_done_cards(self) -> int:
        """Remove all cards from the Done column (legacy) or last column (custom)."""
        self._ensure_writable()

        if not self.use_custom_columns:
            done_count = len(self.columns[Status.DONE])
            self.columns[Status.DONE].cards.clear()
            self.save_board()
            return done_count
        else:
            # For custom columns, clear the last column (typically "Done")
            if not self.custom_columns:
                return 0
            
            last_column = max(self.custom_columns.values(), key=lambda col: col.position)
            card_count = len(last_column.cards)
            last_column.cards.clear()
            self.save_board()
            return card_count
    
    def load_board(self):
        """Load board data from storage."""
        data = self.storage.load()
        
        # Check if data contains custom columns
        has_custom_columns = 'columns' in data
        is_legacy_data = 'cards' in data and not has_custom_columns
        is_empty_board = not data.get('cards') and not has_custom_columns

        if self.use_custom_columns and is_empty_board:
            self._init_default_custom_columns(persist=not self.is_read_only())
            return
        
        if has_custom_columns and self.use_custom_columns:
            # Load custom columns format
            self._load_custom_columns(data)
        elif is_legacy_data:
            # Handle legacy data or convert to custom columns
            if self.use_custom_columns:
                self._convert_legacy_to_custom(data, persist=not self.is_read_only())
            else:
                self._load_legacy_data(data)
        elif self.use_custom_columns and not self.custom_columns:
            # Initialize default custom columns if empty
            self._init_default_custom_columns(persist=not self.is_read_only())
    
    def _load_custom_columns(self, data: Dict):
        """Load custom columns format."""
        self.custom_columns.clear()
        self.card_types.clear()

        for card_type_data in data.get('card_types', []):
            card_type = CardType.from_dict(card_type_data)
            self.card_types[card_type.id] = card_type

        self._ensure_default_card_type()
        self.last_used_card_type_id = data.get('last_used_card_type_id') or self.get_default_card_type_id()
        
        # Load columns
        for column_data in data.get('columns', []):
            column = CustomColumn.from_dict(column_data)
            self.custom_columns[column.id] = column
        
        # Load cards into columns
        for card_data in data.get('cards', []):
            card = Card.from_dict(card_data)
            if not card.card_type_id or card.card_type_id not in self.card_types:
                card.card_type_id = self.get_default_card_type_id()
            if card.column_id in self.custom_columns:
                self.custom_columns[card.column_id].add_card(card)
    
    def _load_legacy_data(self, data: Dict):
        """Load legacy format data."""
        self.card_types.clear()
        self._ensure_default_card_type()
        self.last_used_card_type_id = data.get('last_used_card_type_id') or self.get_default_card_type_id()
        # Clear current columns
        for column in self.columns.values():
            column.cards.clear()
        
        # Load cards into appropriate columns
        for card_data in data.get('cards', []):
            card = Card.from_dict(card_data)
            if not card.card_type_id or card.card_type_id not in self.card_types:
                card.card_type_id = self.get_default_card_type_id()
            if card.status:
                self.columns[card.status].add_card(card)
    
    def _convert_legacy_to_custom(self, data: Dict, persist: bool = True):
        """Convert legacy data to custom columns format."""
        self.custom_columns.clear()
        self.card_types.clear()
        self._ensure_default_card_type()
        self.last_used_card_type_id = self.get_default_card_type_id()
        
        # Create default custom columns based on Status enum
        status_to_column_id = {}
        colors = ["#FF9800", "#2196F3", "#9C27B0", "#4CAF50"]  # Orange, Blue, Purple, Green
        
        for i, status in enumerate(Status):
            column_id = str(uuid.uuid4())
            column = CustomColumn(column_id, status.value, i, colors[i])
            self.custom_columns[column_id] = column
            status_to_column_id[status] = column_id
        
        # Load and convert cards
        for card_data in data.get('cards', []):
            card = Card.from_dict(card_data)
            if not card.card_type_id or card.card_type_id not in self.card_types:
                card.card_type_id = self.get_default_card_type_id()
            if card.status in status_to_column_id:
                column_id = status_to_column_id[card.status]
                card.move_to_column(column_id)
                self.custom_columns[column_id].add_card(card)
        
        # Save in new format
        if persist:
            self.save_board()
    
    def _init_default_custom_columns(self, persist: bool = True):
        """Initialize default custom columns."""
        self._ensure_default_card_type()
        if not self.last_used_card_type_id:
            self.last_used_card_type_id = self.get_default_card_type_id()
        default_columns = [
            ("To Do", "#FF9800"),
            ("In Progress", "#2196F3"),
            ("Review", "#9C27B0"),
            ("Done", "#4CAF50")
        ]
        
        for i, (name, color) in enumerate(default_columns):
            column_id = str(uuid.uuid4())
            column = CustomColumn(column_id, name, i, color)
            self.custom_columns[column_id] = column
        
        if persist:
            self.save_board()
    
    def save_board(self):
        """Save board data to storage."""
        self._ensure_default_card_type()
        if not self.last_used_card_type_id:
            self.last_used_card_type_id = self.get_default_card_type_id()
        if self.use_custom_columns:
            # Save custom columns format
            columns_data = [column.to_dict() for column in self.custom_columns.values()]
            card_types_data = [card_type.to_dict() for card_type in self.get_card_types_ordered()]
            cards_data = []
            
            for column in self.custom_columns.values():
                for card in column:
                    cards_data.append(card.to_dict())
            
            data = {
                'columns': columns_data,
                'card_types': card_types_data,
                'cards': cards_data,
                'last_used_card_type_id': self.last_used_card_type_id,
                'format_version': '2.0'
            }
        else:
            # Save legacy format
            card_types_data = [card_type.to_dict() for card_type in self.get_card_types_ordered()]
            cards_data = []
            for column in self.columns.values():
                for card in column:
                    cards_data.append(card.to_dict())
            
            data = {
                'cards': cards_data,
                'card_types': card_types_data,
                'last_used_card_type_id': self.last_used_card_type_id,
            }
        
        self.storage.save(data)
    
    def export_board(self, format_type: str = "text") -> str:
        """Export board in different formats."""
        if format_type == "text":
            output = []
            output.append("=" * 60)
            output.append("KANBAN BOARD")
            output.append("=" * 60)
            
            if self.use_custom_columns:
                ordered_columns = self.get_columns_ordered()
                for column in ordered_columns:
                    output.append(f"\n{column.name} ({len(column)} cards)")
                    output.append("-" * 30)
                    
                    if len(column) == 0:
                        output.append("  (no cards)")
                    else:
                        for i, card in enumerate(column, 1):
                            output.append(f"  {i}. {card}")
                            if card.description:
                                output.append(f"     Description: {card.description}")
                            if card.project:
                                output.append(f"     Project: {card.project}")
                            parent_card = self.get_parent_card(card)
                            if parent_card:
                                output.append(f"     Parent: {parent_card.title}")
                            completed, total = self.get_subcard_progress(card.id)
                            if total:
                                output.append(f"     Subcards: [{completed}/{total} done]")
            else:
                for status in Status:
                    column = self.columns[status]
                    output.append(f"\n{status.value} ({len(column)} cards)")
                    output.append("-" * 30)
                    
                    if len(column) == 0:
                        output.append("  (no cards)")
                    else:
                        for i, card in enumerate(column, 1):
                            output.append(f"  {i}. {card}")
                            if card.description:
                                output.append(f"     Description: {card.description}")
                            if card.project:
                                output.append(f"     Project: {card.project}")
                            parent_card = self.get_parent_card(card)
                            if parent_card:
                                output.append(f"     Parent: {parent_card.title}")
                            completed, total = self.get_subcard_progress(card.id)
                            if total:
                                output.append(f"     Subcards: [{completed}/{total} done]")
            
            return "\n".join(output)
        
        return "Unsupported format"