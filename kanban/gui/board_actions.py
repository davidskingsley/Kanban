## @file
#  @brief Board and card action mixins for the PySide6 GUI.
"""!Board and card action mixins for the PySide6 GUI."""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox

from ..board import KanbanBoard
from ..models import CardType, Project
from .board_statistics import BoardStatisticsDialog
from .common import (
	column_identifier,
	column_label,
	column_target_value,
)
from .dialogs import (
	AboutDialog,
	ArchivedCardsDialog,
	BoardDialog,
	CardDialog,
	CardTypeDialog,
	CardTypesBrowserDialog,
	ColumnDialog,
	CommandLineGuideDialog,
	DirectActionCliOptionsDialog,
	DueDateViewDialog,
	ProjectDialog,
	ProjectsBrowserDialog,
	ReorderColumnsDialog,
)


class BoardActionsMixin:
	"""!Board, card, project, and dialog actions for the main GUI."""

	def _compat_gui_module(self):
		"""!Compat gui module."""
		from . import pyside_app as compat_gui_module

		return compat_gui_module

	def show_about_dialog(self):
		"""!Show about dialog."""
		dialog = AboutDialog(parent=self.window)
		dialog.exec()

	def show_command_line_guide_dialog(self):
		"""!Show command line guide dialog."""
		dialog = CommandLineGuideDialog(parent=self.window)
		dialog.exec()

	def show_direct_action_cli_options_dialog(self):
		"""!Show direct action cli options dialog."""
		dialog = DirectActionCliOptionsDialog(parent=self.window)
		dialog.exec()

	def _refresh_history_actions(self, board: Optional[KanbanBoard] = None):
		"""!Refresh history actions."""
		current_board = board if board is not None else self.current_board()
		board_can_undo = bool(current_board and not current_board.is_read_only() and current_board.can_undo())
		board_can_redo = bool(current_board and not current_board.is_read_only() and current_board.can_redo())

		undo_board_description = current_board.get_next_undo_description() if board_can_undo else None
		redo_board_description = current_board.get_next_redo_description() if board_can_redo else None
		undo_manager_description = self.board_manager.get_next_undo_description()
		redo_manager_description = self.board_manager.get_next_redo_description()

		self.undo_current_board_qaction.setText(self._history_action_text('Undo Current Board Action', undo_board_description))
		self.redo_current_board_qaction.setText(self._history_action_text('Redo Current Board Action', redo_board_description))
		self.undo_board_management_qaction.setText(self._history_action_text('Undo Board Management Action', undo_manager_description))
		self.redo_board_management_qaction.setText(self._history_action_text('Redo Board Management Action', redo_manager_description))

		self.undo_current_board_qaction.setEnabled(board_can_undo)
		self.redo_current_board_qaction.setEnabled(board_can_redo)
		self.undo_board_management_qaction.setEnabled(self.board_manager.can_undo())
		self.redo_board_management_qaction.setEnabled(self.board_manager.can_redo())

		self.undo_current_board_qaction.setStatusTip(undo_board_description or 'Undo the most recent change on the current board')
		self.redo_current_board_qaction.setStatusTip(redo_board_description or 'Redo the most recently undone change on the current board')
		self.undo_board_management_qaction.setStatusTip(undo_manager_description or 'Undo the most recent board-management change')
		self.redo_board_management_qaction.setStatusTip(redo_manager_description or 'Redo the most recently undone board-management change')

	def _show_history_feedback(self, message: str, timeout_ms: int = 4000):
		"""!Show history feedback."""
		self.window.statusBar().showMessage(message, timeout_ms)

	def _run_current_board_history_action(self, method_name: str, unavailable_message: str, success_prefix: str):
		"""!Run current board history action."""
		board = self.ensure_writable_board()
		if board is None:
			return

		action = getattr(board, method_name, None)
		if action is None:
			QMessageBox.warning(self.window, 'History Unavailable', 'That action is not available for the current board.')
			return

		description = action()
		if not description:
			self._show_history_feedback(unavailable_message)
			self.refresh_ui()
			return

		self.refresh_ui()
		self._show_history_feedback(f'{success_prefix}: {description}')

	def undo_current_board_action(self):
		"""!Undo current board action."""
		self._run_current_board_history_action('undo_last_action', 'No board action is available to undo.', 'Undid')

	def redo_current_board_action(self):
		"""!Redo current board action."""
		self._run_current_board_history_action('redo_last_action', 'No board action is available to redo.', 'Redid')

	def _run_board_management_history_action(self, method_name: str, unavailable_message: str, success_prefix: str):
		"""!Run board management history action."""
		action = getattr(self.board_manager, method_name)
		description = action()
		if not description:
			self._show_history_feedback(unavailable_message)
			self.refresh_ui()
			return

		current_board_id = self.board_manager.current_board_id
		if current_board_id:
			self._remember_recent_board(current_board_id)
		self.refresh_ui()
		self._show_history_feedback(f'{success_prefix}: {description}')

	def undo_board_management_action(self):
		"""!Undo board management action."""
		self._run_board_management_history_action('undo_last_action', 'No board-management action is available to undo.', 'Undid')

	def redo_board_management_action(self):
		"""!Redo board management action."""
		self._run_board_management_history_action('redo_last_action', 'No board-management action is available to redo.', 'Redid')

	def prompt_for_locked_board_action(self, file_path: str, lock_details: dict) -> str:
		"""!Prompt for locked board action."""
		dialog = QMessageBox(self.window)
		dialog.setIcon(QMessageBox.Icon.Warning)
		dialog.setWindowTitle('Board Locked')
		message = ['This board is locked.', '', f'File: {file_path}']
		if lock_details:
			message.append(f"Host: {lock_details.get('hostname', 'unknown')}")
			message.append(f"Opened: {lock_details.get('opened_at', 'unknown')}")
		message.extend(['', 'Choose how to continue.'])
		dialog.setText('\n'.join(message))
		read_only_button = dialog.addButton('Open Read Only', QMessageBox.ButtonRole.AcceptRole)
		delete_button = dialog.addButton('Delete Lock', QMessageBox.ButtonRole.DestructiveRole)
		dialog.addButton(QMessageBox.StandardButton.Cancel)
		dialog.exec()
		clicked = dialog.clickedButton()
		if clicked == read_only_button:
			return 'open_read_only'
		if clicked == delete_button:
			return 'delete_lock'
		return 'cancel'

	def create_board(self):
		"""!Create board."""
		dialog = BoardDialog(self.board_manager.boards_directory, self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		board_id = self.board_manager.create_board(
			values['name'],
			values['description'],
			target_directory=values['storage_dir'],
			storage_backend=values['storage_backend'],
		)
		self._switch_board_by_id(board_id)

	def rename_current_board(self):
		"""!Rename current board."""
		boards = self.board_manager.get_board_list()
		current = next((board for board in boards if board['is_current']), None)
		if current is None:
			return
		new_name, ok = QInputDialog.getText(self.window, 'Rename Board', 'New name', text=current['name'])
		if ok and new_name.strip():
			self.board_manager.rename_board(current['id'], new_name.strip())
			self.refresh_ui()

	def convert_current_board_backend(self):
		"""!Convert current board backend."""
		boards = self.board_manager.get_board_list()
		current = next((board for board in boards if board['is_current']), None)
		if current is None:
			return

		current_backend = current.get('storage_backend', 'json')
		option_map = {
			'Current JSON File': 'json',
			'SQLite3 Backend': 'sqlite',
		}
		available_options = [label for label, backend in option_map.items() if backend != current_backend]
		selected, ok = QInputDialog.getItem(
			self.window,
			'Convert Board Backend',
			f"Current backend: {current_backend}\nConvert to",
			available_options,
			editable=False,
		)
		if not ok or not selected:
			return

		target_backend = option_map[selected]
		try:
			target_file = self.board_manager.convert_board_storage_backend(current['id'], target_backend)
		except Exception as error:
			QMessageBox.warning(self.window, 'Convert Board Backend', str(error))
			return

		QMessageBox.information(
			self.window,
			'Convert Board Backend',
			f"Converted '{current['name']}' to {target_backend}.\n\nNew file: {target_file}",
		)
		self.refresh_ui()

	def delete_current_board(self):
		"""!Delete current board."""
		boards = self.board_manager.get_board_list()
		current = next((board for board in boards if board['is_current']), None)
		if current is None:
			return
		result = QMessageBox.question(
			self.window,
			'Delete Board',
			f"Delete board '{current['name']}'?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result == QMessageBox.StandardButton.Yes:
			self.board_manager.delete_board(current['id'])
			self.refresh_ui()

	def show_board_statistics(self):
		"""!Show board statistics."""
		board = self.ensure_board()
		if board is None:
			return
		dialog = BoardStatisticsDialog(board, self._current_board_name(), self.window)
		dialog.exec()

	def _choose_card_type(
		self,
		board: KanbanBoard,
		title: str,
		prompt: str,
		exclude_default: bool = False,
		exclude_ids: Optional[set[str]] = None,
	) -> Optional[CardType]:
		"""!Choose card type."""
		exclude_ids = set(exclude_ids or set())
		card_types = [
			card_type
			for card_type in board.get_card_types_ordered()
			if (not exclude_default or card_type.id != board.get_default_card_type_id()) and card_type.id not in exclude_ids
		]
		if not card_types:
			QMessageBox.information(self.window, title, 'No card types available.')
			return None

		option_map: Dict[str, CardType] = {}
		for card_type in card_types:
			label = card_type.name
			if card_type.id == board.get_default_card_type_id():
				label += ' [default]'
			if card_type.id == board.get_last_used_card_type().id:
				label += ' [last used]'
			option_map[label] = card_type

		selected, ok = QInputDialog.getItem(self.window, title, prompt, list(option_map.keys()), editable=False)
		if not ok or not selected:
			return None
		return option_map[selected]

	def show_card_types_browser(self):
		"""!Show card types browser."""
		board = self.ensure_board()
		if board is None:
			return
		dialog = CardTypesBrowserDialog(board, self.window)
		if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_card_type_id:
			self.edit_card_type_by_id(dialog.selected_card_type_id)

	def create_card_type(self):
		"""!Create card type."""
		board = self.ensure_writable_board()
		if board is None:
			return
		dialog = CardTypeDialog(board=board, parent=self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		try:
			board.create_card_type(
				values['name'],
				values['description'],
				values['default_project'],
				values['default_color'],
			)
		except ValueError as error:
			QMessageBox.warning(self.window, 'Create Card Type', str(error))
			return
		self.refresh_ui()

	def edit_card_type(self):
		"""!Edit card type."""
		board = self.ensure_writable_board()
		if board is None:
			return
		card_type = self._choose_card_type(board, 'Edit Card Type', 'Card type')
		if card_type is None:
			return
		self._edit_card_type(board, card_type)

	def edit_card_type_by_id(self, card_type_id: str):
		"""!Edit card type by id."""
		board = self.ensure_writable_board()
		if board is None:
			return
		card_type = next((item for item in board.get_card_types_ordered() if item.id == card_type_id), None)
		if card_type is None:
			QMessageBox.information(self.window, 'Card Type', 'The selected card type no longer exists.')
			return
		self._edit_card_type(board, card_type)

	def _edit_card_type(self, board: KanbanBoard, card_type: CardType):
		"""!Edit card type."""
		is_default = card_type.id == board.get_default_card_type_id()
		dialog = CardTypeDialog(card_type=card_type, is_default=is_default, board=board, parent=self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		try:
			board.edit_card_type(
				card_type.id,
				None if is_default else values['name'],
				values['description'],
				default_project=values['default_project'],
				default_color=values['default_color'],
			)
		except ValueError as error:
			QMessageBox.warning(self.window, 'Edit Card Type', str(error))
			return
		self.refresh_ui()

	def delete_card_type(self):
		"""!Delete card type."""
		board = self.ensure_writable_board()
		if board is None:
			return
		card_type = self._choose_card_type(board, 'Delete Card Type', 'Card type', exclude_default=True)
		if card_type is None:
			return

		cards_using_type = board.get_cards_by_type(card_type.id)
		if not cards_using_type:
			result = QMessageBox.question(
				self.window,
				'Delete Card Type',
				f"Delete card type '{card_type.name}'?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			)
			if result != QMessageBox.StandardButton.Yes:
				return
			try:
				board.delete_card_type(card_type.id, delete_cards=False)
			except ValueError as error:
				QMessageBox.warning(self.window, 'Delete Card Type', str(error))
				return
			self.refresh_ui()
			return

		dialog = QMessageBox(self.window)
		dialog.setWindowTitle('Delete Card Type')
		dialog.setIcon(QMessageBox.Icon.Warning)
		dialog.setText(
			f"Card type '{card_type.name}' is used by {len(cards_using_type)} card(s). Choose what to do with those cards."
		)
		reassign_button = dialog.addButton('Reassign Cards', QMessageBox.ButtonRole.AcceptRole)
		delete_cards_button = dialog.addButton('Delete Cards', QMessageBox.ButtonRole.DestructiveRole)
		dialog.addButton(QMessageBox.StandardButton.Cancel)
		dialog.exec()

		clicked = dialog.clickedButton()
		if clicked == reassign_button:
			replacement = self._choose_card_type(
				board,
				'Replacement Card Type',
				'Reassign cards to',
				exclude_ids={card_type.id},
			)
			if replacement is None:
				return
			try:
				board.delete_card_type(card_type.id, delete_cards=False, replacement_type_id=replacement.id)
			except ValueError as error:
				QMessageBox.warning(self.window, 'Delete Card Type', str(error))
				return
			self.refresh_ui()
			return

		if clicked == delete_cards_button:
			confirm = QMessageBox.question(
				self.window,
				'Delete Cards',
				f"Delete card type '{card_type.name}' and all {len(cards_using_type)} card(s) using it?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			)
			if confirm != QMessageBox.StandardButton.Yes:
				return
			try:
				board.delete_card_type(card_type.id, delete_cards=True)
			except ValueError as error:
				QMessageBox.warning(self.window, 'Delete Card Type', str(error))
				return
			self.refresh_ui()

	def _choose_project(
		self,
		board: KanbanBoard,
		title: str,
		prompt: str,
		exclude_ids: Optional[set[str]] = None,
	) -> Optional[Project]:
		"""!Choose project."""
		exclude_ids = set(exclude_ids or set())
		projects = [project for project in board.get_projects_ordered() if project.id not in exclude_ids]
		if not projects:
			QMessageBox.information(self.window, title, 'No projects available.')
			return None

		option_map: Dict[str, Project] = {}
		for project in projects:
			option_map[project.name] = project

		selected, ok = QInputDialog.getItem(self.window, title, prompt, list(option_map.keys()), editable=False)
		if not ok or not selected:
			return None
		return option_map[selected]

	def show_projects_browser(self):
		"""!Show projects browser."""
		board = self.ensure_board()
		if board is None:
			return
		dialog = ProjectsBrowserDialog(board, self.window)
		if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_project_id:
			self.edit_project_by_id(dialog.selected_project_id)

	def create_project(self):
		"""!Create project."""
		board = self.ensure_writable_board()
		if board is None:
			return
		dialog = ProjectDialog(parent=self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		try:
			board.create_project(values['name'], values['description'])
		except ValueError as error:
			QMessageBox.warning(self.window, 'Create Project', str(error))
			return
		self.refresh_ui()

	def edit_project(self):
		"""!Edit project."""
		board = self.ensure_writable_board()
		if board is None:
			return
		project = self._choose_project(board, 'Edit Project', 'Project')
		if project is None:
			return
		self._edit_project(board, project)

	def edit_project_by_id(self, project_id: str):
		"""!Edit project by id."""
		board = self.ensure_writable_board()
		if board is None:
			return
		project = board.get_project(project_id)
		if project is None:
			QMessageBox.information(self.window, 'Project', 'The selected project no longer exists.')
			return
		self._edit_project(board, project)

	def _edit_project(self, board: KanbanBoard, project: Project):
		"""!Edit project."""
		dialog = ProjectDialog(project=project, parent=self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		try:
			board.edit_project(project.id, values['name'], values['description'])
		except ValueError as error:
			QMessageBox.warning(self.window, 'Edit Project', str(error))
			return
		self.refresh_ui()

	def delete_project(self):
		"""!Delete project."""
		board = self.ensure_writable_board()
		if board is None:
			return
		project = self._choose_project(board, 'Delete Project', 'Project')
		if project is None:
			return

		cards_using_project = board.get_cards_by_project(project.id)
		card_types_using_project = board.get_card_types_by_project(project.id)
		if not cards_using_project and not card_types_using_project:
			result = QMessageBox.question(
				self.window,
				'Delete Project',
				f"Delete project '{project.name}'?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			)
			if result != QMessageBox.StandardButton.Yes:
				return
			try:
				board.delete_project(project.id, delete_cards=False)
			except ValueError as error:
				QMessageBox.warning(self.window, 'Delete Project', str(error))
				return
			self.refresh_ui()
			return

		dialog = QMessageBox(self.window)
		dialog.setWindowTitle('Delete Project')
		dialog.setIcon(QMessageBox.Icon.Warning)
		dialog.setText(
			f"Project '{project.name}' is used by {len(cards_using_project)} card(s) and {len(card_types_using_project)} card type preset(s). Choose what to do with those references."
		)
		reassign_button = dialog.addButton('Reassign References', QMessageBox.ButtonRole.AcceptRole)
		clear_references_button = dialog.addButton('Clear References', QMessageBox.ButtonRole.ActionRole)
		delete_cards_button = dialog.addButton('Delete Cards', QMessageBox.ButtonRole.DestructiveRole)
		dialog.addButton(QMessageBox.StandardButton.Cancel)
		dialog.exec()

		clicked = dialog.clickedButton()
		if clicked == reassign_button:
			replacement = self._choose_project(
				board,
				'Replacement Project',
				'Reassign references to',
				exclude_ids={project.id},
			)
			if replacement is None:
				return
			try:
				board.delete_project(project.id, delete_cards=False, replacement_project_id=replacement.id)
			except ValueError as error:
				QMessageBox.warning(self.window, 'Delete Project', str(error))
				return
			self.refresh_ui()
			return

		if clicked == clear_references_button:
			try:
				board.delete_project(project.id, delete_cards=False)
			except ValueError as error:
				QMessageBox.warning(self.window, 'Delete Project', str(error))
				return
			self.refresh_ui()
			return

		if clicked == delete_cards_button:
			confirm = QMessageBox.question(
				self.window,
				'Delete Cards',
				f"Delete project '{project.name}' and all {len(cards_using_project)} card(s) using it? Card type presets will be cleared.",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			)
			if confirm != QMessageBox.StandardButton.Yes:
				return
			try:
				board.delete_project(project.id, delete_cards=True)
			except ValueError as error:
				QMessageBox.warning(self.window, 'Delete Project', str(error))
				return
			self.refresh_ui()

	def show_due_date_view(self):
		"""!Show due date view."""
		board = self.ensure_board()
		if board is None:
			return

		dialog = DueDateViewDialog(
			board,
			self._current_board_name(),
			self.window,
			on_focus_card=self._focus_card_from_due_date_view,
			on_edit_card=self._edit_card_from_due_date_view,
		)
		dialog.exec()

	def _focus_card_from_due_date_view(self, card_id: str, column_id: Optional[str]):
		"""!Focus card from due date view."""
		self.selected_column_id = column_id
		self.selected_card_id = card_id
		self.refresh_ui()

	def _edit_card_from_due_date_view(self, card_id: str, column_id: Optional[str]):
		"""!Edit card from due date view."""
		self.selected_column_id = column_id
		self.selected_card_id = card_id
		self.edit_selected_card()

	def export_all_boards(self):
		"""!Export all boards."""
		compat = self._compat_gui_module()
		file_name = compat.choose_save_file_dialog(self.window, 'Export All Boards', 'kanban_backup.json', 'JSON Files (*.json)')
		if not file_name:
			return
		export_data = self.board_manager.export_all_boards()
		with open(file_name, 'w', encoding='utf-8') as output_file:
			json.dump(export_data, output_file, indent=2, ensure_ascii=False)
		QMessageBox.information(self.window, 'Export Complete', f'Exported boards to {file_name}.')

	def export_current_board(self):
		"""!Export current board."""
		board = self.ensure_board()
		if board is None:
			return

		suggested_name = ''.join(c.lower() if c.isalnum() else '_' for c in self._current_board_name()).strip('_') or 'board'
		compat = self._compat_gui_module()
		file_name = compat.choose_save_file_dialog(
			self.window,
			'Export Current Board',
			f'{suggested_name}.json',
			'JSON Files (*.json)',
		)
		if not file_name:
			return

		export_data = self.board_manager.export_board_data(self.board_manager.current_board_id)
		with open(file_name, 'w', encoding='utf-8') as output_file:
			json.dump(export_data, output_file, indent=2, ensure_ascii=False)
		QMessageBox.information(self.window, 'Export Complete', f'Exported current board to {file_name}.')

	def import_boards(self):
		"""!Import boards."""
		compat = self._compat_gui_module()
		file_name = compat.choose_open_file_dialog(self.window, 'Import Boards', '', 'JSON Files (*.json)')
		if not file_name:
			return
		result = QMessageBox.question(
			self.window,
			'Import Boards',
			'Importing will replace the current board registry. Continue?',
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result != QMessageBox.StandardButton.Yes:
			return
		with open(file_name, 'r', encoding='utf-8') as input_file:
			import_data = json.load(input_file)
		if self.board_manager.import_boards(import_data):
			self.refresh_ui()

	def _discover_boards_in_folder(self, folder: str) -> Dict[str, Dict[str, object]]:
		"""!Discover boards in folder."""
		option_map: Dict[str, Dict[str, object]] = {}
		metadata_path = os.path.join(folder, 'boards_metadata.json')
		if os.path.exists(metadata_path):
			with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
				metadata = json.load(metadata_file)
			for board_id, board_info in metadata.get('boards', {}).items():
				if board_info.get('use_custom_columns') is False:
					continue
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
					'storage_backend': board_info.get('storage_backend'),
				}
		else:
			for entry in sorted(os.listdir(folder)):
				candidate_path = os.path.join(folder, entry)
				if entry == 'boards_metadata.json' or os.path.isdir(candidate_path) or '.backup.' in entry.lower():
					continue
				try:
					inspected = self.board_manager.inspect_board_file(candidate_path)
				except ValueError:
					continue
				label = inspected['name']
				if label in option_map:
					label = f"{label} ({entry})"
				option_map[label] = {
					'data_file': inspected['data_file'],
					'name': inspected['name'],
					'description': '',
					'storage_backend': inspected.get('storage_backend'),
				}
		return option_map

	def load_board_from_folder(self):
		"""!Load board from folder."""
		compat = self._compat_gui_module()
		folder = compat.choose_existing_directory_dialog(self.window, 'Select Folder Containing a Board')
		if not folder:
			return
		option_map = self._discover_boards_in_folder(folder)
		if not option_map:
			QMessageBox.information(self.window, 'No Boards Found', 'No board files were found in the selected folder.')
			return
		options = list(option_map.keys())
		selected, ok = QInputDialog.getItem(self.window, 'Load Board From Folder', 'Board', options, editable=False)
		if not ok or not selected:
			return
		board_choice = option_map[selected]
		board_id = self.board_manager.add_external_board(
			board_choice['data_file'],
			name=board_choice['name'],
			description=board_choice['description'],
			switch_to=True,
		)
		if board_id:
			self.refresh_ui()

	def create_card(self, column_id: Optional[str] = None):
		"""!Create card."""
		board = self.ensure_writable_board()
		if board is None:
			return
		target_column = column_id or self.selected_column_id or board.get_default_add_card_column_id()
		compat = self._compat_gui_module()
		dialog = compat.CardDialog(board, target_column_id=target_column, parent=self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		board.create_card(
			values['title'],
			values['description'],
			values['priority'],
			values['column_id'],
			values['project'] or None,
			values['start_date'],
			values['end_date'],
			None,
			values['color'],
			values['card_type_id'],
			values['assignee'] or None,
			values['tags'],
			values['todo_items'],
		)
		self.refresh_ui()

	def add_subcard_to_selected_card(self):
		"""!Add subcard to selected card."""
		board = self.ensure_writable_board()
		if board is None:
			return
		parent_card = self._selected_card()
		if parent_card is None:
			QMessageBox.information(self.window, 'No Card Selected', 'Select a parent card first.')
			return
		if parent_card.parent_id:
			QMessageBox.information(self.window, 'Add Subcard', 'Nested subcards are not supported.')
			return

		compat = self._compat_gui_module()
		dialog = compat.CardDialog(
			board,
			target_column_id=board.get_subcard_target(parent_card),
			parent_card=parent_card,
			parent=self.window,
		)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			if dialog.did_mutate_board:
				self.refresh_ui()
			return
		values = dialog.values()
		try:
			created = board.create_subcard(
				parent_card.id,
				values['title'],
				values['description'],
				values['priority'],
				values['project'] or None,
				values['color'],
				values['card_type_id'],
				values['start_date'],
				values['end_date'],
				values['assignee'] or None,
				values['tags'],
				values['todo_items'],
			)
		except ValueError as error:
			QMessageBox.warning(self.window, 'Add Subcard', str(error))
			return
		self.selected_card_id = created.id
		self.refresh_ui()

	def _selected_card(self):
		"""!Selected card."""
		board = self.current_board()
		if board is None or not self.selected_card_id:
			return None
		return board.find_card(self.selected_card_id)

	def edit_selected_card(self):
		"""!Edit selected card."""
		board = self.ensure_writable_board()
		if board is None:
			return
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self.window, 'No Card Selected', 'Select a card first.')
			return
		original_column_id = card.column_id
		dialog = CardDialog(board, card=card, parent=self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			if dialog.did_mutate_board:
				self.refresh_ui()
			return
		values = dialog.values()
		board.edit_card(
			card.id,
			title=values['title'],
			description=values['description'],
			priority=values['priority'],
			assignee=values['assignee'] or None,
			project=values['project'] or None,
			start_date=values['start_date'],
			end_date=values['end_date'],
			color=values['color'],
			tags=values['tags'],
			card_type_id=values['card_type_id'],
			todo_items=values['todo_items'],
		)
		if values['column_id'] != original_column_id:
			board.move_card(card.id, values['column_id'])
		self.refresh_ui()

	def delete_selected_card(self):
		"""!Delete selected card."""
		board = self.ensure_writable_board()
		if board is None:
			return
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self.window, 'No Card Selected', 'Select a card first.')
			return
		result = QMessageBox.question(
			self.window,
			'Delete Card',
			f"Delete '{card.title}'?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result == QMessageBox.StandardButton.Yes:
			board.delete_card(card.id)
			self.refresh_ui()

	def move_selected_card(self):
		"""!Move selected card."""
		board = self.ensure_writable_board()
		if board is None:
			return
		card = self._selected_card()
		if card is None:
			QMessageBox.information(self.window, 'No Card Selected', 'Select a card first.')
			return
		current_column_token = card.column_id
		choices = [
			column_label(column)
			for column in board.get_columns_ordered()
			if column_identifier(column) != current_column_token
		]
		if not choices:
			return
		selected, ok = QInputDialog.getItem(self.window, 'Move Card', 'Target Column', choices, editable=False)
		if not ok or not selected:
			return
		for column in board.get_columns_ordered():
			if column_label(column) == selected:
				board.move_card(card.id, column_target_value(column))
				self.refresh_ui()
				return

	def archive_done_cards(self):
		"""!Archive done cards."""
		board = self.ensure_writable_board()
		if board is None:
			return
		done_count = board.get_board_stats().get('done', 0)
		if done_count == 0:
			QMessageBox.information(self.window, 'Archive Done Cards', 'No active cards in completed columns to archive.')
			return
		result = QMessageBox.question(
			self.window,
			'Archive Done Cards',
			f'Archive {done_count} card(s) from completed columns?',
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result != QMessageBox.StandardButton.Yes:
			return
		archived_count = board.archive_done_cards()
		self.selected_card_id = None
		QMessageBox.information(self.window, 'Archive Done Cards', f'Archived {archived_count} card(s).')
		self.refresh_ui()

	def manage_archived_cards(self):
		"""!Manage archived cards."""
		board = self.ensure_board()
		if board is None:
			return
		dialog = ArchivedCardsDialog(board, self._current_board_name(), self.window)
		dialog.exec()
		if self.selected_card_id and board.find_card(self.selected_card_id) is None:
			self.selected_card_id = None
		self.refresh_ui()

	def _selected_column(self):
		"""!Selected column."""
		board = self.current_board()
		if board is None:
			return None
		if self.selected_column_id:
			return next((column for column in board.get_columns_ordered() if column.id == self.selected_column_id), None)
		columns = board.get_columns_ordered()
		return columns[0] if columns else None

	def create_column(self):
		"""!Create column."""
		board = self.ensure_writable_board()
		if board is None:
			return
		dialog = ColumnDialog(parent=self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		column_id = board.create_column(
			values['name'],
			color=values['color'],
			is_completed=values['is_completed'],
			can_add_card=values['can_add_card'],
		)
		self.selected_column_id = column_id
		self.refresh_ui()

	def edit_selected_column(self):
		"""!Edit selected column."""
		board = self.ensure_writable_board()
		if board is None:
			return
		column = self._selected_column()
		if column is None:
			return
		dialog = ColumnDialog(column, self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		values = dialog.values()
		board.update_column(
			column.id,
			name=values['name'],
			color=values['color'],
			is_completed=values['is_completed'],
			can_add_card=values['can_add_card'],
		)
		self.refresh_ui()

	def delete_selected_column(self):
		"""!Delete selected column."""
		board = self.ensure_writable_board()
		if board is None:
			return
		column = self._selected_column()
		if column is None:
			return
		if len(board.get_columns_ordered()) <= 1:
			QMessageBox.warning(self.window, 'Cannot Delete Column', 'A board must keep at least one column.')
			return
		move_target = None
		if column.cards:
			choices = [other.name for other in board.get_columns_ordered() if other.id != column.id]
			selected, ok = QInputDialog.getItem(self.window, 'Delete Column', 'Move cards to', choices, editable=False)
			if not ok or not selected:
				return
			move_target = next(other.id for other in board.get_columns_ordered() if other.name == selected)
		result = QMessageBox.question(
			self.window,
			'Delete Column',
			f"Delete column '{column.name}'?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
		)
		if result == QMessageBox.StandardButton.Yes:
			board.delete_column(column.id, move_cards_to=move_target)
			self.selected_column_id = None
			self.refresh_ui()

	def reorder_columns(self):
		"""!Reorder columns."""
		board = self.ensure_writable_board()
		if board is None:
			return
		dialog = ReorderColumnsDialog(board.get_columns_ordered(), self.window)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		board.reorder_columns(dialog.ordered_ids())
		self.refresh_ui()


__all__ = ['BoardActionsMixin']
