## @file
#  @brief Top-level multi-board GUI shell for board selection and application menus.
"""Main multi-board application shell."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from ..board_manager import BoardManager
from .board_statistics import (
    get_completed_count as get_board_completed_count,
    show_board_statistics as show_board_statistics_dialog,
    update_board_info as update_board_summary,
)
from .common import APP_BG, TEXT_MUTED
from .embedded_board import EmbeddedKanbanGUI
from .dialogs import BoardDialog
from .shell_ui import (
    bind_menu_shortcuts as bind_shell_shortcuts,
    setup_menu as setup_shell_menu,
    setup_toolbar as setup_shell_toolbar,
    show_shortcuts as show_shortcuts_dialog,
)

class MultiBoardGUI:
    """Multi-board GUI wrapper for managing multiple Kanban boards."""

    MENU_SHORTCUTS = {
        'create_board_dialog': ('Ctrl+N', '<Control-n>'),
        'load_board_from_folder_dialog': ('Ctrl+Shift+O', '<Control-Shift-O>'),
        'switch_board_dialog': ('Ctrl+O', '<Control-o>'),
        'rename_current_board_dialog': ('Ctrl+R', '<Control-r>'),
        'delete_current_board_dialog': ('Ctrl+Shift+D', '<Control-Shift-D>'),
        'show_board_statistics': ('Ctrl+I', '<Control-i>'),
        'create_card_dialog': ('Ctrl+Shift+N', '<Control-Shift-N>'),
        'edit_card_dialog': ('Ctrl+E', '<Control-e>'),
        'move_card_dialog': ('Ctrl+M', '<Control-m>'),
        'delete_card_dialog': ('Ctrl+D', '<Control-d>'),
        'clear_done_cards': ('Ctrl+Shift+K', '<Control-Shift-K>'),
        'create_backup': ('Ctrl+B', '<Control-b>'),
        'search_dialog': ('Ctrl+F', '<Control-f>'),
        'filter_priority_dialog': ('Ctrl+Shift+P', '<Control-Shift-P>'),
        'filter_assignee_dialog': ('Ctrl+Shift+A', '<Control-Shift-A>'),
        'filter_overdue_dialog': ('Ctrl+Shift+L', '<Control-Shift-L>'),
        'clear_filters': ('Ctrl+Shift+F', '<Control-Shift-F>'),
        'create_column_dialog': ('Ctrl+Shift+C', '<Control-Shift-C>'),
        'rename_column_dialog': ('Ctrl+Alt+R', '<Control-Alt-r>'),
        'delete_column_dialog': ('Ctrl+Alt+D', '<Control-Alt-d>'),
        'reorder_columns_dialog': ('Ctrl+Alt+O', '<Control-Alt-o>'),
        'export_all_boards': ('Ctrl+Shift+E', '<Control-Shift-E>'),
        'import_boards': ('Ctrl+Shift+I', '<Control-Shift-I>'),
        'show_shortcuts': ('F1', '<F1>'),
        'on_close': ('Ctrl+Q', '<Control-q>'),
    }
    
    def __init__(self, board_manager: BoardManager):
        self.board_manager = board_manager
        self.root = tk.Tk()
        self.current_board_gui: Optional['EmbeddedKanbanGUI'] = None
        self.board_frame = None
        
        self.setup_window()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_main_area()
        
        # Load initial board
        self.refresh_board_display()
    
    def setup_window(self):
        """Set up the main window."""
        self.root.title("🗂️ Multi-Board Kanban Manager")
        self.root.geometry("1400x800")
        self.root.configure(bg=APP_BG)

        style = ttk.Style(self.root)
        try:
            style.theme_use('vista')
        except tk.TclError:
            pass
        style.configure('Soft.TCombobox', padding=6)
        style.configure('SoftPrimary.TButton', font=('Arial', 10, 'bold'), padding=(16, 8))
        style.configure('SoftSecondary.TButton', font=('Arial', 10, 'bold'), padding=(16, 8))
        style.configure('SoftAccent.TButton', font=('Arial', 10, 'bold'), padding=(16, 8))
        style.configure('SoftLight.TButton', font=('Arial', 10, 'bold'), padding=(16, 8))
        style.configure('AddCard.TButton', font=('Arial', 10, 'bold'), padding=(10, 4))
        
        # Set minimum window size
        self.root.minsize(1000, 600)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_menu(self):
        """Set up the menu bar."""
        setup_shell_menu(self)

    def get_shortcut_label(self, action_name):
        """Return the display label for a configured shortcut."""
        shortcut = self.MENU_SHORTCUTS.get(action_name)
        return shortcut[0] if shortcut else ''

    def bind_shortcut(self, sequence, callback):
        """Bind a shortcut and stop further event processing after handling it."""
        def handler(event=None):
            callback()
            return 'break'

        self.root.bind(sequence, handler)

    def bind_menu_shortcuts(self):
        """Bind keyboard shortcuts for primary menu actions."""
        bind_shell_shortcuts(self)
    
    def setup_toolbar(self):
        """Set up the toolbar with board selection and quick actions."""
        setup_shell_toolbar(self)
    
    def setup_main_area(self):
        """Set up the main area where the board GUI will be embedded."""
        self.main_frame = tk.Frame(self.root, bg=APP_BG)
        self.main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Welcome message for when no boards exist
        self.welcome_frame = tk.Frame(self.main_frame, bg=APP_BG)
        
        welcome_label = tk.Label(self.welcome_frame, 
                                text="🗂️ Welcome to Multi-Board Kanban Manager!\n\n" +
                                  "Use Boards > Create New Board to get started.",
                                                                font=('Arial', 16), bg=APP_BG, fg=TEXT_MUTED,
                                justify='center')
        welcome_label.pack(expand=True)
    
    def refresh_board_display(self):
        """Refresh the board display and selector."""
        boards = self.board_manager.get_board_list()
        
        # Update board selector (only if it exists)
        if hasattr(self, 'board_selector') and self.board_selector:
            board_names = [f"{board['name']}" for board in boards]
            self.board_selector['values'] = board_names
        
        if boards:
            # Hide welcome frame before loading the board interface so it does not compete for layout
            if hasattr(self, 'welcome_frame'):
                try:
                    self.welcome_frame.pack_forget()
                except:
                    pass

            # Find current board
            current_board_name = None
            current_board_stats = None
            for board in boards:
                if board['is_current']:
                    current_board_name = board['name']
                    current_board_stats = board.get('stats')
                    break

            if current_board_name is None and boards:
                fallback_board = boards[0]
                self.board_manager.switch_board(fallback_board['id'])
                current_board_name = fallback_board['name']
                current_board_stats = fallback_board.get('stats')
            
            if current_board_name:
                if hasattr(self, 'board_var'):
                    self.board_var.set(current_board_name)
                if hasattr(self, 'board_selector') and self.board_selector:
                    self.board_selector.set(current_board_name)
                self.load_board_interface()
                self.update_board_info(current_board_stats)
            else:
                self.clear_board_interface()
                if hasattr(self, 'board_var'):
                    self.board_var.set("")
                if hasattr(self, 'board_selector') and self.board_selector:
                    self.board_selector.set("")
                self.update_board_info()
        else:
            # Show welcome frame
            self.clear_board_interface()
            if hasattr(self, 'welcome_frame'):
                try:
                    self.welcome_frame.pack(fill='both', expand=True)
                except:
                    pass  # Frame might already be packed
            self.clear_board_selector()
            if hasattr(self, 'board_info_var'):
                self.board_info_var.set("No board selected")

    def clear_board_selector(self):
        """Clear the board selector state, including readonly combobox text."""
        if hasattr(self, 'board_var'):
            self.board_var.set("")

        if hasattr(self, 'board_selector') and self.board_selector:
            self.board_selector['values'] = ()
            try:
                self.board_selector.set("")
                self.board_selector.configure(state='normal')
                self.board_selector.delete(0, tk.END)
            finally:
                self.board_selector.configure(state='readonly')

    def get_completed_count(self, stats, board=None):
        """Get the completed-card count for legacy and custom-column boards."""
        return get_board_completed_count(stats, board)

    def update_board_info(self, stats=None, board=None):
        """Update the toolbar summary for the current board."""
        update_board_summary(self, stats, board)
    
    def load_board_interface(self):
        """Load the current board into the interface."""
        current_board = self.board_manager.get_current_board()
        if not current_board:
            return
        
        # Clear existing interface
        self.clear_board_interface()
        
        # Create board frame
        self.board_frame = tk.Frame(self.main_frame, bg=APP_BG)
        self.board_frame.pack(fill='both', expand=True)
        
        # Create embedded GUI (modify existing GUI to work within a frame)
        self.current_board_gui = EmbeddedKanbanGUI(self.board_frame, current_board, self)
        self.update_board_info(board=current_board)
        self.root.after_idle(lambda: self.update_board_info(board=current_board))
    
    def clear_board_interface(self):
        """Clear the current board interface."""
        if self.current_board_gui:
            self.current_board_gui.cleanup()
            self.current_board_gui = None

        if self.board_frame:
            self.board_frame.destroy()
            self.board_frame = None
    
    def on_board_selected(self, event):
        """Handle board selection from the combobox."""
        selected_board_name = self.board_var.get()
        if not selected_board_name:
            return
        
        # Find the board ID
        boards = self.board_manager.get_board_list()
        for board in boards:
            if board['name'] == selected_board_name:
                if not board['is_current']:
                    self.board_manager.switch_board(board['id'])
                    self.refresh_board_display()
                break
    
    def create_board_dialog(self):
        """Show dialog to create a new board."""
        dialog = BoardDialog(self.root, self.board_manager.boards_directory, "Create New Board")
        if dialog.result:
            name, description, storage_dir = dialog.result
            board_id = self.board_manager.create_board(name, description, target_directory=storage_dir)
            if board_id:
                self.board_manager.switch_board(board_id)
                self.welcome_frame.pack_forget()
                self.refresh_board_display()
                messagebox.showinfo("Success", f"Board '{name}' created successfully!")
            else:
                messagebox.showerror("Error", "Failed to create board!")

    def load_board_from_folder_dialog(self):
        """Load a single board from an external folder into the board list."""
        from tkinter import filedialog
        import os
        import json

        folder = filedialog.askdirectory(title="Select Folder Containing a Board")
        if not folder:
            return

        options = []
        option_map = {}
        metadata_path = os.path.join(folder, 'boards_metadata.json')

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
                    metadata = json.load(metadata_file)

                for board_id, board_info in metadata.get('boards', {}).items():
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
                        'use_custom_columns': board_info.get('use_custom_columns'),
                    }
                    options.append(label)
            except Exception as error:
                messagebox.showerror("Error", f"Failed to read board metadata:\n{error}")
                return
        else:
            for entry in sorted(os.listdir(folder)):
                if not entry.endswith('.json') or entry == 'boards_metadata.json' or entry.endswith('.backup.json'):
                    continue

                data_file = os.path.join(folder, entry)
                inspected = self.board_manager.inspect_board_file(data_file)
                label = inspected['name']
                if label in option_map:
                    label = f"{label} ({entry})"
                option_map[label] = {
                    'data_file': inspected['data_file'],
                    'name': inspected['name'],
                    'description': '',
                    'use_custom_columns': inspected['use_custom_columns'],
                }
                options.append(label)

        if not options:
            messagebox.showinfo("No Boards Found", "No board files were found in the selected folder.")
            return

        selected = SelectionDialog(
            self.root,
            "Load Board From Folder",
            "Select a board to load:",
            options,
        ).result
        if selected is None:
            return

        board_choice = option_map[selected]
        try:
            board_id = self.board_manager.add_external_board(
                board_choice['data_file'],
                name=board_choice['name'],
                description=board_choice['description'],
                use_custom_columns=board_choice['use_custom_columns'],
                switch_to=True,
            )
            self.refresh_board_display()
            board = self.board_manager.get_current_board()
            if board and board.is_read_only():
                messagebox.showwarning("Read Only Board", board.get_read_only_message())
            else:
                messagebox.showinfo("Success", f"Board '{board_choice['name']}' loaded successfully!")
        except FileNotFoundError:
            messagebox.showerror("Error", "The selected board file could not be found.")
        except Exception as error:
            messagebox.showerror("Error", f"Failed to load board:\n{error}")
    
    def switch_board_dialog(self):
        """Show dialog to switch to a different board."""
        boards = self.board_manager.get_board_list()
        if len(boards) <= 1:
            messagebox.showinfo("Info", "Only one board available!")
            return
        
        board_names = [board['name'] for board in boards if not board['is_current']]
        if not board_names:
            messagebox.showinfo("Info", "No other boards to switch to!")
            return

        selected = SelectionDialog(
            self.root,
            "Switch Board",
            "Select a board:",
            board_names
        ).result
        
        if selected:
            for board in boards:
                if board['name'] == selected:
                    self.board_manager.switch_board(board['id'])
                    self.refresh_board_display()
                    return
            messagebox.showerror("Error", "Board not found!")
    
    def rename_current_board_dialog(self):
        """Show dialog to rename the current board."""
        current_board = self.board_manager.get_current_board()
        if not current_board:
            messagebox.showwarning("Warning", "No board selected!")
            return
        
        boards = self.board_manager.get_board_list()
        current_board_id = None
        current_name = ""
        
        for board in boards:
            if board['is_current']:
                current_board_id = board['id']
                current_name = board['name']
                break
        
        new_name = simpledialog.askstring("Rename Board", 
                                         f"Current name: {current_name}\n\nEnter new name:",
                                         initialvalue=current_name)
        
        if new_name and new_name != current_name:
            if self.board_manager.rename_board(current_board_id, new_name):
                self.refresh_board_display()
                messagebox.showinfo("Success", f"Board renamed to '{new_name}'!")
            else:
                messagebox.showerror("Error", "Failed to rename board!")
    
    def delete_current_board_dialog(self):
        """Show dialog to delete the current board."""
        boards = self.board_manager.get_board_list()
        current_board_id = None
        current_name = ""
        
        for board in boards:
            if board['is_current']:
                current_board_id = board['id']
                current_name = board['name']
                break
        
        if not current_board_id:
            messagebox.showwarning("Warning", "No board selected!")
            return
        
        result = messagebox.askyesno("Confirm Deletion", 
                       f"Are you sure you want to delete board '{current_name}'?\n\n" +
                       "This action cannot be undone. If this is the last board, the app will return to the empty welcome state.")
        
        if result:
            if self.board_manager.delete_board(current_board_id):
                if len(boards) == 1:
                    self.clear_board_interface()
                    self.clear_board_selector()
                    if hasattr(self, 'board_info_var'):
                        self.board_info_var.set("No board selected")
                self.refresh_board_display()
                messagebox.showinfo("Success", f"Board '{current_name}' deleted!")
            else:
                messagebox.showerror("Error", "Failed to delete board!")
    
    def show_board_statistics(self):
        """Show statistics for all boards."""
        show_board_statistics_dialog(self)
    
    def export_all_boards(self):
        """Export all boards to a backup file."""
        from tkinter import filedialog
        import json
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export All Boards"
        )
        
        if filename:
            try:
                export_data = self.board_manager.export_all_boards()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Success", f"All boards exported to '{filename}'!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export boards: {e}")
    
    def import_boards(self):
        """Import boards from a backup file."""
        from tkinter import filedialog
        import json
        
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Boards"
        )
        
        if filename:
            result = messagebox.askyesno("Confirm Import", 
                                       "This will replace all existing boards!\n\n" +
                                       "Are you sure you want to continue?")
            if result:
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        import_data = json.load(f)
                    
                    if self.board_manager.import_boards(import_data):
                        self.refresh_board_display()
                        messagebox.showinfo("Success", f"Boards imported from '{filename}'!")
                    else:
                        messagebox.showerror("Error", "Failed to import boards!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to import boards: {e}")
    
    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo("About", 
                          "🗂️ Multi-Board Kanban Manager\n\n" +
                          "A comprehensive task management system\n" +
                          "with support for multiple Kanban boards.\n\n" +
                          "Features:\n" +
                          "• Multiple board management\n" +
                          "• Drag & drop interface\n" +
                          "• Task prioritization\n" +
                          "• Team collaboration\n" +
                          "• Data export/import")
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        show_shortcuts_dialog(self)
    
    def on_close(self):
        """Handle application close."""
        self.board_manager.close()
        self.root.quit()
        self.root.destroy()

    def invoke_current_board_action(self, method_name):
        """Invoke an action on the currently active embedded board GUI."""
        if not self.current_board_gui:
            messagebox.showwarning("Warning", "No board selected!")
            return

        action = getattr(self.current_board_gui, method_name, None)
        if not action:
            messagebox.showerror("Error", "That action is not available for the current board.")
            return

        action()
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


## @brief Embed single-board interactions inside the multi-board shell.
