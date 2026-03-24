## @file
#  @brief Shared GUI styling, constants, and Tkinter helper utilities.
"""Shared helpers for the multi-board Tkinter GUI."""

from datetime import date
import os
import tkinter as tk
from typing import Optional

try:
    from tkinterdnd2 import COPY, DND_FILES, TkinterDnD
    FILE_DROP_AVAILABLE = True
except ImportError:
    COPY = None
    DND_FILES = None
    TkinterDnD = None
    FILE_DROP_AVAILABLE = False


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


def mousewheel_units(event) -> int:
    """Normalize wheel input across platforms into Tk scroll units."""
    delta = getattr(event, 'delta', 0)
    if delta:
        units = int(-delta / 120)
        if units == 0:
            return -1 if delta > 0 else 1
        return units

    button_number = getattr(event, 'num', None)
    if button_number == 4:
        return -1
    if button_number == 5:
        return 1
    return 0


def can_scroll_target(widget, orient='y') -> bool:
    """Return whether a scroll target currently has overflow in the requested direction."""
    if widget is None:
        return False

    try:
        view = widget.xview() if orient == 'x' else widget.yview()
    except (AttributeError, tk.TclError):
        return False

    if not view or len(view) != 2:
        return False

    first, last = view
    return not (first <= 0.0 and last >= 1.0)


def scroll_target_by_units(widget, units, orient='y') -> bool:
    """Scroll a Tk target by the requested units and report whether it succeeded."""
    if widget is None or units == 0:
        return False

    try:
        if orient == 'x':
            widget.xview_scroll(units, 'units')
        else:
            widget.yview_scroll(units, 'units')
    except (AttributeError, tk.TclError):
        return False
    return True


def iter_mousewheel_bindings(widget):
    """Yield configured mouse-wheel bindings for a widget and its ancestors."""
    current = widget
    while current is not None:
        bindings = getattr(current, '_kanban_mousewheel_bindings', ())
        for orient, target in bindings:
            yield orient, target
        current = getattr(current, 'master', None)


def bind_mousewheel(widget, target=None, orient='y'):
    """Bind the mouse wheel to a scrollable Tk widget target."""
    if widget is None:
        return

    scroll_target = target or widget

    bindings = list(getattr(widget, '_kanban_mousewheel_bindings', []))
    binding_entry = (orient, scroll_target)
    if binding_entry not in bindings:
        bindings.append(binding_entry)
        widget._kanban_mousewheel_bindings = bindings

    def on_mousewheel(event):
        units = mousewheel_units(event)
        if units == 0:
            return None

        for axis, active_target in iter_mousewheel_bindings(event.widget):
            if not can_scroll_target(active_target, axis):
                continue
            if scroll_target_by_units(active_target, units, axis):
                return 'break'
        return None

    if not getattr(widget, '_kanban_mousewheel_handler_bound', False):
        widget.bind('<MouseWheel>', on_mousewheel, add='+')
        widget.bind('<Button-4>', on_mousewheel, add='+')
        widget.bind('<Button-5>', on_mousewheel, add='+')
        widget._kanban_mousewheel_handler_bound = True


def bind_mousewheel_recursive(root, target=None, orient='y', exclude_classes=None):
    """Bind the mouse wheel to a widget subtree while excluding dedicated scrollers."""
    excluded = set(exclude_classes or [])

    def bind_widget(widget):
        if widget.winfo_class() not in excluded:
            bind_mousewheel(widget, target, orient)
        for child in widget.winfo_children():
            bind_widget(child)

    bind_widget(root)


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


def finalize_modal_size(dialog, min_width, min_height, resizable=False, screen_margin=60):
    """Resize and recenter a modal after its content is created so action buttons remain visible."""
    dialog.update_idletasks()

    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    max_width = max(min_width, screen_width - screen_margin)
    max_height = max(min_height, screen_height - screen_margin)

    requested_width = max(min_width, dialog.winfo_reqwidth())
    requested_height = max(min_height, dialog.winfo_reqheight())
    width = min(requested_width, max_width)
    height = min(requested_height, max_height)

    x = max(0, (screen_width // 2) - (width // 2))
    y = max(0, (screen_height // 2) - (height // 2))

    dialog.minsize(min_width, min_height)
    dialog.resizable(resizable, resizable)
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


def create_tooltip(widget, text):
    """Attach a simple hover tooltip to a widget."""
    if not text:
        return

    tooltip_state = {'window': None}

    def show_tooltip(_event=None):
        if tooltip_state['window'] is not None:
            return

        try:
            x = widget.winfo_rootx() + 12
            y = widget.winfo_rooty() + widget.winfo_height() + 6
        except tk.TclError:
            return

        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f'+{x}+{y}')
        tooltip.configure(bg='#FFF9E8')

        tk.Label(
            tooltip,
            text=text,
            bg='#FFF9E8',
            fg='#2F2923',
            relief='solid',
            bd=1,
            padx=8,
            pady=4,
            font=('Arial', 9),
        ).pack()
        tooltip_state['window'] = tooltip

    def hide_tooltip(_event=None):
        tooltip = tooltip_state['window']
        if tooltip is not None:
            try:
                tooltip.destroy()
            except tk.TclError:
                pass
            tooltip_state['window'] = None

    widget.bind('<Enter>', show_tooltip, add='+')
    widget.bind('<Leave>', hide_tooltip, add='+')
    widget.bind('<ButtonPress>', hide_tooltip, add='+')


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


def create_app_root():
    """Create the main Tk root with file-drop support when available."""
    if FILE_DROP_AVAILABLE:
        return TkinterDnD.Tk()
    return tk.Tk()


def parse_dropped_files(widget, raw_data):
    """Parse a TkDND file payload into absolute file paths."""
    if not raw_data:
        return []

    try:
        items = widget.tk.splitlist(raw_data)
    except tk.TclError:
        items = [raw_data]

    paths = []
    for item in items:
        cleaned = item.strip()
        if cleaned.startswith('{') and cleaned.endswith('}'):
            cleaned = cleaned[1:-1]
        if cleaned:
            paths.append(os.path.abspath(cleaned))
    return paths


def bind_file_drop(widget, callback, enter_callback=None, leave_callback=None):
    """Bind an OS file-drop handler to a widget when TkDND is available."""
    if not FILE_DROP_AVAILABLE or widget is None or not hasattr(widget, 'drop_target_register'):
        return False

    widget.drop_target_register(DND_FILES)

    drop_action = COPY or 'copy'

    def on_enter(event):
        if enter_callback is not None:
            enter_callback()
        return event.action if getattr(event, 'action', None) else drop_action

    def on_position(event):
        return event.action if getattr(event, 'action', None) else drop_action

    def on_drop(event):
        callback(parse_dropped_files(widget, getattr(event, 'data', '')))
        return event.action if getattr(event, 'action', None) else drop_action

    widget.dnd_bind('<<Drop>>', on_drop)
    widget.dnd_bind('<<DropPosition>>', on_position)
    if enter_callback is not None:
        widget.dnd_bind('<<DropEnter>>', on_enter)
    if leave_callback is not None:
        widget.dnd_bind('<<DropLeave>>', lambda event: leave_callback())
    return True


def open_path_with_default_app(path):
    """Open a file path with the operating system's default application."""
    absolute_path = os.path.abspath(path)
    if os.name == 'nt':
        os.startfile(absolute_path)
        return

    import subprocess
    import sys

    command = ['open', absolute_path] if sys.platform == 'darwin' else ['xdg-open', absolute_path]
    subprocess.Popen(command)


__all__ = [
    'APP_BG',
    'PANEL_BG',
    'SURFACE_BG',
    'SURFACE_ALT_BG',
    'OUTLINE_COLOR',
    'TEXT_MUTED',
    'HOVER_BG',
    'PRIMARY_ACTION',
    'SECONDARY_ACTION',
    'ACCENT_ACTION',
    'is_dark_color',
    'get_card_palette',
    'format_optional_date',
    'parse_optional_date',
    'mousewheel_units',
    'can_scroll_target',
    'bind_mousewheel',
    'bind_mousewheel_recursive',
    'FILE_DROP_AVAILABLE',
    'create_app_root',
    'bind_file_drop',
    'parse_dropped_files',
    'open_path_with_default_app',
    'center_modal',
    'create_soft_button',
    'create_tooltip',
    'style_text_input',
]


## @brief Coordinate multi-board selection, menus, and embedded board views.
