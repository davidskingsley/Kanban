## @file
#  @brief Board selection, welcome state, and embedded board surface coordination.
"""Board navigation helpers for the multi-board application."""

import tkinter as tk

from .common import APP_BG, TEXT_MUTED
from .embedded_board import EmbeddedKanbanGUI


def setup_main_area(app):
    """Set up the main area where the board GUI will be embedded."""
    app.main_frame = tk.Frame(app.root, bg=APP_BG)
    app.main_frame.pack(fill='both', expand=True, padx=5, pady=5)

    app.welcome_frame = tk.Frame(app.main_frame, bg=APP_BG)

    welcome_label = tk.Label(
        app.welcome_frame,
        text="🗂️ Welcome to Multi-Board Kanban Manager!\n\nUse Boards > Create New Board to get started.",
        font=('Arial', 16),
        bg=APP_BG,
        fg=TEXT_MUTED,
        justify='center',
    )
    welcome_label.pack(expand=True)


def refresh_board_display(app):
    """Refresh the board display and selector."""
    boards = app.board_manager.get_board_list()

    if hasattr(app, 'board_selector') and app.board_selector:
        board_names = [f"{board['name']}" for board in boards]
        app.board_selector['values'] = board_names

    if boards:
        if hasattr(app, 'welcome_frame'):
            try:
                app.welcome_frame.pack_forget()
            except Exception:
                pass

        current_board = app.board_manager.get_current_board()
        current_board_name = None

        if current_board is None and app.board_manager.current_board_id is None and boards:
            fallback_board = boards[0]
            app.board_manager.switch_board(fallback_board['id'])
            current_board = app.board_manager.get_current_board()

        if current_board is not None:
            for board in boards:
                if board['id'] == app.board_manager.current_board_id:
                    current_board_name = board['name']
                    break

        if current_board_name and current_board is not None:
            if hasattr(app, 'board_var'):
                app.board_var.set(current_board_name)
            if hasattr(app, 'board_selector') and app.board_selector:
                app.board_selector.set(current_board_name)
            clear_board_interface(app)
            app.board_frame = tk.Frame(app.main_frame, bg=APP_BG)
            app.board_frame.pack(fill='both', expand=True)
            app.current_board_gui = EmbeddedKanbanGUI(app.board_frame, current_board, app)
            app.update_board_info(board=current_board)
            app.root.after_idle(lambda: app.update_board_info(board=current_board))
        else:
            clear_board_interface(app)
            if hasattr(app, 'board_var'):
                app.board_var.set("")
            if hasattr(app, 'board_selector') and app.board_selector:
                app.board_selector.set("")
            app.update_board_info()
    else:
        clear_board_interface(app)
        if hasattr(app, 'welcome_frame'):
            try:
                app.welcome_frame.pack(fill='both', expand=True)
            except Exception:
                pass
        clear_board_selector(app)
        if hasattr(app, 'board_info_var'):
            app.board_info_var.set("No board selected")


def clear_board_selector(app):
    """Clear the board selector state, including readonly combobox text."""
    if hasattr(app, 'board_var'):
        app.board_var.set("")

    if hasattr(app, 'board_selector') and app.board_selector:
        app.board_selector['values'] = ()
        try:
            app.board_selector.set("")
            app.board_selector.configure(state='normal')
            app.board_selector.delete(0, tk.END)
        finally:
            app.board_selector.configure(state='readonly')


def load_board_interface(app):
    """Load the current board into the interface."""
    current_board = app.board_manager.get_current_board()
    if not current_board:
        clear_board_interface(app)
        return

    clear_board_interface(app)

    app.board_frame = tk.Frame(app.main_frame, bg=APP_BG)
    app.board_frame.pack(fill='both', expand=True)

    app.current_board_gui = EmbeddedKanbanGUI(app.board_frame, current_board, app)
    app.update_board_info(board=current_board)
    app.root.after_idle(lambda: app.update_board_info(board=current_board))


def clear_board_interface(app):
    """Clear the current board interface."""
    if app.current_board_gui:
        app.current_board_gui.cleanup()
        app.current_board_gui = None

    if app.board_frame:
        app.board_frame.destroy()
        app.board_frame = None


def on_board_selected(app, _event=None):
    """Handle board selection from the combobox."""
    selected_board_name = app.board_var.get()
    if not selected_board_name:
        return

    boards = app.board_manager.get_board_list()
    for board in boards:
        if board['name'] == selected_board_name:
            if not board['is_current']:
                if app.board_manager.switch_board(board['id']):
                    app.refresh_board_display()
                else:
                    app.refresh_board_display()
            break