## @file
#  @brief Board domain logic for cards, columns, persistence, and read-only guards.
"""Main Kanban board implementation with custom column support."""

import os
import uuid
from copy import deepcopy
from datetime import date, datetime
from typing import Dict, List, Optional, Set, Union

from .models import UNSET, Card, CardAttachment, CardTodoItem, CardType, Column, CustomColumn, Priority, Project, Status
from .storage import DataStorage, LockHandler, get_default_single_board_file


## @brief Encapsulates the state and operations of a single Kanban board.
class KanbanBoard:
    """Main Kanban board class for managing cards and columns."""
    DEFAULT_CARD_TYPE_NAME = 'Default'
    MAX_UNDO_STEPS = 100
    
    def __init__(self, data_file: str = None, use_custom_columns: bool = True,
                 lock_handler: Optional[LockHandler] = None, storage_backend: Optional[str] = None):
        if data_file is None:
            data_file = get_default_single_board_file()
        
        self.storage = DataStorage(data_file, lock_handler=lock_handler, backend=storage_backend)
        self.use_custom_columns = True
        self.card_types: Dict[str, CardType] = {}
        self.projects: Dict[str, Project] = {}
        self.last_used_card_type_id = None
        self._undo_stack: List[Dict[str, object]] = []
        self._redo_stack: List[Dict[str, object]] = []
        self.custom_columns: Dict[str, CustomColumn] = {}
        self.columns = None
        
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

    def export_data(self) -> Dict:
        """Return the current board state as serializable data."""
        self._ensure_default_card_type()
        if not self.last_used_card_type_id:
            self.last_used_card_type_id = self.get_default_card_type_id()

        card_types_data = [card_type.to_dict() for card_type in self.get_card_types_ordered()]
        projects_data = [project.to_dict() for project in self.get_projects_ordered()]
        columns_data = [column.to_dict() for column in self.custom_columns.values()]
        cards_data = []
        for column in self.custom_columns.values():
            for card in column:
                cards_data.append(card.to_dict())

        return {
            'columns': columns_data,
            'cards': cards_data,
            'card_types': card_types_data,
            'projects': projects_data,
            'last_used_card_type_id': self.last_used_card_type_id,
            'format_version': '2.0',
        }

    def _push_history_state(self, stack: List[Dict[str, object]], description: str):
        """Capture the current state on the provided history stack."""
        stack.append({
            'description': description,
            'data': deepcopy(self.export_data()),
        })
        if len(stack) > self.MAX_UNDO_STEPS:
            stack.pop(0)

    def _push_undo_state(self, description: str):
        """Capture the current state so the next change can be undone."""
        self._push_history_state(self._undo_stack, description)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        """Return whether an undo snapshot is available."""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """Return whether a redo snapshot is available."""
        return bool(self._redo_stack)

    def get_next_undo_description(self) -> Optional[str]:
        """Return the description of the next undo action, if any."""
        if not self._undo_stack:
            return None
        return self._undo_stack[-1]['description']

    def get_next_redo_description(self) -> Optional[str]:
        """Return the description of the next redo action, if any."""
        if not self._redo_stack:
            return None
        return self._redo_stack[-1]['description']

    def undo_last_action(self) -> Optional[str]:
        """Restore the most recently captured board state."""
        self._ensure_writable()
        if not self._undo_stack:
            return None

        snapshot = self._undo_stack.pop()
        self._push_history_state(self._redo_stack, snapshot['description'])
        self._load_from_data(deepcopy(snapshot['data']), persist_defaults=False)
        self.save_board()
        return snapshot['description']

    def redo_last_action(self) -> Optional[str]:
        """Reapply the most recently undone board state."""
        self._ensure_writable()
        if not self._redo_stack:
            return None

        snapshot = self._redo_stack.pop()
        self._push_history_state(self._undo_stack, snapshot['description'])
        self._load_from_data(deepcopy(snapshot['data']), persist_defaults=False)
        self.save_board()
        return snapshot['description']
    
    # Column Management Methods
    def create_column(self, name: str, position: int = None, color: str = "#2196F3",
                      is_completed: bool = False, can_add_card: bool = False) -> str:
        """Create a new custom column."""
        self._ensure_writable()

        if not self.use_custom_columns:
            raise ValueError("Custom columns not enabled for this board")
        
        if position is None:
            position = len(self.custom_columns)

        self._push_undo_state(f"Create column '{name}'")
        
        column_id = str(uuid.uuid4())
        column = CustomColumn(column_id, name, position, color, is_completed, can_add_card)
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

        self._push_undo_state(f"Rename column '{self.custom_columns[column_id].name}'")
        
        self.custom_columns[column_id].rename(new_name)
        self.save_board()
        return True

    def update_column(self, column_id: str, name: str = None, color: str = None,
                      is_completed=UNSET, can_add_card=UNSET) -> bool:
        """Update one or more custom column properties in a single undo step."""
        self._ensure_writable()

        if not self.use_custom_columns or column_id not in self.custom_columns:
            return False

        column = self.custom_columns[column_id]
        if name is None and color is None and is_completed is UNSET and can_add_card is UNSET:
            return False

        self._push_undo_state(f"Update column '{column.name}'")
        if name is not None:
            column.rename(name)
        if color is not None:
            column.change_color(color)
        if is_completed is not UNSET:
            column.set_completed(is_completed)
        if can_add_card is not UNSET:
            column.set_can_add_card(can_add_card)
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
        self._push_undo_state(f"Delete column '{column.name}'")
        
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

        self._push_undo_state("Reorder columns")
        
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

        self._push_undo_state(f"Change color of column '{self.custom_columns[column_id].name}'")
        
        self.custom_columns[column_id].change_color(color)
        self.save_board()
        return True
    
    def get_columns_ordered(self) -> List[Union[CustomColumn, Column]]:
        """Get columns in position order."""
        return sorted(self.custom_columns.values(), key=lambda col: col.position)
    
    def get_column_by_id(self, column_id: str) -> Optional[CustomColumn]:
        """Get a custom column by ID."""
        return self.custom_columns.get(column_id)
    
    def _adjust_column_positions(self):
        """Ensure column positions are sequential starting from 0."""
        ordered_columns = sorted(self.custom_columns.values(), key=lambda col: col.position)
        for index, column in enumerate(ordered_columns):
            column.position = index
    
    def _get_first_column_id(self) -> Optional[str]:
        """Get the ID of the first column."""
        if not self.custom_columns:
            return None
        return min(self.custom_columns.keys(), key=lambda cid: self.custom_columns[cid].position)

    def get_default_add_card_column_id(self) -> Optional[str]:
        """Return the preferred column for creating new cards in custom-column mode."""
        if not self.use_custom_columns:
            return None

        ordered_columns = self.get_columns_ordered()
        for column in ordered_columns:
            if column.can_add_card:
                return column.id
        return ordered_columns[0].id if ordered_columns else None

    def get_subcard_target(self, parent_card: Card):
        """Return the column or status where a new subcard should be created."""
        if not self.use_custom_columns:
            return parent_card.status

        parent_column = self.get_column_by_id(parent_card.column_id)
        if parent_column is not None and parent_column.can_add_card:
            return parent_column.id

        return self._get_first_column_id() or parent_card.column_id

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

    def get_project(self, project_id: str) -> Optional[Project]:
        """Return a project by ID."""
        return self.projects.get(project_id)

    def get_project_by_name(self, name: Optional[str]) -> Optional[Project]:
        """Return a project matching the provided name, ignoring case."""
        normalized_name = (name or '').strip().lower()
        if not normalized_name:
            return None
        return next(
            (project for project in self.projects.values() if project.name.strip().lower() == normalized_name),
            None,
        )

    def get_projects_ordered(self) -> List[Project]:
        """Return projects sorted by name."""
        return sorted(self.projects.values(), key=lambda project: project.name.lower())

    def _project_name_matches(self, value: Optional[str], project_name: str) -> bool:
        """Return whether a stored project reference matches the given project name."""
        return bool(value and value.strip().lower() == project_name.strip().lower())

    def _ensure_project_exists(self, project_name: Optional[str], description: str = '') -> Optional[Project]:
        """Ensure a project registry entry exists for the provided name."""
        normalized_name = (project_name or '').strip()
        if not normalized_name:
            return None
        existing = self.get_project_by_name(normalized_name)
        if existing is not None:
            return existing
        project = Project(normalized_name, description)
        self.projects[project.id] = project
        return project

    def _sync_projects_from_references(self):
        """Backfill managed projects from cards and card-type presets."""
        for card_type in self.card_types.values():
            self._ensure_project_exists(card_type.default_project)
        for card in self.get_all_cards():
            self._ensure_project_exists(card.project)

    def create_project(self, name: str, description: str = '') -> str:
        """Create a new reusable project."""
        self._ensure_writable()

        name = (name or '').strip()
        if not name:
            raise ValueError('Project name is required')
        if self.get_project_by_name(name) is not None:
            raise ValueError('A project with that name already exists')

        self._push_undo_state(f"Create project '{name}'")

        project = Project(name, description)
        self.projects[project.id] = project
        self.save_board()
        return project.id

    def edit_project(self, project_id: str, name: str = None, description: str = None) -> Optional[Project]:
        """Edit an existing project and update any references to it."""
        self._ensure_writable()

        project = self.get_project(project_id)
        if project is None:
            return None

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError('Project name is required')
            duplicate = next(
                (existing for existing in self.projects.values()
                 if existing.id != project_id and existing.name.lower() == name.lower()),
                None,
            )
            if duplicate is not None:
                raise ValueError('A project with that name already exists')

        old_name = project.name
        self._push_undo_state(f"Edit project '{old_name}'")

        project.update(name, description)
        if name is not None and project.name != old_name:
            for card in self.get_all_cards():
                if self._project_name_matches(card.project, old_name):
                    card.project = project.name
                    card.updated_at = datetime.now()
            for card_type in self.card_types.values():
                if self._project_name_matches(card_type.default_project, old_name):
                    card_type.update(default_project=project.name)

        self.save_board()
        return project

    def get_cards_by_project(self, project_id: str) -> List[Card]:
        """Return all cards referencing the given project."""
        project = self.get_project(project_id)
        if project is None:
            return []
        return [card for card in self.get_all_cards() if self._project_name_matches(card.project, project.name)]

    def get_card_types_by_project(self, project_id: str) -> List[CardType]:
        """Return card types whose project preset references the given project."""
        project = self.get_project(project_id)
        if project is None:
            return []
        return [
            card_type
            for card_type in self.card_types.values()
            if self._project_name_matches(card_type.default_project, project.name)
        ]

    def delete_project(self, project_id: str, delete_cards: bool = False,
                       replacement_project_id: str = None) -> bool:
        """Delete a project and either remove, clear, or reassign its references."""
        self._ensure_writable()

        project = self.get_project(project_id)
        if project is None:
            return False

        replacement_project = None
        replacement_name = None
        if replacement_project_id:
            replacement_project = self.get_project(replacement_project_id)
            if replacement_project is None:
                raise ValueError('Replacement project does not exist')
            if replacement_project.id == project_id:
                raise ValueError('Replacement project must be different')
            replacement_name = replacement_project.name

        self._push_undo_state(f"Delete project '{project.name}'")

        cards = self.get_cards_by_project(project_id)
        if delete_cards:
            top_level_cards = [card for card in cards if not card.parent_id]
            nested_cards = [card for card in cards if card.parent_id]
            for card in top_level_cards + nested_cards:
                if self.find_card(card.id):
                    self._delete_card_internal(card.id)
        else:
            for card in cards:
                card.project = replacement_name
                card.updated_at = datetime.now()

        for card_type in self.get_card_types_by_project(project_id):
            card_type.update(default_project=replacement_name)

        del self.projects[project_id]
        self.save_board()
        return True

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

        self._push_undo_state(f"Create card type '{name}'")

        card_type = CardType(name, description, default_project, default_color)
        self.card_types[card_type.id] = card_type
        self._ensure_project_exists(default_project)
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

        self._push_undo_state(f"Edit card type '{card_type.name}'")

        card_type.update(name, description, default_project, default_color)
        if default_project is not UNSET:
            self._ensure_project_exists(card_type.default_project)
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

        self._push_undo_state(f"Delete card type '{card_type.name}'")

        cards = self.get_cards_by_type(card_type_id)
        if delete_cards:
            top_level_cards = [card for card in cards if not card.parent_id]
            nested_cards = [card for card in cards if card.parent_id]
            for card in top_level_cards + nested_cards:
                if self.find_card(card.id):
                    self._delete_card_internal(card.id)
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
                   card_type_id: str = None, assignee: str = None,
                   tags: Optional[List[str]] = None,
                   todo_items: Optional[List[object]] = None) -> Card:
        """Create a new card and add it to the specified column (or first column if none specified)."""
        self._ensure_writable()
        card_type = self._resolve_card_type(card_type_id)
        effective_project = project if project is not None else card_type.default_project
        effective_color = color if color is not None else card_type.default_color
        self._ensure_project_exists(effective_project)

        if self.use_custom_columns:
            if not column_id:
                column_id = self._get_first_column_id()
                if not column_id:
                    raise ValueError("No columns available. Create a column first.")
            
            if column_id not in self.custom_columns:
                raise ValueError(f"Column {column_id} does not exist")

            self._push_undo_state(f"Create card '{title}'")
            card = Card(title, description, priority, column_id)
            card.project = effective_project
            card.start_date = start_date
            card.end_date = end_date
            if parent_id is not None:
                card.parent_id = parent_id
            card.color = effective_color
            card.card_type_id = card_type.id
            card.assignee = assignee
            if tags:
                card.tags = list(dict.fromkeys(tags))
            card.todo_items = card._coerce_todo_items(todo_items or [])
            self.custom_columns[column_id].add_card(card)
        else:
            # Legacy mode
            self._push_undo_state(f"Create card '{title}'")
            card = Card(title, description, priority)
            card.project = effective_project
            card.start_date = start_date
            card.end_date = end_date
            if parent_id is not None:
                card.parent_id = parent_id
            card.color = effective_color
            card.card_type_id = card_type.id
            card.assignee = assignee
            if tags:
                card.tags = list(dict.fromkeys(tags))
            card.todo_items = card._coerce_todo_items(todo_items or [])
            self.columns[Status.TODO].add_card(card)

        self.last_used_card_type_id = card_type.id
        self.save_board()
        return card
    
    def edit_card(self, card_id: str, title: str = None, description: str = None, 
                  priority: Priority = None, assignee: str = None, project: str = None,
                  start_date=UNSET, end_date=UNSET, parent_id: str = None, color=UNSET,
                  tags=UNSET,
                  card_type_id=UNSET,
                  todo_items=UNSET) -> Optional[Card]:
        """Edit an existing card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if card:
            resolved_type_id = card_type_id
            if card_type_id is not UNSET:
                resolved_type = self._resolve_card_type(card_type_id)
                resolved_type_id = resolved_type.id
                self.last_used_card_type_id = resolved_type.id
            self._push_undo_state(f"Edit card '{card.title}'")
            card.update(title, description, priority, assignee, project, start_date, end_date, parent_id, color, resolved_type_id, todo_items)
            if project is not None:
                self._ensure_project_exists(project)
            if tags is not UNSET:
                card.tags = list(dict.fromkeys(tags or []))
                card.updated_at = datetime.now()
            self.save_board()
            return card
        return None

    def update_card_tags(self, card_id: str, tags: List[str]) -> Optional[Card]:
        """Replace the tag list for a card in a single undo step."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return None

        self._push_undo_state(f"Update tags on '{card.title}'")
        card.tags = list(dict.fromkeys(tags or []))
        card.updated_at = datetime.now()
        self.save_board()
        return card

    def add_card_tag(self, card_id: str, tag: str) -> bool:
        """Add a single tag to a card in a reversible way."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card or not tag or tag in card.tags:
            return False

        self._push_undo_state(f"Add tag to '{card.title}'")
        card.add_tag(tag)
        self.save_board()
        return True

    def add_card_todo_item(self, card_id: str, text: str, completed: bool = False) -> Optional[CardTodoItem]:
        """Add a single checklist item to a card in a reversible way."""
        self._ensure_writable()

        card = self.find_card(card_id)
        normalized_text = (text or '').strip()
        if not card or not normalized_text:
            return None

        self._push_undo_state(f"Add checklist item to '{card.title}'")
        todo_item = CardTodoItem(normalized_text, completed)
        card.todo_items.append(todo_item)
        card.updated_at = datetime.now()
        self.save_board()
        return todo_item

    def update_card_todo_item(self, card_id: str, todo_item_id: str, text=UNSET, completed=UNSET) -> Optional[CardTodoItem]:
        """Update a single checklist item on a card in a reversible way."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return None

        todo_item = next((item for item in card.todo_items if item.id == todo_item_id), None)
        if todo_item is None:
            return None

        new_text = todo_item.text if text is UNSET else (text or '').strip()
        new_completed = todo_item.completed if completed is UNSET else bool(completed)
        if not new_text:
            return None
        if new_text == todo_item.text and new_completed == todo_item.completed:
            return todo_item

        self._push_undo_state(f"Update checklist item on '{card.title}'")
        todo_item.text = new_text
        todo_item.completed = new_completed
        card.updated_at = datetime.now()
        self.save_board()
        return todo_item

    def delete_card_todo_item(self, card_id: str, todo_item_id: str) -> bool:
        """Delete a single checklist item from a card in a reversible way."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return False

        for index, todo_item in enumerate(card.todo_items):
            if todo_item.id != todo_item_id:
                continue
            self._push_undo_state(f"Remove checklist item from '{card.title}'")
            card.todo_items.pop(index)
            card.updated_at = datetime.now()
            self.save_board()
            return True
        return False

    def get_all_cards(self, include_archived: bool = False) -> List[Card]:
        """Return every card currently on the board."""
        cards = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        for column in columns:
            for card in column:
                if include_archived or not card.is_archived():
                    cards.append(card)
        return cards

    def get_column_cards(self, column: Union[str, CustomColumn], include_archived: bool = False) -> List[Card]:
        """Return cards for one column, optionally including archived cards."""
        target_column = column if isinstance(column, CustomColumn) else self.get_column_by_id(column)
        if target_column is None:
            return []
        if include_archived:
            return list(target_column.cards)
        return [card for card in target_column.cards if not card.is_archived()]

    def get_archived_cards(self) -> List[Card]:
        """Return archived cards ordered by archive timestamp then title."""
        cards = [card for card in self.get_all_cards(include_archived=True) if card.is_archived()]
        return sorted(cards, key=lambda card: ((card.archived_at or card.updated_at), card.title.lower()))

    def get_parent_card(self, card: Card) -> Optional[Card]:
        """Return the direct parent card for the given card, if any."""
        if not card.parent_id:
            return None
        parent = self.find_card(card.parent_id)
        if parent is not None:
            return parent
        return self.find_card(card.parent_id, include_archived=True)

    def get_subcards(self, parent_id: str, include_archived: bool = False) -> List[Card]:
        """Return the direct child cards of the given parent card."""
        return [card for card in self.get_all_cards(include_archived=include_archived) if card.parent_id == parent_id]

    def get_card_attachment(self, card_id: str, attachment_id: str) -> Optional[CardAttachment]:
        """Return a specific attachment linked to a card."""
        card = self.find_card(card_id)
        if not card:
            return None
        return card.get_attachment(attachment_id)

    def get_card_attachment_path(self, card_id: str, attachment_id: str) -> Optional[str]:
        """Return the absolute path for a card attachment."""
        attachment = self.get_card_attachment(card_id, attachment_id)
        if attachment is None:
            return None
        return self.storage.resolve_attachment_path(attachment.relative_path)

    def add_card_attachment(self, card_id: str, source_path: str) -> Optional[CardAttachment]:
        """Copy a file into board storage and link it to a card."""
        attachments = self.add_card_attachments(card_id, [source_path])
        return attachments[0] if attachments else None

    def add_card_attachments(self, card_id: str, source_paths: List[str]) -> List[CardAttachment]:
        """Copy one or more files into board storage and link them to a card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return []

        normalized_paths = []
        for path in source_paths:
            absolute_path = os.path.abspath(path)
            if os.path.isfile(absolute_path) and absolute_path not in normalized_paths:
                normalized_paths.append(absolute_path)

        if not normalized_paths:
            return []

        count = len(normalized_paths)
        label = 'attachment' if count == 1 else 'attachments'
        self._push_undo_state(f"Add {count} {label} to '{card.title}'")

        attachments: List[CardAttachment] = []
        try:
            for source_path in normalized_paths:
                relative_path = self.storage.copy_attachment(source_path, card.id)
                attachments.append(card.add_attachment(os.path.basename(source_path), relative_path))
        except Exception:
            self._undo_stack.pop()
            raise

        self.save_board()
        return attachments

    def delete_card_attachment(self, card_id: str, attachment_id: str) -> bool:
        """Remove an attachment link from a card while keeping the copied file available for history."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return False

        attachment = card.get_attachment(attachment_id)
        if attachment is None:
            return False

        self._push_undo_state(f"Remove attachment from '{card.title}'")
        removed = card.remove_attachment(attachment_id)
        if removed is None:
            self._undo_stack.pop()
            return False

        self.save_board()
        return True

    def _collect_attachment_paths_from_data(self, data: Dict) -> Set[str]:
        """Return the normalized absolute attachment paths referenced by serialized board data."""
        attachment_paths: Set[str] = set()
        for card_data in data.get('cards', []):
            for attachment_data in card_data.get('attachments', []):
                relative_path = attachment_data.get('relative_path')
                if not relative_path:
                    continue
                attachment_paths.add(
                    os.path.normcase(os.path.abspath(self.storage.resolve_attachment_path(relative_path)))
                )
        return attachment_paths

    def get_referenced_attachment_paths(self, include_history: bool = True) -> Set[str]:
        """Return attachment paths referenced by the current board state and optional history snapshots."""
        referenced_paths = self._collect_attachment_paths_from_data(self.export_data())
        if not include_history:
            return referenced_paths

        for snapshot in self._undo_stack:
            referenced_paths.update(self._collect_attachment_paths_from_data(snapshot['data']))
        for snapshot in self._redo_stack:
            referenced_paths.update(self._collect_attachment_paths_from_data(snapshot['data']))
        return referenced_paths

    def cleanup_orphaned_attachment_files(self) -> Dict[str, object]:
        """Delete stored attachment files that are no longer referenced by the board or its history."""
        self._ensure_writable()

        stored_files = self.storage.list_attachment_files()
        if not stored_files:
            return {
                'removed_files': 0,
                'removed_directories': 0,
                'scanned_files': 0,
                'retained_files': 0,
                'removed_paths': [],
            }

        referenced_paths = self.get_referenced_attachment_paths(include_history=True)
        removed_paths = []
        for file_path in stored_files:
            normalized_path = os.path.normcase(os.path.abspath(file_path))
            if normalized_path in referenced_paths:
                continue
            if self.storage.delete_attachment_file(file_path):
                removed_paths.append(file_path)

        removed_directories = self.storage.remove_empty_attachment_directories()
        return {
            'removed_files': len(removed_paths),
            'removed_directories': removed_directories,
            'scanned_files': len(stored_files),
            'retained_files': len(stored_files) - len(removed_paths),
            'removed_paths': removed_paths,
        }

    def add_card_note(self, card_id: str, text: str = ""):
        """Add a timestamped note to an existing card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return None

        self._push_undo_state(f"Add note to '{card.title}'")
        note = card.add_note(text)
        self.save_board()
        return note

    def delete_card_note(self, card_id: str, note_id: str) -> bool:
        """Delete a note from an existing card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return False

        self._push_undo_state(f"Delete note from '{card.title}'")
        removed = card.remove_note(note_id)
        if removed:
            self.save_board()
        else:
            self._undo_stack.pop()
        return removed

    def edit_card_note(self, card_id: str, note_id: str, text: str = ""):
        """Edit an existing note on a card."""
        self._ensure_writable()

        card = self.find_card(card_id)
        if not card:
            return None

        self._push_undo_state(f"Edit note on '{card.title}'")
        note = card.update_note(note_id, text)
        if note is not None:
            self.save_board()
        else:
            self._undo_stack.pop()
        return note

    def get_subcard_progress(self, parent_id: str) -> tuple[int, int]:
        """Return completed and total counts for a parent card's direct subcards."""
        subcards = self.get_subcards(parent_id)
        completed = sum(1 for card in subcards if self.is_card_done(card))
        return completed, len(subcards)

    def is_card_done(self, card: Card) -> bool:
        """Return whether the given card is currently in the done column."""
        if self.use_custom_columns:
            column = self.get_column_by_id(card.column_id)
            return bool(column and column.is_completed)
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
                       end_date: date = None, assignee: str = None,
                       tags: Optional[List[str]] = None,
                       todo_items: Optional[List[object]] = None) -> Card:
        """Create a child card under an existing parent card."""
        parent_card = self.find_card(parent_id)
        if not parent_card:
            raise ValueError("Parent card does not exist")
        if parent_card.parent_id:
            raise ValueError("Nested subcards are not supported")

        target = self.get_subcard_target(parent_card)
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
            assignee,
            tags,
            todo_items,
        )
    
    def _delete_card_internal(self, card_id: str) -> bool:
        """Delete a card without capturing a second undo snapshot."""
        for subcard in list(self.get_subcards(card_id, include_archived=True)):
            self._delete_card_internal(subcard.id)

        if self.use_custom_columns:
            for column in self.custom_columns.values():
                removed_card = column.remove_card(card_id)
                if removed_card:
                    return True
        else:
            for column in self.columns.values():
                removed_card = column.remove_card(card_id)
                if removed_card:
                    return True
        return False

    def delete_card(self, card_id: str) -> bool:
        """Delete a card from the board."""
        self._ensure_writable()

        card = self.find_card(card_id, include_archived=True)
        if not card:
            return False

        self._push_undo_state(f"Delete card '{card.title}'")

        removed = self._delete_card_internal(card_id)
        if removed:
            self.save_board()
        return removed
    
    def move_card(
        self,
        card_id: str,
        to_column: Union[str, Status],
        target_card_id: Optional[str] = None,
        insert_after: bool = False,
    ) -> bool:
        """Move a card to a different column."""
        self._ensure_writable()

        card = None
        existing_card = self.find_card(card_id)
        if not existing_card:
            return False
        self._push_undo_state(f"Move card '{existing_card.title}'")
        
        if self.use_custom_columns:
            if not isinstance(to_column, str) or to_column not in self.custom_columns:
                self._undo_stack.pop()
                return False

            target_column = self.custom_columns[to_column]
            source_column = self.custom_columns.get(existing_card.column_id)
            if source_column is None:
                self._undo_stack.pop()
                return False

            if target_card_id == card_id and source_column is target_column:
                self._undo_stack.pop()
                return False

            # Find and remove the card from its current column
            for column in self.custom_columns.values():
                card = column.remove_card(card_id)
                if card:
                    break

            if card:
                target_index = None
                if target_card_id is not None:
                    target_index = target_column.card_index(target_card_id)
                    if target_index is None:
                        self._undo_stack.pop()
                        return False
                    if insert_after:
                        target_index += 1

                card.move_to_column(to_column)
                target_column.add_card(card, target_index)
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

        self._undo_stack.pop()
        return False
    
    def find_card(self, card_id: str, include_archived: bool = False) -> Optional[Card]:
        """Find a card by its ID."""
        if self.use_custom_columns:
            for column in self.custom_columns.values():
                card = column.get_card(card_id)
                if card and (include_archived or not card.is_archived()):
                    return card
        else:
            for column in self.columns.values():
                card = column.get_card(card_id)
                if card and (include_archived or not card.is_archived()):
                    return card
        return None

    def _set_card_archived_state(self, card: Card, archived: bool):
        """Apply archived or restored state recursively to a card tree."""
        for subcard in self.get_subcards(card.id, include_archived=True):
            self._set_card_archived_state(subcard, archived)
        if archived:
            card.archive()
        else:
            card.restore()

    def archive_card(self, card_id: str) -> bool:
        """Archive a card and its child cards."""
        self._ensure_writable()

        card = self.find_card(card_id, include_archived=True)
        if not card or card.is_archived():
            return False

        self._push_undo_state(f"Archive card '{card.title}'")
        self._set_card_archived_state(card, archived=True)
        self.save_board()
        return True

    def restore_archived_card(self, card_id: str) -> bool:
        """Restore an archived card and its child cards."""
        self._ensure_writable()

        card = self.find_card(card_id, include_archived=True)
        if not card or not card.is_archived():
            return False

        self._push_undo_state(f"Restore archived card '{card.title}'")
        self._set_card_archived_state(card, archived=False)
        self.save_board()
        return True
    
    def search_cards(self, query: str, include_archived: bool = False) -> List[Card]:
        """Search for cards by title, description, project, tags, and child-card titles."""
        results = []
        query_lower = query.lower()
        
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        
        for column in columns:
            for card in column:
                if card.is_archived() and not include_archived:
                    continue
                if (query_lower in card.title.lower() or 
                    query_lower in card.description.lower() or
                    (card.project and query_lower in card.project.lower()) or
                    any(query_lower in subcard.title.lower() for subcard in self.get_subcards(card.id, include_archived=include_archived)) or
                    any(query_lower in tag.lower() for tag in card.tags)):
                    results.append(card)
        
        return results
    
    def get_cards_by_priority(self, priority: Priority, include_archived: bool = False) -> List[Card]:
        """Get all cards with a specific priority."""
        results = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        
        for column in columns:
            for card in column:
                if card.is_archived() and not include_archived:
                    continue
                if card.priority == priority:
                    results.append(card)
        return results
    
    def get_cards_by_assignee(self, assignee: str, include_archived: bool = False) -> List[Card]:
        """Get all cards assigned to a specific person."""
        results = []
        columns = self.custom_columns.values() if self.use_custom_columns else self.columns.values()
        
        for column in columns:
            for card in column:
                if card.is_archived() and not include_archived:
                    continue
                if card.assignee and card.assignee.lower() == assignee.lower():
                    results.append(card)
        return results
    
    def get_board_stats(self) -> Dict:
        """Get statistics about the board."""
        if self.use_custom_columns:
            total_cards = sum(len(self.get_column_cards(column)) for column in self.custom_columns.values())
            column_stats = {column.name: len(self.get_column_cards(column)) for column in self.custom_columns.values()}
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
                if card.is_archived():
                    continue
                priority_counts[card.priority] += 1

        done_cards = sum(1 for card in self.get_all_cards() if self.is_card_done(card))
        
        stats = {
            'total_cards': total_cards,
            'done': done_cards,
            'priority_counts': priority_counts,
            'use_custom_columns': self.use_custom_columns,
            'archived_cards': len(self.get_archived_cards()),
        }
        stats.update(column_stats)
        
        return stats
    
    def archive_done_cards(self) -> int:
        """Archive all active cards currently in completed columns."""
        self._ensure_writable()

        if not self.custom_columns:
            return 0

        completed_columns = [column for column in self.custom_columns.values() if column.is_completed]
        cards_to_archive: List[Card] = []
        seen_ids: Set[str] = set()
        for column in completed_columns:
            for card in self.get_column_cards(column):
                if card.id in seen_ids:
                    continue
                cards_to_archive.append(card)
                seen_ids.add(card.id)

        if not cards_to_archive:
            return 0

        self._push_undo_state("Archive done cards")
        for card in cards_to_archive:
            self._set_card_archived_state(card, archived=True)
        self.save_board()
        return len(cards_to_archive)

    def clear_done_cards(self) -> int:
        """Backward-compatible alias for archiving cards in completed columns."""
        return self.archive_done_cards()
    
    def load_board(self):
        """Load board data from storage."""
        data = self.storage.load()
        self._load_from_data(data, persist_defaults=not self.is_read_only())

    def _load_from_data(self, data: Dict, persist_defaults: bool = True):
        """Load board data from a provided serialized representation."""
        self.custom_columns.clear()
        self.card_types.clear()
        self.projects.clear()
        self.last_used_card_type_id = None
        
        # Check if data contains custom columns
        has_custom_columns = 'columns' in data
        is_legacy_data = 'cards' in data and not has_custom_columns
        is_empty_board = not data.get('cards') and not has_custom_columns

        if is_empty_board:
            self._init_default_custom_columns(persist=persist_defaults)
            return

        if has_custom_columns:
            # Load custom columns format
            self._load_custom_columns(data)
        elif is_legacy_data:
            raise ValueError('Legacy boards are no longer supported. Boards must use custom columns.')
        elif not self.custom_columns:
            # Initialize default custom columns if empty
            self._init_default_custom_columns(persist=persist_defaults)
    
    def _load_custom_columns(self, data: Dict):
        """Load custom columns format."""
        self.custom_columns.clear()
        self.card_types.clear()
        self.projects.clear()

        for card_type_data in data.get('card_types', []):
            card_type = CardType.from_dict(card_type_data)
            self.card_types[card_type.id] = card_type

        for project_data in data.get('projects', []):
            project = Project.from_dict(project_data)
            if self.get_project_by_name(project.name) is None:
                self.projects[project.id] = project

        self._ensure_default_card_type()
        self.last_used_card_type_id = data.get('last_used_card_type_id') or self.get_default_card_type_id()
        
        # Load columns
        for column_data in data.get('columns', []):
            column = CustomColumn.from_dict(column_data)
            self.custom_columns[column.id] = column

        self._apply_missing_column_defaults(data.get('columns', []))
        
        # Load cards into columns
        for card_data in data.get('cards', []):
            card = Card.from_dict(card_data)
            if not card.card_type_id or card.card_type_id not in self.card_types:
                card.card_type_id = self.get_default_card_type_id()
            if card.column_id in self.custom_columns:
                self.custom_columns[card.column_id].add_card(card)
        self._sync_projects_from_references()
    
    def _load_legacy_data(self, data: Dict):
        """Load legacy format data."""
        self.card_types.clear()
        self.projects.clear()
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
        self._sync_projects_from_references()
    
    def _convert_legacy_to_custom(self, data: Dict, persist: bool = True):
        """Convert legacy data to custom columns format."""
        self.custom_columns.clear()
        self.card_types.clear()
        self.projects.clear()
        self._ensure_default_card_type()
        self.last_used_card_type_id = self.get_default_card_type_id()
        
        # Create default custom columns based on Status enum
        status_to_column_id = {}
        colors = ["#FF9800", "#2196F3", "#9C27B0", "#4CAF50"]  # Orange, Blue, Purple, Green
        
        for i, status in enumerate(Status):
            column_id = str(uuid.uuid4())
            column = CustomColumn(
                column_id,
                status.value,
                i,
                colors[i],
                is_completed=(status == Status.DONE),
                can_add_card=(status == Status.TODO),
            )
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

        self._sync_projects_from_references()
        
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
            column = CustomColumn(
                column_id,
                name,
                i,
                color,
                is_completed=(name == "Done"),
                can_add_card=(name == "To Do"),
            )
            self.custom_columns[column_id] = column
        
        if persist:
            self.save_board()
    
    def save_board(self):
        """Save board data to storage."""
        self.storage.save(self.export_data())

    def _apply_missing_column_defaults(self, columns_data: List[Dict]):
        """Backfill new column flags for older saved boards that do not persist them yet."""
        if not self.custom_columns:
            return

        if not any('is_completed' in column_data for column_data in columns_data):
            ordered_columns = self.get_columns_ordered()
            if ordered_columns:
                ordered_columns[-1].set_completed(True)

        if not any('can_add_card' in column_data for column_data in columns_data):
            ordered_columns = self.get_columns_ordered()
            if ordered_columns:
                ordered_columns[0].set_can_add_card(True)
    
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
                            todo_completed, todo_total = card.get_todo_progress()
                            if todo_total:
                                output.append(f"     Checklist: [{todo_completed}/{todo_total} done]")
                                for todo_item in card.todo_items[:3]:
                                    tick = '[x]' if todo_item.completed else '[ ]'
                                    output.append(f"       {tick} {todo_item.text}")
                                if todo_total > 3:
                                    output.append(f"       ... {todo_total - 3} more item(s)")
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
                            todo_completed, todo_total = card.get_todo_progress()
                            if todo_total:
                                output.append(f"     Checklist: [{todo_completed}/{todo_total} done]")
                                for todo_item in card.todo_items[:3]:
                                    tick = '[x]' if todo_item.completed else '[ ]'
                                    output.append(f"       {tick} {todo_item.text}")
                                if todo_total > 3:
                                    output.append(f"       ... {todo_total - 3} more item(s)")
                            parent_card = self.get_parent_card(card)
                            if parent_card:
                                output.append(f"     Parent: {parent_card.title}")
                            completed, total = self.get_subcard_progress(card.id)
                            if total:
                                output.append(f"     Subcards: [{completed}/{total} done]")
            
            return "\n".join(output)
        
        return "Unsupported format"