## @file
#  @brief Embedded single-board GUI surface used inside the multi-board shell.
"""Embedded board view for the multi-board GUI."""

import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from ..models import Status, Priority
from .common import (
    ACCENT_ACTION,
    APP_BG,
    OUTLINE_COLOR,
    PANEL_BG,
    SURFACE_ALT_BG,
    SURFACE_BG,
    TEXT_MUTED,
    bind_file_drop,
    bind_mousewheel,
    get_card_palette,
    mousewheel_units,
    open_path_with_default_app,
)
from .dialogs import (
    CardDialog,
    CardTypeDialog,
    CardTypesOverviewDialog,
    ColumnDialog,
    DueDateOverviewDialog,
    ReorderColumnsDialog,
    SelectionDialog,
)

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
        self.column_drop_targets = []
        self.drag_preview = None
        self.column_drag_state = None
        
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
        bind_mousewheel(self.canvas, self.canvas, orient='x')
        bind_mousewheel(self.scrollable_frame, self.canvas, orient='x')
        bind_mousewheel(canvas_frame, self.canvas, orient='x')
        
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
        self.column_drop_targets = []
        
        if hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns:
            self.refresh_custom_columns()
        else:
            self.refresh_legacy_columns()

        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.multi_board_gui:
            self.multi_board_gui.update_board_info(self.board.get_board_stats(), self.board)
            self.multi_board_gui.sync_toolbar_filters()
        
        self.update_status_bar()

    def get_available_assignees(self):
        """Return sorted assignee names available on the board."""
        assignees = {card.assignee for card in self.board.get_all_cards() if card.assignee}
        return sorted(assignees)

    def get_filter_state(self):
        """Return the currently active board-filter values."""
        return {
            'search': self.search_filter or '',
            'priority': self.priority_filter or '',
            'assignee': self.assignee_filter or '',
            'overdue': bool(self.overdue_filter),
        }

    def apply_toolbar_filters(self, search_text=None, priority=None, assignee=None, overdue=None):
        """Apply compact toolbar filter values in one refresh."""
        self.search_filter = (search_text or '').strip() or None
        self.priority_filter = (priority or '').strip() or None
        self.assignee_filter = (assignee or '').strip() or None
        self.overdue_filter = bool(overdue)
        self.refresh_display()

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
            self.bind_column_drag_events(header_frame, column)
            self.bind_column_drag_events(header_label, column)
            
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
            self.column_drop_targets.append({
                'column_id': column.id,
                'label': column.name,
                'frame': col_frame,
            })
            
            # Display cards
            self.display_cards_in_frame(cards_frame, column.cards)

    def bind_column_drag_events(self, widget, column):
        """Bind drag events that allow custom columns to be reordered from the header."""
        widget.bind("<Button-1>", lambda event, current_column=column: self.start_column_drag(event, current_column))
        widget.bind("<B1-Motion>", lambda event, current_column=column: self.drag_column(event, current_column))
        widget.bind("<ButtonRelease-1>", lambda event, current_column=column: self.end_column_drag(event, current_column))

    def start_column_drag(self, event, column):
        """Record the starting state for a potential column drag."""
        if not (hasattr(self.board, 'use_custom_columns') and self.board.use_custom_columns):
            return

        self.column_drag_state = {
            'column_id': column.id,
            'start_x': event.x_root,
            'start_y': event.y_root,
            'is_dragging': False,
        }

    def drag_column(self, event, column):
        """Track column drag motion and highlight the target insertion point."""
        if not self.column_drag_state or self.column_drag_state.get('column_id') != column.id:
            return

        if not self.column_drag_state['is_dragging']:
            dx = abs(event.x_root - self.column_drag_state['start_x'])
            dy = abs(event.y_root - self.column_drag_state['start_y'])
            if dx > 6 or dy > 6:
                self.column_drag_state['is_dragging'] = True
                self.create_column_drag_preview(column, event.x_root, event.y_root)
                self.status_bar.config(text=f"Dragging column '{column.name}'")

        if self.column_drag_state['is_dragging']:
            self.move_drag_preview(event.x_root, event.y_root)
            self.highlight_column_drop_targets(event.x_root)
            self.auto_scroll_column_drag(event.x_root)

    def end_column_drag(self, event, column):
        """Complete a column drag-drop reorder when released over another column."""
        if not self.column_drag_state or self.column_drag_state.get('column_id') != column.id:
            return

        was_dragging = self.column_drag_state.get('is_dragging', False)
        self.column_drag_state = None
        if not was_dragging:
            return

        target_order = self.get_dragged_column_order(event.x_root, column.id)
        self.clear_column_drop_highlights()
        self.destroy_drag_preview()

        if target_order is None:
            self.refresh_display()
            return

        current_order = [item.id for item in self.board.get_columns_ordered()]
        if target_order == current_order:
            self.refresh_display()
            return

        if not self.ensure_board_writable():
            self.refresh_display()
            return

        if self.board.reorder_columns(target_order):
            self.refresh_display()
            self.status_bar.config(text=f"🔄 Reordered column: {column.name}")
            return

        self.refresh_display()

    def create_column_drag_preview(self, column, x, y):
        """Create a floating preview for the dragged column header."""
        self.destroy_drag_preview()

        preview = tk.Toplevel(self.parent_frame)
        preview.overrideredirect(True)
        preview.attributes('-topmost', True)
        preview.configure(bg='#DCE8F8')

        preview_frame = tk.Frame(
            preview,
            bg=column.color if hasattr(column, 'color') else SURFACE_BG,
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground='#C8D8F0',
        )
        preview_frame.pack(fill='both', expand=True)

        tk.Label(
            preview_frame,
            text=f"{column.name} ({len(column)})",
            font=('Arial', 10, 'bold'),
            bg=preview_frame['bg'],
            fg='white' if getattr(column, 'color', '#FFFFFF') != '#FFFFFF' else '#2F2923',
            padx=12,
            pady=10,
        ).pack(fill='both', expand=True)

        preview.geometry(f"240x44+{x + 12}+{y + 12}")
        self.drag_preview = preview

    def highlight_column_drop_targets(self, x):
        """Highlight the column where the dragged header would be inserted."""
        insertion_index = self.get_column_insertion_index(x)
        for index, target in enumerate(self.column_drop_targets):
            frame = target['frame']
            if insertion_index is None:
                frame.config(highlightbackground=OUTLINE_COLOR, highlightcolor=OUTLINE_COLOR, highlightthickness=1)
                continue

            highlight_active = index == insertion_index or (insertion_index == len(self.column_drop_targets) and index == len(self.column_drop_targets) - 1)
            if highlight_active:
                frame.config(highlightbackground=ACCENT_ACTION, highlightcolor=ACCENT_ACTION, highlightthickness=3)
            else:
                frame.config(highlightbackground=OUTLINE_COLOR, highlightcolor=OUTLINE_COLOR, highlightthickness=1)

    def clear_column_drop_highlights(self):
        """Restore default column highlight styling after a drag completes."""
        for target in self.column_drop_targets:
            frame = target['frame']
            frame.config(highlightbackground=OUTLINE_COLOR, highlightcolor=OUTLINE_COLOR, highlightthickness=1)

    def get_column_insertion_index(self, x_root):
        """Return the insertion index for a dragged column based on the pointer position."""
        if not self.column_drop_targets:
            return None

        first_frame = self.column_drop_targets[0]['frame']
        last_frame = self.column_drop_targets[-1]['frame']
        board_left = first_frame.winfo_rootx()
        board_right = last_frame.winfo_rootx() + last_frame.winfo_width()
        if x_root < board_left or x_root > board_right:
            return None

        for index, target in enumerate(self.column_drop_targets):
            frame = target['frame']
            frame_x = frame.winfo_rootx()
            frame_width = frame.winfo_width()
            midpoint = frame_x + (frame_width / 2)
            if x_root < midpoint:
                return index
        return len(self.column_drop_targets)

    def get_dragged_column_order(self, x_root, dragged_column_id):
        """Return the reordered column ID list implied by the drag position."""
        insertion_index = self.get_column_insertion_index(x_root)
        if insertion_index is None:
            return None

        order = [item.id for item in self.board.get_columns_ordered()]
        if dragged_column_id not in order:
            return None

        order.remove(dragged_column_id)
        insertion_index = min(insertion_index, len(order))
        order.insert(insertion_index, dragged_column_id)
        return order

    def auto_scroll_column_drag(self, x_root):
        """Auto-scroll the board horizontally while dragging a column near an edge."""
        canvas_left = self.canvas.winfo_rootx()
        canvas_right = canvas_left + self.canvas.winfo_width()
        threshold = 48

        if x_root <= canvas_left + threshold:
            self.canvas.xview_scroll(-1, 'units')
        elif x_root >= canvas_right - threshold:
            self.canvas.xview_scroll(1, 'units')
    
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
        bind_mousewheel(canvas)
        bind_mousewheel(scrollable_frame, canvas)
        bind_mousewheel(container, canvas)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        scrollable_frame.scroll_canvas = canvas

        return scrollable_frame

    def bind_column_mousewheel(self, widget, canvas):
        """Bind mouse-wheel scrolling for any widget within a column."""
        bind_mousewheel(widget, canvas)

    def scroll_column_canvas(self, event, canvas):
        """Scroll a specific column canvas using the mouse wheel."""
        units = mousewheel_units(event)
        if units == 0:
            return None
        canvas.yview_scroll(units, 'units')
        return 'break'
    
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

        if card.attachments:
            attachments_frame = tk.Frame(content_frame, bg=card_bg)
            attachments_frame.pack(fill='x', pady=(6, 0))

            for attachment in card.attachments[:2]:
                attachment_label = tk.Label(
                    attachments_frame,
                    text=f"📎 {attachment.name} | {attachment.created_at.strftime('%Y-%m-%d %H:%M')}",
                    font=('Arial', 8, 'underline'),
                    bg=card_bg,
                    fg='#2F5D95',
                    cursor='hand2',
                    anchor='w',
                    justify='left',
                    wraplength=220,
                )
                attachment_label.pack(fill='x')
                attachment_label.skip_card_bindings = True
                attachment_label.bind(
                    '<Button-1>',
                    lambda event, current_card=card, current_attachment=attachment: self.open_card_attachment(current_card, current_attachment),
                )

            if len(card.attachments) > 2:
                more_label = tk.Label(
                    attachments_frame,
                    text=f"+{len(card.attachments) - 2} more attachment(s)",
                    font=('Arial', 8),
                    bg=card_bg,
                    fg=muted_fg,
                    anchor='w',
                )
                more_label.pack(fill='x')
                more_label.skip_card_bindings = True

        card_frame.scroll_canvas = getattr(parent, 'scroll_canvas', None)

        self.bind_card_events(card_frame, card)
        self.bind_card_file_drop(card_frame, card)
        return card_frame

    def bind_card_events(self, card_frame, card):
        """Bind click, drag, and context menu events to a card and its children."""
        def bind_recursive(widget):
            if getattr(widget, 'skip_card_bindings', False):
                if getattr(card_frame, 'scroll_canvas', None) is not None:
                    bind_mousewheel(widget, card_frame.scroll_canvas)
                for child in widget.winfo_children():
                    bind_recursive(child)
                return

            widget.bind("<Button-1>", lambda e, frame=card_frame: self.start_card_drag(e, frame))
            widget.bind("<B1-Motion>", lambda e, current_card=card, frame=card_frame: self.drag_card(e, current_card, frame))
            widget.bind("<ButtonRelease-1>", lambda e, current_card=card, frame=card_frame: self.end_card_drag(e, current_card, frame))
            widget.bind("<Double-Button-1>", lambda e, current_card=card: self.edit_card_dialog(current_card))
            widget.bind("<Button-3>", lambda e, current_card=card: self.show_card_context_menu(e, current_card))
            if getattr(card_frame, 'scroll_canvas', None) is not None:
                bind_mousewheel(widget, card_frame.scroll_canvas)

            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(card_frame)

    def bind_card_file_drop(self, card_frame, card):
        """Allow files to be dropped onto a card to create attachments."""
        def register_recursive(widget):
            bind_file_drop(widget, lambda paths, current_card=card: self.handle_card_file_drop(current_card, paths))
            for child in widget.winfo_children():
                register_recursive(child)

        register_recursive(card_frame)

    def handle_card_file_drop(self, card, paths):
        """Copy dropped files into board storage and link them to a card."""
        if not self.ensure_board_writable():
            return

        files = [path for path in paths if os.path.isfile(path)]
        if not files:
            return

        try:
            attachments = self.board.add_card_attachments(card.id, files)
        except (PermissionError, FileNotFoundError, OSError) as error:
            messagebox.showerror("Attachment Error", str(error))
            return

        if not attachments:
            return

        self.refresh_display()
        self.status_bar.config(text=f"📎 Added {len(attachments)} attachment(s) to {card.title}")

    def open_card_attachment(self, card, attachment):
        """Open an attachment linked from a board card."""
        attachment_path = self.board.get_card_attachment_path(card.id, attachment.id)
        if not attachment_path or not os.path.exists(attachment_path):
            messagebox.showerror("Attachment Missing", f"The stored file for '{attachment.name}' could not be found.")
            return 'break'

        try:
            open_path_with_default_app(attachment_path)
        except Exception as error:
            messagebox.showerror("Open Attachment", f"Could not open file:\n{error}")
        return 'break'

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
                    self.board.create_card(
                        title,
                        description,
                        priority,
                        target_column,
                        project,
                        start_date,
                        end_date,
                        color=color,
                        card_type_id=card_type_id,
                        assignee=assignee,
                        tags=tags,
                    )
                else:
                    messagebox.showerror("Error", "No columns available!")
                    return
            else:
                self.board.create_card(
                    title,
                    description,
                    priority,
                    Status.TODO,
                    project,
                    start_date,
                    end_date,
                    color=color,
                    card_type_id=card_type_id,
                    assignee=assignee,
                    tags=tags,
                )
            
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
                               end_date=end_date, color=color, tags=tags,
                               card_type_id=card_type_id)
            
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
        
        if messagebox.askyesno("Confirm Delete", f"Delete card '{card.title}'?"):
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
        if search_term is not None:
            self.search_filter = search_term.strip() or None
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
        assignees = self.get_available_assignees()
        
        if not assignees:
            messagebox.showinfo("No Assignees", "No cards have assignees!")
            return

        selected = self.choose_option("Filter by Assignee", "Select assignee:", assignees)
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
        menu.add_command(label="📎 Add Attachment", command=lambda: self.edit_card_dialog(card))
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
            if self.board.add_card_tag(card.id, tag):
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
                self.board.create_subcard(
                    parent_card.id,
                    title,
                    description,
                    priority,
                    project,
                    color,
                    card_type_id,
                    start_date,
                    end_date,
                    assignee,
                    tags,
                )

                self.refresh_display()
                self.status_bar.config(text=f"✅ Created subcard: {title}")
            except ValueError as error:
                messagebox.showerror("Error", str(error))

    def show_card_details(self, card):
        """Show detailed information about a card."""
        card = self.board.find_card(card.id) or card
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
        details += f"Attachments: {len(card.attachments)}\n"
        parent_card = self.board.get_parent_card(card)
        details += f"Parent: {parent_card.title if parent_card else 'None'}\n"
        details += f"Created: {card.created_at.strftime('%Y-%m-%d %H:%M') if card.created_at else 'Unknown'}\n"
        details += f"Updated: {card.updated_at.strftime('%Y-%m-%d %H:%M') if card.updated_at else 'Unknown'}\n"

        if card.notes:
            details += "\nNotes:\n"
            for note in card.notes:
                details += f"- {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"

        if card.attachments:
            details += "\nAttachments:\n"
            for attachment in card.attachments:
                details += f"- {attachment.created_at.strftime('%Y-%m-%d %H:%M')} | {attachment.name}\n"

        completed, total = self.board.get_subcard_progress(card.id)
        if total:
            details += "\nSubcards:\n"
            for subcard in self.board.get_subcards(card.id):
                tick = "[x]" if self.board.is_card_done(subcard) else "[ ]"
                details += f"{tick} {subcard.title} ({self.board.get_card_location_label(subcard)})\n"
        
        messagebox.showinfo("Card Details", details)

    def show_due_dates_view(self):
        """Show a graphical due-date timeline and open card details on click."""
        DueDateOverviewDialog(
            self.parent_frame,
            self.board,
            on_card_selected=lambda selected_card: self.show_card_details(selected_card),
        )

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
        self.board.update_column(column.id, name=new_name, color=new_color)
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

    def undo_last_action(self):
        """Undo the most recent change on the current board."""
        description = self.board.undo_last_action()
        if not description:
            messagebox.showinfo("Nothing to Undo", "No board action is available to undo.")
            return

        self.refresh_display()
        self.status_bar.config(text=f"↩ Undid: {description}")

    def redo_last_action(self):
        """Redo the most recently undone change on the current board."""
        description = self.board.redo_last_action()
        if not description:
            messagebox.showinfo("Nothing to Redo", "No board action is available to redo.")
            return

        self.refresh_display()
        self.status_bar.config(text=f"↪ Redid: {description}")

    def create_backup(self):
        """Create a backup of the board."""
        try:
            backup_path = self.board.storage.create_backup()
            messagebox.showinfo("Backup Created", f"Backup created at:\n{backup_path}")
            self.status_bar.config(text="💾 Backup created")
        except Exception as e:
            messagebox.showerror("Backup Failed", f"Failed to create backup:\n{str(e)}")

    def cleanup_orphaned_attachment_files(self):
        """Delete copied attachment files that are no longer referenced by the board or history."""
        if not self.ensure_board_writable():
            return

        try:
            result = self.board.cleanup_orphaned_attachment_files()
        except Exception as error:
            messagebox.showerror("Cleanup Failed", f"Failed to clean orphaned attachments:\n{error}")
            return

        removed_files = result['removed_files']
        removed_directories = result['removed_directories']
        if removed_files == 0:
            messagebox.showinfo("No Orphaned Attachments", "No orphaned attachment files were found.")
            if removed_directories:
                self.status_bar.config(
                    text=f"🧹 Removed {removed_directories} empty attachment director{'y' if removed_directories == 1 else 'ies'}"
                )
            return

        self.status_bar.config(text=f"🧹 Removed {removed_files} orphaned attachment file(s)")
        messagebox.showinfo(
            "Cleanup Complete",
            f"Removed {removed_files} orphaned attachment file(s)\n"
            f"Removed {removed_directories} empty attachment director{'y' if removed_directories == 1 else 'ies'}",
        )
    
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
