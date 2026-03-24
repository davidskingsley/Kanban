## @file
#  @brief Board workflow dialogs and import-export helpers for the multi-board GUI shell.
"""Board action helpers for the multi-board application."""

import json
import os
from tkinter import filedialog, messagebox, simpledialog

from .dialogs import BoardDialog, SelectionDialog


def create_board_dialog(app):
    """Show dialog to create a new board."""
    dialog = BoardDialog(app.root, app.board_manager.boards_directory, "Create New Board")
    if dialog.result:
        name, description, storage_dir = dialog.result
        board_id = app.board_manager.create_board(name, description, target_directory=storage_dir)
        if board_id:
            app.board_manager.switch_board(board_id)
            app.welcome_frame.pack_forget()
            app.refresh_board_display()
            messagebox.showinfo("Success", f"Board '{name}' created successfully!")
        else:
            messagebox.showerror("Error", "Failed to create board!")


def load_board_from_folder_dialog(app):
    """Load a single board from an external folder into the board list."""
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
            inspected = app.board_manager.inspect_board_file(data_file)
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
        app.root,
        "Load Board From Folder",
        "Select a board to load:",
        options,
    ).result
    if selected is None:
        return

    board_choice = option_map[selected]
    try:
        board_id = app.board_manager.add_external_board(
            board_choice['data_file'],
            name=board_choice['name'],
            description=board_choice['description'],
            use_custom_columns=board_choice['use_custom_columns'],
            switch_to=True,
        )
        if not board_id:
            return
        app.refresh_board_display()
        board = app.board_manager.get_current_board()
        if board and board.is_read_only():
            messagebox.showwarning("Read Only Board", board.get_read_only_message())
        else:
            messagebox.showinfo("Success", f"Board '{board_choice['name']}' loaded successfully!")
    except FileNotFoundError:
        messagebox.showerror("Error", "The selected board file could not be found.")
    except Exception as error:
        messagebox.showerror("Error", f"Failed to load board:\n{error}")


def switch_board_dialog(app):
    """Show dialog to switch to a different board."""
    boards = app.board_manager.get_board_list()
    if len(boards) <= 1:
        messagebox.showinfo("Info", "Only one board available!")
        return

    board_names = [board['name'] for board in boards if not board['is_current']]
    if not board_names:
        messagebox.showinfo("Info", "No other boards to switch to!")
        return

    selected = SelectionDialog(
        app.root,
        "Switch Board",
        "Select a board:",
        board_names,
    ).result

    if selected:
        for board in boards:
            if board['name'] == selected:
                app.board_manager.switch_board(board['id'])
                app.refresh_board_display()
                return
        messagebox.showerror("Error", "Board not found!")


def rename_current_board_dialog(app):
    """Show dialog to rename the current board."""
    current_board = app.board_manager.get_current_board()
    if not current_board:
        messagebox.showwarning("Warning", "No board selected!")
        return

    boards = app.board_manager.get_board_list()
    current_board_id = None
    current_name = ""

    for board in boards:
        if board['is_current']:
            current_board_id = board['id']
            current_name = board['name']
            break

    new_name = simpledialog.askstring(
        "Rename Board",
        f"Current name: {current_name}\n\nEnter new name:",
        initialvalue=current_name,
    )

    if new_name and new_name != current_name:
        if app.board_manager.rename_board(current_board_id, new_name):
            app.refresh_board_display()
            messagebox.showinfo("Success", f"Board renamed to '{new_name}'!")
        else:
            messagebox.showerror("Error", "Failed to rename board!")


def delete_current_board_dialog(app):
    """Show dialog to delete the current board."""
    boards = app.board_manager.get_board_list()
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

    result = messagebox.askyesno(
        "Confirm Deletion",
        f"Are you sure you want to delete board '{current_name}'?\n\n"
        + "If this is the last board, the app will return to the empty welcome state.",
    )

    if result:
        if app.board_manager.delete_board(current_board_id):
            if len(boards) == 1:
                app.clear_board_interface()
                app.clear_board_selector()
                if hasattr(app, 'board_info_var'):
                    app.board_info_var.set("No board selected")
            app.refresh_board_display()
            messagebox.showinfo("Success", f"Board '{current_name}' deleted!")
        else:
            messagebox.showerror("Error", "Failed to delete board!")


def export_all_boards(app):
    """Export all boards to a backup file."""
    filename = filedialog.asksaveasfilename(
        defaultextension='.json',
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="Export All Boards",
    )

    if filename:
        try:
            export_data = app.board_manager.export_all_boards()
            with open(filename, 'w', encoding='utf-8') as export_file:
                json.dump(export_data, export_file, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"All boards exported to '{filename}'!")
        except Exception as error:
            messagebox.showerror("Error", f"Failed to export boards: {error}")


def import_boards(app):
    """Import boards from a backup file."""
    filename = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="Import Boards",
    )

    if filename:
        result = messagebox.askyesno(
            "Confirm Import",
            "This will replace all existing boards!\n\nAre you sure you want to continue?",
        )
        if result:
            try:
                with open(filename, 'r', encoding='utf-8') as import_file:
                    import_data = json.load(import_file)

                if app.board_manager.import_boards(import_data):
                    app.refresh_board_display()
                    messagebox.showinfo("Success", f"Boards imported from '{filename}'!")
                else:
                    messagebox.showerror("Error", "Failed to import boards!")
            except Exception as error:
                messagebox.showerror("Error", f"Failed to import boards: {error}")