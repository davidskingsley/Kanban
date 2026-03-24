## @file
#  @brief Dialog classes used by the multi-board GUI.
"""Dialog windows for the multi-board GUI."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser

from ..models import Priority
from .common import (
    APP_BG,
    SURFACE_ALT_BG,
    SURFACE_BG,
    TEXT_MUTED,
    bind_mousewheel,
    bind_mousewheel_recursive,
    center_modal,
    create_soft_button,
    create_tooltip,
    format_optional_date,
    is_dark_color,
    parse_optional_date,
    style_text_input,
)

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
        bind_mousewheel(self.desc_text)

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
        center_modal(self.dialog, parent, 420, 280)

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
        bind_mousewheel(self.listbox)
        bind_mousewheel(list_frame, self.listbox)

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
        bind_mousewheel(self.desc_text)

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
        bind_mousewheel(self.listbox)
        bind_mousewheel(list_container, self.listbox)

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

    def __init__(self, parent, title, initial_text="", read_only=False, helper_text=None):
        self.result = None
        self.read_only = read_only
        self.helper_text = helper_text

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        center_modal(self.dialog, parent, 620, 420 if read_only else 320)

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

        text_frame = tk.Frame(main_frame, bg=APP_BG)
        text_frame.pack(fill='both', expand=True, pady=(0, 14))

        self.text_widget = tk.Text(text_frame, height=10, width=60, font=('Arial', 10), wrap='word')
        self.text_widget.pack(side='left', fill='both', expand=True)
        self.text_widget.insert('1.0', initial_text)
        style_text_input(self.text_widget)
        bind_mousewheel(self.text_widget)
        bind_mousewheel(text_frame, self.text_widget)

        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        if self.read_only:
            self.text_widget.configure(state='disabled')

        helper_text = self.helper_text
        if helper_text is None and not self.read_only:
            helper_text = "The note will be saved with the current date and time."
        if helper_text:
            tk.Label(main_frame, text=helper_text, font=('Arial', 9), fg=TEXT_MUTED, bg=APP_BG).pack(anchor='w', pady=(0, 14))

        button_frame = tk.Frame(main_frame, bg=APP_BG)
        button_frame.pack(fill='x')
        if self.read_only:
            create_soft_button(button_frame, "Close", self.cancel, variant='primary').pack(side='right')
        else:
            create_soft_button(button_frame, "Cancel", self.cancel, variant='secondary').pack(side='right', padx=(10, 0))
            create_soft_button(button_frame, "Save Note", self.confirm, variant='primary').pack(side='right')

        self.dialog.bind('<Escape>', lambda _event: self.cancel())
        if not self.read_only:
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
        bind_mousewheel(self.form_canvas)
        bind_mousewheel(content_frame, self.form_canvas)
        
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
        bind_mousewheel(self.description_text)
        
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

        bind_mousewheel_recursive(fields_frame, self.form_canvas, exclude_classes={'Listbox', 'Text'})
        
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
        bind_mousewheel(self.subcards_listbox)
        bind_mousewheel(list_frame, self.subcards_listbox)

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
        bind_mousewheel(self.notes_listbox)
        bind_mousewheel(list_frame, self.notes_listbox)

        actions_frame = tk.Frame(notes_frame, bg=APP_BG)
        actions_frame.pack(fill='x', pady=(8, 0))

        add_button = create_soft_button(actions_frame, "＋", self.add_note, variant='accent', width=2)
        add_button.configure(font=('Segoe UI Symbol', 10, 'bold'), padx=10, pady=5)
        add_button.pack(side='left')
        create_tooltip(add_button, 'Add note')

        view_button = create_soft_button(actions_frame, "👁", self.view_selected_note, variant='secondary', width=2)
        view_button.configure(font=('Segoe UI Emoji', 10, 'bold'), padx=10, pady=5)
        view_button.pack(side='left', padx=(6, 0))
        create_tooltip(view_button, 'View selected note')

        edit_button = create_soft_button(actions_frame, "✎", self.edit_selected_note, variant='secondary', width=2)
        edit_button.configure(font=('Segoe UI Symbol', 10, 'bold'), padx=10, pady=5)
        edit_button.pack(side='left', padx=(6, 0))
        create_tooltip(edit_button, 'Edit selected note')

        delete_button = create_soft_button(actions_frame, "🗑", self.delete_selected_note, variant='secondary', width=2)
        delete_button.configure(font=('Segoe UI Emoji', 10, 'bold'), padx=10, pady=5)
        delete_button.pack(side='left', padx=(6, 0))
        create_tooltip(delete_button, 'Delete selected note')

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

    def edit_selected_note(self):
        """Edit the selected note for the current card."""
        if self.card is None or not hasattr(self, 'notes_listbox'):
            return

        current = self.notes_listbox.curselection()
        if not current or not self.card.notes:
            messagebox.showinfo('Edit Note', 'Select a note to edit.', parent=self.dialog)
            return

        index = current[0]
        if index >= len(self.card.notes):
            return

        note = self.card.notes[index]
        note_dialog = NoteDialog(
            self.dialog,
            f"Edit Note - {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            initial_text=note.text,
            helper_text=f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )
        if note_dialog.result is None:
            return

        updated_note = self.board.edit_card_note(self.card.id, note.id, note_dialog.result)
        if updated_note is None:
            messagebox.showerror('Error', 'Note could not be updated.', parent=self.dialog)
            return

        self.card = self.board.find_card(self.card.id)
        self.refresh_notes_list()
        self.notes_listbox.selection_clear(0, tk.END)
        self.notes_listbox.selection_set(index)
        if self.on_change:
            self.on_change()

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
        details = note.text or '(empty note)'
        NoteDialog(
            self.dialog,
            f"Card Note - {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            initial_text=details,
            read_only=True,
            helper_text=f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )

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
            self.board.create_subcard(
                self.card.id,
                title,
                description,
                priority,
                project or parent_project,
                color,
                card_type_id,
                start_date,
                end_date,
                assignee,
                tags,
            )
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
