## @file
#  @brief Shared enums and data objects for boards, cards, and columns.
"""Data models for the Kanban board application."""

from datetime import datetime
from typing import List, Optional, Union
from enum import Enum
import uuid


## @brief Enumerates supported card priority values.
class Priority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


## @brief Enumerates legacy board status columns.
class Status(Enum):
    """Default task status options (for backward compatibility)."""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"


## @brief Represents a configurable board column with custom ordering and color.
class CustomColumn:
    """Represents a custom column on the Kanban board."""
    
    def __init__(self, column_id: str, name: str, position: int = 0, color: str = "#2196F3"):
        self.id = column_id if column_id else str(uuid.uuid4())
        self.name = name
        self.position = position
        self.color = color
        self.cards: List['Card'] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_card(self, card: 'Card'):
        """Add a card to this column."""
        card.column_id = self.id
        self.cards.append(card)
        self.updated_at = datetime.now()
    
    def remove_card(self, card_id: str) -> Optional['Card']:
        """Remove a card from this column by ID."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                removed_card = self.cards.pop(i)
                self.updated_at = datetime.now()
                return removed_card
        return None
    
    def get_card(self, card_id: str) -> Optional['Card']:
        """Get a card from this column by ID."""
        for card in self.cards:
            if card.id == card_id:
                return card
        return None
    
    def rename(self, new_name: str):
        """Rename the column."""
        self.name = new_name
        self.updated_at = datetime.now()
    
    def change_color(self, new_color: str):
        """Change the column color."""
        self.color = new_color
        self.updated_at = datetime.now()
    
    def reposition(self, new_position: int):
        """Change the column position."""
        self.position = new_position
        self.updated_at = datetime.now()
    
    def to_dict(self):
        """Convert column to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'color': self.color,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create column from dictionary."""
        column = cls(data['id'], data['name'], data.get('position', 0), data.get('color', '#2196F3'))
        column.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        column.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        return column
    
    def __len__(self):
        return len(self.cards)
    
    def __iter__(self):
        return iter(self.cards)
    
    def __str__(self):
        return f"{self.name} ({len(self.cards)} cards)"


## @brief Represents an individual task card tracked on the board.
class Card:
    """Represents a single task card on the Kanban board."""
    
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.MEDIUM, 
                 column_id: str = None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.priority = priority
        self.column_id = column_id  # Use column_id instead of fixed status
        self.status = None  # Keep for backward compatibility
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.assignee = None
        self.tags = []
    
    def update(self, title: str = None, description: str = None, 
               priority: Priority = None, assignee: str = None):
        """Update card properties."""
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if priority is not None:
            self.priority = priority
        if assignee is not None:
            self.assignee = assignee
        self.updated_at = datetime.now()
    
    def move_to_status(self, status: Union[Status, str]):
        """Move card to a different status column (backward compatibility)."""
        if isinstance(status, Status):
            self.status = status
        else:
            self.column_id = status
        self.updated_at = datetime.now()
    
    def move_to_column(self, column_id: str):
        """Move card to a different column."""
        self.column_id = column_id
        self.updated_at = datetime.now()
    
    def add_tag(self, tag: str):
        """Add a tag to the card."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str):
        """Remove a tag from the card."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def to_dict(self):
        """Convert card to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'column_id': self.column_id,
            'status': self.status.value if self.status else None,  # Backward compatibility
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'assignee': self.assignee,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create card from dictionary."""
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
        card.assignee = data.get('assignee')
        card.tags = data.get('tags', [])
        return card
    
    def __str__(self):
        priority_icon = {
            Priority.LOW: "🟢",
            Priority.MEDIUM: "🟡", 
            Priority.HIGH: "🟠",
            Priority.CRITICAL: "🔴"
        }
        
        assignee_info = f" (@{self.assignee})" if self.assignee else ""
        tags_info = f" #{', #'.join(self.tags)}" if self.tags else ""
        
        return f"{priority_icon[self.priority]} {self.title}{assignee_info}{tags_info}"


## @brief Represents a legacy fixed-status column kept for backward compatibility.
class Column:
    """Legacy column class for backward compatibility."""
    
    def __init__(self, status: Status):
        self.status = status
        self.cards: List[Card] = []
    
    def add_card(self, card: Card):
        """Add a card to this column."""
        card.status = self.status
        self.cards.append(card)
    
    def remove_card(self, card_id: str) -> Optional[Card]:
        """Remove a card from this column by ID."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                return self.cards.pop(i)
        return None
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """Get a card from this column by ID."""
        for card in self.cards:
            if card.id == card_id:
                return card
        return None
    
    def __len__(self):
        return len(self.cards)
    
    def __iter__(self):
        return iter(self.cards)