## @file
#  @brief Multi-board Tkinter interface with embedded board views and dialogs.
"""Multi-board graphical user interface for the Kanban board application."""

from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, colorchooser
from typing import Dict, Optional, List

from .board_manager import BoardManager
from .models import Status, Priority


APP_BG = '#F6F2EB'
PANEL_BG = '#EEE7DD'
SURFACE_BG = '#FFFCF7'
SURFACE_ALT_BG = '#FBF7F1'
OUTLINE_COLOR = '#DED5C8'
TEXT_MUTED = '#6F675E'
HOVER_BG = '#F5E9D5'
PRIMARY_ACTION = '#557C65'
SECONDARY_ACTION = '#8B7E74'
ACCENT_ACTION = '#5D8AC8'
def is_dark_color(color):
    """Return whether a hex color is visually dark."""
    if not color or not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
        return False
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    return luminance < 150


def get_card_palette(card):
    """Return background and text colors for a card."""
    background = card.color or SURFACE_ALT_BG
    if card.color and is_dark_color(card.color):
        return background, 'white', '#F1EEE9'
    return background, '#2F2923', TEXT_MUTED


def format_optional_date(value: Optional[date]) -> str:
    """Return an ISO date string for an optional date value."""
    return value.isoformat() if value else ""


def parse_optional_date(value: str, field_name: str) -> Optional[date]:
    """Parse an optional ISO date string and raise a readable error on invalid input."""
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from error


def center_modal(dialog, parent, width, height):
    """Configure a modal dialog with consistent positioning and styling."""
    dialog.configure(bg=APP_BG)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")


def create_soft_button(parent, text, command, variant='primary', width=None):
    """Create a softer button style with explicit colors for reliable contrast."""
    palette = {
        'primary': (PRIMARY_ACTION, 'white', '#486A57'),
        'secondary': (SECONDARY_ACTION, 'white', '#7B6F66'),
        'accent': (ACCENT_ACTION, 'white', '#4D78B2'),
        'light': ('white', '#3F3A34', HOVER_BG),
    }
    bg, fg, active_bg = palette.get(variant, palette['primary'])
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=fg,
        relief='flat',
        bd=0,
        cursor='hand2',
        font=('Arial', 10, 'bold'),
        padx=16,
        pady=7,
        width=width,
    )


def style_text_input(widget):
    """Apply a softer input style to text-entry widgets."""
    widget.configure(
        bg='white',
        relief='flat',
        bd=0,
        highlightthickness=1,
        highlightbackground=OUTLINE_COLOR,
        highlightcolor=ACCENT_ACTION,
    )


## @brief Coordinate multi-board selection, menus, and embedded board views.
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
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Boards menu
        boards_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Boards", menu=boards_menu)
        boards_menu.add_command(label="Create New Board", command=self.create_board_dialog,
                                accelerator=self.get_shortcut_label('create_board_dialog'))
        boards_menu.add_command(label="Load Board From Folder", command=self.load_board_from_folder_dialog,
                                accelerator=self.get_shortcut_label('load_board_from_folder_dialog'))
        boards_menu.add_separator()
        boards_menu.add_command(label="Switch Board", command=self.switch_board_dialog,
                                accelerator=self.get_shortcut_label('switch_board_dialog'))
        boards_menu.add_command(label="Rename Current Board", command=self.rename_current_board_dialog,
                                accelerator=self.get_shortcut_label('rename_current_board_dialog'))
        boards_menu.add_command(label="Delete Current Board", command=self.delete_current_board_dialog,
                                accelerator=self.get_shortcut_label('delete_current_board_dialog'))
        boards_menu.add_separator()
        boards_menu.add_command(label="Board Statistics", command=self.show_board_statistics,
                                accelerator=self.get_shortcut_label('show_board_statistics'))

        # Cards menu
        cards_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Cards", menu=cards_menu)
        cards_menu.add_command(label="New Card", command=lambda: self.invoke_current_board_action('create_card_dialog'),
                               accelerator=self.get_shortcut_label('create_card_dialog'))
        cards_menu.add_command(label="Edit Card", command=lambda: self.invoke_current_board_action('edit_card_dialog'),
                               accelerator=self.get_shortcut_label('edit_card_dialog'))
        cards_menu.add_command(label="Move Card", command=lambda: self.invoke_current_board_action('move_card_dialog'),
                               accelerator=self.get_shortcut_label('move_card_dialog'))
        cards_menu.add_command(label="Delete Card", command=lambda: self.invoke_current_board_action('delete_card_dialog'),
                               accelerator=self.get_shortcut_label('delete_card_dialog'))
        cards_menu.add_separator()
        card_types_menu = tk.Menu(cards_menu, tearoff=0)
        cards_menu.add_cascade(label="Card Types", menu=card_types_menu)
        card_types_menu.add_command(label="View Card Types", command=lambda: self.invoke_current_board_action('view_card_types_dialog'))
        card_types_menu.add_command(label="Create Card Type", command=lambda: self.invoke_current_board_action('create_card_type_dialog'))
        card_types_menu.add_command(label="Edit Card Type", command=lambda: self.invoke_current_board_action('edit_card_type_dialog'))
        card_types_menu.add_command(label="Delete Card Type", command=lambda: self.invoke_current_board_action('delete_card_type_dialog'))
        cards_menu.add_separator()
        cards_menu.add_command(label="Clear Done Cards", command=lambda: self.invoke_current_board_action('clear_done_cards'),
                               accelerator=self.get_shortcut_label('clear_done_cards'))
        cards_menu.add_command(label="Create Backup", command=lambda: self.invoke_current_board_action('create_backup'),
                               accelerator=self.get_shortcut_label('create_backup'))

        # Filters menu
        filters_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Filters", menu=filters_menu)
        filters_menu.add_command(label="Search Cards", command=lambda: self.invoke_current_board_action('search_dialog'),
                                 accelerator=self.get_shortcut_label('search_dialog'))
        filters_menu.add_command(label="Filter by Priority", command=lambda: self.invoke_current_board_action('filter_priority_dialog'),
                                 accelerator=self.get_shortcut_label('filter_priority_dialog'))
        filters_menu.add_command(label="Filter by Assignee", command=lambda: self.invoke_current_board_action('filter_assignee_dialog'),
                                 accelerator=self.get_shortcut_label('filter_assignee_dialog'))
        filters_menu.add_command(label="Show Late Cards", command=lambda: self.invoke_current_board_action('filter_overdue_dialog'),
                     accelerator=self.get_shortcut_label('filter_overdue_dialog'))
        filters_menu.add_separator()
        filters_menu.add_command(label="Clear Filters", command=lambda: self.invoke_current_board_action('clear_filters'),
                                 accelerator=self.get_shortcut_label('clear_filters'))

        # Columns menu
        columns_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Columns", menu=columns_menu)
        columns_menu.add_command(label="New Column", command=lambda: self.invoke_current_board_action('create_column_dialog'),
                                 accelerator=self.get_shortcut_label('create_column_dialog'))
        columns_menu.add_command(label="Column Properties", command=lambda: self.invoke_current_board_action('rename_column_dialog'),
                                 accelerator=self.get_shortcut_label('rename_column_dialog'))
        columns_menu.add_command(label="Delete Column", command=lambda: self.invoke_current_board_action('delete_column_dialog'),
                                 accelerator=self.get_shortcut_label('delete_column_dialog'))
        columns_menu.add_command(label="Reorder Columns", command=lambda: self.invoke_current_board_action('reorder_columns_dialog'),
                                 accelerator=self.get_shortcut_label('reorder_columns_dialog'))
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Export All Boards", command=self.export_all_boards,
                               accelerator=self.get_shortcut_label('export_all_boards'))
        tools_menu.add_command(label="Import Boards", command=self.import_boards,
                               accelerator=self.get_shortcut_label('import_boards'))
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts,
                              accelerator=self.get_shortcut_label('show_shortcuts'))
        
        self.bind_menu_shortcuts()

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
        self.bind_shortcut(self.MENU_SHORTCUTS['create_board_dialog'][1], self.create_board_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['load_board_from_folder_dialog'][1], self.load_board_from_folder_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['switch_board_dialog'][1], self.switch_board_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['rename_current_board_dialog'][1], self.rename_current_board_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['delete_current_board_dialog'][1], self.delete_current_board_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['show_board_statistics'][1], self.show_board_statistics)
        self.bind_shortcut(self.MENU_SHORTCUTS['create_card_dialog'][1],
                           lambda: self.invoke_current_board_action('create_card_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['edit_card_dialog'][1],
                           lambda: self.invoke_current_board_action('edit_card_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['move_card_dialog'][1],
                           lambda: self.invoke_current_board_action('move_card_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['delete_card_dialog'][1],
                           lambda: self.invoke_current_board_action('delete_card_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['clear_done_cards'][1],
                           lambda: self.invoke_current_board_action('clear_done_cards'))
        self.bind_shortcut(self.MENU_SHORTCUTS['create_backup'][1],
                           lambda: self.invoke_current_board_action('create_backup'))
        self.bind_shortcut(self.MENU_SHORTCUTS['search_dialog'][1],
                           lambda: self.invoke_current_board_action('search_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['filter_priority_dialog'][1],
                           lambda: self.invoke_current_board_action('filter_priority_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['filter_assignee_dialog'][1],
                           lambda: self.invoke_current_board_action('filter_assignee_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['filter_overdue_dialog'][1],
                   lambda: self.invoke_current_board_action('filter_overdue_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['clear_filters'][1],
                           lambda: self.invoke_current_board_action('clear_filters'))
        self.bind_shortcut(self.MENU_SHORTCUTS['create_column_dialog'][1],
                           lambda: self.invoke_current_board_action('create_column_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['rename_column_dialog'][1],
                           lambda: self.invoke_current_board_action('rename_column_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['delete_column_dialog'][1],
                           lambda: self.invoke_current_board_action('delete_column_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['reorder_columns_dialog'][1],
                           lambda: self.invoke_current_board_action('reorder_columns_dialog'))
        self.bind_shortcut(self.MENU_SHORTCUTS['export_all_boards'][1], self.export_all_boards)
        self.bind_shortcut(self.MENU_SHORTCUTS['import_boards'][1], self.import_boards)
        self.bind_shortcut(self.MENU_SHORTCUTS['show_shortcuts'][1], self.show_shortcuts)
        self.bind_shortcut(self.MENU_SHORTCUTS['on_close'][1], self.on_close)
    
    def setup_toolbar(self):
        """Set up the toolbar with board selection and quick actions."""
        toolbar_frame = tk.Frame(
            self.root,
            bg=PANEL_BG,
            height=48,
            highlightthickness=1,
            highlightbackground=OUTLINE_COLOR,
        )
        toolbar_frame.pack(fill='x', padx=8, pady=(8, 4))
        toolbar_frame.pack_propagate(False)
        
        # Board selector
        tk.Label(toolbar_frame, text="Current Board:", 
            bg=PANEL_BG, font=('Arial', 10, 'bold')).pack(side='left', padx=12)
        
        self.board_var = tk.StringVar()
        self.board_selector = ttk.Combobox(toolbar_frame, textvariable=self.board_var,
                                          width=30, state='readonly', style='Soft.TCombobox')
        self.board_selector.pack(side='left', padx=5)
        self.board_selector.bind('<<ComboboxSelected>>', self.on_board_selected)

        spacer = tk.Frame(toolbar_frame, bg=PANEL_BG)
        spacer.pack(side='left', fill='x', expand=True)

        self.board_info_var = tk.StringVar(value="0 cards | 0 completed")
        self.board_info_label = tk.Label(
            toolbar_frame,
            textvariable=self.board_info_var,
            bg=PANEL_BG,
            fg='#3F3A34',
            font=('Arial', 10, 'bold'),
            anchor='e',
            justify='right'
        )
        self.board_info_label.pack(side='right', padx=12)
    
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
        if not stats:
            return 0

        if 'Done' in stats:
            return stats['Done']
        if 'done' in stats:
            return stats['done']

        for key, value in stats.items():
            if isinstance(key, str) and key.strip().lower() == 'done':
                return value

        if board and hasattr(board, 'use_custom_columns') and board.use_custom_columns:
            columns = board.get_columns_ordered()
            if columns:
                return len(columns[-1])

        return 0

    def update_board_info(self, stats=None, board=None):
        """Update the toolbar summary for the current board."""
        if not hasattr(self, 'board_info_var'):
            return

        current_board = board
        if current_board is None and self.current_board_gui is not None:
            current_board = getattr(self.current_board_gui, 'board', None)
        if current_board is None:
            current_board = self.board_manager.get_current_board()

        if stats is None:
            if current_board is not None:
                stats = current_board.get_board_stats()
            else:
                boards = self.board_manager.get_board_list()
                current_board_stats = next((item.get('stats') for item in boards if item.get('is_current')), None)
                stats = current_board_stats

        if not stats:
            if current_board is None:
                self.board_info_var.set("No board selected")
                return
            stats = current_board.get_board_stats()

        if not stats:
            self.board_info_var.set("0 cards | 0 completed")
            return

        total_cards = stats.get('total_cards', 0)
        done_count = self.get_completed_count(stats, current_board)
        access_suffix = " | read only" if current_board is not None and current_board.is_read_only() else ""
        info_text = f"{total_cards} cards | {done_count} completed{access_suffix}"
        self.board_info_var.set(info_text)
    
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
        boards = self.board_manager.get_board_list()
        if not boards:
            messagebox.showinfo("Statistics", "No boards available!")
            return
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Board Statistics")
        stats_window.geometry("500x400")
        stats_window.configure(bg='#F5F5F5')
        
        # Create scrollable text widget
        text_frame = tk.Frame(stats_window, bg='#F5F5F5')
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=('Courier', 10), bg='white')
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Generate statistics
        stats_text = "📊 BOARD STATISTICS\n" + "=" * 50 + "\n\n"
        
        total_cards = 0
        total_todos = 0
        total_in_progress = 0
        total_review = 0
        total_done = 0
        
        for board in boards:
            stats_text += f"📋 {board['name']}\n"
            if board['description']:
                stats_text += f"   📝 {board['description']}\n"
            
            current_marker = " (current)" if board['is_current'] else ""
            stats_text += f"   Status: Active{current_marker}\n"
            
            if 'stats' in board:
                stats = board['stats']
                stats_text += f"   📊 Total cards: {stats['total_cards']}\n"
                
                # Handle different possible key formats for columns
                todo_count = stats.get('To Do', stats.get('todo', 0))
                in_progress_count = stats.get('In Progress', stats.get('in_progress', 0))
                review_count = stats.get('Review', stats.get('review', 0))
                done_count = stats.get('Done', stats.get('done', 0))
                
                stats_text += f"   📝 To Do: {todo_count}\n"
                stats_text += f"   ⚡ In Progress: {in_progress_count}\n"
                stats_text += f"   🔍 Review: {review_count}\n"
                stats_text += f"   ✅ Done: {done_count}\n"
                
                total_cards += stats['total_cards']
                total_todos += todo_count
                total_in_progress += in_progress_count
                total_review += review_count
                total_done += done_count
            else:
                stats_text += "   📊 (Statistics not available)\n"
            
            stats_text += "\n"
        
        stats_text += "🌟 OVERALL SUMMARY\n" + "=" * 30 + "\n"
        stats_text += f"📋 Total boards: {len(boards)}\n"
        stats_text += f"📊 Total cards: {total_cards}\n"
        stats_text += f"📝 Total To Do: {total_todos}\n"
        stats_text += f"⚡ Total In Progress: {total_in_progress}\n"
        stats_text += f"🔍 Total Review: {total_review}\n"
        stats_text += f"✅ Total Done: {total_done}\n"
        
        text_widget.insert(tk.END, stats_text)
        text_widget.config(state='disabled')
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
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
        shortcuts_text = (
            "⌨️ Keyboard Shortcuts\n\n"
            "Boards:\n"
            f"{self.get_shortcut_label('create_board_dialog')} - Create new board\n"
            f"{self.get_shortcut_label('load_board_from_folder_dialog')} - Load board from folder\n"
            f"{self.get_shortcut_label('switch_board_dialog')} - Switch board\n"
            f"{self.get_shortcut_label('rename_current_board_dialog')} - Rename current board\n"
            f"{self.get_shortcut_label('delete_current_board_dialog')} - Delete current board\n"
            f"{self.get_shortcut_label('show_board_statistics')} - Board statistics\n\n"
            "Cards and filters:\n"
            f"{self.get_shortcut_label('create_card_dialog')} - New card\n"
            f"{self.get_shortcut_label('edit_card_dialog')} - Edit card\n"
            f"{self.get_shortcut_label('move_card_dialog')} - Move card\n"
            f"{self.get_shortcut_label('delete_card_dialog')} - Delete card\n"
            f"{self.get_shortcut_label('clear_done_cards')} - Clear done cards\n"
            f"{self.get_shortcut_label('create_backup')} - Create backup\n"
            f"{self.get_shortcut_label('search_dialog')} - Search cards\n"
            f"{self.get_shortcut_label('filter_priority_dialog')} - Filter by priority\n"
            f"{self.get_shortcut_label('filter_assignee_dialog')} - Filter by assignee\n"
            f"{self.get_shortcut_label('filter_overdue_dialog')} - Show late cards\n"
            f"{self.get_shortcut_label('clear_filters')} - Clear filters\n\n"
            "Columns and app:\n"
            f"{self.get_shortcut_label('create_column_dialog')} - New column\n"
            f"{self.get_shortcut_label('rename_column_dialog')} - Column properties\n"
            f"{self.get_shortcut_label('delete_column_dialog')} - Delete column\n"
            f"{self.get_shortcut_label('reorder_columns_dialog')} - Reorder columns\n"
            f"{self.get_shortcut_label('export_all_boards')} - Export all boards\n"
            f"{self.get_shortcut_label('import_boards')} - Import boards\n"
            f"{self.get_shortcut_label('show_shortcuts')} - Show shortcuts\n"
            f"{self.get_shortcut_label('on_close')} - Quit application\n\n"
            "Mouse actions:\n"
            "Double-click card - Edit card\n"
            "Right-click card - Context menu"
        )
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)
    
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
class EmbeddedKanbanGUI:
    """Full-featured embedded Kanban interface with all CLI functionality."""
    
    def __init__(self, parent_frame, board, multi_board_gui):
        self.parent_frame = parent_frame
        self.multi_board_gui = multi_board_gui
        self.board = board
        self.search_filter = None
        self.priority_filter = None
        self.assignee_filter = None
        self.overdue_filter = False
        self.drop_targets = []
        self.drag_preview = None
        
        # Create main interface
        self.setup_full_interface()
    
    def setup_full_interface(self):
        """Set up a full-featured board interface."""
        # Create main container with board area
        main_container = tk.Frame(self.parent_frame, bg=APP_BG)
        main_container.pack(fill='both', expand=True)
        
        # Board display area
        self.setup_board_display(main_container)
        
        # Refresh the display
        self.refresh_display()
    
    def setup_board_display(self, parent):
        """Set up the board display area."""
        # Create scrollable frame for columns
        canvas_frame = tk.Frame(parent, bg=APP_BG)
        canvas_frame.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(canvas_frame, bg=APP_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=APP_BG)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        def sync_board_area_height(event):
            self.canvas.itemconfigure(self.board_window_id, height=event.height)

        self.canvas.bind("<Configure>", sync_board_area_height)
        self.board_window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="bottom", fill="x")
        
        # Status bar
        self.status_bar = tk.Label(parent, text="Ready", anchor="w",
                      bg=PANEL_BG, fg=TEXT_MUTED, font=('Arial', 9),
                      padx=12, pady=6)
        self.status_bar.pack(side="bottom", fill="x")
    
    def refresh_display(self):
        """Refresh the board display with current data."""
        # Clear existing columns
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.drop_targets = []
        
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            self.refresh_custom_columns()
        else:
            self.refresh_legacy_columns()

        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.multi_board_gui:
            self.multi_board_gui.update_board_info(self.board.get_board_stats(), self.board)
        
        self.update_status_bar()

    def ensure_board_writable(self):
        """Show a message and return False if the current board is read-only."""
        if not self.board.is_read_only():
            return True

        messagebox.showwarning("Read Only Board", self.board.get_read_only_message())
        self.status_bar.config(text="🔒 Board is read only")
        return False

    def create_add_card_button(self, parent, header_bg):
        """Create a more visible add-card button for the first column header."""
        return ttk.Button(
            parent,
            text="+ Add",
            command=self.create_card_dialog,
            style='AddCard.TButton',
        )
    
    def refresh_custom_columns(self):
        """Refresh display for boards with custom columns."""
        columns = self.board.get_columns_ordered()
        
        for i, column in enumerate(columns):
            # Create column frame
            col_frame = tk.Frame(
                self.scrollable_frame,
                bg=SURFACE_BG,
                bd=0,
                highlightthickness=1,
                highlightbackground=OUTLINE_COLOR,
                highlightcolor=OUTLINE_COLOR,
                width=250,
            )
            col_frame.pack(side='left', fill='y', padx=8, pady=8)
            col_frame.pack_propagate(False)
            
            # Column header
            header_frame = tk.Frame(col_frame, bg=column.color if hasattr(column, 'color') else '#E0E0E0', height=40)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)
            
            header_label = tk.Label(header_frame, text=f"{column.name} ({len(column)})",
                                   bg=header_frame['bg'], fg='white' if column.color != '#FFFFFF' else 'black',
                                   font=('Arial', 10, 'bold'))
            header_label.pack(side='left', fill='x', expand=True, padx=(8, 0))

            if i == 0:
                add_button = self.create_add_card_button(header_frame, header_frame['bg'])
                add_button.pack(side='right', padx=4, pady=2)
            
            # Add context menu to header
            header_frame.bind("<Button-3>", lambda e, col=column: self.show_column_context_menu(e, col))
            header_label.bind("<Button-3>", lambda e, col=column: self.show_column_context_menu(e, col))
            
            # Cards area
            cards_frame = self.create_scrollable_cards_area(col_frame)
            self.bind_column_mousewheel(col_frame, cards_frame.scroll_canvas)
            self.bind_column_mousewheel(header_frame, cards_frame.scroll_canvas)
            self.bind_column_mousewheel(header_label, cards_frame.scroll_canvas)
            if i == 0:
                self.bind_column_mousewheel(add_button, cards_frame.scroll_canvas)

            self.drop_targets.append({
                'target': column.id,
                'label': column.name,
                'frame': col_frame,
                'default_bg': SURFACE_BG,
                'canvas': cards_frame.scroll_canvas
            })
            
            # Display cards
            self.display_cards_in_frame(cards_frame, column.cards)
    
    def refresh_legacy_columns(self):
        """Refresh display for boards with legacy columns."""
        for i, status in enumerate(Status):
            # Create column frame
            col_frame = tk.Frame(
                self.scrollable_frame,
                bg=SURFACE_BG,
                bd=0,
                highlightthickness=1,
                highlightbackground=OUTLINE_COLOR,
                highlightcolor=OUTLINE_COLOR,
                width=250,
            )
            col_frame.pack(side='left', fill='y', padx=8, pady=8)
            col_frame.pack_propagate(False)
            
            # Column header
            header_colors = {
                Status.TODO: '#FF9800',
                Status.IN_PROGRESS: '#2196F3',
                Status.REVIEW: '#9C27B0',
                Status.DONE: '#4CAF50'
            }
            
            cards = list(self.board.columns[status])
            header_frame = tk.Frame(col_frame, bg=header_colors[status], height=40)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)
            
            header_label = tk.Label(header_frame, text=f"{status.value} ({len(cards)})",
                                   bg=header_frame['bg'], fg='white',
                                   font=('Arial', 10, 'bold'))
            header_label.pack(side='left', fill='x', expand=True, padx=(8, 0))

            if i == 0:
                add_button = self.create_add_card_button(header_frame, header_frame['bg'])
                add_button.pack(side='right', padx=4, pady=2)
            
            # Cards area
            cards_frame = self.create_scrollable_cards_area(col_frame)
            self.bind_column_mousewheel(col_frame, cards_frame.scroll_canvas)
            self.bind_column_mousewheel(header_frame, cards_frame.scroll_canvas)
            self.bind_column_mousewheel(header_label, cards_frame.scroll_canvas)
            if i == 0:
                self.bind_column_mousewheel(add_button, cards_frame.scroll_canvas)

            self.drop_targets.append({
                'target': status,
                'label': status.value,
                'frame': col_frame,
                'default_bg': SURFACE_BG,
                'canvas': cards_frame.scroll_canvas
            })
            
            # Display cards
            self.display_cards_in_frame(cards_frame, cards)
    
    def display_cards_in_frame(self, frame, cards):
        """Display cards in the given frame with filtering applied."""
        filtered_cards = self.apply_filters(cards)
        
        for card in filtered_cards:
            self.create_card_widget(frame, card)

    def create_scrollable_cards_area(self, parent):
        """Create a vertically scrollable area for cards within a column."""
        container = tk.Frame(parent, bg=SURFACE_BG)
        container.pack(fill='both', expand=True, padx=6, pady=6)

        canvas = tk.Canvas(container, bg=SURFACE_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=SURFACE_BG)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        def sync_inner_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        canvas.bind("<Configure>", sync_inner_width)

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        container.bind("<MouseWheel>", on_mousewheel)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        scrollable_frame.scroll_canvas = canvas

        return scrollable_frame

    def bind_column_mousewheel(self, widget, canvas):
        """Bind mouse-wheel scrolling for any widget within a column."""
        widget.bind("<MouseWheel>", lambda event, target_canvas=canvas: self.scroll_column_canvas(event, target_canvas))

    def scroll_column_canvas(self, event, canvas):
        """Scroll a specific column canvas using the mouse wheel."""
        canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def create_card_widget(self, parent, card):
        """Create a card widget."""
        card_bg, text_fg, muted_fg = get_card_palette(card)
        card_type = self.board.get_card_type(card.card_type_id)
        card_type_name = card_type.name if card_type else self.board.get_default_card_type().name
        is_late = card.has_past_end_date() and not self.board.is_card_done(card)
        border_color = '#D6453D' if is_late else '#E8DED1'
        border_width = 2 if is_late else 1
        card_frame = tk.Frame(
            parent,
            bg=card_bg,
            relief='flat',
            bd=0,
            cursor='hand2',
            highlightthickness=border_width,
            highlightbackground=border_color,
            highlightcolor=border_color,
        )
        card_frame.pack(fill='x', pady=4, padx=2)
        card_frame.default_bg = card_bg
        card_frame.default_highlight = border_color
        card_frame.default_highlight_thickness = border_width
        card_frame.drag_start_x = 0
        card_frame.drag_start_y = 0
        card_frame.is_dragging = False
        
        # Priority indicator
        priority_colors = {
            'low': '#4CAF50', 'medium': '#FF9800', 
            'high': '#FF5722', 'critical': '#F44336'
        }
        priority_bar = tk.Frame(card_frame, bg=priority_colors.get(card.priority.value, '#E0E0E0'), height=4)
        priority_bar.pack(fill='x')
        
        # Card content
        content_frame = tk.Frame(card_frame, bg=card_bg)
        content_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Title
        title_label = tk.Label(content_frame, text=card.title, font=('Arial', 9, 'bold'),
                      bg=card_bg, fg=text_fg, anchor='w', wraplength=220)
        title_label.pack(fill='x')
        
        # Description (truncated)
        if card.description:
            desc_text = card.description[:50] + "..." if len(card.description) > 50 else card.description
            desc_label = tk.Label(content_frame, text=desc_text, font=('Arial', 8),
                                 bg=card_bg, fg=muted_fg, anchor='w', wraplength=220)
            desc_label.pack(fill='x')

        if card.start_date or card.end_date or is_late:
            schedule_frame = tk.Frame(content_frame, bg=card_bg)
            schedule_frame.pack(fill='x', pady=(4, 0))

            schedule_parts = []
            if card.start_date and card.end_date:
                schedule_parts.append(f"{card.start_date.isoformat()} -> {card.end_date.isoformat()}")
            elif card.start_date:
                schedule_parts.append(f"Starts {card.start_date.isoformat()}")
            elif card.end_date:
                schedule_parts.append(f"Due {card.end_date.isoformat()}")

            if schedule_parts:
                tk.Label(
                    schedule_frame,
                    text="  ".join(schedule_parts),
                    font=('Arial', 8),
                    bg=card_bg,
                    fg=muted_fg,
                    anchor='w',
                ).pack(side='left')

            if is_late:
                tk.Label(
                    schedule_frame,
                    text='LATE',
                    font=('Arial', 8, 'bold'),
                    bg='#F8D6D2',
                    fg='#A1261A',
                    padx=6,
                    pady=2,
                ).pack(side='right')
        
        # Footer
        footer_frame = tk.Frame(content_frame, bg=card_bg)
        footer_frame.pack(fill='x', pady=(5, 0))

        type_label = tk.Label(
            footer_frame,
            text=card_type_name,
            font=('Arial', 8, 'bold'),
            bg='#F3EEE4',
            fg='#6A5847',
            padx=6,
            pady=2,
        )
        type_label.pack(side='left', padx=(0, 4))

        if card.project:
            project_label = tk.Label(footer_frame, text=f"[{card.project}]",
                                     font=('Arial', 8), bg='#F4E8FF', fg='#6B3FA0', padx=6, pady=2)
            project_label.pack(side='left', padx=(0, 4))
        
        if card.assignee:
            assignee_label = tk.Label(footer_frame, text=f"@{card.assignee}",
                                     font=('Arial', 8), bg='#EDF4FF', fg='#3461A5', padx=6, pady=2)
            assignee_label.pack(side='left')

        parent_card = self.board.get_parent_card(card)
        if parent_card:
            parent_label = tk.Label(footer_frame, text=f"sub of {parent_card.title[:16]}",
                                    font=('Arial', 8), bg='#F2F2F2', fg='#666', padx=6, pady=2)
            parent_label.pack(side='left', padx=(4, 0))
        else:
            completed, total = self.board.get_subcard_progress(card.id)
            if total:
                subcards_label = tk.Label(footer_frame, text=f"{completed}/{total} done",
                                          font=('Arial', 8), bg='#EEF7EA', fg='#3A7A36', padx=6, pady=2)
                subcards_label.pack(side='left', padx=(4, 0))
        
        if card.tags:
            tags_text = " ".join(f"#{tag}" for tag in card.tags[:2])
            if len(card.tags) > 2:
                tags_text += f" +{len(card.tags)-2}"
            tags_label = tk.Label(footer_frame, text=tags_text, font=('Arial', 8),
                                 bg=card_bg, fg=muted_fg)
            tags_label.pack(side='right')

        card_frame.scroll_canvas = getattr(parent, 'scroll_canvas', None)

        self.bind_card_events(card_frame, card)
        return card_frame

    def bind_card_events(self, card_frame, card):
        """Bind click, drag, and context menu events to a card and its children."""
        def bind_recursive(widget):
            widget.bind("<Button-1>", lambda e, frame=card_frame: self.start_card_drag(e, frame))
            widget.bind("<B1-Motion>", lambda e, current_card=card, frame=card_frame: self.drag_card(e, current_card, frame))
            widget.bind("<ButtonRelease-1>", lambda e, current_card=card, frame=card_frame: self.end_card_drag(e, current_card, frame))
            widget.bind("<Double-Button-1>", lambda e, current_card=card: self.edit_card_dialog(current_card))
            widget.bind("<Button-3>", lambda e, current_card=card: self.show_card_context_menu(e, current_card))
            if getattr(card_frame, 'scroll_canvas', None) is not None:
                widget.bind("<MouseWheel>", lambda e, canvas=card_frame.scroll_canvas: self.scroll_column_canvas(e, canvas))

            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(card_frame)

    def start_card_drag(self, event, card_frame):
        """Initialize drag state for a card."""
        card_frame.drag_start_x = event.x_root
        card_frame.drag_start_y = event.y_root
        card_frame.is_dragging = False
        card_frame.lift()

    def drag_card(self, event, card, card_frame):
        """Track drag motion and highlight the current drop target."""
        if not card_frame.is_dragging:
            dx = abs(event.x_root - card_frame.drag_start_x)
            dy = abs(event.y_root - card_frame.drag_start_y)
            if dx > 5 or dy > 5:
                card_frame.is_dragging = True
                card_frame.config(bg='#F8FBFF', highlightbackground=ACCENT_ACTION, highlightcolor=ACCENT_ACTION)
                self.create_drag_preview(card, event.x_root, event.y_root)
                self.status_bar.config(text=f"Dragging '{card.title}'")

        if card_frame.is_dragging:
            self.move_drag_preview(event.x_root, event.y_root)
            self.highlight_drop_targets(event.x_root, event.y_root)
            self.auto_scroll_drop_target(event.x_root, event.y_root)

    def end_card_drag(self, event, card, card_frame):
        """Complete a drag operation and move the card if dropped on a new column."""
        if card_frame.is_dragging:
            target = self.get_drop_target(event.x_root, event.y_root)
            self.clear_drop_target_highlights()
            self.destroy_drag_preview()
            default_highlight = getattr(card_frame, 'default_highlight', '#E8DED1')
            card_frame.config(
                bg=getattr(card_frame, 'default_bg', SURFACE_ALT_BG),
                highlightthickness=getattr(card_frame, 'default_highlight_thickness', 1),
                highlightbackground=default_highlight,
                highlightcolor=default_highlight,
            )
            card_frame.is_dragging = False

            if target is not None and not self.is_same_column(card, target):
                if not self.ensure_board_writable():
                    self.refresh_display()
                    return
                if self.board.move_card(card.id, target):
                    target_name = self.get_target_label(target)
                    self.refresh_display()
                    self.status_bar.config(text=f"✅ Moved card to {target_name}")
                    return

            self.refresh_display()

    def create_drag_preview(self, card, x, y):
        """Create a floating preview of the card while dragging."""
        self.destroy_drag_preview()

        preview = tk.Toplevel(self.parent_frame)
        preview.overrideredirect(True)
        preview.attributes('-topmost', True)
        preview.configure(bg='#DCE8F8')

        preview_bg, preview_fg, preview_muted = get_card_palette(card)
        card_type = self.board.get_card_type(card.card_type_id)
        card_type_name = card_type.name if card_type else self.board.get_default_card_type().name
        preview_frame = tk.Frame(preview, bg=preview_bg, relief='flat', bd=0,
                     highlightthickness=1, highlightbackground='#C8D8F0')
        preview_frame.pack(fill='both', expand=True)

        priority_colors = {
            'low': '#4CAF50',
            'medium': '#FF9800',
            'high': '#FF5722',
            'critical': '#F44336'
        }
        tk.Frame(preview_frame, bg=priority_colors.get(card.priority.value, '#E0E0E0'), height=4).pack(fill='x')

        content = tk.Frame(preview_frame, bg=preview_bg, padx=8, pady=6)
        content.pack(fill='both', expand=True)

        tk.Label(content, text=card.title, font=('Arial', 9, 'bold'), bg=preview_bg, fg=preview_fg, anchor='w',
                 justify='left', wraplength=190).pack(fill='x')

        subtitle_parts = [card_type_name]
        if card.project:
            subtitle_parts.append(f"[{card.project}]")
        if card.assignee:
            subtitle_parts.append(f"@{card.assignee}")
        parent_card = self.board.get_parent_card(card)
        if parent_card:
            subtitle_parts.append(f"sub of {parent_card.title[:16]}")
        else:
            completed, total = self.board.get_subcard_progress(card.id)
            if total:
                subtitle_parts.append(f"{completed}/{total} done")
        if card.tags:
            subtitle_parts.append(" ".join(f"#{tag}" for tag in card.tags[:2]))
        if card.end_date:
            subtitle_parts.append(f"due {card.end_date.isoformat()}")
        if card.has_past_end_date() and not self.board.is_card_done(card):
            subtitle_parts.append('LATE')
        if subtitle_parts:
            tk.Label(content, text="  ".join(subtitle_parts), font=('Arial', 8), bg=preview_bg, fg=preview_muted,
                     anchor='w', justify='left', wraplength=190).pack(fill='x', pady=(2, 0))

        preview.geometry(f"220x60+{x + 12}+{y + 12}")
        self.drag_preview = preview

    def move_drag_preview(self, x, y):
        """Move the floating drag preview with the cursor."""
        if self.drag_preview and self.drag_preview.winfo_exists():
            self.drag_preview.geometry(f"+{x + 12}+{y + 12}")

    def destroy_drag_preview(self):
        """Destroy any active floating drag preview."""
        if self.drag_preview and self.drag_preview.winfo_exists():
            self.drag_preview.destroy()
        self.drag_preview = None

    def highlight_drop_targets(self, x, y):
        """Highlight the drop target under the cursor."""
        active_target = self.get_drop_target(x, y)
        for drop_target in self.drop_targets:
            frame = drop_target['frame']
            if drop_target['target'] == active_target:
                frame.config(bg='#F2F9F3', highlightbackground='#BFD8C2', highlightcolor='#BFD8C2')
            else:
                frame.config(bg=drop_target['default_bg'], highlightbackground=OUTLINE_COLOR, highlightcolor=OUTLINE_COLOR)

    def clear_drop_target_highlights(self):
        """Clear all drop target highlights."""
        for drop_target in self.drop_targets:
            drop_target['frame'].config(bg=drop_target['default_bg'], highlightbackground=OUTLINE_COLOR, highlightcolor=OUTLINE_COLOR)

    def auto_scroll_drop_target(self, x, y):
        """Auto-scroll the hovered column when dragging near its top or bottom edge."""
        for drop_target in self.drop_targets:
            frame = drop_target['frame']
            frame_x = frame.winfo_rootx()
            frame_y = frame.winfo_rooty()
            frame_width = frame.winfo_width()
            frame_height = frame.winfo_height()

            if frame_x <= x <= frame_x + frame_width and frame_y <= y <= frame_y + frame_height:
                canvas = drop_target.get('canvas')
                if canvas is None:
                    return

                threshold = 40
                if y <= frame_y + threshold:
                    canvas.yview_scroll(-1, 'units')
                elif y >= frame_y + frame_height - threshold:
                    canvas.yview_scroll(1, 'units')
                return

    def get_drop_target(self, x, y):
        """Get the column target currently under the cursor."""
        for drop_target in self.drop_targets:
            frame = drop_target['frame']
            frame_x = frame.winfo_rootx()
            frame_y = frame.winfo_rooty()
            frame_width = frame.winfo_width()
            frame_height = frame.winfo_height()

            if frame_x <= x <= frame_x + frame_width and frame_y <= y <= frame_y + frame_height:
                return drop_target['target']
        return None

    def get_target_label(self, target):
        """Get the display label for a drop target."""
        for drop_target in self.drop_targets:
            if drop_target['target'] == target:
                return drop_target['label']
        return str(target)

    def is_same_column(self, card, target):
        """Check whether the target matches the card's current column."""
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            return card.column_id == target
        return card.status == target

    def parse_selection_index(self, selected, count):
        """Parse a 1-based selection string and return a 0-based index, or None if cancelled."""
        if selected is None:
            return None

        selected = selected.strip()
        if not selected:
            return None

        try:
            index = int(selected) - 1
        except ValueError:
            return False

        if 0 <= index < count:
            return index
        return False

    def choose_option(self, title, prompt, options, initial_index=0):
        """Show a dropdown selection dialog and return the selected option or None."""
        return SelectionDialog(
            self.parent_frame,
            title,
            prompt,
            options,
            initial_index=initial_index
        ).result
    
    def apply_filters(self, cards):
        """Apply current filters to the cards list."""
        filtered = cards
        
        if self.search_filter:
            filtered = [c for c in filtered if 
                       self.search_filter.lower() in c.title.lower() or
                       self.search_filter.lower() in c.description.lower()]
        
        if self.priority_filter:
            filtered = [c for c in filtered if c.priority.value == self.priority_filter]
        
        if self.assignee_filter:
            filtered = [c for c in filtered if c.assignee == self.assignee_filter]

        if self.overdue_filter:
            filtered = [c for c in filtered if c.has_past_end_date() and not self.board.is_card_done(c)]
        
        return filtered
    
    def update_status_bar(self):
        """Update the status bar with current information."""
        stats = self.board.get_board_stats()
        filter_info = ""
        if any([self.search_filter, self.priority_filter, self.assignee_filter, self.overdue_filter]):
            filters = []
            if self.search_filter: filters.append(f"Search: {self.search_filter}")
            if self.priority_filter: filters.append(f"Priority: {self.priority_filter}")
            if self.assignee_filter: filters.append(f"Assignee: {self.assignee_filter}")
            if self.overdue_filter: filters.append("Late only")
            filter_info = f" | Filtered: {', '.join(filters)}"
        
        access_info = " | Read only" if self.board.is_read_only() else ""
        status_text = f"📊 {stats['total_cards']} total cards{filter_info}{access_info} | Ready"
        self.status_bar.config(text=status_text)

    # Card Management Methods
    def create_card_dialog(self):
        """Show dialog to create a new card."""
        if not self.ensure_board_writable():
            return

        dialog = CardDialog(self.parent_frame, "Create New Card", board=self.board, on_change=self.refresh_display)
        if dialog.result:
            title, description, priority, assignee, project, start_date, end_date, color, card_type_id, tags = dialog.result
            
            # Get target column
            if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
                columns = self.board.get_columns_ordered()
                if columns:
                    target_column = columns[0].id  # Add to first column
                    card = self.board.create_card(title, description, priority, target_column, project, start_date, end_date, color=color, card_type_id=card_type_id)
                else:
                    messagebox.showerror("Error", "No columns available!")
                    return
            else:
                card = self.board.create_card(title, description, priority, Status.TODO, project, start_date, end_date, color=color, card_type_id=card_type_id)
            
            if assignee:
                self.board.edit_card(card.id, assignee=assignee)
            
            for tag in tags:
                card.add_tag(tag)
            
            self.refresh_display()
            self.status_bar.config(text=f"✅ Created card: {title}")

    def edit_card_dialog(self, card=None):
        """Show dialog to edit a card."""
        if not self.ensure_board_writable():
            return

        if not card:
            # Let user select a card
            card = self.select_card_dialog("Select Card to Edit")
            if not card:
                return
        
        # Pre-fill dialog with current values
        dialog = CardDialog(self.parent_frame, "Edit Card", 
                          initial_title=card.title,
                          initial_description=card.description,
                          initial_priority=card.priority,
                          initial_assignee=card.assignee,
                          initial_project=card.project,
                          initial_start_date=card.start_date,
                          initial_end_date=card.end_date,
                          initial_color=card.color,
                          initial_card_type_id=card.card_type_id,
                          initial_tags=list(card.tags),
                          board=self.board,
                          card=card,
                          on_change=self.refresh_display)
        
        if dialog.result:
            title, description, priority, assignee, project, start_date, end_date, color, card_type_id, tags = dialog.result
            self.board.edit_card(card.id, title=title, description=description, 
                               priority=priority, assignee=assignee, project=project, start_date=start_date,
                               end_date=end_date, color=color,
                               card_type_id=card_type_id)
            
            # Update tags
            card.tags.clear()
            for tag in tags:
                card.add_tag(tag)
            
            self.refresh_display()
            self.status_bar.config(text=f"✅ Updated card: {title}")

    def move_card_dialog(self):
        """Show dialog to move a card."""
        if not self.ensure_board_writable():
            return

        # Select card
        card = self.select_card_dialog("Select Card to Move")
        if not card:
            return
        
        # Select target column/status
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            columns = self.board.get_columns_ordered()
            option_map = {col.name: col for col in columns}
            selected = self.choose_option("Move Card", f"Move '{card.title}' to column:", list(option_map.keys()))
            if selected is None:
                return
            target_column = option_map[selected]
            self.board.move_card(card.id, target_column.id)
            self.refresh_display()
            self.status_bar.config(text=f"✅ Moved card to {target_column.name}")
        else:
            # Legacy columns
            statuses = list(Status)
            option_map = {status.value: status for status in statuses}
            selected = self.choose_option("Move Card", f"Move '{card.title}' to status:", list(option_map.keys()))
            if selected is None:
                return
            target_status = option_map[selected]
            self.board.move_card(card.id, target_status)
            self.refresh_display()
            self.status_bar.config(text=f"✅ Moved card to {target_status.value}")

    def delete_card_dialog(self):
        """Show dialog to delete a card."""
        if not self.ensure_board_writable():
            return

        card = self.select_card_dialog("Select Card to Delete")
        if not card:
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete card '{card.title}'?\nThis cannot be undone."):
            self.board.delete_card(card.id)
            self.refresh_display()
            self.status_bar.config(text=f"📋 Deleted card: {card.title}")

    def select_card_dialog(self, title):
        """Show dialog to select a card from available cards."""
        # Get all cards from all columns
        all_cards = []
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            columns = self.board.get_columns_ordered()
            for column in columns:
                for card in column.cards:
                    all_cards.append((card, column.name))
        else:
            for status in Status:
                for card in self.board.columns[status]:
                    all_cards.append((card, status.value))
        
        if not all_cards:
            messagebox.showinfo("No Cards", "No cards available!")
            return None
        
        option_labels = []
        for card, location in all_cards:
            suffix = " <subcard>" if card.parent_id else ""
            option_labels.append(f"{card.title} ({location}){suffix}")
        selected = self.choose_option(title, "Select a card:", option_labels)
        if selected is None:
            return None

        return all_cards[option_labels.index(selected)][0]

    # Search and Filter Methods
    def search_dialog(self):
        """Show search dialog."""
        search_term = simpledialog.askstring("Search Cards", "Enter search term:")
        if search_term:
            self.search_filter = search_term
            self.refresh_display()
        
    def filter_priority_dialog(self):
        """Show priority filter dialog."""
        priorities = ['low', 'medium', 'high', 'critical']
        priority_map = {priority.title(): priority for priority in priorities}
        selected = self.choose_option("Filter by Priority", "Select priority:", list(priority_map.keys()))
        if selected is None:
            return

        self.priority_filter = priority_map[selected]
        self.refresh_display()

    def filter_assignee_dialog(self):
        """Show assignee filter dialog."""
        # Get unique assignees
        assignees = set()
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            columns = self.board.get_columns_ordered()
            for column in columns:
                for card in column.cards:
                    if card.assignee:
                        assignees.add(card.assignee)
        else:
            for status in Status:
                for card in self.board.columns[status]:
                    if card.assignee:
                        assignees.add(card.assignee)
        
        if not assignees:
            messagebox.showinfo("No Assignees", "No cards have assignees!")
            return

        assignee_list = sorted(assignees)
        selected = self.choose_option("Filter by Assignee", "Select assignee:", assignee_list)
        if selected is None:
            return

        self.assignee_filter = selected
        self.refresh_display()

    def filter_overdue_dialog(self):
        """Show only cards whose end date has passed and are not done."""
        has_overdue_cards = any(
            card.has_past_end_date() and not self.board.is_card_done(card)
            for card in self.board.get_all_cards()
        )
        if not has_overdue_cards:
            messagebox.showinfo("No Late Cards", "No cards are currently late.")
            return

        self.overdue_filter = True
        self.refresh_display()
        self.status_bar.config(text="⏰ Showing late cards only")

    def clear_filters(self):
        """Clear all active filters."""
        self.search_filter = None
        self.priority_filter = None
        self.assignee_filter = None
        self.overdue_filter = False
        self.refresh_display()
        self.status_bar.config(text="🔄 Filters cleared")

    # Column Management Methods (for custom columns)
    def create_column_dialog(self):
        """Show dialog to create a new column."""
        if not self.ensure_board_writable():
            return

        if not (hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns):
            messagebox.showinfo("Not Available", "Column management only available for custom column boards!")
            return
        
        dialog = ColumnDialog(self.parent_frame, "Create Column")
        if not dialog.result:
            return
        name, color_value = dialog.result
        column_id = self.board.create_column(name, color=color_value)
        self.refresh_display()
        self.status_bar.config(text=f"✅ Created column: {name}")

    def rename_column_dialog(self):
        """Show dialog to edit a column's properties."""
        if not self.ensure_board_writable():
            return

        if not (hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns):
            messagebox.showinfo("Not Available", "Column management only available for custom column boards!")
            return
            
        columns = self.board.get_columns_ordered()
        if not columns:
            messagebox.showinfo("No Columns", "No columns available!")
            return

        option_map = {column.name: column for column in columns}
        selected = self.choose_option("Column Properties", "Select column:", list(option_map.keys()))
        if selected is None:
            return

        column = option_map[selected]
        self.modify_specific_column(column)

    def delete_column_dialog(self):
        """Show dialog to delete a column."""
        if not self.ensure_board_writable():
            return

        if not (hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns):
            messagebox.showinfo("Not Available", "Column management only available for custom column boards!")
            return
            
        columns = self.board.get_columns_ordered()
        if len(columns) <= 1:
            messagebox.showinfo("Cannot Delete", "Must have at least one column!")
            return

        option_map = {f"{col.name} ({len(col)} cards)": col for col in columns}
        selected = self.choose_option("Delete Column", "Select column to delete:", list(option_map.keys()))
        if selected is None:
            return

        try:
            column_to_delete = option_map[selected]
            
            # If column has cards, ask for migration target
            if len(column_to_delete) > 0:
                remaining_columns = [col for col in columns if col.id != column_to_delete.id]
                migration_map = {col.name: col for col in remaining_columns}
                migration_selected = self.choose_option(
                    "Migrate Cards",
                    f"Move cards from '{column_to_delete.name}' to:",
                    list(migration_map.keys())
                )
                if migration_selected is None:
                    return

                target_column = migration_map[migration_selected]
                
                if messagebox.askyesno("Confirm Delete", 
                                     f"Delete column '{column_to_delete.name}' and move {len(column_to_delete)} cards to '{target_column.name}'?"):
                    self.board.delete_column(column_to_delete.id, target_column.id)
                    self.refresh_display()
                    self.status_bar.config(text=f"📋 Deleted column: {column_to_delete.name}")
            else:
                if messagebox.askyesno("Confirm Delete", f"Delete empty column '{column_to_delete.name}'?"):
                    self.board.delete_column(column_to_delete.id)
                    self.refresh_display()
                    self.status_bar.config(text=f"📋 Deleted column: {column_to_delete.name}")
                    
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Please enter a valid number!")

    def reorder_columns_dialog(self):
        """Show dialog to reorder columns."""
        if not self.ensure_board_writable():
            return

        if not (hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns):
            messagebox.showinfo("Not Available", "Column management only available for custom column boards!")
            return
            
        columns = self.board.get_columns_ordered()
        if len(columns) <= 1:
            messagebox.showinfo("Cannot Reorder", "Need at least two columns to reorder!")
            return

        dialog = ReorderColumnsDialog(self.parent_frame, columns)
        if dialog.result:
            self.board.reorder_columns(dialog.result)
            self.refresh_display()
            self.status_bar.config(text="🔄 Columns reordered")

    # Context Menu Methods
    def show_card_context_menu(self, event, card):
        """Show context menu for a card."""
        menu = tk.Menu(self.parent_frame, tearoff=0)
        menu.add_command(label="📝 Edit", command=lambda: self.edit_card_dialog(card))
        if not card.parent_id:
            menu.add_command(label="➕ Add Subcard", command=lambda: self.add_subcard_dialog(card))
        menu.add_command(label="🔄 Move", command=lambda: self.move_card_specific(card))
        menu.add_command(label="🏷️ Add Tag", command=lambda: self.add_tag_to_card(card))
        menu.add_command(label="ℹ️ Details", command=lambda: self.show_card_details(card))
        menu.add_separator()
        menu.add_command(label="🗑️ Delete", command=lambda: self.delete_specific_card(card))
        
        menu.post(event.x_root, event.y_root)

    def show_column_context_menu(self, event, column):
        """Show context menu for a column."""
        if not (hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns):
            return
            
        menu = tk.Menu(self.parent_frame, tearoff=0)
        menu.add_command(label="✏️ Column Properties", command=lambda: self.modify_specific_column(column))
        menu.add_separator()
        menu.add_command(label="🗑️ Delete", command=lambda: self.delete_specific_column(column))
        
        menu.post(event.x_root, event.y_root)

    def move_card_specific(self, card):
        """Move a specific card."""
        if not self.ensure_board_writable():
            return

        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            columns = self.board.get_columns_ordered()
            option_map = {col.name: col for col in columns}
            selected = self.choose_option("Move Card", f"Move '{card.title}' to:", list(option_map.keys()))
            if selected is None:
                return

            target_column = option_map[selected]
            self.board.move_card(card.id, target_column.id)
            self.refresh_display()
            self.status_bar.config(text=f"✅ Moved card to {target_column.name}")

    def delete_specific_card(self, card):
        """Delete a specific card."""
        if not self.ensure_board_writable():
            return

        if messagebox.askyesno("Confirm Delete", f"Delete card '{card.title}'?"):
            self.board.delete_card(card.id)
            self.refresh_display()
            self.status_bar.config(text=f"📋 Deleted card: {card.title}")

    def add_tag_to_card(self, card):
        """Add a tag to a specific card."""
        if not self.ensure_board_writable():
            return

        tag = simpledialog.askstring("Add Tag", f"Add tag to '{card.title}':")
        if tag:
            card.add_tag(tag)
            self.refresh_display()
            self.status_bar.config(text=f"🏷️ Added tag '{tag}' to {card.title}")

    def add_subcard_dialog(self, parent_card):
        """Create a real child card under the provided parent card."""
        if not self.ensure_board_writable():
            return

        dialog = CardDialog(
            self.parent_frame,
            f"Add Subcard to '{parent_card.title}'",
            initial_project=parent_card.project,
            initial_color=parent_card.color,
            initial_card_type_id=parent_card.card_type_id,
            board=self.board,
        )

        if dialog.result:
            title, description, priority, assignee, project, start_date, end_date, color, card_type_id, tags = dialog.result
            try:
                subcard = self.board.create_subcard(parent_card.id, title, description, priority, project, color, card_type_id, start_date, end_date)
                if assignee:
                    self.board.edit_card(subcard.id, assignee=assignee)

                for tag in tags:
                    subcard.add_tag(tag)

                self.refresh_display()
                self.status_bar.config(text=f"✅ Created subcard: {title}")
            except ValueError as error:
                messagebox.showerror("Error", str(error))

    def show_card_details(self, card):
        """Show detailed information about a card."""
        details = f"📋 Card Details\n\n"
        details += f"Title: {card.title}\n"
        details += f"Description: {card.description or 'None'}\n"
        details += f"Priority: {card.priority.value.title()}\n"
        card_type = self.board.get_card_type(card.card_type_id)
        details += f"Type: {card_type.name if card_type else self.board.get_default_card_type().name}\n"
        details += f"Project: {card.project or 'None'}\n"
        details += f"Assignee: {card.assignee or 'None'}\n"
        details += f"Start Date: {card.start_date.isoformat() if card.start_date else 'None'}\n"
        details += f"End Date: {card.end_date.isoformat() if card.end_date else 'None'}\n"
        details += f"Late: {'Yes' if card.has_past_end_date() and not self.board.is_card_done(card) else 'No'}\n"
        details += f"Color: {card.color or 'Default'}\n"
        details += f"Tags: {', '.join(card.tags) if card.tags else 'None'}\n"
        details += f"Notes: {len(card.notes)}\n"
        parent_card = self.board.get_parent_card(card)
        details += f"Parent: {parent_card.title if parent_card else 'None'}\n"
        details += f"Created: {card.created_at.strftime('%Y-%m-%d %H:%M') if card.created_at else 'Unknown'}\n"
        details += f"Updated: {card.updated_at.strftime('%Y-%m-%d %H:%M') if card.updated_at else 'Unknown'}\n"

        if card.notes:
            details += "\nNotes:\n"
            for note in card.notes:
                details += f"- {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"

        completed, total = self.board.get_subcard_progress(card.id)
        if total:
            details += "\nSubcards:\n"
            for subcard in self.board.get_subcards(card.id):
                tick = "[x]" if self.board.is_card_done(subcard) else "[ ]"
                details += f"{tick} {subcard.title} ({self.board.get_card_location_label(subcard)})\n"
        
        messagebox.showinfo("Card Details", details)

    def modify_specific_column(self, column):
        """Modify a specific column's name and color."""
        if not self.ensure_board_writable():
            return

        dialog = ColumnDialog(
            self.parent_frame,
            "Column Properties",
            initial_name=column.name,
            initial_color=column.color,
        )
        if not dialog.result:
            return

        new_name, new_color = dialog.result
        self.board.rename_column(column.id, new_name)
        self.board.change_column_color(column.id, new_color)
        self.refresh_display()
        self.status_bar.config(text=f"✅ Updated column: {new_name}")

    def change_column_color(self, column):
        """Change a column's color."""
        self.modify_specific_column(column)

    def view_card_types_dialog(self):
        """Show all configured card types for the current board."""
        CardTypesOverviewDialog(self.parent_frame, self.board)

    def create_card_type_dialog(self):
        """Create a new card type."""
        if not self.ensure_board_writable():
            return

        dialog = CardTypeDialog(self.parent_frame, "Create Card Type")
        if not dialog.result:
            return

        name, description, default_project, default_color = dialog.result
        try:
            self.board.create_card_type(name, description, default_project, default_color)
            self.refresh_display()
            self.status_bar.config(text=f"✅ Created card type: {name}")
        except ValueError as error:
            messagebox.showerror("Error", str(error))

    def edit_card_type_dialog(self):
        """Edit an existing card type."""
        if not self.ensure_board_writable():
            return

        card_type = self.select_card_type_dialog("Select Card Type to Edit")
        if not card_type:
            return

        dialog = CardTypeDialog(
            self.parent_frame,
            "Edit Card Type",
            initial_name=card_type.name,
            initial_description=card_type.description,
            initial_project=card_type.default_project,
            initial_color=card_type.default_color,
            allow_name_edit=card_type.id != self.board.get_default_card_type_id(),
        )
        if not dialog.result:
            return

        name, description, default_project, default_color = dialog.result
        try:
            self.board.edit_card_type(card_type.id, name, description, default_project, default_color)
            self.refresh_display()
            self.status_bar.config(text=f"✅ Updated card type: {name}")
        except ValueError as error:
            messagebox.showerror("Error", str(error))

    def delete_card_type_dialog(self):
        """Delete a card type and optionally delete or reassign affected cards."""
        if not self.ensure_board_writable():
            return

        card_type = self.select_card_type_dialog("Select Card Type to Delete", exclude_default=True)
        if not card_type:
            return

        cards_using_type = self.board.get_cards_by_type(card_type.id)
        if cards_using_type:
            action = self.choose_option(
                "Delete Card Type",
                f"'{card_type.name}' is used by {len(cards_using_type)} card(s). Choose what to do:",
                ["Delete all cards of this type", "Change those cards to another type"],
            )
            if action is None:
                return

            try:
                if action == "Delete all cards of this type":
                    if messagebox.askyesno("Confirm Delete", f"Delete card type '{card_type.name}' and all cards using it?"):
                        self.board.delete_card_type(card_type.id, delete_cards=True)
                        self.refresh_display()
                        self.status_bar.config(text=f"📋 Deleted card type: {card_type.name}")
                    return

                replacement = self.select_card_type_dialog(
                    "Replacement Card Type",
                    exclude_ids={card_type.id},
                )
                if not replacement:
                    return
                if messagebox.askyesno("Confirm Delete", f"Delete '{card_type.name}' and change its cards to '{replacement.name}'?"):
                    self.board.delete_card_type(card_type.id, delete_cards=False, replacement_type_id=replacement.id)
                    self.refresh_display()
                    self.status_bar.config(text=f"📋 Deleted card type: {card_type.name}")
            except ValueError as error:
                messagebox.showerror("Error", str(error))
            return

        if messagebox.askyesno("Confirm Delete", f"Delete card type '{card_type.name}'?"):
            self.board.delete_card_type(card_type.id, delete_cards=False)
            self.refresh_display()
            self.status_bar.config(text=f"📋 Deleted card type: {card_type.name}")

    def select_card_type_dialog(self, title, exclude_default=False, exclude_ids=None):
        """Show dialog to select a card type from the current board."""
        exclude_ids = set(exclude_ids or [])
        card_types = []
        for card_type in self.board.get_card_types_ordered():
            if exclude_default and card_type.id == self.board.get_default_card_type_id():
                continue
            if card_type.id in exclude_ids:
                continue
            card_types.append(card_type)

        if not card_types:
            messagebox.showinfo("No Card Types", "No matching card types are available!")
            return None

        option_map = {}
        default_type_id = self.board.get_default_card_type_id()
        last_used_id = self.board.get_last_used_card_type().id
        for card_type in card_types:
            flags = []
            if card_type.id == default_type_id:
                flags.append('default')
            if card_type.id == last_used_id:
                flags.append('last used')
            suffix = f" [{' | '.join(flags)}]" if flags else ''
            option_map[f"{card_type.name}{suffix}"] = card_type

        selected = self.choose_option(title, "Select a card type:", list(option_map.keys()))
        if selected is None:
            return None
        return option_map[selected]

    def delete_specific_column(self, column):
        """Delete a specific column."""
        if not self.ensure_board_writable():
            return

        columns = self.board.get_columns_ordered()
        if len(columns) <= 1:
            messagebox.showinfo("Cannot Delete", "Must have at least one column!")
            return
            
        if len(column) > 0:
            remaining_columns = [col for col in columns if col.id != column.id]
            migration_map = {col.name: col for col in remaining_columns}
            migration_selected = self.choose_option(
                "Migrate Cards",
                f"Move cards from '{column.name}' to:",
                list(migration_map.keys())
            )
            if migration_selected is None:
                return

            target_column = migration_map[migration_selected]
            if messagebox.askyesno("Confirm Delete", 
                                 f"Delete column and move cards to '{target_column.name}'?"):
                self.board.delete_column(column.id, target_column.id)
                self.refresh_display()
                self.status_bar.config(text=f"📋 Deleted column: {column.name}")
        else:
            if messagebox.askyesno("Confirm Delete", f"Delete empty column '{column.name}'?"):
                self.board.delete_column(column.id)
                self.refresh_display()
                self.status_bar.config(text=f"📋 Deleted column: {column.name}")

    # Other Methods  
    def clear_done_cards(self):
        """Clear all cards from Done column/status."""
        if not self.ensure_board_writable():
            return

        count = self.board.clear_done_cards()
        if count > 0:
            self.refresh_display()
            self.status_bar.config(text=f"🗑️ Cleared {count} done cards")
        else:
            messagebox.showinfo("No Cards", "No done cards to clear!")

    def create_backup(self):
        """Create a backup of the board."""
        try:
            backup_path = self.board.storage.create_backup()
            messagebox.showinfo("Backup Created", f"Backup created at:\n{backup_path}")
            self.status_bar.config(text="💾 Backup created")
        except Exception as e:
            messagebox.showerror("Backup Failed", f"Failed to create backup:\n{str(e)}")
    
    def cleanup(self):
        """Clean up resources when switching boards."""
        try:
            if not self.parent_frame or not self.parent_frame.winfo_exists():
                return
        except tk.TclError:
            return

        for widget in self.parent_frame.winfo_children():
            widget.destroy()


## @brief Modal dialog for capturing board name and description values.
class BoardDialog:
    """Dialog for creating/editing board information."""
    
    def __init__(self, parent, default_storage_dir, title="Board Information"):
        self.result = None
        self.default_storage_dir = default_storage_dir
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        center_modal(self.dialog, parent, 520, 320)
        
        self.setup_ui()
        
        # Focus on name entry
        self.name_entry.focus()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, bg=APP_BG)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Board name
        tk.Label(main_frame, text="Board Name:", font=('Arial', 11, 'bold'),
            bg=APP_BG).pack(anchor='w')
        self.name_entry = tk.Entry(main_frame, font=('Arial', 11), width=40)
        self.name_entry.pack(fill='x', pady=(5, 15))
        style_text_input(self.name_entry)
        
        # Board description
        tk.Label(main_frame, text="Description (optional):", font=('Arial', 11, 'bold'),
            bg=APP_BG).pack(anchor='w')
        self.desc_text = tk.Text(main_frame, height=4, font=('Arial', 10))
        self.desc_text.pack(fill='both', expand=True, pady=(5, 15))
        style_text_input(self.desc_text)

        tk.Label(main_frame, text="Storage Folder:", font=('Arial', 11, 'bold'),
            bg=APP_BG).pack(anchor='w')

        storage_frame = tk.Frame(main_frame, bg=APP_BG)
        storage_frame.pack(fill='x', pady=(5, 20))

        self.storage_var = tk.StringVar(value=self.default_storage_dir)
        self.storage_entry = tk.Entry(storage_frame, textvariable=self.storage_var, font=('Arial', 10))
        self.storage_entry.pack(side='left', fill='x', expand=True)
        style_text_input(self.storage_entry)

        create_soft_button(storage_frame, "Browse", self.browse_storage_folder, variant='accent').pack(side='left', padx=(8, 0))
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x')
        
        create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(8, 0))
        create_soft_button(button_frame, "Create", self.confirm, variant='primary').pack(side='right')
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def browse_storage_folder(self):
        """Select a folder where the new board file will be stored."""
        selected = filedialog.askdirectory(
            title="Select Board Storage Folder",
            initialdir=self.storage_var.get() or self.default_storage_dir,
            parent=self.dialog,
        )
        if selected:
            self.storage_var.set(selected)
    
    def confirm(self):
        """Confirm the dialog."""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Board name is required!")
            return
        
        description = self.desc_text.get(1.0, tk.END).strip()
        storage_dir = self.storage_var.get().strip() or self.default_storage_dir
        self.result = (name, description, storage_dir)
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()


## @brief Modal dialog for creating or editing column properties.
class ColumnDialog:
    """Dialog for creating or editing column properties."""

    DEFAULT_COLORS = ['#FF9800', '#2196F3', '#4CAF50', '#F44336', '#9C27B0', '#FF5722']

    def __init__(self, parent, title="Column Properties", initial_name="", initial_color="#FF9800"):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        center_modal(self.dialog, parent, 420, 220)

        self.setup_ui(initial_name, initial_color)
        self.name_entry.focus()
        self.dialog.wait_window()

    def setup_ui(self, initial_name, initial_color):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, bg=APP_BG)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(main_frame, text="Column Name:", font=('Arial', 11, 'bold'), bg=APP_BG).pack(anchor='w')
        self.name_entry = tk.Entry(main_frame, font=('Arial', 11), width=40)
        self.name_entry.pack(fill='x', pady=(5, 15))
        self.name_entry.insert(0, initial_name)
        style_text_input(self.name_entry)

        tk.Label(main_frame, text="Column Color:", font=('Arial', 11, 'bold'), bg=APP_BG).pack(anchor='w')

        color_frame = tk.Frame(main_frame, bg=APP_BG)
        color_frame.pack(fill='x', pady=(5, 12))

        self.color_var = tk.StringVar(value=initial_color or self.DEFAULT_COLORS[0])
        self.color_preview = tk.Label(
            color_frame,
            text="Current",
            width=10,
            bg=self.color_var.get(),
            fg='white',
            relief='solid',
            bd=1,
            font=('Arial', 9, 'bold'),
            padx=8,
            pady=6,
        )
        self.color_preview.pack(side='left')

        create_soft_button(color_frame, "Pick Color", self.pick_color, variant='accent').pack(side='right')

        palette_frame = tk.Frame(main_frame, bg=APP_BG)
        palette_frame.pack(fill='x', pady=(0, 20))
        for color in self.DEFAULT_COLORS:
            swatch = tk.Button(
                palette_frame,
                bg=color,
                width=3,
                relief='flat',
                bd=0,
                command=lambda value=color: self.set_color(value),
                cursor='hand2',
            )
            swatch.pack(side='left', padx=(0, 6), ipady=6)

        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x')

        create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(8, 0))
        create_soft_button(button_frame, "Save", self.confirm, variant='primary').pack(side='right')

        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def set_color(self, color):
        """Update the selected color and preview."""
        self.color_var.set(color)
        self.color_preview.config(bg=color)

    def pick_color(self):
        """Choose a color using the native color picker."""
        _, color = colorchooser.askcolor(color=self.color_var.get(), parent=self.dialog, title="Choose Column Color")
        if color:
            self.set_color(color)

    def confirm(self):
        """Confirm the dialog."""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Column name is required!", parent=self.dialog)
            return

        color = self.color_var.get().strip() or self.DEFAULT_COLORS[0]

        self.result = (name, color)
        self.dialog.destroy()

    def cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()


## @brief Modal list-selection dialog used by the multi-board GUI.
class SelectionDialog:
    """Dialog for selecting a single option from a dropdown list."""

    def __init__(self, parent, title, prompt, options, initial_index=0):
        self.result = None
        self.options = list(options)

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        center_modal(self.dialog, parent, 420, 180)

        self.setup_ui(prompt, initial_index)
        self.dialog.wait_window()

    def setup_ui(self, prompt, initial_index):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20, bg=APP_BG)
        main_frame.pack(fill='both', expand=True)

        tk.Label(main_frame, text=prompt, font=('Arial', 10, 'bold'), justify='left', bg=APP_BG).pack(anchor='w', pady=(0, 10))

        self.selection_var = tk.StringVar()
        self.combobox = ttk.Combobox(main_frame, textvariable=self.selection_var, state='readonly', values=self.options, style='Soft.TCombobox')
        self.combobox.pack(fill='x', pady=(0, 20))

        if self.options:
            index = initial_index if 0 <= initial_index < len(self.options) else 0
            self.combobox.current(index)

        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x')

        create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(10, 0))
        create_soft_button(button_frame, "OK", self.confirm, variant='primary').pack(side='right')

        self.combobox.focus()
        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def confirm(self):
        """Confirm the selection."""
        value = self.selection_var.get().strip()
        if not value:
            return
        self.result = value
        self.dialog.destroy()

    def cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()


## @brief Modal dialog for reordering custom columns visually.
class ReorderColumnsDialog:
    """Dialog for reordering columns visually."""

    def __init__(self, parent, columns):
        self.result = None
        self.columns = list(columns)

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Reorder Columns")
        center_modal(self.dialog, parent, 420, 360)

        self.setup_ui()
        self.dialog.wait_window()

    def setup_ui(self):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20, bg=APP_BG)
        main_frame.pack(fill='both', expand=True)

        tk.Label(
            main_frame,
            text="Select a column and use the buttons to change its position.",
            font=('Arial', 10, 'bold'),
            justify='left',
            bg=APP_BG,
        ).pack(anchor='w', pady=(0, 10))

        content_frame = tk.Frame(main_frame, bg=APP_BG)
        content_frame.pack(fill='both', expand=True)

        list_frame = tk.Frame(content_frame, bg=APP_BG)
        list_frame.pack(side='left', fill='both', expand=True)

        self.listbox = tk.Listbox(list_frame, font=('Arial', 10), activestyle='dotbox')
        self.listbox.pack(side='left', fill='both', expand=True)
        style_text_input(self.listbox)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.listbox.configure(yscrollcommand=scrollbar.set)

        controls_frame = tk.Frame(content_frame, bg=APP_BG)
        controls_frame.pack(side='right', fill='y', padx=(12, 0))

        create_soft_button(controls_frame, "Move Up", self.move_up, variant='accent', width=10).pack(pady=(0, 8))
        create_soft_button(controls_frame, "Move Down", self.move_down, variant='accent', width=10).pack()

        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x', pady=(16, 0))

        create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(10, 0))
        create_soft_button(button_frame, "Apply", self.confirm, variant='primary').pack(side='right')

        self.refresh_listbox()
        if self.columns:
            self.listbox.selection_set(0)
            self.listbox.activate(0)

        self.dialog.bind('<Escape>', lambda e: self.cancel())
        self.dialog.bind('<Return>', lambda e: self.confirm())

    def refresh_listbox(self):
        """Refresh the list of columns in their current order."""
        self.listbox.delete(0, tk.END)
        for index, column in enumerate(self.columns, start=1):
            self.listbox.insert(tk.END, f"{index}. {column.name}")

    def move_up(self):
        """Move the selected column up by one position."""
        selection = self.listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index == 0:
            return

        self.columns[index - 1], self.columns[index] = self.columns[index], self.columns[index - 1]
        self.refresh_listbox()
        self.listbox.selection_set(index - 1)
        self.listbox.activate(index - 1)

    def move_down(self):
        """Move the selected column down by one position."""
        selection = self.listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index >= len(self.columns) - 1:
            return

        self.columns[index + 1], self.columns[index] = self.columns[index], self.columns[index + 1]
        self.refresh_listbox()
        self.listbox.selection_set(index + 1)
        self.listbox.activate(index + 1)

    def confirm(self):
        """Confirm the new column order."""
        self.result = [column.id for column in self.columns]
        self.dialog.destroy()

    def cancel(self):
        """Cancel reordering."""
        self.dialog.destroy()


## @brief Modal dialog for creating or editing reusable card types.
class CardTypeDialog:
    """Dialog for creating or editing a card type."""

    def __init__(self, parent, title, initial_name="", initial_description="",
                 initial_project="", initial_color="", allow_name_edit=True):
        self.result = None
        self.allow_name_edit = allow_name_edit

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        center_modal(self.dialog, parent, 460, 420)

        self.setup_ui(initial_name or "", initial_description or "", initial_project or "", initial_color or "")
        if self.allow_name_edit:
            self.name_entry.focus()
        else:
            self.desc_text.focus()
        self.dialog.wait_window()

    def setup_ui(self, initial_name, initial_description, initial_project, initial_color):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20, bg=APP_BG)
        main_frame.pack(fill='both', expand=True)

        tk.Label(main_frame, text="Name:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.name_entry = tk.Entry(main_frame, width=50)
        self.name_entry.pack(fill='x', pady=(0, 10))
        self.name_entry.insert(0, initial_name)
        style_text_input(self.name_entry)
        if not self.allow_name_edit:
            self.name_entry.configure(state='disabled')

        tk.Label(main_frame, text="Description:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.desc_text = tk.Text(main_frame, height=5, width=50)
        self.desc_text.pack(fill='x', pady=(0, 10))
        self.desc_text.insert('1.0', initial_description)
        style_text_input(self.desc_text)

        tk.Label(main_frame, text="Project Preset:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.project_entry = tk.Entry(main_frame, width=50)
        self.project_entry.pack(fill='x', pady=(0, 10))
        self.project_entry.insert(0, initial_project)
        style_text_input(self.project_entry)

        tk.Label(main_frame, text="Color Preset:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        color_frame = tk.Frame(main_frame, bg=APP_BG)
        color_frame.pack(fill='x', pady=(0, 18))

        self.color_var = tk.StringVar(value=initial_color)
        self.color_preview = tk.Label(
            color_frame,
            text="Default" if not initial_color else "Preview",
            width=10,
            bg=initial_color or SURFACE_ALT_BG,
            fg='white' if initial_color and is_dark_color(initial_color) else '#2F2923',
            relief='solid',
            bd=1,
            font=('Arial', 9, 'bold'),
            padx=8,
            pady=6,
        )
        self.color_preview.pack(side='left')

        create_soft_button(color_frame, "Pick", self.pick_color, variant='accent').pack(side='right')
        create_soft_button(color_frame, "Default", self.clear_color, variant='secondary').pack(side='right', padx=(0, 8))

        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x')
        create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(10, 0))
        create_soft_button(button_frame, "Save", self.confirm, variant='primary').pack(side='right')

        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def set_color(self, color):
        """Set the color preset preview."""
        self.color_var.set(color)
        self.color_preview.config(
            text='Preview',
            bg=color,
            fg='white' if is_dark_color(color) else '#2F2923',
        )

    def clear_color(self):
        """Clear the color preset."""
        self.color_var.set('')
        self.color_preview.config(text='Default', bg=SURFACE_ALT_BG, fg='#2F2923')

    def pick_color(self):
        """Choose a preset color using the native color picker."""
        _, color = colorchooser.askcolor(color=self.color_var.get() or SURFACE_ALT_BG, parent=self.dialog, title='Choose Preset Card Color')
        if color:
            self.set_color(color)

    def confirm(self):
        """Confirm the dialog values."""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Card type name is required!", parent=self.dialog)
            return

        description = self.desc_text.get('1.0', 'end-1c').strip()
        default_project = self.project_entry.get().strip() or None
        default_color = self.color_var.get().strip() or None
        self.result = (name, description, default_project, default_color)
        self.dialog.destroy()

    def cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()


## @brief Modal dialog for browsing card types and their presets.
class CardTypesOverviewDialog:
    """Dialog for browsing configured card types on the current board."""

    def __init__(self, parent, board):
        self.board = board
        self.card_types = self.board.get_card_types_ordered()
        self.default_type_id = self.board.get_default_card_type_id()
        self.last_used_id = self.board.get_last_used_card_type().id

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Card Types")
        center_modal(self.dialog, parent, 760, 440)

        self.setup_ui()
        self.dialog.wait_window()

    def setup_ui(self):
        """Set up the card type overview UI."""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20, bg=APP_BG)
        main_frame.pack(fill='both', expand=True)

        total_cards = len(self.board.get_all_cards())
        summary = f"{len(self.card_types)} types configured | {total_cards} total cards on this board"
        tk.Label(main_frame, text=summary, font=('Arial', 10, 'bold'), bg=APP_BG, fg='#5F554D').pack(anchor='w', pady=(0, 12))

        content_frame = tk.Frame(main_frame, bg=APP_BG)
        content_frame.pack(fill='both', expand=True)

        list_frame = tk.Frame(content_frame, bg=APP_BG)
        list_frame.pack(side='left', fill='both', expand=False)

        tk.Label(list_frame, text="Card Types", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w', pady=(0, 8))

        list_container = tk.Frame(list_frame, bg=APP_BG)
        list_container.pack(fill='both', expand=True)

        self.listbox = tk.Listbox(list_container, width=28, font=('Arial', 10), activestyle='dotbox')
        self.listbox.pack(side='left', fill='both', expand=True)
        style_text_input(self.listbox)

        list_scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.listbox.yview)
        list_scrollbar.pack(side='right', fill='y')
        self.listbox.configure(yscrollcommand=list_scrollbar.set)

        details_frame = tk.Frame(content_frame, bg=SURFACE_BG, highlightthickness=1, highlightbackground='#E0D7CA')
        details_frame.pack(side='left', fill='both', expand=True, padx=(18, 0))

        details_inner = tk.Frame(details_frame, bg=SURFACE_BG, padx=18, pady=18)
        details_inner.pack(fill='both', expand=True)

        self.name_label = tk.Label(details_inner, text="", font=('Arial', 15, 'bold'), bg=SURFACE_BG, anchor='w')
        self.name_label.pack(fill='x')

        self.meta_label = tk.Label(details_inner, text="", font=('Arial', 9, 'bold'), bg=SURFACE_BG, fg='#7A6A5A', anchor='w')
        self.meta_label.pack(fill='x', pady=(4, 14))

        self.description_value = tk.Label(details_inner, text="", font=('Arial', 10), bg=SURFACE_BG, justify='left', anchor='nw', wraplength=360)
        self.description_value.pack(fill='x', pady=(0, 14))

        self.project_value = tk.Label(details_inner, text="", font=('Arial', 10), bg=SURFACE_BG, justify='left', anchor='w')
        self.project_value.pack(fill='x', pady=(0, 10))

        self.color_row = tk.Frame(details_inner, bg=SURFACE_BG)
        self.color_row.pack(fill='x', pady=(0, 10))

        self.color_value = tk.Label(self.color_row, text="", font=('Arial', 10), bg=SURFACE_BG, anchor='w')
        self.color_value.pack(side='left')

        self.color_preview = tk.Label(
            self.color_row,
            text="Default",
            width=10,
            bg=SURFACE_ALT_BG,
            fg='#2F2923',
            relief='solid',
            bd=1,
            font=('Arial', 9, 'bold'),
            padx=8,
            pady=4,
        )
        self.color_preview.pack(side='right')

        self.usage_value = tk.Label(details_inner, text="", font=('Arial', 10), bg=SURFACE_BG, justify='left', anchor='w')
        self.usage_value.pack(fill='x')

        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x', pady=(16, 0))
        create_soft_button(button_frame, "Close", self.close, variant='primary').pack(side='right')

        self.populate_list()
        self.listbox.bind('<<ListboxSelect>>', self.on_selection_changed)
        self.listbox.bind('<Double-Button-1>', lambda _event: self.close())
        self.dialog.bind('<Escape>', lambda _event: self.close())
        self.dialog.bind('<Return>', lambda _event: self.close())

    def populate_list(self):
        """Populate the list of card types."""
        self.listbox.delete(0, tk.END)
        for card_type in self.card_types:
            suffixes = []
            if card_type.id == self.default_type_id:
                suffixes.append('default')
            if card_type.id == self.last_used_id:
                suffixes.append('last used')
            suffix = f" [{' | '.join(suffixes)}]" if suffixes else ''
            self.listbox.insert(tk.END, f"{card_type.name}{suffix}")

        if self.card_types:
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            self.update_details(self.card_types[0])

    def on_selection_changed(self, _event=None):
        """Update the details panel for the selected card type."""
        selection = self.listbox.curselection()
        if not selection:
            return
        self.update_details(self.card_types[selection[0]])

    def update_details(self, card_type):
        """Render the selected card type details."""
        flags = []
        if card_type.id == self.default_type_id:
            flags.append('Cannot be deleted')
        if card_type.id == self.last_used_id:
            flags.append('Used for next new card')

        usage_count = len(self.board.get_cards_by_type(card_type.id))

        self.name_label.config(text=card_type.name)
        self.meta_label.config(text=' | '.join(flags) if flags else 'Custom card type')
        self.description_value.config(text=f"Description: {card_type.description or 'No description'}")
        self.project_value.config(text=f"Project preset: {card_type.default_project or 'None'}")
        self.color_value.config(text=f"Color preset: {card_type.default_color or 'Default'}")
        self.usage_value.config(text=f"Cards using this type: {usage_count}")

        if card_type.default_color:
            self.color_preview.config(
                text='Preview',
                bg=card_type.default_color,
                fg='white' if is_dark_color(card_type.default_color) else '#2F2923',
            )
        else:
            self.color_preview.config(text='Default', bg=SURFACE_ALT_BG, fg='#2F2923')

    def close(self):
        """Close the dialog."""
        self.dialog.destroy()


## @brief Modal dialog for entering a card note before it is saved.
class NoteDialog:
    """Dialog for entering note text."""

    def __init__(self, parent, title, initial_text=""):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        center_modal(self.dialog, parent, 520, 320)

        self.setup_ui(initial_text or "")
        self.text_widget.focus()
        self.dialog.wait_window()

    def setup_ui(self, initial_text):
        """Set up the note entry UI."""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20, bg=APP_BG)
        main_frame.pack(fill='both', expand=True)

        tk.Label(
            main_frame,
            text="Note:",
            font=('Arial', 10, 'bold'),
            bg=APP_BG,
        ).pack(anchor='w')

        self.text_widget = tk.Text(main_frame, height=10, width=60, font=('Arial', 10), wrap='word')
        self.text_widget.pack(fill='both', expand=True, pady=(0, 14))
        self.text_widget.insert('1.0', initial_text)
        style_text_input(self.text_widget)

        helper_text = "The note will be saved with the current date and time."
        tk.Label(main_frame, text=helper_text, font=('Arial', 9), fg=TEXT_MUTED, bg=APP_BG).pack(anchor='w', pady=(0, 14))

        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x')
        create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(10, 0))
        create_soft_button(button_frame, "Save Note", self.confirm, variant='primary').pack(side='right')

        self.dialog.bind('<Escape>', lambda _event: self.cancel())
        self.dialog.bind('<Control-Return>', lambda _event: self.confirm())

    def confirm(self):
        """Save the entered note text and close the dialog."""
        self.result = self.text_widget.get('1.0', 'end-1c').strip()
        self.dialog.destroy()

    def cancel(self):
        """Close the dialog without saving."""
        self.dialog.destroy()


## @brief Modal dialog for creating or editing cards in the multi-board GUI.
class CardDialog:
    """Dialog for creating/editing cards."""
    
    def __init__(self, parent, title, initial_title="", initial_description="", 
                 initial_priority=None, initial_assignee="", initial_project="", initial_start_date=None,
                 initial_end_date=None, initial_color="", initial_card_type_id=None,
                 initial_tags=None,
                 board=None, card=None, on_change=None):
        self.result = None
        self.board = board
        self.card = card
        self.on_change = on_change
        self.subcards = []

        initial_title = initial_title or ""
        initial_description = initial_description or ""
        initial_assignee = initial_assignee or ""
        initial_project = initial_project or ""
        initial_color = initial_color or ""
        initial_tags = list(initial_tags or [])
        self.card_types = self.board.get_card_types_ordered() if self.board else []
        self.current_card_type_id = initial_card_type_id
        if self.board:
            self.current_card_type_id = initial_card_type_id or self.board.get_last_used_card_type().id
        self.last_applied_card_type_id = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        dialog_height = 780 if self._supports_subcard_management() else 620
        center_modal(self.dialog, parent, 440, dialog_height)
        
        self.setup_ui(initial_title, initial_description, initial_priority, 
                 initial_assignee, initial_project, initial_start_date, initial_end_date, initial_color, initial_tags)
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_ui(self, initial_title, initial_description, initial_priority, 
                 initial_assignee, initial_project, initial_start_date, initial_end_date, initial_color, initial_tags):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20, bg=APP_BG)
        main_frame.pack(fill='both', expand=True)

        content_frame = tk.Frame(main_frame, bg=APP_BG)
        content_frame.pack(fill='both', expand=True)

        self.form_canvas = tk.Canvas(content_frame, bg=APP_BG, highlightthickness=0, bd=0)
        self.form_canvas.pack(side='left', fill='both', expand=True)

        form_scrollbar = ttk.Scrollbar(content_frame, orient='vertical', command=self.form_canvas.yview)
        form_scrollbar.pack(side='right', fill='y')
        self.form_canvas.configure(yscrollcommand=form_scrollbar.set)

        fields_frame = tk.Frame(self.form_canvas, bg=APP_BG)
        self.form_window = self.form_canvas.create_window((0, 0), window=fields_frame, anchor='nw')
        fields_frame.bind('<Configure>', self._update_scroll_region)
        self.form_canvas.bind('<Configure>', self._resize_form_width)
        
        # Title
        tk.Label(fields_frame, text="Title:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.title_entry = tk.Entry(fields_frame, width=50)
        self.title_entry.pack(fill='x', pady=(0, 10))
        self.title_entry.insert(0, initial_title)
        style_text_input(self.title_entry)
        
        # Description
        tk.Label(fields_frame, text="Description:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.description_text = tk.Text(fields_frame, height=6, width=50)
        self.description_text.pack(fill='x', pady=(0, 10))
        self.description_text.insert("1.0", initial_description)
        style_text_input(self.description_text)
        
        # Priority
        tk.Label(fields_frame, text="Priority:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.priority_var = tk.StringVar()
        priority_frame = tk.Frame(fields_frame, bg=APP_BG)
        priority_frame.pack(fill='x', pady=(0, 10))
        
        priorities = ['low', 'medium', 'high', 'critical']
        for i, priority in enumerate(priorities):
            rb = tk.Radiobutton(priority_frame, text=priority.title(), 
                               variable=self.priority_var, value=priority,
                               bg=APP_BG, activebackground=APP_BG, selectcolor=SURFACE_BG)
            rb.pack(side='left', padx=(0, 10))
            if initial_priority and initial_priority.value == priority:
                rb.select()
        
        if not initial_priority:
            self.priority_var.set('medium')

        if self.board and self.card_types:
            tk.Label(fields_frame, text="Card Type:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
            self.card_type_map = {card_type.name: card_type for card_type in self.card_types}
            type_names = list(self.card_type_map.keys())
            self.card_type_var = tk.StringVar()
            self.card_type_combo = ttk.Combobox(
                fields_frame,
                textvariable=self.card_type_var,
                state='readonly',
                values=type_names,
                style='Soft.TCombobox',
            )
            self.card_type_combo.pack(fill='x', pady=(0, 4))

            selected_type = self.board.get_card_type(self.current_card_type_id) or self.board.get_last_used_card_type()
            self.card_type_combo.set(selected_type.name)
            self.card_type_description = tk.Label(fields_frame, text="", font=('Arial', 9), fg=TEXT_MUTED, bg=APP_BG, justify='left', wraplength=360)
            self.card_type_description.pack(anchor='w', pady=(0, 10))
            self.card_type_combo.bind('<<ComboboxSelected>>', self.on_card_type_changed)
        else:
            self.card_type_map = {}
            self.card_type_var = tk.StringVar(value="")
            self.card_type_description = None
        
        # Assignee
        tk.Label(fields_frame, text="Assignee:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.assignee_entry = tk.Entry(fields_frame, width=50)
        self.assignee_entry.pack(fill='x', pady=(0, 10))
        self.assignee_entry.insert(0, initial_assignee)
        style_text_input(self.assignee_entry)

        # Project
        tk.Label(fields_frame, text="Project:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.project_entry = tk.Entry(fields_frame, width=50)
        self.project_entry.pack(fill='x', pady=(0, 10))
        self.project_entry.insert(0, initial_project)
        style_text_input(self.project_entry)

        tk.Label(fields_frame, text="Start Date (YYYY-MM-DD):", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.start_date_entry = tk.Entry(fields_frame, width=50)
        self.start_date_entry.pack(fill='x', pady=(0, 10))
        self.start_date_entry.insert(0, format_optional_date(initial_start_date))
        style_text_input(self.start_date_entry)

        tk.Label(fields_frame, text="End Date (YYYY-MM-DD):", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.end_date_entry = tk.Entry(fields_frame, width=50)
        self.end_date_entry.pack(fill='x', pady=(0, 10))
        self.end_date_entry.insert(0, format_optional_date(initial_end_date))
        style_text_input(self.end_date_entry)

        tk.Label(fields_frame, text="Card Color:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        color_frame = tk.Frame(fields_frame, bg=APP_BG)
        color_frame.pack(fill='x', pady=(0, 10))

        self.card_color_var = tk.StringVar(value=initial_color)
        preview_bg = initial_color or SURFACE_ALT_BG
        preview_fg = 'white' if initial_color and is_dark_color(initial_color) else '#2F2923'
        self.card_color_preview = tk.Label(
            color_frame,
            text="Default" if not initial_color else "Preview",
            width=10,
            bg=preview_bg,
            fg=preview_fg,
            relief='solid',
            bd=1,
            font=('Arial', 9, 'bold'),
            padx=8,
            pady=6,
        )
        self.card_color_preview.pack(side='left')

        create_soft_button(color_frame, "Pick", self.pick_card_color, variant='accent').pack(side='right')
        create_soft_button(color_frame, "Default", self.clear_card_color, variant='secondary').pack(side='right', padx=(0, 8))

        if self.board and self.card_types:
            self.apply_selected_card_type_presets(force=not initial_project and not initial_color)
        
        # Tags
        tk.Label(fields_frame, text="Tags (comma-separated):", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')
        self.tags_entry = tk.Entry(fields_frame, width=50)
        self.tags_entry.pack(fill='x', pady=(0, 20))
        self.tags_entry.insert(0, ', '.join(initial_tags))
        style_text_input(self.tags_entry)

        if self.card is not None:
            self._build_notes_section(fields_frame)

        if self._supports_subcard_management():
            self._build_subcards_section(fields_frame)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x', pady=(12, 0))
        
        create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(10, 0))
        create_soft_button(button_frame, "OK", self.ok, variant='primary').pack(side='right')
        
        # Set focus and bind Enter key
        self.title_entry.focus()
        self.dialog.bind('<Return>', lambda e: self.ok())
        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def _update_scroll_region(self, _event=None):
        """Keep the form canvas scroll region in sync with its content."""
        self.form_canvas.configure(scrollregion=self.form_canvas.bbox('all'))

    def _resize_form_width(self, event):
        """Resize the embedded form to match the visible canvas width."""
        self.form_canvas.itemconfigure(self.form_window, width=event.width)

    def _supports_subcard_management(self):
        """Return whether the current dialog should allow subcard management."""
        return self.board is not None and self.card is not None and not self.card.parent_id

    def set_card_color(self, color):
        """Set the selected card color and refresh the preview."""
        self.card_color_var.set(color)
        preview_fg = 'white' if is_dark_color(color) else '#2F2923'
        self.card_color_preview.config(text='Preview', bg=color, fg=preview_fg)

    def clear_card_color(self):
        """Reset the card color to the default board styling."""
        self.card_color_var.set('')
        self.card_color_preview.config(text='Default', bg=SURFACE_ALT_BG, fg='#2F2923')

    def pick_card_color(self):
        """Choose a card color using the native color picker."""
        _, color = colorchooser.askcolor(color=self.card_color_var.get() or SURFACE_ALT_BG, parent=self.dialog, title='Choose Card Color')
        if color:
            self.set_card_color(color)

    def get_selected_card_type(self):
        """Return the currently selected card type, if any."""
        if not self.board or not self.card_type_map:
            return None
        return self.card_type_map.get(self.card_type_var.get().strip())

    def on_card_type_changed(self, _event=None):
        """Apply card type metadata when the selection changes."""
        self.apply_selected_card_type_presets(force=False)

    def apply_selected_card_type_presets(self, force=False):
        """Apply the selected card type's optional presets to project and color fields."""
        card_type = self.get_selected_card_type()
        if card_type is None:
            return

        previous_type = self.board.get_card_type(self.last_applied_card_type_id) if self.board else None
        if self.card_type_description is not None:
            description = card_type.description or "No description"
            self.card_type_description.config(text=description)

        current_project = self.project_entry.get().strip()
        current_color = self.card_color_var.get().strip()
        previous_project = previous_type.default_project if previous_type else None
        previous_color = previous_type.default_color if previous_type else None

        if force or current_project == '' or current_project == (previous_project or ''):
            self.project_entry.delete(0, tk.END)
            if card_type.default_project:
                self.project_entry.insert(0, card_type.default_project)

        if force or current_color == '' or current_color == (previous_color or ''):
            if card_type.default_color:
                self.set_card_color(card_type.default_color)
            else:
                self.clear_card_color()

        self.current_card_type_id = card_type.id
        self.last_applied_card_type_id = card_type.id

    def _build_subcards_section(self, parent):
        """Render subcard management controls for a top-level card."""
        tk.Label(parent, text="Subcards:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')

        subcards_frame = tk.Frame(parent, bg=APP_BG)
        subcards_frame.pack(fill='both', expand=True, pady=(0, 20))

        list_frame = tk.Frame(subcards_frame, bg=APP_BG)
        list_frame.pack(fill='both', expand=True)

        self.subcards_listbox = tk.Listbox(list_frame, height=7, font=('Arial', 10), activestyle='dotbox')
        self.subcards_listbox.pack(side='left', fill='both', expand=True)
        style_text_input(self.subcards_listbox)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.subcards_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.subcards_listbox.configure(yscrollcommand=scrollbar.set)

        actions_frame = tk.Frame(subcards_frame, bg=APP_BG)
        actions_frame.pack(fill='x', pady=(8, 0))

        create_soft_button(actions_frame, "Add Subcard", self.add_subcard, variant='accent').pack(side='left')
        create_soft_button(actions_frame, "Delete Selected", self.delete_selected_subcard, variant='secondary').pack(side='left', padx=(8, 0))

        self.refresh_subcards_list()

    def _build_notes_section(self, parent):
        """Render note management controls for an existing card."""
        tk.Label(parent, text="Notes:", font=('Arial', 10, 'bold'), bg=APP_BG).pack(anchor='w')

        notes_frame = tk.Frame(parent, bg=APP_BG)
        notes_frame.pack(fill='both', expand=True, pady=(0, 20))

        list_frame = tk.Frame(notes_frame, bg=APP_BG)
        list_frame.pack(fill='both', expand=True)

        self.notes_listbox = tk.Listbox(list_frame, height=5, font=('Arial', 10), activestyle='dotbox')
        self.notes_listbox.pack(side='left', fill='both', expand=True)
        style_text_input(self.notes_listbox)
        self.notes_listbox.bind('<Double-Button-1>', self.view_selected_note)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.notes_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.notes_listbox.configure(yscrollcommand=scrollbar.set)

        actions_frame = tk.Frame(notes_frame, bg=APP_BG)
        actions_frame.pack(fill='x', pady=(8, 0))

        create_soft_button(actions_frame, "Add Note", self.add_note, variant='accent').pack(side='left')
        create_soft_button(actions_frame, "View Selected", self.view_selected_note, variant='secondary').pack(side='left', padx=(8, 0))
        create_soft_button(actions_frame, "Delete Selected", self.delete_selected_note, variant='secondary').pack(side='left', padx=(8, 0))

        self.refresh_notes_list()

    def refresh_notes_list(self):
        """Refresh the list of notes for the current card."""
        if not hasattr(self, 'notes_listbox') or self.card is None:
            return

        self.notes_listbox.delete(0, tk.END)
        for note in self.card.notes:
            summary = note.text.strip().splitlines()[0] if note.text.strip() else 'Empty note'
            self.notes_listbox.insert(tk.END, f"{note.created_at.strftime('%Y-%m-%d %H:%M')} | {summary[:40]}")

        if not self.card.notes:
            self.notes_listbox.insert(tk.END, 'No notes yet')

    def add_note(self):
        """Prompt for note text and create a new timestamped note for the current card."""
        if self.card is None:
            return

        note_dialog = NoteDialog(self.dialog, f"Add Note to '{self.card.title}'")
        if note_dialog.result is None:
            return

        note = self.board.add_card_note(self.card.id, note_dialog.result)
        if note is None:
            messagebox.showerror('Error', 'Card not found.', parent=self.dialog)
            return

        self.card = self.board.find_card(self.card.id)
        self.refresh_notes_list()
        if self.on_change:
            self.on_change()
        self.dialog.after(0, lambda: messagebox.showinfo('Note Added', f"Created note at {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}", parent=self.dialog))

    def view_selected_note(self, _event=None):
        """Show the selected note details."""
        if self.card is None or not hasattr(self, 'notes_listbox'):
            return

        current = self.notes_listbox.curselection()
        if not current or not self.card.notes:
            messagebox.showinfo('View Note', 'Select a note to view.', parent=self.dialog)
            return

        index = current[0]
        if index >= len(self.card.notes):
            return

        note = self.card.notes[index]
        details = f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n{note.text or '(empty note)'}"
        messagebox.showinfo('Card Note', details, parent=self.dialog)

    def delete_selected_note(self):
        """Delete the selected note from the current card."""
        if self.card is None or not hasattr(self, 'notes_listbox'):
            return

        current = self.notes_listbox.curselection()
        if not current or not self.card.notes:
            messagebox.showinfo('Delete Note', 'Select a note to delete.', parent=self.dialog)
            return

        index = current[0]
        if index >= len(self.card.notes):
            return

        note = self.card.notes[index]
        summary = note.text.strip().splitlines()[0] if note.text.strip() else 'this empty note'
        confirm_message = f"Delete note from {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}?\n\n{summary[:80]}"
        if not messagebox.askyesno('Delete Note', confirm_message, parent=self.dialog):
            return

        deleted = self.board.delete_card_note(self.card.id, note.id)
        if not deleted:
            messagebox.showerror('Error', 'Note could not be deleted.', parent=self.dialog)
            return

        self.card = self.board.find_card(self.card.id)
        self.refresh_notes_list()
        if self.on_change:
            self.on_change()

    def refresh_subcards_list(self):
        """Refresh the list of current subcards and their locations."""
        if not hasattr(self, 'subcards_listbox'):
            return

        self.subcards = self.board.get_subcards(self.card.id)
        self.subcards_listbox.delete(0, tk.END)
        for subcard in self.subcards:
            tick = "[x]" if self.board.is_card_done(subcard) else "[ ]"
            location = self.board.get_card_location_label(subcard)
            self.subcards_listbox.insert(tk.END, f"{tick} {subcard.title} ({location})")

        if not self.subcards:
            self.subcards_listbox.insert(tk.END, "No subcards yet")

    def add_subcard(self):
        """Open a nested dialog to create a new subcard for this card."""
        parent_project = self.project_entry.get().strip() or self.card.project
        dialog = CardDialog(
            self.dialog,
            f"Add Subcard to '{self.card.title}'",
            initial_project=parent_project,
            initial_color=self.card_color_var.get().strip(),
            initial_card_type_id=self.current_card_type_id or self.card.card_type_id,
            board=self.board,
        )
        if not dialog.result:
            return

        title, description, priority, assignee, project, start_date, end_date, color, card_type_id, tags = dialog.result
        try:
            subcard = self.board.create_subcard(self.card.id, title, description, priority, project or parent_project, color, card_type_id, start_date, end_date)
            if assignee:
                self.board.edit_card(subcard.id, assignee=assignee)

            for tag in tags:
                subcard.add_tag(tag)
            self.board.save_board()
            self.refresh_subcards_list()
            if self.on_change:
                self.on_change()
        except ValueError as error:
            messagebox.showerror("Error", str(error), parent=self.dialog)

    def delete_selected_subcard(self):
        """Delete the selected subcard from the current card."""
        selection = getattr(self, 'subcards_listbox', None)
        if selection is None:
            return

        current = self.subcards_listbox.curselection()
        if not current or not self.subcards:
            messagebox.showinfo("Delete Subcard", "Select a subcard to delete.", parent=self.dialog)
            return

        index = current[0]
        if index >= len(self.subcards):
            return

        subcard = self.subcards[index]
        if not messagebox.askyesno("Delete Subcard", f"Delete subcard '{subcard.title}'?", parent=self.dialog):
            return

        self.board.delete_card(subcard.id)
        self.refresh_subcards_list()
        if self.on_change:
            self.on_change()
    
    def ok(self):
        """Handle OK button."""
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Error", "Title is required!")
            return
        
        description = self.description_text.get("1.0", "end-1c").strip()
        
        # Get priority
        priority_map = {
            'low': Priority.LOW,
            'medium': Priority.MEDIUM,
            'high': Priority.HIGH,
            'critical': Priority.CRITICAL
        }
        priority = priority_map[self.priority_var.get()]
        
        assignee = self.assignee_entry.get().strip()
        project = self.project_entry.get().strip()
        try:
            start_date = parse_optional_date(self.start_date_entry.get(), 'Start date')
            end_date = parse_optional_date(self.end_date_entry.get(), 'End date')
        except ValueError as error:
            messagebox.showerror("Error", str(error), parent=self.dialog)
            return

        if start_date and end_date and end_date < start_date:
            messagebox.showerror("Error", "End date cannot be earlier than start date.", parent=self.dialog)
            return

        color = self.card_color_var.get().strip() or None
        card_type = self.get_selected_card_type()
        
        # Parse tags
        tags_text = self.tags_entry.get().strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []
        
        self.result = (title, description, priority, assignee or None, project or None, start_date, end_date, color, card_type.id if card_type else None, tags)
        self.dialog.destroy()
    
    def cancel(self):
        """Handle Cancel button."""
        self.dialog.destroy()