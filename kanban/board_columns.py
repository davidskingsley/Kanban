## @file
#  @brief Column-related mixins for the board domain.
"""!Column-related mixins for the board domain."""

from __future__ import annotations

import uuid
from typing import List, Optional, Union

from .models import UNSET, Card, Column, CustomColumn


class BoardColumnsMixin:
    """!Column and layout helpers for a Kanban board."""

    def create_column(self, name: str, position: int = None, color: str = '#2196F3',
                      is_completed: bool = False, can_add_card: bool = False) -> str:
        """!Create column."""
        self._ensure_writable()

        if not self.use_custom_columns:
            raise ValueError('Custom columns not enabled for this board')

        if position is None:
            position = len(self.custom_columns)

        self._push_undo_state(f"Create column '{name}'")

        column_id = str(uuid.uuid4())
        column = CustomColumn(column_id, name, position, color, is_completed, can_add_card)
        self.custom_columns[column_id] = column
        self._adjust_column_positions()
        self.save_board()
        return column_id

    def rename_column(self, column_id: str, new_name: str) -> bool:
        """!Rename column."""
        self._ensure_writable()

        if not self.use_custom_columns or column_id not in self.custom_columns:
            return False

        self._push_undo_state(f"Rename column '{self.custom_columns[column_id].name}'")
        self.custom_columns[column_id].rename(new_name)
        self.save_board()
        return True

    def update_column(self, column_id: str, name: str = None, color: str = None,
                      is_completed=UNSET, can_add_card=UNSET) -> bool:
        """!Update column."""
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
        """!Delete column."""
        self._ensure_writable()

        if not self.use_custom_columns or column_id not in self.custom_columns:
            return False
        if len(self.custom_columns) <= 1:
            return False

        column = self.custom_columns[column_id]
        self._push_undo_state(f"Delete column '{column.name}'")

        if move_cards_to and move_cards_to in self.custom_columns:
            target_column = self.custom_columns[move_cards_to]
            for card in column.cards:
                card.move_to_column(move_cards_to)
                target_column.add_card(card)
        elif column.cards:
            first_column_id = next(iter(self.custom_columns.keys()))
            if first_column_id != column_id:
                target_column = self.custom_columns[first_column_id]
                for card in column.cards:
                    card.move_to_column(first_column_id)
                    target_column.add_card(card)

        del self.custom_columns[column_id]
        self._adjust_column_positions()
        self.save_board()
        return True

    def reorder_columns(self, column_order: List[str]) -> bool:
        """!Reorder columns."""
        self._ensure_writable()

        if not self.use_custom_columns:
            return False
        if set(column_order) != set(self.custom_columns.keys()):
            return False

        self._push_undo_state('Reorder columns')
        for index, column_id in enumerate(column_order):
            self.custom_columns[column_id].reposition(index)

        self.save_board()
        return True

    def change_column_color(self, column_id: str, color: str) -> bool:
        """!Change column color."""
        self._ensure_writable()

        if not self.use_custom_columns or column_id not in self.custom_columns:
            return False

        self._push_undo_state(f"Change color of column '{self.custom_columns[column_id].name}'")
        self.custom_columns[column_id].change_color(color)
        self.save_board()
        return True

    def get_columns_ordered(self) -> List[Union[CustomColumn, Column]]:
        """!Get columns ordered."""
        return sorted(self.custom_columns.values(), key=lambda col: col.position)

    def get_column_by_id(self, column_id: str) -> Optional[CustomColumn]:
        """!Get column by id."""
        return self.custom_columns.get(column_id)

    def _adjust_column_positions(self):
        """!Adjust column positions."""
        ordered_columns = sorted(self.custom_columns.values(), key=lambda col: col.position)
        for index, column in enumerate(ordered_columns):
            column.position = index

    def _get_first_column_id(self) -> Optional[str]:
        """!Get first column id."""
        if not self.custom_columns:
            return None
        return min(self.custom_columns.keys(), key=lambda cid: self.custom_columns[cid].position)

    def get_default_add_card_column_id(self) -> Optional[str]:
        """!Get default add card column id."""
        if not self.use_custom_columns:
            return None

        ordered_columns = self.get_columns_ordered()
        for column in ordered_columns:
            if column.can_add_card:
                return column.id
        return ordered_columns[0].id if ordered_columns else None

    def get_subcard_target(self, parent_card: Card):
        """!Get subcard target."""
        if not self.use_custom_columns:
            return parent_card.status

        parent_column = self.get_column_by_id(parent_card.column_id)
        if parent_column is not None and parent_column.can_add_card:
            return parent_column.id

        return self._get_first_column_id() or parent_card.column_id