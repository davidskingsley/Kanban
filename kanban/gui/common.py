## @file
#  @brief Shared GUI styling, constants, and Tkinter helper utilities.
"""Shared helpers for the multi-board Tkinter GUI."""

from datetime import date
import tkinter as tk
from typing import Optional


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


def bind_mousewheel(widget, target=None, orient='y'):
    """Bind the mouse wheel to a scrollable Tk widget target."""
    if widget is None:
        return

    scroll_target = target or widget

    def on_mousewheel(event, active_target=scroll_target, axis=orient):
        units = mousewheel_units(event)
        if units == 0:
            return None

        if not can_scroll_target(active_target, axis):
            return None

        try:
            if axis == 'x':
                active_target.xview_scroll(units, 'units')
            else:
                active_target.yview_scroll(units, 'units')
        except tk.TclError:
            return None
        return 'break'

    widget.bind('<MouseWheel>', on_mousewheel, add='+')
    widget.bind('<Button-4>', on_mousewheel, add='+')
    widget.bind('<Button-5>', on_mousewheel, add='+')


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
    'center_modal',
    'create_soft_button',
    'style_text_input',
]


## @brief Coordinate multi-board selection, menus, and embedded board views.
