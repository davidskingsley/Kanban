## @file
#  @brief Multi-board registry and metadata management for the Kanban application.
"""!Board Manager for handling multiple Kanban boards."""

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

from .board import KanbanBoard
from .storage import (
    JSON_STORAGE_BACKEND,
    BoardLockCancelledError,
    LockHandler,
    delete_board_lock,
    get_board_file_extension,
    get_default_boards_dir,
    infer_storage_backend,
    is_supported_board_file,
    load_board_data_file,
    normalize_storage_backend,
    save_board_data_file,
)


## @brief Manage board metadata, loading, switching, import, and export flows.
class BoardManager:
    """!Manages multiple Kanban boards and their metadata."""
    MAX_UNDO_STEPS = 100
    
    def __init__(self, boards_directory: str = None):
        """!Init."""
        if boards_directory is None:
            boards_directory = get_default_boards_dir()
        
        self.boards_directory = boards_directory
        self.metadata_file = os.path.join(boards_directory, "boards_metadata.json")
        profile_directory = os.path.abspath(boards_directory)
        if os.path.basename(profile_directory).lower() == 'boards':
            profile_directory = os.path.dirname(profile_directory)
        self.user_profile_file = os.path.join(profile_directory, 'user_profile.json')
        self.boards: Dict[str, KanbanBoard] = {}
        self.current_board_id: Optional[str] = None
        self.lock_handler: Optional[LockHandler] = None
        self._undo_stack: List[Dict[str, object]] = []
        self._redo_stack: List[Dict[str, object]] = []
        self.actor_name: Optional[str] = self._load_actor_name()
        
        # Ensure boards directory exists
        os.makedirs(boards_directory, exist_ok=True)
        
        # Load existing boards
        self.load_boards_metadata()

    def _normalize_actor_name(self, actor_name: Optional[str]) -> Optional[str]:
        """!Normalize a persisted actor name."""
        normalized = (actor_name or '').strip()
        return normalized or None

    def _load_actor_name(self) -> Optional[str]:
        """!Load the saved actor name from the user profile file."""
        if not os.path.exists(self.user_profile_file):
            return None
        try:
            with open(self.user_profile_file, 'r', encoding='utf-8') as profile_file:
                profile = json.load(profile_file)
        except Exception:
            return None
        return self._normalize_actor_name(profile.get('name'))

    def get_actor_name(self) -> Optional[str]:
        """!Return the saved actor name for this board-manager session."""
        return self.actor_name

    def set_actor_name(self, actor_name: str, persist: bool = True) -> str:
        """!Set the current actor name and optionally persist it to disk."""
        normalized = self._normalize_actor_name(actor_name)
        if normalized is None:
            raise ValueError('User name is required.')
        self.actor_name = normalized
        if persist:
            os.makedirs(os.path.dirname(self.user_profile_file), exist_ok=True)
            with open(self.user_profile_file, 'w', encoding='utf-8') as profile_file:
                json.dump({'name': normalized}, profile_file, indent=2, ensure_ascii=False)
        for board in self.boards.values():
            board.set_actor_name(normalized)
        return normalized

    def _normalize_board_info(self, board_info: Dict) -> Dict:
        """!Return a metadata entry with backend defaults applied."""
        normalized = dict(board_info)
        data_file = normalized.get('data_file', '')
        normalized['description'] = normalized.get('description', '')
        normalized['use_custom_columns'] = normalized.get('use_custom_columns', True)
        normalized['storage_backend'] = normalize_storage_backend(
            normalized.get('storage_backend'),
            file_path=data_file,
        )
        normalized['external'] = normalized.get('external', False)
        return normalized

    def _board_backend(self, board_info: Dict) -> str:
        """!Return the normalized backend name for a board metadata entry."""
        return normalize_storage_backend(board_info.get('storage_backend'), file_path=board_info.get('data_file'))

    def _remove_board_file(self, data_file: str) -> None:
        """!Remove a board data file and its adjacent lock file when present."""
        absolute_path = os.path.abspath(data_file)
        delete_board_lock(absolute_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)

    def _capture_state(self) -> Dict[str, object]:
        """!Capture metadata and board files for board-management undo."""
        metadata = deepcopy(self.load_metadata())
        boards_data = {}

        for board_id, board_info in metadata['boards'].items():
            if board_id in self.boards:
                boards_data[board_id] = self.boards[board_id].export_data()
            elif os.path.exists(board_info['data_file']):
                boards_data[board_id] = load_board_data_file(
                    board_info['data_file'],
                    backend=self._board_backend(board_info),
                )
            else:
                boards_data[board_id] = None

        return {
            'metadata': metadata,
            'boards': boards_data,
        }

    def _push_history_state(self, stack: List[Dict[str, object]], description: str):
        """!Capture the current manager state on the provided history stack."""
        stack.append({
            'description': description,
            'state': self._capture_state(),
        })
        if len(stack) > self.MAX_UNDO_STEPS:
            stack.pop(0)

    def _push_undo_state(self, description: str):
        """!Capture the current manager state so the next change can be undone."""
        self._push_history_state(self._undo_stack, description)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        """!Return whether a board-management undo snapshot is available."""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """!Return whether a board-management redo snapshot is available."""
        return bool(self._redo_stack)

    def get_next_undo_description(self) -> Optional[str]:
        """!Return the description of the next manager action to undo."""
        if not self._undo_stack:
            return None
        return self._undo_stack[-1]['description']

    def get_next_redo_description(self) -> Optional[str]:
        """!Return the description of the next manager action to redo."""
        if not self._redo_stack:
            return None
        return self._redo_stack[-1]['description']

    def _restore_state(self, state: Dict[str, object]):
        """!Restore metadata and board files from a captured snapshot."""
        current_metadata = self.load_metadata()
        target_metadata = deepcopy(state['metadata'])

        for board in self.boards.values():
            board.close()
        self.boards = {}

        current_board_ids = set(current_metadata['boards'].keys())
        target_board_ids = set(target_metadata['boards'].keys())
        for board_id in current_board_ids - target_board_ids:
            board_info = current_metadata['boards'][board_id]
            data_file = board_info['data_file']
            if not board_info.get('external') and os.path.exists(data_file):
                self._remove_board_file(data_file)

        for board_id in current_board_ids & target_board_ids:
            current_info = current_metadata['boards'][board_id]
            target_info = target_metadata['boards'][board_id]
            current_path = os.path.abspath(current_info['data_file'])
            target_path = os.path.abspath(target_info['data_file'])
            if current_path != target_path and os.path.exists(current_path):
                self._remove_board_file(current_path)

        for board_id, board_info in target_metadata['boards'].items():
            board_data = state['boards'].get(board_id)
            if board_data is None:
                continue

            data_file = board_info['data_file']
            save_board_data_file(data_file, board_data, backend=self._board_backend(board_info))

        self.save_metadata(target_metadata)
        self.current_board_id = target_metadata.get('current_board')
        self.load_boards_metadata()

    def undo_last_action(self) -> Optional[str]:
        """!Restore the most recent board-management snapshot."""
        if not self._undo_stack:
            return None

        snapshot = self._undo_stack.pop()
        self._push_history_state(self._redo_stack, snapshot['description'])
        self._restore_state(snapshot['state'])
        return snapshot['description']

    def redo_last_action(self) -> Optional[str]:
        """!Reapply the most recently undone board-management snapshot."""
        if not self._redo_stack:
            return None

        snapshot = self._redo_stack.pop()
        self._push_history_state(self._undo_stack, snapshot['description'])
        self._restore_state(snapshot['state'])
        return snapshot['description']

    def set_lock_handler(self, lock_handler: Optional[LockHandler]):
        """!Set the callback used when a board lock is encountered."""
        self.lock_handler = lock_handler

    def _load_board_from_metadata(self, board_id: str, board_info: Dict) -> KanbanBoard:
        """!Load a board instance from stored metadata."""
        data_file = board_info['data_file']
        if board_info.get('use_custom_columns') is False:
            raise ValueError('Legacy boards are no longer supported.')
        board = KanbanBoard(
            data_file,
            lock_handler=self.lock_handler,
            storage_backend=self._board_backend(board_info),
        )
        board.set_actor_name(self.actor_name)
        self.boards[board_id] = board
        return board

    def inspect_board_file(self, data_file: str) -> Dict[str, object]:
        """!Inspect a board file and infer metadata needed to register it."""
        absolute_path = os.path.abspath(data_file)
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(absolute_path)
        if not is_supported_board_file(absolute_path):
            raise ValueError('Unsupported board storage format.')

        backend = infer_storage_backend(absolute_path)
        data = load_board_data_file(absolute_path, backend=backend)
        has_custom_columns = 'columns' in data
        if not has_custom_columns and data.get('cards'):
            raise ValueError('Legacy boards are no longer supported. Boards must use custom columns.')
        default_name = os.path.splitext(os.path.basename(absolute_path))[0]
        return {
            'data_file': absolute_path,
            'storage_backend': backend,
            'use_custom_columns': True,
            'name': default_name.replace('_', ' ').strip() or default_name,
        }

    def add_external_board(self, data_file: str, name: str = None, description: str = "",
                           use_custom_columns: Optional[bool] = None, switch_to: bool = True) -> Optional[str]:
        """!Register a board stored outside the managed boards directory."""
        inspected = self.inspect_board_file(data_file)
        absolute_path = inspected['data_file']
        metadata = self.load_metadata()

        for existing_board_id, board_info in metadata['boards'].items():
            if os.path.abspath(board_info['data_file']) == absolute_path:
                if switch_to:
                    self.switch_board(existing_board_id)
                return existing_board_id

        self._push_undo_state(f"Load board '{name or inspected['name']}' from folder")

        board_name = name or inspected['name']
        board_id = self._generate_board_id(board_name)
        try:
            board = KanbanBoard(
                absolute_path,
                lock_handler=self.lock_handler,
                storage_backend=inspected['storage_backend'],
            )
        except BoardLockCancelledError:
            return None

        board.set_actor_name(self.actor_name)

        self.boards[board_id] = board

        metadata['boards'][board_id] = {
            'name': board_name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'data_file': absolute_path,
            'storage_backend': inspected['storage_backend'],
            'use_custom_columns': True,
            'external': True,
        }

        if switch_to:
            metadata['current_board'] = board_id
            self.current_board_id = board_id

        self.save_metadata(metadata)
        return board_id

    def _is_managed_board_path(self, data_file: str) -> bool:
        """!Return whether the given board file lives in the managed boards directory."""
        managed_root = os.path.abspath(self.boards_directory)
        candidate = os.path.abspath(data_file)
        try:
            common_path = os.path.commonpath([managed_root, candidate])
        except ValueError:
            return False
        return common_path == managed_root
    
    def create_board(self, name: str, description: str = "", use_custom_columns: bool = True,
                     target_directory: str = None, storage_backend: Optional[str] = None) -> str:
        """!Create a new Kanban board."""
        self._push_undo_state(f"Create board '{name}'")

        # Generate unique board ID
        board_id = self._generate_board_id(name)

        if target_directory is None:
            target_directory = self.boards_directory
        target_directory = os.path.abspath(target_directory)
        os.makedirs(target_directory, exist_ok=True)
        storage_backend = normalize_storage_backend(storage_backend or JSON_STORAGE_BACKEND)
        
        # Create board data file path
        data_file = os.path.join(target_directory, f"{board_id}{get_board_file_extension(storage_backend)}")
        
        # Create the board with custom columns by default
        board = KanbanBoard(data_file, lock_handler=self.lock_handler, storage_backend=storage_backend)
        board.set_actor_name(self.actor_name)
        if not board.get_columns_ordered():
            board._init_default_custom_columns()
        self.boards[board_id] = board
        
        # Update metadata
        metadata = self.load_metadata()
        metadata['boards'][board_id] = {
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'data_file': data_file,
            'storage_backend': storage_backend,
            'use_custom_columns': True,
            'external': not self._is_managed_board_path(data_file),
        }
        
        # Set as current board if it's the first one
        if len(metadata['boards']) == 1:
            metadata['current_board'] = board_id
            self.current_board_id = board_id
        
        self.save_metadata(metadata)
        return board_id

    def convert_board_storage_backend(self, board_id: str, storage_backend: str, target_directory: str = None) -> str:
        """!Convert an existing board between JSON and SQLite storage backends."""
        metadata = self.load_metadata()
        if board_id not in metadata['boards']:
            raise KeyError(board_id)

        board_info = metadata['boards'][board_id]
        current_backend = self._board_backend(board_info)
        target_backend = normalize_storage_backend(storage_backend)
        if current_backend == target_backend:
            raise ValueError(f"Board '{board_info['name']}' already uses the {target_backend} backend.")

        if board_id not in self.boards:
            self._load_board_from_metadata(board_id, board_info)

        board = self.boards[board_id]
        if board.is_read_only():
            raise PermissionError(board.get_read_only_message())

        self._push_undo_state(f"Convert board '{board_info['name']}' to {target_backend}")

        source_file = os.path.abspath(board_info['data_file'])
        source_directory = os.path.dirname(source_file)
        source_name = os.path.splitext(os.path.basename(source_file))[0] or board_id
        target_directory = os.path.abspath(target_directory or source_directory)
        os.makedirs(target_directory, exist_ok=True)
        target_file = os.path.join(target_directory, f"{source_name}{get_board_file_extension(target_backend)}")

        if os.path.abspath(target_file) != source_file and os.path.exists(target_file):
            raise FileExistsError(target_file)

        board_data = deepcopy(board.export_data())
        board.close()
        del self.boards[board_id]

        save_board_data_file(target_file, board_data, backend=target_backend)
        if os.path.abspath(target_file) != source_file and os.path.exists(source_file):
            self._remove_board_file(source_file)

        board_info['data_file'] = target_file
        board_info['storage_backend'] = target_backend
        board_info['external'] = not self._is_managed_board_path(target_file)
        self.save_metadata(metadata)

        self._load_board_from_metadata(board_id, board_info)
        return target_file
    
    def delete_board(self, board_id: str) -> bool:
        """!Delete a Kanban board."""
        metadata = self.load_metadata()
        
        if board_id not in metadata['boards']:
            return False

        self._push_undo_state(f"Delete board '{metadata['boards'][board_id]['name']}'")
        
        board_info = metadata['boards'][board_id]

        # Delete the board data file only for managed local boards.
        data_file = board_info['data_file']
        if not board_info.get('external') and os.path.exists(data_file):
            self._remove_board_file(data_file)
        
        # Remove from metadata
        del metadata['boards'][board_id]
        
        # Remove from memory
        if board_id in self.boards:
            self.boards[board_id].close()
            del self.boards[board_id]
        
        # Update current board if necessary
        if metadata['current_board'] == board_id:
            remaining_boards = list(metadata['boards'].keys())
            metadata['current_board'] = remaining_boards[0] if remaining_boards else None
            self.current_board_id = metadata['current_board']
        
        self.save_metadata(metadata)
        return True
    
    def rename_board(self, board_id: str, new_name: str) -> bool:
        """!Rename a Kanban board."""
        metadata = self.load_metadata()
        
        if board_id not in metadata['boards']:
            return False

        current_name = metadata['boards'][board_id]['name']
        if current_name == new_name:
            return False

        self._push_undo_state(f"Rename board '{current_name}'")
        
        metadata['boards'][board_id]['name'] = new_name
        self.save_metadata(metadata)
        return True
    
    def switch_board(self, board_id: str) -> bool:
        """!Switch to a different board."""
        metadata = self.load_metadata()
        
        if board_id not in metadata['boards']:
            return False
        if metadata.get('current_board') == board_id:
            return False

        if board_id not in self.boards:
            try:
                self._load_board_from_metadata(board_id, metadata['boards'][board_id])
            except BoardLockCancelledError:
                return False
            except ValueError:
                return False

        self._push_undo_state(f"Switch to board '{metadata['boards'][board_id]['name']}'")
        
        metadata['current_board'] = board_id
        self.current_board_id = board_id
        
        self.save_metadata(metadata)
        return True
    
    def get_current_board(self) -> Optional[KanbanBoard]:
        """!Get the currently active board."""
        if self.current_board_id is None:
            return None
        
        if self.current_board_id not in self.boards:
            metadata = self.load_metadata()
            if self.current_board_id in metadata['boards']:
                try:
                    self._load_board_from_metadata(self.current_board_id, metadata['boards'][self.current_board_id])
                except BoardLockCancelledError:
                    return None
                except ValueError:
                    return None
        
        return self.boards.get(self.current_board_id)
    
    def get_board_list(self) -> List[Dict]:
        """!Get list of all boards with their metadata."""
        metadata = self.load_metadata()
        board_list = []
        
        for board_id, board_info in metadata['boards'].items():
            board_data = {
                'id': board_id,
                'name': board_info['name'],
                'description': board_info['description'],
                'storage_backend': self._board_backend(board_info),
                'is_current': board_id == self.current_board_id,
                'external': board_info.get('external', False),
            }
            
            # Add statistics if board is loaded
            if board_id in self.boards:
                stats = self.boards[board_id].get_board_stats()
                board_data['stats'] = stats
                board_data['read_only'] = self.boards[board_id].is_read_only()
            
            board_list.append(board_data)
        
        return board_list
    
    def load_boards_metadata(self):
        """!Load boards metadata and set current board."""
        metadata = self.load_metadata()
        self.current_board_id = metadata.get('current_board')
    
    def load_metadata(self) -> Dict:
        """!Load boards metadata from file."""
        if not os.path.exists(self.metadata_file):
            return {'boards': {}, 'current_board': None}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Error loading boards metadata: {e}")
            return {'boards': {}, 'current_board': None}

        normalized_boards = {
            board_id: self._normalize_board_info(board_info)
            for board_id, board_info in metadata.get('boards', {}).items()
        }
        return {
            'boards': normalized_boards,
            'current_board': metadata.get('current_board'),
        }
    
    def save_metadata(self, metadata: Dict):
        """!Save boards metadata to file."""
        try:
            normalized_metadata = {
                'boards': {
                    board_id: self._normalize_board_info(board_info)
                    for board_id, board_info in metadata.get('boards', {}).items()
                },
                'current_board': metadata.get('current_board'),
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(normalized_metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving boards metadata: {e}")
    
    def _generate_board_id(self, name: str) -> str:
        """!Generate a unique board ID from the name."""
        # Create base ID from name
        base_id = "".join(c.lower() if c.isalnum() else "_" for c in name)
        base_id = base_id.strip("_")
        
        if not base_id:
            base_id = "board"
        
        # Ensure uniqueness
        metadata = self.load_metadata()
        board_id = base_id
        counter = 1
        
        while board_id in metadata['boards']:
            board_id = f"{base_id}_{counter}"
            counter += 1
        
        return board_id
    
    def export_all_boards(self) -> Dict:
        """!Export all boards data for backup purposes."""
        metadata = self.load_metadata()
        export_data = {
            'metadata': metadata,
            'boards': {}
        }
        
        for board_id, board_info in metadata['boards'].items():
            data_file = board_info['data_file']
            if os.path.exists(data_file):
                export_data['boards'][board_id] = load_board_data_file(
                    data_file,
                    backend=self._board_backend(board_info),
                )
        
        return export_data

    def export_board_data(self, board_id: str) -> Dict:
        """!Export a single board as standalone board-file data."""
        metadata = self.load_metadata()
        if board_id not in metadata['boards']:
            raise KeyError(board_id)

        if board_id in self.boards:
            return deepcopy(self.boards[board_id].export_data())

        data_file = metadata['boards'][board_id]['data_file']
        if not os.path.exists(data_file):
            raise FileNotFoundError(data_file)

        return load_board_data_file(data_file, backend=self._board_backend(metadata['boards'][board_id]))
    
    def import_boards(self, import_data: Dict) -> bool:
        """!Import boards data from backup."""
        try:
            self._push_undo_state("Import boards")
            # Save current metadata as backup
            current_metadata = self.load_metadata()
            backup_file = f"{self.metadata_file}.backup"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(current_metadata, f, indent=2)
            
            # Import new data
            metadata = import_data.get('metadata', {'boards': {}, 'current_board': None})
            metadata = {
                'boards': {
                    board_id: self._normalize_board_info(board_info)
                    for board_id, board_info in metadata.get('boards', {}).items()
                },
                'current_board': metadata.get('current_board'),
            }

            for board in self.boards.values():
                board.close()
            self.boards = {}
            
            for board_id, board_data in import_data.get('boards', {}).items():
                if board_id in metadata['boards']:
                    board_info = metadata['boards'][board_id]
                    save_board_data_file(
                        board_info['data_file'],
                        board_data,
                        backend=self._board_backend(board_info),
                    )
            
            self.save_metadata(metadata)
            self.load_boards_metadata()
            return True
            
        except Exception as e:
            print(f"Error importing boards: {e}")
            return False

    def close(self):
        """!Release resources for all loaded boards."""
        for board in self.boards.values():
            board.close()