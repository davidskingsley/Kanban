## @file
#  @brief Multi-board registry and metadata management for the Kanban application.
"""Board Manager for handling multiple Kanban boards."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from .board import KanbanBoard
from .storage import get_default_boards_dir, load_json_file


## @brief Manage board metadata, loading, switching, import, and export flows.
class BoardManager:
    """Manages multiple Kanban boards and their metadata."""
    
    def __init__(self, boards_directory: str = None):
        if boards_directory is None:
            boards_directory = get_default_boards_dir()
        
        self.boards_directory = boards_directory
        self.metadata_file = os.path.join(boards_directory, "boards_metadata.json")
        self.boards: Dict[str, KanbanBoard] = {}
        self.current_board_id: Optional[str] = None
        
        # Ensure boards directory exists
        os.makedirs(boards_directory, exist_ok=True)
        
        # Load existing boards
        self.load_boards_metadata()

    def _load_board_from_metadata(self, board_id: str, board_info: Dict) -> KanbanBoard:
        """Load a board instance from stored metadata."""
        data_file = board_info['data_file']
        use_custom_columns = board_info.get('use_custom_columns', True)
        board = KanbanBoard(data_file, use_custom_columns)
        self.boards[board_id] = board
        return board

    def inspect_board_file(self, data_file: str) -> Dict[str, object]:
        """Inspect a board file and infer metadata needed to register it."""
        absolute_path = os.path.abspath(data_file)
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(absolute_path)

        data = load_json_file(absolute_path)
        has_custom_columns = 'columns' in data
        use_custom_columns = True if has_custom_columns or not data.get('cards') else False
        default_name = os.path.splitext(os.path.basename(absolute_path))[0]
        return {
            'data_file': absolute_path,
            'use_custom_columns': use_custom_columns,
            'name': default_name.replace('_', ' ').strip() or default_name,
        }

    def add_external_board(self, data_file: str, name: str = None, description: str = "",
                           use_custom_columns: Optional[bool] = None, switch_to: bool = True) -> str:
        """Register a board stored outside the managed boards directory."""
        inspected = self.inspect_board_file(data_file)
        absolute_path = inspected['data_file']
        metadata = self.load_metadata()

        for existing_board_id, board_info in metadata['boards'].items():
            if os.path.abspath(board_info['data_file']) == absolute_path:
                if switch_to:
                    self.switch_board(existing_board_id)
                return existing_board_id

        board_name = name or inspected['name']
        board_id = self._generate_board_id(board_name)
        board = KanbanBoard(absolute_path, use_custom_columns if use_custom_columns is not None else inspected['use_custom_columns'])
        self.boards[board_id] = board

        metadata['boards'][board_id] = {
            'name': board_name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'data_file': absolute_path,
            'use_custom_columns': board.use_custom_columns,
            'external': True,
        }

        if switch_to:
            metadata['current_board'] = board_id
            self.current_board_id = board_id

        self.save_metadata(metadata)
        return board_id

    def _is_managed_board_path(self, data_file: str) -> bool:
        """Return whether the given board file lives in the managed boards directory."""
        managed_root = os.path.abspath(self.boards_directory)
        candidate = os.path.abspath(data_file)
        try:
            common_path = os.path.commonpath([managed_root, candidate])
        except ValueError:
            return False
        return common_path == managed_root
    
    def create_board(self, name: str, description: str = "", use_custom_columns: bool = True,
                     target_directory: str = None) -> str:
        """Create a new Kanban board."""
        # Generate unique board ID
        board_id = self._generate_board_id(name)

        if target_directory is None:
            target_directory = self.boards_directory
        target_directory = os.path.abspath(target_directory)
        os.makedirs(target_directory, exist_ok=True)
        
        # Create board data file path
        data_file = os.path.join(target_directory, f"{board_id}.json")
        
        # Create the board with custom columns by default
        board = KanbanBoard(data_file, use_custom_columns)
        if use_custom_columns and not board.get_columns_ordered():
            board._init_default_custom_columns()
        self.boards[board_id] = board
        
        # Update metadata
        metadata = self.load_metadata()
        metadata['boards'][board_id] = {
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'data_file': data_file,
            'use_custom_columns': use_custom_columns,
            'external': not self._is_managed_board_path(data_file),
        }
        
        # Set as current board if it's the first one
        if len(metadata['boards']) == 1:
            metadata['current_board'] = board_id
            self.current_board_id = board_id
        
        self.save_metadata(metadata)
        return board_id
    
    def delete_board(self, board_id: str) -> bool:
        """Delete a Kanban board."""
        metadata = self.load_metadata()
        
        if board_id not in metadata['boards']:
            return False
        
        board_info = metadata['boards'][board_id]

        # Delete the board data file only for managed local boards.
        data_file = board_info['data_file']
        if not board_info.get('external') and os.path.exists(data_file):
            os.remove(data_file)
        
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
        """Rename a Kanban board."""
        metadata = self.load_metadata()
        
        if board_id not in metadata['boards']:
            return False
        
        metadata['boards'][board_id]['name'] = new_name
        self.save_metadata(metadata)
        return True
    
    def switch_board(self, board_id: str) -> bool:
        """Switch to a different board."""
        metadata = self.load_metadata()
        
        if board_id not in metadata['boards']:
            return False
        
        metadata['current_board'] = board_id
        self.current_board_id = board_id
        
        # Load board if not already loaded
        if board_id not in self.boards:
            self._load_board_from_metadata(board_id, metadata['boards'][board_id])
        
        self.save_metadata(metadata)
        return True
    
    def get_current_board(self) -> Optional[KanbanBoard]:
        """Get the currently active board."""
        if self.current_board_id is None:
            return None
        
        if self.current_board_id not in self.boards:
            metadata = self.load_metadata()
            if self.current_board_id in metadata['boards']:
                self._load_board_from_metadata(self.current_board_id, metadata['boards'][self.current_board_id])
        
        return self.boards.get(self.current_board_id)
    
    def get_board_list(self) -> List[Dict]:
        """Get list of all boards with their metadata."""
        metadata = self.load_metadata()
        board_list = []
        
        for board_id, board_info in metadata['boards'].items():
            board_data = {
                'id': board_id,
                'name': board_info['name'],
                'description': board_info['description'],
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
        """Load boards metadata and set current board."""
        metadata = self.load_metadata()
        self.current_board_id = metadata.get('current_board')
        
        # Auto-load current board if it exists
        if self.current_board_id and self.current_board_id in metadata['boards']:
            self._load_board_from_metadata(self.current_board_id, metadata['boards'][self.current_board_id])
    
    def load_metadata(self) -> Dict:
        """Load boards metadata from file."""
        if not os.path.exists(self.metadata_file):
            return {'boards': {}, 'current_board': None}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading boards metadata: {e}")
            return {'boards': {}, 'current_board': None}
    
    def save_metadata(self, metadata: Dict):
        """Save boards metadata to file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving boards metadata: {e}")
    
    def _generate_board_id(self, name: str) -> str:
        """Generate a unique board ID from the name."""
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
        """Export all boards data for backup purposes."""
        metadata = self.load_metadata()
        export_data = {
            'metadata': metadata,
            'boards': {}
        }
        
        for board_id, board_info in metadata['boards'].items():
            data_file = board_info['data_file']
            if os.path.exists(data_file):
                export_data['boards'][board_id] = load_json_file(data_file)
        
        return export_data
    
    def import_boards(self, import_data: Dict) -> bool:
        """Import boards data from backup."""
        try:
            # Save current metadata as backup
            current_metadata = self.load_metadata()
            backup_file = f"{self.metadata_file}.backup"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(current_metadata, f, indent=2)
            
            # Import new data
            metadata = import_data.get('metadata', {'boards': {}, 'current_board': None})
            
            for board_id, board_data in import_data.get('boards', {}).items():
                if board_id in metadata['boards']:
                    data_file = metadata['boards'][board_id]['data_file']
                    directory = os.path.dirname(data_file)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                    with open(data_file, 'w', encoding='utf-8') as output_file:
                        json.dump(board_data, output_file, indent=2, ensure_ascii=False)
            
            self.save_metadata(metadata)
            self.load_boards_metadata()
            return True
            
        except Exception as e:
            print(f"Error importing boards: {e}")
            return False

    def close(self):
        """Release resources for all loaded boards."""
        for board in self.boards.values():
            board.close()