## @file
#  @brief Project and card-type mixins for the board domain.
"""!Project and card-type mixins for the board domain."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .models import UNSET, CardType, Project


class BoardCatalogMixin:
    """!Project and card-type helpers for a Kanban board."""

    def _ensure_default_card_type(self):
        """!Ensure default card type."""
        default_type = next((card_type for card_type in self.card_types.values() if card_type.name == self.DEFAULT_CARD_TYPE_NAME), None)
        if default_type is None:
            default_type = CardType(self.DEFAULT_CARD_TYPE_NAME, 'Standard card type')
            self.card_types[default_type.id] = default_type
        return default_type

    def get_default_card_type(self) -> CardType:
        """!Get default card type."""
        return self._ensure_default_card_type()

    def get_default_card_type_id(self) -> str:
        """!Get default card type id."""
        return self.get_default_card_type().id

    def get_card_type(self, card_type_id: str) -> Optional[CardType]:
        """!Get card type."""
        return self.card_types.get(card_type_id)

    def get_card_types_ordered(self) -> List[CardType]:
        """!Get card types ordered."""
        default_type = self.get_default_card_type()
        other_types = [card_type for card_type in self.card_types.values() if card_type.id != default_type.id]
        other_types.sort(key=lambda card_type: card_type.name.lower())
        return [default_type] + other_types

    def get_project(self, project_id: str) -> Optional[Project]:
        """!Get project."""
        return self.projects.get(project_id)

    def get_project_by_name(self, name: Optional[str]) -> Optional[Project]:
        """!Get project by name."""
        normalized_name = (name or '').strip().lower()
        if not normalized_name:
            return None
        return next((project for project in self.projects.values() if project.name.strip().lower() == normalized_name), None)

    def get_projects_ordered(self) -> List[Project]:
        """!Get projects ordered."""
        return sorted(self.projects.values(), key=lambda project: project.name.lower())

    def _project_name_matches(self, value: Optional[str], project_name: str) -> bool:
        """!Project name matches."""
        return bool(value and value.strip().lower() == project_name.strip().lower())

    def _ensure_project_exists(self, project_name: Optional[str], description: str = '') -> Optional[Project]:
        """!Ensure project exists."""
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
        """!Sync projects from references."""
        for card_type in self.card_types.values():
            self._ensure_project_exists(card_type.default_project)
        for card in self.get_all_cards():
            self._ensure_project_exists(card.project)

    def create_project(self, name: str, description: str = '') -> str:
        """!Create project."""
        self._ensure_writable()
        name = (name or '').strip()
        if not name:
            raise ValueError('Project name is required')
        if self.get_project_by_name(name) is not None:
            raise ValueError('A project with that name already exists')

        self._push_undo_state(f"Create project '{name}'")
        project = Project(name, description)
        self.projects[project.id] = project
        self._record_action(f"Created project '{name}'.")
        self.save_board()
        return project.id

    def edit_project(self, project_id: str, name: str = None, description: str = None) -> Optional[Project]:
        """!Edit project."""
        self._ensure_writable()
        project = self.get_project(project_id)
        if project is None:
            return None

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError('Project name is required')
            duplicate = next((existing for existing in self.projects.values() if existing.id != project_id and existing.name.lower() == name.lower()), None)
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

        self._record_action(f"Edited project '{project.name}'.")
        self.save_board()
        return project

    def get_cards_by_project(self, project_id: str):
        """!Get cards by project."""
        project = self.get_project(project_id)
        if project is None:
            return []
        return [card for card in self.get_all_cards() if self._project_name_matches(card.project, project.name)]

    def get_card_types_by_project(self, project_id: str):
        """!Get card types by project."""
        project = self.get_project(project_id)
        if project is None:
            return []
        return [card_type for card_type in self.card_types.values() if self._project_name_matches(card_type.default_project, project.name)]

    def delete_project(self, project_id: str, delete_cards: bool = False, replacement_project_id: str = None) -> bool:
        """!Delete project."""
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
        self._record_action(f"Deleted project '{project.name}'.")
        self.save_board()
        return True

    def get_last_used_card_type(self) -> CardType:
        """!Get last used card type."""
        card_type = self.get_card_type(self.last_used_card_type_id)
        if card_type is None:
            card_type = self.get_default_card_type()
            self.last_used_card_type_id = card_type.id
        return card_type

    def _resolve_card_type(self, card_type_id: str = None) -> CardType:
        """!Resolve card type."""
        if card_type_id:
            card_type = self.get_card_type(card_type_id)
            if card_type is None:
                raise ValueError('Card type does not exist')
            return card_type
        return self.get_last_used_card_type()

    def create_card_type(self, name: str, description: str = '', default_project: str = None, default_color: str = None) -> str:
        """!Create card type."""
        self._ensure_writable()
        name = (name or '').strip()
        if not name:
            raise ValueError('Card type name is required')
        if any(card_type.name.lower() == name.lower() for card_type in self.card_types.values()):
            raise ValueError('A card type with that name already exists')

        self._push_undo_state(f"Create card type '{name}'")
        card_type = CardType(name, description, default_project, default_color)
        self.card_types[card_type.id] = card_type
        self._ensure_project_exists(default_project)
        self.last_used_card_type_id = card_type.id
        self._record_action(f"Created card type '{name}'.")
        self.save_board()
        return card_type.id

    def edit_card_type(self, card_type_id: str, name: str = None, description: str = None, default_project=UNSET, default_color=UNSET) -> Optional[CardType]:
        """!Edit card type."""
        self._ensure_writable()
        card_type = self.get_card_type(card_type_id)
        if card_type is None:
            return None

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError('Card type name is required')
            duplicate = next((existing for existing in self.card_types.values() if existing.id != card_type_id and existing.name.lower() == name.lower()), None)
            if duplicate is not None:
                raise ValueError('A card type with that name already exists')
            if card_type_id == self.get_default_card_type_id() and name != self.DEFAULT_CARD_TYPE_NAME:
                raise ValueError('The default card type name cannot be changed')

        self._push_undo_state(f"Edit card type '{card_type.name}'")
        card_type.update(name, description, default_project, default_color)
        if default_project is not UNSET:
            self._ensure_project_exists(card_type.default_project)
        self._record_action(f"Edited card type '{card_type.name}'.")
        self.save_board()
        return card_type

    def get_cards_by_type(self, card_type_id: str):
        """!Get cards by type."""
        return [card for card in self.get_all_cards() if card.card_type_id == card_type_id]

    def delete_card_type(self, card_type_id: str, delete_cards: bool = False, replacement_type_id: str = None) -> bool:
        """!Delete card type."""
        self._ensure_writable()
        card_type = self.get_card_type(card_type_id)
        if card_type is None:
            return False
        if card_type_id == self.get_default_card_type_id():
            raise ValueError('The default card type cannot be deleted')

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
                raise ValueError('Replacement card type must be different')
            for card in cards:
                card.update(card_type_id=replacement_type.id)

        del self.card_types[card_type_id]
        if self.last_used_card_type_id == card_type_id:
            self.last_used_card_type_id = replacement_type.id if not delete_cards else self.get_default_card_type_id()
        self._record_action(f"Deleted card type '{card_type.name}'.")
        self.save_board()
        return True