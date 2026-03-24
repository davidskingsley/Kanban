## @file
#  @brief Top-level multi-board GUI shell for board selection and application menus.
"""Main multi-board application shell."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from ..board_manager import BoardManager
from .board_actions import (
    create_board_dialog as create_board_dialog_impl,
    delete_current_board_dialog as delete_current_board_dialog_impl,
    export_all_boards as export_all_boards_impl,
    import_boards as import_boards_impl,
    load_board_from_folder_dialog as load_board_from_folder_dialog_impl,
    rename_current_board_dialog as rename_current_board_dialog_impl,
    switch_board_dialog as switch_board_dialog_impl,
)
from .board_navigation import (
    clear_board_interface as clear_board_interface_impl,
    clear_board_selector as clear_board_selector_impl,
    load_board_interface as load_board_interface_impl,
    on_board_selected as on_board_selected_impl,
    refresh_board_display as refresh_board_display_impl,
    setup_main_area as setup_main_area_impl,
)
from .board_statistics import (
    get_completed_count as get_board_completed_count,
    show_board_statistics as show_board_statistics_dialog,
    update_board_info as update_board_summary,
)
from .common import APP_BG
from .common import create_app_root
from .shell_ui import (
    bind_menu_shortcuts as bind_shell_shortcuts,
    setup_menu as setup_shell_menu,
    setup_toolbar as setup_shell_toolbar,
    show_shortcuts as show_shortcuts_dialog,
)

class MultiBoardGUI:
    """Multi-board GUI wrapper for managing multiple Kanban boards."""

    MENU_SHORTCUTS = {
        'undo_current_board_action': ('Ctrl+Z', '<Control-z>'),
        'undo_board_management_action': ('Ctrl+Shift+Z', '<Control-Shift-Z>'),
        'redo_current_board_action': ('Ctrl+Y', '<Control-y>'),
        'redo_board_management_action': ('Ctrl+Shift+Y', '<Control-Shift-Y>'),
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
        'show_due_dates_view': ('Ctrl+Shift+T', '<Control-Shift-T>'),
        'clear_done_cards': ('Ctrl+Shift+K', '<Control-Shift-K>'),
        'create_backup': ('Ctrl+B', '<Control-b>'),
        'cleanup_orphaned_attachment_files': ('Ctrl+Alt+K', '<Control-Alt-k>'),
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
        self.root = create_app_root()
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
        setup_main_area_impl(self)
    
    def refresh_board_display(self):
        """Refresh the board display and selector."""
        refresh_board_display_impl(self)

    def clear_board_selector(self):
        """Clear the board selector state, including readonly combobox text."""
        clear_board_selector_impl(self)

    def get_completed_count(self, stats, board=None):
        """Get the completed-card count for legacy and custom-column boards."""
        return get_board_completed_count(stats, board)

    def update_board_info(self, stats=None, board=None):
        """Update the toolbar summary for the current board."""
        update_board_summary(self, stats, board)
    
    def load_board_interface(self):
        """Load the current board into the interface."""
        load_board_interface_impl(self)
    
    def clear_board_interface(self):
        """Clear the current board interface."""
        clear_board_interface_impl(self)
    
    def on_board_selected(self, event):
        """Handle board selection from the combobox."""
        on_board_selected_impl(self, event)
    
    def create_board_dialog(self):
        """Show dialog to create a new board."""
        create_board_dialog_impl(self)

    def load_board_from_folder_dialog(self):
        """Load a single board from an external folder into the board list."""
        load_board_from_folder_dialog_impl(self)
    
    def switch_board_dialog(self):
        """Show dialog to switch to a different board."""
        switch_board_dialog_impl(self)
    
    def rename_current_board_dialog(self):
        """Show dialog to rename the current board."""
        rename_current_board_dialog_impl(self)
    
    def delete_current_board_dialog(self):
        """Show dialog to delete the current board."""
        delete_current_board_dialog_impl(self)
    
    def show_board_statistics(self):
        """Show statistics for all boards."""
        show_board_statistics_dialog(self)
    
    def export_all_boards(self):
        """Export all boards to a backup file."""
        export_all_boards_impl(self)
    
    def import_boards(self):
        """Import boards from a backup file."""
        import_boards_impl(self)
    
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

    def undo_current_board_action(self):
        """Undo the last change on the currently active board."""
        self.invoke_current_board_action('undo_last_action')

    def undo_board_management_action(self):
        """Undo the last board-management action."""
        description = self.board_manager.undo_last_action()
        if not description:
            messagebox.showinfo("Nothing to Undo", "No board-management action is available to undo.")
            return

        self.refresh_board_display()
        messagebox.showinfo("Undo Complete", f"Undid: {description}")

    def redo_current_board_action(self):
        """Redo the last undone change on the currently active board."""
        self.invoke_current_board_action('redo_last_action')

    def redo_board_management_action(self):
        """Redo the last undone board-management action."""
        description = self.board_manager.redo_last_action()
        if not description:
            messagebox.showinfo("Nothing to Redo", "No board-management action is available to redo.")
            return

        self.refresh_board_display()
        messagebox.showinfo("Redo Complete", f"Redid: {description}")
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


## @brief Embed single-board interactions inside the multi-board shell.
