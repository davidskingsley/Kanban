## @file
#  @brief Menu, toolbar, and shortcut helpers for the multi-board GUI shell.
"""Shell UI helpers for the multi-board application."""

import tkinter as tk
from tkinter import ttk, messagebox

from .common import OUTLINE_COLOR, PANEL_BG


def setup_menu(app):
    """Set up the menu bar for the multi-board shell."""
    menubar = tk.Menu(app.root)
    app.root.config(menu=menubar)

    edit_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Edit", menu=edit_menu)
    edit_menu.add_command(
        label="Undo Board Action",
        command=app.undo_current_board_action,
        accelerator=app.get_shortcut_label('undo_current_board_action'),
    )
    edit_menu.add_command(
        label="Undo Board Management Action",
        command=app.undo_board_management_action,
        accelerator=app.get_shortcut_label('undo_board_management_action'),
    )
    edit_menu.add_separator()
    edit_menu.add_command(
        label="Redo Board Action",
        command=app.redo_current_board_action,
        accelerator=app.get_shortcut_label('redo_current_board_action'),
    )
    edit_menu.add_command(
        label="Redo Board Management Action",
        command=app.redo_board_management_action,
        accelerator=app.get_shortcut_label('redo_board_management_action'),
    )

    boards_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Boards", menu=boards_menu)
    boards_menu.add_command(
        label="Create New Board",
        command=app.create_board_dialog,
        accelerator=app.get_shortcut_label('create_board_dialog'),
    )
    boards_menu.add_command(
        label="Load Board From Folder",
        command=app.load_board_from_folder_dialog,
        accelerator=app.get_shortcut_label('load_board_from_folder_dialog'),
    )
    boards_menu.add_separator()
    boards_menu.add_command(
        label="Switch Board",
        command=app.switch_board_dialog,
        accelerator=app.get_shortcut_label('switch_board_dialog'),
    )
    boards_menu.add_command(
        label="Rename Current Board",
        command=app.rename_current_board_dialog,
        accelerator=app.get_shortcut_label('rename_current_board_dialog'),
    )
    boards_menu.add_command(
        label="Delete Current Board",
        command=app.delete_current_board_dialog,
        accelerator=app.get_shortcut_label('delete_current_board_dialog'),
    )
    boards_menu.add_separator()
    boards_menu.add_command(
        label="Board Statistics",
        command=app.show_board_statistics,
        accelerator=app.get_shortcut_label('show_board_statistics'),
    )

    cards_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Cards", menu=cards_menu)
    cards_menu.add_command(
        label="New Card",
        command=lambda: app.invoke_current_board_action('create_card_dialog'),
        accelerator=app.get_shortcut_label('create_card_dialog'),
    )
    cards_menu.add_command(
        label="Edit Card",
        command=lambda: app.invoke_current_board_action('edit_card_dialog'),
        accelerator=app.get_shortcut_label('edit_card_dialog'),
    )
    cards_menu.add_command(
        label="Move Card",
        command=lambda: app.invoke_current_board_action('move_card_dialog'),
        accelerator=app.get_shortcut_label('move_card_dialog'),
    )
    cards_menu.add_command(
        label="Delete Card",
        command=lambda: app.invoke_current_board_action('delete_card_dialog'),
        accelerator=app.get_shortcut_label('delete_card_dialog'),
    )
    cards_menu.add_separator()
    card_types_menu = tk.Menu(cards_menu, tearoff=0)
    cards_menu.add_cascade(label="Card Types", menu=card_types_menu)
    card_types_menu.add_command(
        label="View Card Types",
        command=lambda: app.invoke_current_board_action('view_card_types_dialog'),
    )
    card_types_menu.add_command(
        label="Create Card Type",
        command=lambda: app.invoke_current_board_action('create_card_type_dialog'),
    )
    card_types_menu.add_command(
        label="Edit Card Type",
        command=lambda: app.invoke_current_board_action('edit_card_type_dialog'),
    )
    card_types_menu.add_command(
        label="Delete Card Type",
        command=lambda: app.invoke_current_board_action('delete_card_type_dialog'),
    )
    cards_menu.add_separator()
    cards_menu.add_command(
        label="Clear Done Cards",
        command=lambda: app.invoke_current_board_action('clear_done_cards'),
        accelerator=app.get_shortcut_label('clear_done_cards'),
    )
    cards_menu.add_command(
        label="Create Backup",
        command=lambda: app.invoke_current_board_action('create_backup'),
        accelerator=app.get_shortcut_label('create_backup'),
    )

    filters_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Filters", menu=filters_menu)
    filters_menu.add_command(
        label="Search Cards",
        command=lambda: app.invoke_current_board_action('search_dialog'),
        accelerator=app.get_shortcut_label('search_dialog'),
    )
    filters_menu.add_command(
        label="Filter by Priority",
        command=lambda: app.invoke_current_board_action('filter_priority_dialog'),
        accelerator=app.get_shortcut_label('filter_priority_dialog'),
    )
    filters_menu.add_command(
        label="Filter by Assignee",
        command=lambda: app.invoke_current_board_action('filter_assignee_dialog'),
        accelerator=app.get_shortcut_label('filter_assignee_dialog'),
    )
    filters_menu.add_command(
        label="Show Late Cards",
        command=lambda: app.invoke_current_board_action('filter_overdue_dialog'),
        accelerator=app.get_shortcut_label('filter_overdue_dialog'),
    )
    filters_menu.add_separator()
    filters_menu.add_command(
        label="Clear Filters",
        command=lambda: app.invoke_current_board_action('clear_filters'),
        accelerator=app.get_shortcut_label('clear_filters'),
    )

    columns_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Columns", menu=columns_menu)
    columns_menu.add_command(
        label="New Column",
        command=lambda: app.invoke_current_board_action('create_column_dialog'),
        accelerator=app.get_shortcut_label('create_column_dialog'),
    )
    columns_menu.add_command(
        label="Column Properties",
        command=lambda: app.invoke_current_board_action('rename_column_dialog'),
        accelerator=app.get_shortcut_label('rename_column_dialog'),
    )
    columns_menu.add_command(
        label="Delete Column",
        command=lambda: app.invoke_current_board_action('delete_column_dialog'),
        accelerator=app.get_shortcut_label('delete_column_dialog'),
    )
    columns_menu.add_command(
        label="Reorder Columns",
        command=lambda: app.invoke_current_board_action('reorder_columns_dialog'),
        accelerator=app.get_shortcut_label('reorder_columns_dialog'),
    )

    tools_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Tools", menu=tools_menu)
    tools_menu.add_command(
        label="Clean Up Orphaned Attachments",
        command=lambda: app.invoke_current_board_action('cleanup_orphaned_attachment_files'),
        accelerator=app.get_shortcut_label('cleanup_orphaned_attachment_files'),
    )
    tools_menu.add_separator()
    tools_menu.add_command(
        label="Export All Boards",
        command=app.export_all_boards,
        accelerator=app.get_shortcut_label('export_all_boards'),
    )
    tools_menu.add_command(
        label="Import Boards",
        command=app.import_boards,
        accelerator=app.get_shortcut_label('import_boards'),
    )

    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="About", command=app.show_about)
    help_menu.add_command(
        label="Keyboard Shortcuts",
        command=app.show_shortcuts,
        accelerator=app.get_shortcut_label('show_shortcuts'),
    )

    bind_menu_shortcuts(app)



def bind_menu_shortcuts(app):
    """Bind keyboard shortcuts for primary menu actions."""
    app.bind_shortcut(app.MENU_SHORTCUTS['undo_current_board_action'][1], app.undo_current_board_action)
    app.bind_shortcut(app.MENU_SHORTCUTS['undo_board_management_action'][1], app.undo_board_management_action)
    app.bind_shortcut(app.MENU_SHORTCUTS['redo_current_board_action'][1], app.redo_current_board_action)
    app.bind_shortcut(app.MENU_SHORTCUTS['redo_board_management_action'][1], app.redo_board_management_action)
    app.bind_shortcut(app.MENU_SHORTCUTS['create_board_dialog'][1], app.create_board_dialog)
    app.bind_shortcut(app.MENU_SHORTCUTS['load_board_from_folder_dialog'][1], app.load_board_from_folder_dialog)
    app.bind_shortcut(app.MENU_SHORTCUTS['switch_board_dialog'][1], app.switch_board_dialog)
    app.bind_shortcut(app.MENU_SHORTCUTS['rename_current_board_dialog'][1], app.rename_current_board_dialog)
    app.bind_shortcut(app.MENU_SHORTCUTS['delete_current_board_dialog'][1], app.delete_current_board_dialog)
    app.bind_shortcut(app.MENU_SHORTCUTS['show_board_statistics'][1], app.show_board_statistics)
    app.bind_shortcut(
        app.MENU_SHORTCUTS['create_card_dialog'][1],
        lambda: app.invoke_current_board_action('create_card_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['edit_card_dialog'][1],
        lambda: app.invoke_current_board_action('edit_card_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['move_card_dialog'][1],
        lambda: app.invoke_current_board_action('move_card_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['delete_card_dialog'][1],
        lambda: app.invoke_current_board_action('delete_card_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['clear_done_cards'][1],
        lambda: app.invoke_current_board_action('clear_done_cards'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['create_backup'][1],
        lambda: app.invoke_current_board_action('create_backup'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['cleanup_orphaned_attachment_files'][1],
        lambda: app.invoke_current_board_action('cleanup_orphaned_attachment_files'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['search_dialog'][1],
        lambda: app.invoke_current_board_action('search_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['filter_priority_dialog'][1],
        lambda: app.invoke_current_board_action('filter_priority_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['filter_assignee_dialog'][1],
        lambda: app.invoke_current_board_action('filter_assignee_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['filter_overdue_dialog'][1],
        lambda: app.invoke_current_board_action('filter_overdue_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['clear_filters'][1],
        lambda: app.invoke_current_board_action('clear_filters'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['create_column_dialog'][1],
        lambda: app.invoke_current_board_action('create_column_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['rename_column_dialog'][1],
        lambda: app.invoke_current_board_action('rename_column_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['delete_column_dialog'][1],
        lambda: app.invoke_current_board_action('delete_column_dialog'),
    )
    app.bind_shortcut(
        app.MENU_SHORTCUTS['reorder_columns_dialog'][1],
        lambda: app.invoke_current_board_action('reorder_columns_dialog'),
    )
    app.bind_shortcut(app.MENU_SHORTCUTS['export_all_boards'][1], app.export_all_boards)
    app.bind_shortcut(app.MENU_SHORTCUTS['import_boards'][1], app.import_boards)
    app.bind_shortcut(app.MENU_SHORTCUTS['show_shortcuts'][1], app.show_shortcuts)
    app.bind_shortcut(app.MENU_SHORTCUTS['on_close'][1], app.on_close)



def setup_toolbar(app):
    """Set up the toolbar with board selection and quick summary."""
    toolbar_frame = tk.Frame(
        app.root,
        bg=PANEL_BG,
        height=48,
        highlightthickness=1,
        highlightbackground=OUTLINE_COLOR,
    )
    toolbar_frame.pack(fill='x', padx=8, pady=(8, 4))
    toolbar_frame.pack_propagate(False)

    tk.Label(
        toolbar_frame,
        text="Current Board:",
        bg=PANEL_BG,
        font=('Arial', 10, 'bold'),
    ).pack(side='left', padx=12)

    app.board_var = tk.StringVar()
    app.board_selector = ttk.Combobox(
        toolbar_frame,
        textvariable=app.board_var,
        width=30,
        state='readonly',
        style='Soft.TCombobox',
    )
    app.board_selector.pack(side='left', padx=5)
    app.board_selector.bind('<<ComboboxSelected>>', app.on_board_selected)

    spacer = tk.Frame(toolbar_frame, bg=PANEL_BG)
    spacer.pack(side='left', fill='x', expand=True)

    app.board_info_var = tk.StringVar(value="0 cards | 0 completed")
    app.board_info_label = tk.Label(
        toolbar_frame,
        textvariable=app.board_info_var,
        bg=PANEL_BG,
        fg='#3F3A34',
        font=('Arial', 10, 'bold'),
        anchor='e',
        justify='right',
    )
    app.board_info_label.pack(side='right', padx=12)



def build_shortcuts_text(app):
    """Return the keyboard shortcuts help text."""
    return (
        "⌨️ Keyboard Shortcuts\n\n"
        "Undo:\n"
        f"{app.get_shortcut_label('undo_current_board_action')} - Undo current board action\n"
        f"{app.get_shortcut_label('undo_board_management_action')} - Undo board management action\n"
        f"{app.get_shortcut_label('redo_current_board_action')} - Redo current board action\n"
        f"{app.get_shortcut_label('redo_board_management_action')} - Redo board management action\n\n"
        "Boards:\n"
        f"{app.get_shortcut_label('create_board_dialog')} - Create new board\n"
        f"{app.get_shortcut_label('load_board_from_folder_dialog')} - Load board from folder\n"
        f"{app.get_shortcut_label('switch_board_dialog')} - Switch board\n"
        f"{app.get_shortcut_label('rename_current_board_dialog')} - Rename current board\n"
        f"{app.get_shortcut_label('delete_current_board_dialog')} - Delete current board\n"
        f"{app.get_shortcut_label('show_board_statistics')} - Board statistics\n\n"
        "Cards and filters:\n"
        f"{app.get_shortcut_label('create_card_dialog')} - New card\n"
        f"{app.get_shortcut_label('edit_card_dialog')} - Edit card\n"
        f"{app.get_shortcut_label('move_card_dialog')} - Move card\n"
        f"{app.get_shortcut_label('delete_card_dialog')} - Delete card\n"
        f"{app.get_shortcut_label('clear_done_cards')} - Clear done cards\n"
        f"{app.get_shortcut_label('create_backup')} - Create backup\n"
        f"{app.get_shortcut_label('cleanup_orphaned_attachment_files')} - Clean up orphaned attachments\n"
        f"{app.get_shortcut_label('search_dialog')} - Search cards\n"
        f"{app.get_shortcut_label('filter_priority_dialog')} - Filter by priority\n"
        f"{app.get_shortcut_label('filter_assignee_dialog')} - Filter by assignee\n"
        f"{app.get_shortcut_label('filter_overdue_dialog')} - Show late cards\n"
        f"{app.get_shortcut_label('clear_filters')} - Clear filters\n\n"
        "Columns and app:\n"
        f"{app.get_shortcut_label('create_column_dialog')} - New column\n"
        f"{app.get_shortcut_label('rename_column_dialog')} - Column properties\n"
        f"{app.get_shortcut_label('delete_column_dialog')} - Delete column\n"
        f"{app.get_shortcut_label('reorder_columns_dialog')} - Reorder columns\n"
        f"{app.get_shortcut_label('export_all_boards')} - Export all boards\n"
        f"{app.get_shortcut_label('import_boards')} - Import boards\n"
        f"{app.get_shortcut_label('show_shortcuts')} - Show shortcuts\n"
        f"{app.get_shortcut_label('on_close')} - Quit application\n\n"
        "Mouse actions:\n"
        "Double-click card - Edit card\n"
        "Right-click card - Context menu"
    )



def show_shortcuts(app):
    """Show the keyboard shortcuts dialog."""
    messagebox.showinfo("Keyboard Shortcuts", build_shortcuts_text(app))
