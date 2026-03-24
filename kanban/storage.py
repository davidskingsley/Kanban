## @file
#  @brief JSON storage helpers and file-lock handling for board persistence.
"""Data storage and persistence layer for the Kanban board."""

import atexit
import json
import os
import shutil
import socket
from datetime import datetime
from typing import Any, Dict, List


def get_default_storage_dir() -> str:
    """Return the default storage root for Kanban application data."""
    return os.path.join(os.path.expanduser("~"), ".kanban-ds")


def get_default_single_board_file() -> str:
    """Return the default data file path for legacy single-board mode."""
    return os.path.join(get_default_storage_dir(), "kanban_data.json")


def get_default_boards_dir() -> str:
    """Return the default directory path for multi-board mode."""
    return os.path.join(get_default_storage_dir(), "boards")


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load raw JSON data from a board file without acquiring locks."""
    if not os.path.exists(file_path):
        return {'cards': []}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'cards': []}


## @brief Persist board data and coordinate read-only lock behavior.
class DataStorage:
    """Handles saving and loading board data to/from JSON files."""

    _owned_locks: Dict[str, int] = {}
    
    def __init__(self, file_path: str):
        self.file_path = os.path.abspath(file_path)
        self.lock_path = f"{self.file_path}.lock"
        self.read_only = False
        self.lock_owned = False
        self.lock_info: Dict[str, Any] = {}
        self._lock_registered = False
        self._acquire_lock()

    def _build_lock_info(self) -> Dict[str, Any]:
        """Build metadata describing the current lock owner."""
        return {
            'pid': os.getpid(),
            'hostname': socket.gethostname(),
            'opened_at': datetime.now().isoformat(),
            'file_path': self.file_path,
        }

    def _read_lock_info(self) -> Dict[str, Any]:
        """Read lock metadata from disk, if available."""
        return load_json_file(self.lock_path)

    def _acquire_lock(self):
        """Acquire a write lock if possible; otherwise fall back to read-only mode."""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if self.file_path in DataStorage._owned_locks:
            DataStorage._owned_locks[self.file_path] += 1
            self.lock_owned = True
            self.lock_info = self._build_lock_info()
            return

        try:
            lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            self.lock_info = self._build_lock_info()
            with os.fdopen(lock_fd, 'w', encoding='utf-8') as lock_file:
                json.dump(self.lock_info, lock_file, indent=2, ensure_ascii=False)

            DataStorage._owned_locks[self.file_path] = 1
            self.lock_owned = True
            if not self._lock_registered:
                atexit.register(self.release_lock)
                self._lock_registered = True
        except FileExistsError:
            self.read_only = True
            self.lock_info = self._read_lock_info()
        except OSError:
            self.read_only = True

    def release_lock(self):
        """Release the lock file owned by this process, if any."""
        if not self.lock_owned:
            return

        ref_count = DataStorage._owned_locks.get(self.file_path, 0)
        if ref_count > 1:
            DataStorage._owned_locks[self.file_path] = ref_count - 1
            return

        DataStorage._owned_locks.pop(self.file_path, None)
        self.lock_owned = False

        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except OSError:
            pass

    def is_read_only(self) -> bool:
        """Return whether this storage instance is read-only."""
        return self.read_only

    def get_lock_details(self) -> Dict[str, Any]:
        """Return metadata about the lock owner, if known."""
        return dict(self.lock_info)

    def get_read_only_message(self) -> str:
        """Return a user-friendly read-only message."""
        details = self.get_lock_details()
        if not details:
            return "This board is currently open elsewhere and is available in read-only mode only."

        hostname = details.get('hostname', 'another machine')
        opened_at = details.get('opened_at', 'an unknown time')
        return (
            "This board is currently locked by another user or process and has been opened in read-only mode.\n\n"
            f"Host: {hostname}\n"
            f"Opened: {opened_at}"
        )
    
    def save(self, data: Dict[str, Any]):
        """Save data to the JSON file."""
        if self.read_only:
            raise PermissionError(self.get_read_only_message())

        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(self.file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def load(self) -> Dict[str, Any]:
        """Load data from the JSON file."""
        data = load_json_file(self.file_path)
        if not data:
            return {'cards': []}
        return data
    
    def backup(self, backup_path: str = None):
        """Create a backup of the current data file."""
        if backup_path is None:
            backup_path = f"{self.file_path}.backup"
        
        if os.path.exists(self.file_path):
            try:
                import shutil
                shutil.copy2(self.file_path, backup_path)
                return backup_path
            except Exception as e:
                print(f"Error creating backup: {e}")
                return None
        return None

    def get_board_directory(self) -> str:
        """Return the directory containing the board data file."""
        return os.path.dirname(self.file_path) or os.getcwd()

    def get_attachments_directory(self) -> str:
        """Return the board-specific attachments directory path."""
        board_name = os.path.splitext(os.path.basename(self.file_path))[0] or 'board'
        return os.path.join(self.get_board_directory(), f"{board_name}_attachments")

    def resolve_attachment_path(self, relative_path: str) -> str:
        """Return an absolute path for a stored attachment path."""
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.abspath(os.path.join(self.get_board_directory(), relative_path))

    def copy_attachment(self, source_path: str, card_id: str) -> str:
        """Copy a source file into the board attachment store and return a relative path."""
        if self.read_only:
            raise PermissionError(self.get_read_only_message())

        absolute_source = os.path.abspath(source_path)
        if not os.path.isfile(absolute_source):
            raise FileNotFoundError(absolute_source)

        card_directory = os.path.join(self.get_attachments_directory(), card_id)
        os.makedirs(card_directory, exist_ok=True)

        base_name = os.path.basename(absolute_source)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        destination_name = f"{timestamp}_{base_name}"
        destination_path = os.path.join(card_directory, destination_name)
        if os.path.exists(destination_path):
            stem, extension = os.path.splitext(base_name)
            destination_name = f"{timestamp}_{stem}_{os.getpid()}{extension}"
            destination_path = os.path.join(card_directory, destination_name)

        shutil.copy2(absolute_source, destination_path)
        return os.path.relpath(destination_path, self.get_board_directory())

    def list_attachment_files(self) -> List[str]:
        """Return all stored attachment file paths for this board."""
        attachments_directory = self.get_attachments_directory()
        if not os.path.isdir(attachments_directory):
            return []

        attachment_files = []
        for root, _, files in os.walk(attachments_directory):
            for filename in files:
                attachment_files.append(os.path.abspath(os.path.join(root, filename)))
        return sorted(attachment_files)

    def delete_attachment_file(self, file_path: str) -> bool:
        """Delete a stored attachment file if it belongs to this board's attachment store."""
        if self.read_only:
            raise PermissionError(self.get_read_only_message())

        absolute_path = os.path.abspath(file_path)
        attachments_directory = os.path.abspath(self.get_attachments_directory())
        try:
            common_path = os.path.commonpath([absolute_path, attachments_directory])
        except ValueError:
            return False

        if common_path != attachments_directory or not os.path.isfile(absolute_path):
            return False

        os.remove(absolute_path)
        return True

    def remove_empty_attachment_directories(self) -> int:
        """Remove empty directories from the board attachment store, including the root if empty."""
        attachments_directory = self.get_attachments_directory()
        if not os.path.isdir(attachments_directory):
            return 0

        removed_count = 0
        for root, _, _ in os.walk(attachments_directory, topdown=False):
            if os.path.isdir(root) and not os.listdir(root):
                os.rmdir(root)
                removed_count += 1
        return removed_count
    
    def restore(self, backup_path: str):
        """Restore data from a backup file."""
        if os.path.exists(backup_path):
            try:
                import shutil
                shutil.copy2(backup_path, self.file_path)
                return True
            except Exception as e:
                print(f"Error restoring backup: {e}")
                return False
        return False