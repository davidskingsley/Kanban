## @file
#  @brief Shared enums and data objects for boards, cards, and columns.
"""!Data models for the Kanban board application."""

import uuid
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Union

UNSET = object()


## @brief Enumerates supported card priority values.
class Priority(Enum):
    """!Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


## @brief Enumerates legacy board status columns.
class Status(Enum):
    """!Default task status options (for backward compatibility)."""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"


## @brief Represents one timestamped audit-log entry for a board action.
class ActionLogEntry:
    """!Represents one timestamped audit-log entry for a board action."""

    def __init__(self, actor_name: str, description: str, occurred_at: datetime = None,
                 card_id: str = None, entry_id: str = None):
        """!Init."""
        self.id = entry_id if entry_id else str(uuid.uuid4())
        self.actor_name = (actor_name or '').strip() or 'Unknown User'
        self.description = (description or '').strip()
        self.occurred_at = occurred_at or datetime.now()
        self.card_id = card_id

    def to_dict(self):
        """!Convert audit entry to dictionary for serialization."""
        return {
            'id': self.id,
            'actor_name': self.actor_name,
            'description': self.description,
            'occurred_at': self.occurred_at.isoformat(),
            'card_id': self.card_id,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """!Create audit entry from dictionary."""
        return cls(
            data.get('actor_name', 'Unknown User'),
            data.get('description', ''),
            datetime.fromisoformat(data.get('occurred_at', datetime.now().isoformat())),
            data.get('card_id'),
            data.get('id'),
        )


## @brief Represents a timestamped note attached to a card.
class CardNote:
    """!Represents a note recorded against a card."""

    def __init__(self, text: str = "", created_at: datetime = None, note_id: str = None):
        """!Init."""
        self.id = note_id if note_id else str(uuid.uuid4())
        self.text = text or ""
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        """!Convert note to dictionary for serialization."""
        return {
            'id': self.id,
            'text': self.text,
            'created_at': self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        """!Create note from dictionary."""
        return cls(
            data.get('text', ''),
            datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            data.get('id'),
        )


## @brief Represents a copied file linked to a card.
class CardAttachment:
    """!Represents a file attachment recorded against a card."""

    def __init__(self, name: str, relative_path: str, created_at: datetime = None, attachment_id: str = None):
        """!Init."""
        self.id = attachment_id if attachment_id else str(uuid.uuid4())
        self.name = name or "attachment"
        self.relative_path = relative_path
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        """!Convert attachment to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'relative_path': self.relative_path,
            'created_at': self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        """!Create attachment from dictionary."""
        return cls(
            data.get('name', 'attachment'),
            data.get('relative_path', ''),
            datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            data.get('id'),
        )


class CardTodoItem:
    """!Represents a checklist item attached to a card."""

    def __init__(self, text: str, completed: bool = False, todo_id: str = None):
        """!Init."""
        self.id = todo_id if todo_id else str(uuid.uuid4())
        self.text = (text or '').strip()
        self.completed = bool(completed)

    def to_dict(self):
        """!Convert checklist item to dictionary for serialization."""
        return {
            'id': self.id,
            'text': self.text,
            'completed': self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """!Create checklist item from dictionary."""
        return cls(
            data.get('text', ''),
            data.get('completed', False),
            data.get('id'),
        )


## @brief Represents a reusable board-level card type with optional presets.
class CardType:
    """!Represents a configurable card type with optional project and color presets."""

    def __init__(self, name: str, description: str = "", default_project: str = None,
                 default_color: str = None, card_type_id: str = None):
        """!Init."""
        self.id = card_type_id if card_type_id else str(uuid.uuid4())
        self.name = name
        self.description = description or ""
        self.default_project = default_project
        self.default_color = default_color
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def update(self, name: str = None, description: str = None,
               default_project=UNSET, default_color=UNSET):
        """!Update card type properties."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if default_project is not UNSET:
            self.default_project = default_project
        if default_color is not UNSET:
            self.default_color = default_color
        self.updated_at = datetime.now()

    def to_dict(self):
        """!Convert card type to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'default_project': self.default_project,
            'default_color': self.default_color,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        """!Create card type from dictionary."""
        card_type = cls(
            data['name'],
            data.get('description', ''),
            data.get('default_project'),
            data.get('default_color'),
            data.get('id'),
        )
        card_type.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        card_type.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        return card_type


## @brief Represents a reusable board-level project with optional description.
class Project:
    """!Represents a configurable project that cards and card-type presets can reference."""

    def __init__(self, name: str, description: str = "", project_id: str = None):
        """!Init."""
        self.id = project_id if project_id else str(uuid.uuid4())
        self.name = name
        self.description = description or ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def update(self, name: str = None, description: str = None):
        """!Update project properties."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.now()

    def to_dict(self):
        """!Convert project to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        """!Create project from dictionary."""
        project = cls(
            data['name'],
            data.get('description', ''),
            data.get('id'),
        )
        project.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        project.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        return project


## @brief Represents a configurable board column with custom ordering and color.
class CustomColumn:
    """!Represents a custom column on the Kanban board."""
    
    def __init__(self, column_id: str, name: str, position: int = 0, color: str = "#2196F3",
                 is_completed: bool = False, can_add_card: bool = False):
        """!Init."""
        self.id = column_id if column_id else str(uuid.uuid4())
        self.name = name
        self.position = position
        self.color = color
        self.is_completed = is_completed
        self.can_add_card = can_add_card
        self.cards: List['Card'] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_card(self, card: 'Card', index: Optional[int] = None):
        """!Add a card to this column."""
        card.column_id = self.id
        if index is None:
            self.cards.append(card)
        else:
            bounded_index = max(0, min(index, len(self.cards)))
            self.cards.insert(bounded_index, card)
        self.updated_at = datetime.now()
    
    def remove_card(self, card_id: str) -> Optional['Card']:
        """!Remove a card from this column by ID."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                removed_card = self.cards.pop(i)
                self.updated_at = datetime.now()
                return removed_card
        return None
    
    def get_card(self, card_id: str) -> Optional['Card']:
        """!Get a card from this column by ID."""
        for card in self.cards:
            if card.id == card_id:
                return card
        return None

    def card_index(self, card_id: str) -> Optional[int]:
        """!Return the index of a card in this column, if present."""
        for index, card in enumerate(self.cards):
            if card.id == card_id:
                return index
        return None
    
    def rename(self, new_name: str):
        """!Rename the column."""
        self.name = new_name
        self.updated_at = datetime.now()
    
    def change_color(self, new_color: str):
        """!Change the column color."""
        self.color = new_color
        self.updated_at = datetime.now()

    def set_completed(self, is_completed: bool):
        """!Control whether cards in this column are treated as done."""
        self.is_completed = bool(is_completed)
        self.updated_at = datetime.now()

    def set_can_add_card(self, can_add_card: bool):
        """!Control whether this column exposes a direct add-card action."""
        self.can_add_card = bool(can_add_card)
        self.updated_at = datetime.now()
    
    def reposition(self, new_position: int):
        """!Change the column position."""
        self.position = new_position
        self.updated_at = datetime.now()
    
    def to_dict(self):
        """!Convert column to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'color': self.color,
            'is_completed': self.is_completed,
            'can_add_card': self.can_add_card,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """!Create column from dictionary."""
        column = cls(
            data['id'],
            data['name'],
            data.get('position', 0),
            data.get('color', '#2196F3'),
            data.get('is_completed', False),
            data.get('can_add_card', False),
        )
        column.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        column.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        return column
    
    def __len__(self):
        """!Len."""
        return len(self.cards)
    
    def __iter__(self):
        """!Iter."""
        return iter(self.cards)
    
    def __str__(self):
        """!Str."""
        return f"{self.name} ({len(self.cards)} cards)"


## @brief Represents an individual task card tracked on the board.
class Card:
    """!Represents a single task card on the Kanban board."""
    
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.MEDIUM, 
                 column_id: str = None):
        """!Init."""
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.priority = priority
        self.column_id = column_id  # Use column_id instead of fixed status
        self.status = None  # Keep for backward compatibility
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.project = None
        self.assignee = None
        self.color = None
        self.card_type_id = None
        self.parent_id = None
        self.tags = []
        self.notes: List[CardNote] = []
        self.attachments: List[CardAttachment] = []
        self.todo_items: List[CardTodoItem] = []
        self.start_date: Optional[date] = None
        self.end_date: Optional[date] = None
        self.archived_at: Optional[datetime] = None

    def update(self, title: str = None, description: str = None,
             priority: Priority = None, assignee: str = None, project: str = None,
             start_date=UNSET, end_date=UNSET, parent_id: str = None, color=UNSET,
             card_type_id=UNSET, todo_items=UNSET):
        """!Update card properties."""
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if priority is not None:
            self.priority = priority
        if assignee is not None:
            self.assignee = assignee
        if project is not None:
            self.project = project
        if start_date is not UNSET:
            self.start_date = start_date
        if end_date is not UNSET:
            self.end_date = end_date
        if parent_id is not None:
            self.parent_id = parent_id
        if color is not UNSET:
            self.color = color
        if card_type_id is not UNSET:
            self.card_type_id = card_type_id
        if todo_items is not UNSET:
            self.todo_items = self._coerce_todo_items(todo_items)
        self.updated_at = datetime.now()

    def archive(self):
        """!Mark the card as archived."""
        now = datetime.now()
        self.archived_at = now
        self.updated_at = now

    def restore(self):
        """!Mark the card as active again."""
        self.archived_at = None
        self.updated_at = datetime.now()

    def is_archived(self) -> bool:
        """!Return whether the card is archived."""
        return self.archived_at is not None

    @staticmethod
    def _coerce_todo_items(todo_items) -> List[CardTodoItem]:
        """!Normalize checklist items from model objects, dicts, or plain text."""
        normalized: List[CardTodoItem] = []
        for todo_item in todo_items or []:
            if isinstance(todo_item, CardTodoItem):
                item = todo_item
            elif isinstance(todo_item, dict):
                item = CardTodoItem.from_dict(todo_item)
            elif isinstance(todo_item, str):
                item = CardTodoItem(todo_item)
            else:
                raise TypeError('todo_items must contain CardTodoItem, dict, or string values')

            if item.text:
                normalized.append(item)
        return normalized

    def get_todo_progress(self) -> tuple[int, int]:
        """!Return completed and total checklist counts for this card."""
        total = len(self.todo_items)
        completed = sum(1 for todo_item in self.todo_items if todo_item.completed)
        return completed, total

    def has_past_end_date(self, today: Optional[date] = None) -> bool:
        """!Return whether the card's end date is before today."""
        if self.end_date is None:
            return False
        reference = today or date.today()
        return self.end_date < reference
    
    def move_to_status(self, status: Union[Status, str]):
        """!Move card to a different status column (backward compatibility)."""
        if isinstance(status, Status):
            self.status = status
        else:
            self.column_id = status
        self.updated_at = datetime.now()
    
    def move_to_column(self, column_id: str):
        """!Move card to a different column."""
        self.column_id = column_id
        self.updated_at = datetime.now()
    
    def add_tag(self, tag: str):
        """!Add a tag to the card."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str):
        """!Remove a tag from the card."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()

    def add_note(self, text: str = "") -> CardNote:
        """!Add a timestamped note to the card."""
        note = CardNote(text)
        self.notes.append(note)
        self.updated_at = datetime.now()
        return note

    def remove_note(self, note_id: str) -> bool:
        """!Remove a note from the card by ID."""
        for index, note in enumerate(self.notes):
            if note.id == note_id:
                self.notes.pop(index)
                self.updated_at = datetime.now()
                return True
        return False

    def update_note(self, note_id: str, text: str = "") -> Optional[CardNote]:
        """!Update an existing note on the card by ID."""
        for note in self.notes:
            if note.id == note_id:
                note.text = text or ""
                self.updated_at = datetime.now()
                return note
        return None

    def add_attachment(self, name: str, relative_path: str, created_at: datetime = None) -> CardAttachment:
        """!Add a copied file attachment to the card."""
        attachment = CardAttachment(name, relative_path, created_at)
        self.attachments.append(attachment)
        self.updated_at = datetime.now()
        return attachment

    def get_attachment(self, attachment_id: str) -> Optional[CardAttachment]:
        """!Return a card attachment by ID."""
        for attachment in self.attachments:
            if attachment.id == attachment_id:
                return attachment
        return None

    def remove_attachment(self, attachment_id: str) -> Optional[CardAttachment]:
        """!Remove an attachment link from the card by ID."""
        for index, attachment in enumerate(self.attachments):
            if attachment.id == attachment_id:
                removed = self.attachments.pop(index)
                self.updated_at = datetime.now()
                return removed
        return None
    
    def to_dict(self):
        """!Convert card to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'column_id': self.column_id,
            'status': self.status.value if self.status else None,  # Backward compatibility
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'project': self.project,
            'assignee': self.assignee,
            'color': self.color,
            'card_type_id': self.card_type_id,
            'parent_id': self.parent_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'tags': self.tags,
            'notes': [note.to_dict() for note in self.notes],
            'attachments': [attachment.to_dict() for attachment in self.attachments],
            'todo_items': [todo_item.to_dict() for todo_item in self.todo_items],
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """!Create card from dictionary."""
        # Handle both new column_id format and old status format
        column_id = data.get('column_id')
        status = data.get('status')
        
        card = cls(data['title'], data['description'], Priority(data['priority']), column_id)
        card.id = data['id']
        
        # Backward compatibility
        if status and not column_id:
            card.status = Status(status)
        elif status:
            card.status = Status(status)
        
        card.created_at = datetime.fromisoformat(data['created_at'])
        card.updated_at = datetime.fromisoformat(data['updated_at'])
        card.project = data.get('project')
        card.assignee = data.get('assignee')
        card.color = data.get('color')
        card.card_type_id = data.get('card_type_id')
        card.parent_id = data.get('parent_id')
        card.start_date = date.fromisoformat(data['start_date']) if data.get('start_date') else None
        card.end_date = date.fromisoformat(data['end_date']) if data.get('end_date') else None
        card.tags = data.get('tags', [])
        card.notes = [CardNote.from_dict(note_data) for note_data in data.get('notes', [])]
        card.attachments = [CardAttachment.from_dict(item) for item in data.get('attachments', [])]
        card.todo_items = [CardTodoItem.from_dict(item) for item in data.get('todo_items', []) if item.get('text')]
        card.archived_at = datetime.fromisoformat(data['archived_at']) if data.get('archived_at') else None
        return card
    
    def __str__(self):
        """!Str."""
        priority_icon = {
            Priority.LOW: "🟢",
            Priority.MEDIUM: "🟡", 
            Priority.HIGH: "🟠",
            Priority.CRITICAL: "🔴"
        }
        
        project_info = f" [{self.project}]" if self.project else ""
        assignee_info = f" (@{self.assignee})" if self.assignee else ""
        subcard_info = " <subcard>" if self.parent_id else ""
        tags_info = f" #{', #'.join(self.tags)}" if self.tags else ""
        
        return f"{priority_icon[self.priority]} {self.title}{project_info}{assignee_info}{subcard_info}{tags_info}"


## @brief Represents a legacy fixed-status column kept for backward compatibility.
class Column:
    """!Legacy column class for backward compatibility."""
    
    def __init__(self, status: Status):
        """!Init."""
        self.status = status
        self.cards: List[Card] = []
    
    def add_card(self, card: Card):
        """!Add a card to this column."""
        card.status = self.status
        self.cards.append(card)
    
    def remove_card(self, card_id: str) -> Optional[Card]:
        """!Remove a card from this column by ID."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                return self.cards.pop(i)
        return None
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """!Get a card from this column by ID."""
        for card in self.cards:
            if card.id == card_id:
                return card
        return None
    
    def __len__(self):
        """!Len."""
        return len(self.cards)
    
    def __iter__(self):
        """!Iter."""
        return iter(self.cards)