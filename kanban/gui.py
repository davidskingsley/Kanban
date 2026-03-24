## @file
#  @brief Single-board Tkinter interface with drag-and-drop task management.
"""Graphical User Interface for the Kanban board application using tkinter."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Optional

from .board import KanbanBoard
from .models import Card, Status, Priority


## @brief Render and manage a draggable card widget inside a board column.
class CardWidget(tk.Frame):
    """Widget representing a draggable card on the Kanban board."""
    
    def __init__(self, parent, card: Card, gui_manager):
        super().__init__(parent, relief='raised', bd=1, bg='white', cursor='hand2')
        self.card = card
        self.gui_manager = gui_manager
        self.parent = parent
        
        # Drag and drop variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        
        self.setup_ui()
        self.bind_events()
    
    def setup_ui(self):
        """Set up the card's visual elements."""
        self.config(width=200, height=100)
        self.pack_propagate(False)
        
        # Priority indicator
        priority_colors = {
            Priority.LOW: '#4CAF50',      # Green
            Priority.MEDIUM: '#FF9800',   # Orange  
            Priority.HIGH: '#FF5722',     # Red-Orange
            Priority.CRITICAL: '#F44336'  # Red
        }
        
        priority_frame = tk.Frame(self, bg=priority_colors[self.card.priority], height=8)
        priority_frame.pack(fill='x', side='top')
        
        # Main content frame
        content_frame = tk.Frame(self, bg='white')
        content_frame.pack(fill='both', expand=True, padx=5, pady=2)
        
        # Title
        title_label = tk.Label(content_frame, text=self.card.title, 
                              font=('Arial', 9, 'bold'), 
                              bg='white', fg='black',
                              wraplength=180, justify='left')
        title_label.pack(anchor='w')
        
        # Description (truncated)
        if self.card.description:
            desc_text = self.card.description
            if len(desc_text) > 50:
                desc_text = desc_text[:47] + "..."
            desc_label = tk.Label(content_frame, text=desc_text,
                                 font=('Arial', 8),
                                 bg='white', fg='gray',
                                 wraplength=180, justify='left')
            desc_label.pack(anchor='w')
        
        # Footer with project, assignee, and tags
        footer_frame = tk.Frame(content_frame, bg='white')
        footer_frame.pack(side='bottom', fill='x')

        if self.card.project:
            project_label = tk.Label(footer_frame, text=f"[{self.card.project}]",
                                    font=('Arial', 8),
                                    bg='#F4E8FF', fg='#6B3FA0')
            project_label.pack(side='left', padx=(0, 4))
        
        if self.card.assignee:
            assignee_label = tk.Label(footer_frame, text=f"@{self.card.assignee}",
                                     font=('Arial', 8),
                                     bg='#E3F2FD', fg='#1976D2')
            assignee_label.pack(side='left')

        parent_card = self.gui_manager.board.get_parent_card(self.card)
        if parent_card:
            parent_label = tk.Label(footer_frame, text=f"sub of {parent_card.title[:16]}",
                                   font=('Arial', 8), bg='#F2F2F2', fg='#666')
            parent_label.pack(side='left', padx=(4, 0))
        else:
            completed, total = self.gui_manager.board.get_subcard_progress(self.card.id)
            if total:
                subcards_label = tk.Label(footer_frame, text=f"{completed}/{total} done",
                                         font=('Arial', 8), bg='#EEF7EA', fg='#3A7A36')
                subcards_label.pack(side='left', padx=(4, 0))
        
        if self.card.tags:
            tags_text = " ".join(f"#{tag}" for tag in self.card.tags[:2])
            if len(self.card.tags) > 2:
                tags_text += f" +{len(self.card.tags)-2}"
            tags_label = tk.Label(footer_frame, text=tags_text,
                                 font=('Arial', 8),
                                 bg='white', fg='#666')
            tags_label.pack(side='right')
    
    def bind_events(self):
        """Bind mouse events for drag and drop functionality."""
        # Bind to self and all children for consistent behavior
        def bind_recursive(widget):
            widget.bind('<Button-1>', self.on_click)
            widget.bind('<B1-Motion>', self.on_drag)
            widget.bind('<ButtonRelease-1>', self.on_drop)
            widget.bind('<Double-Button-1>', self.on_double_click)
            widget.bind('<Button-3>', self.on_right_click)  # Right-click context menu
            
            for child in widget.winfo_children():
                bind_recursive(child)
        
        bind_recursive(self)
    
    def on_click(self, event):
        """Handle mouse click to start drag operation."""
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.is_dragging = False
        
        # Bring card to front
        self.lift()
    
    def on_drag(self, event):
        """Handle mouse drag to move the card."""
        if not self.is_dragging:
            # Start dragging if movement threshold is exceeded
            dx = abs(event.x_root - self.drag_start_x)
            dy = abs(event.y_root - self.drag_start_y)
            if dx > 5 or dy > 5:
                self.is_dragging = True
                self.config(relief='flat', bg='#E8EAF6')  # Change appearance while dragging
        
        if self.is_dragging:
            # Calculate new position
            x = self.winfo_x() + (event.x_root - self.drag_start_x)
            y = self.winfo_y() + (event.y_root - self.drag_start_y)
            
            # Move the card
            self.place(x=x, y=y)
            
            # Update drag start position
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
            
            # Highlight drop zones
            self.gui_manager.highlight_drop_zones(event.x_root, event.y_root)
    
    def on_drop(self, event):
        """Handle mouse release to complete the drop operation."""
        if self.is_dragging:
            # Reset card appearance
            self.config(relief='raised', bg='white')
            
            # Find drop target
            target_column = self.gui_manager.get_drop_target(event.x_root, event.y_root)
            
            if target_column and target_column != self.card.status:
                # Move card to new column
                self.gui_manager.move_card_to_column(self.card, target_column)
            else:
                # Return card to original position if no valid drop target
                self.gui_manager.refresh_column(self.card.status)
            
            # Clear drop zone highlights
            self.gui_manager.clear_drop_zone_highlights()
            
        self.is_dragging = False
    
    def on_double_click(self, event):
        """Handle double-click to edit the card."""
        self.gui_manager.edit_card_dialog(self.card)
    
    def on_right_click(self, event):
        """Handle right-click to show context menu."""
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(label="Edit Card", command=lambda: self.gui_manager.edit_card_dialog(self.card))
        if not self.card.parent_id:
            context_menu.add_command(label="Add Subcard", command=lambda: self.gui_manager.add_subcard_dialog(self.card))
        context_menu.add_command(label="Delete Card", command=lambda: self.gui_manager.delete_card_confirm(self.card))
        context_menu.add_separator()
        context_menu.add_command(label="View Details", command=lambda: self.gui_manager.show_card_details(self.card))
        
        try:
            context_menu.post(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()


## @brief Render a single board column and its scrolling card list.
class ColumnWidget(tk.Frame):
    """Widget representing a column on the Kanban board."""
    
    def __init__(self, parent, status: Status, gui_manager):
        super().__init__(parent, relief='solid', bd=1, bg='#FAFAFA')
        self.status = status
        self.gui_manager = gui_manager
        self.is_highlighted = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the column's visual elements."""
        # Column header
        header_colors = {
            Status.TODO: '#FF9800',
            Status.IN_PROGRESS: '#2196F3', 
            Status.REVIEW: '#9C27B0',
            Status.DONE: '#4CAF50'
        }
        
        header_frame = tk.Frame(self, bg=header_colors[self.status], height=40)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text=self.status.value,
                              font=('Arial', 12, 'bold'),
                              bg=header_colors[self.status], fg='white')
        title_label.pack(expand=True)
        
        # Card count label
        self.count_label = tk.Label(header_frame, text="0 cards",
                                   font=('Arial', 8),
                                   bg=header_colors[self.status], fg='white')
        self.count_label.pack()
        
        # Scrollable card area
        self.canvas = tk.Canvas(self, bg='#FAFAFA', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#FAFAFA')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Add card button
        add_button = tk.Button(self.scrollable_frame, text="+ Add Card",
                              command=self.gui_manager.create_card_dialog,
                              bg='#E0E0E0', fg='#666',
                              relief='flat', font=('Arial', 9))
        add_button.pack(pady=5, padx=5, fill='x')
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def add_card_widget(self, card: Card):
        """Add a card widget to the column."""
        card_widget = CardWidget(self.scrollable_frame, card, self.gui_manager)
        card_widget.pack(pady=2, padx=5, fill='x')
        return card_widget
    
    def clear_cards(self):
        """Remove all card widgets from the column."""
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, CardWidget):
                widget.destroy()
    
    def update_count(self, count: int):
        """Update the card count display."""
        self.count_label.config(text=f"{count} card{'s' if count != 1 else ''}")
    
    def highlight(self):
        """Highlight the column as a valid drop zone."""
        if not self.is_highlighted:
            self.config(bg='#E8F5E8', bd=3)
            self.is_highlighted = True
    
    def clear_highlight(self):
        """Remove highlight from the column."""
        if self.is_highlighted:
            self.config(bg='#FAFAFA', bd=1)
            self.is_highlighted = False


## @brief Coordinate the single-board Tkinter window and user actions.
class KanbanGUI:
    """Main GUI application for the Kanban board."""

    MENU_SHORTCUTS = {
        'create_card_dialog': ('Ctrl+N', '<Control-n>'),
        'export_board': ('Ctrl+E', '<Control-e>'),
        'create_backup': ('Ctrl+B', '<Control-b>'),
        'clear_done_cards': ('Ctrl+Shift+K', '<Control-Shift-K>'),
        'search_dialog': ('Ctrl+F', '<Control-f>'),
        'filter_priority_dialog': ('Ctrl+Shift+P', '<Control-Shift-P>'),
        'filter_assignee_dialog': ('Ctrl+Shift+A', '<Control-Shift-A>'),
        'show_statistics': ('Ctrl+I', '<Control-i>'),
        'show_shortcuts': ('F1', '<F1>'),
        'quit': ('Ctrl+Q', '<Control-q>'),
    }
    
    def __init__(self, board: KanbanBoard):
        self.board = board
        self.root = tk.Tk()
        self.columns: Dict[Status, ColumnWidget] = {}
        
        self.setup_window()
        self.setup_menu()
        self.setup_main_frame()
        self.setup_status_bar()
        self.refresh_board()
    
    def setup_window(self):
        """Set up the main window."""
        self.root.title("🗂️ Kanban Board Manager")
        self.root.geometry("1200x700")
        self.root.configure(bg='#F5F5F5')
        
        # Set window icon (if available)
        try:
            # You can add an icon file if you have one
            # self.root.iconbitmap('kanban_icon.ico')
            pass
        except:
            pass
    
    def setup_menu(self):
        """Set up the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Board menu
        board_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Board", menu=board_menu)
        board_menu.add_command(label="New Card", command=self.create_card_dialog,
                       accelerator=self.get_shortcut_label('create_card_dialog'))
        board_menu.add_separator()
        board_menu.add_command(label="Export Board", command=self.export_board,
                       accelerator=self.get_shortcut_label('export_board'))
        board_menu.add_command(label="Create Backup", command=self.create_backup,
                       accelerator=self.get_shortcut_label('create_backup'))
        board_menu.add_separator()
        board_menu.add_command(label="Clear Done Cards", command=self.clear_done_cards,
                       accelerator=self.get_shortcut_label('clear_done_cards'))
        board_menu.add_separator()
        board_menu.add_command(label="Exit", command=self.root.quit,
                       accelerator=self.get_shortcut_label('quit'))
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Search Cards", command=self.search_dialog,
                       accelerator=self.get_shortcut_label('search_dialog'))
        tools_menu.add_command(label="Filter by Priority", command=self.filter_priority_dialog,
                       accelerator=self.get_shortcut_label('filter_priority_dialog'))
        tools_menu.add_command(label="Filter by Assignee", command=self.filter_assignee_dialog,
                       accelerator=self.get_shortcut_label('filter_assignee_dialog'))
        tools_menu.add_command(label="Show Statistics", command=self.show_statistics,
                       accelerator=self.get_shortcut_label('show_statistics'))
        
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
        """Bind a shortcut and stop further event handling after execution."""
        def handler(event=None):
            callback()
            return 'break'

        self.root.bind(sequence, handler)

    def bind_menu_shortcuts(self):
        """Bind keyboard shortcuts for menu actions."""
        self.bind_shortcut(self.MENU_SHORTCUTS['create_card_dialog'][1], self.create_card_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['export_board'][1], self.export_board)
        self.bind_shortcut(self.MENU_SHORTCUTS['create_backup'][1], self.create_backup)
        self.bind_shortcut(self.MENU_SHORTCUTS['clear_done_cards'][1], self.clear_done_cards)
        self.bind_shortcut(self.MENU_SHORTCUTS['search_dialog'][1], self.search_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['filter_priority_dialog'][1], self.filter_priority_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['filter_assignee_dialog'][1], self.filter_assignee_dialog)
        self.bind_shortcut(self.MENU_SHORTCUTS['show_statistics'][1], self.show_statistics)
        self.bind_shortcut(self.MENU_SHORTCUTS['show_shortcuts'][1], self.show_shortcuts)
        self.bind_shortcut(self.MENU_SHORTCUTS['quit'][1], self.root.quit)
    
    def setup_main_frame(self):
        """Set up the main board frame with columns."""
        self.main_frame = tk.Frame(self.root, bg='#F5F5F5')
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create columns
        column_width = 280
        for i, status in enumerate(Status):
            column_frame = tk.Frame(self.main_frame)
            column_frame.grid(row=0, column=i, sticky='nsew', padx=5)
            
            column = ColumnWidget(column_frame, status, self)
            column.pack(fill='both', expand=True)
            self.columns[status] = column
        
        # Configure grid weights for responsive layout
        for i in range(len(Status)):
            self.main_frame.grid_columnconfigure(i, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
    
    def setup_status_bar(self):
        """Set up the status bar at the bottom."""
        self.status_frame = tk.Frame(self.root, bg='#E0E0E0', height=25)
        self.status_frame.pack(fill='x', side='bottom')
        
        self.status_label = tk.Label(self.status_frame, text="Ready", 
                                    bg='#E0E0E0', fg='#333',
                                    font=('Arial', 9))
        self.status_label.pack(side='left', padx=10, pady=2)
        
        # Card count in status bar
        self.card_count_label = tk.Label(self.status_frame, text="0 cards total",
                                        bg='#E0E0E0', fg='#333',
                                        font=('Arial', 9))
        self.card_count_label.pack(side='right', padx=10, pady=2)
    
    def refresh_board(self):
        """Refresh the entire board display."""
        for status in Status:
            self.refresh_column(status)
        self.update_status_bar()
    
    def refresh_column(self, status: Status):
        """Refresh a specific column."""
        column = self.columns[status]
        column.clear_cards()
        
        cards = list(self.board.columns[status])
        for card in cards:
            column.add_card_widget(card)
        
        column.update_count(len(cards))
    
    def update_status_bar(self):
        """Update the status bar information."""
        stats = self.board.get_board_stats()
        self.card_count_label.config(text=f"{stats['total_cards']} cards total")
        self.status_label.config(text="Board updated")
        
        # Auto-clear status message after 3 seconds
        self.root.after(3000, lambda: self.status_label.config(text="Ready"))
    
    def highlight_drop_zones(self, x: int, y: int):
        """Highlight valid drop zones during drag operation."""
        for column in self.columns.values():
            # Check if cursor is over this column
            column_x = column.winfo_rootx()
            column_y = column.winfo_rooty()
            column_width = column.winfo_width()
            column_height = column.winfo_height()
            
            if (column_x <= x <= column_x + column_width and
                column_y <= y <= column_y + column_height):
                column.highlight()
            else:
                column.clear_highlight()
    
    def clear_drop_zone_highlights(self):
        """Clear all drop zone highlights."""
        for column in self.columns.values():
            column.clear_highlight()
    
    def get_drop_target(self, x: int, y: int) -> Optional[Status]:
        """Get the target column status for a drop operation."""
        for status, column in self.columns.items():
            column_x = column.winfo_rootx()
            column_y = column.winfo_rooty()
            column_width = column.winfo_width()
            column_height = column.winfo_height()
            
            if (column_x <= x <= column_x + column_width and
                column_y <= y <= column_y + column_height):
                return status
        return None
    
    def move_card_to_column(self, card: Card, target_status: Status):
        """Move a card to a different column."""
        if self.board.move_card(card.id, target_status):
            self.refresh_board()
            self.status_label.config(text=f"Moved '{card.title}' to {target_status.value}")
    
    def create_card_dialog(self):
        """Show dialog to create a new card."""
        dialog = CardEditDialog(self.root, "Create New Card", board=self.board, on_change=self.refresh_board)
        if dialog.result:
            card_data = dialog.result
            card = self.board.create_card(
                card_data['title'],
                card_data['description'],
                card_data['priority'],
                project=card_data['project']
            )
            if card_data['assignee']:
                self.board.edit_card(card.id, assignee=card_data['assignee'])
            
            for tag in card_data['tags']:
                card.add_tag(tag)
            self.board.save_board()
            
            self.refresh_board()
            self.status_label.config(text=f"Created card '{card.title}'")
    
    def edit_card_dialog(self, card: Card):
        """Show dialog to edit an existing card."""
        dialog = CardEditDialog(self.root, "Edit Card", card, self.board, self.refresh_board)
        if dialog.result:
            card_data = dialog.result
            self.board.edit_card(
                card.id,
                card_data['title'],
                card_data['description'],
                card_data['priority'],
                card_data['assignee'],
                card_data['project']
            )
            
            # Update tags
            card.tags.clear()
            for tag in card_data['tags']:
                card.add_tag(tag)
            self.board.save_board()
            
            self.refresh_board()
            self.status_label.config(text=f"Updated card '{card.title}'")
    
    def delete_card_confirm(self, card: Card):
        """Confirm and delete a card."""
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the card:\n\n'{card.title}'?"
        )
        
        if result:
            if self.board.delete_card(card.id):
                self.refresh_board()
                self.status_label.config(text=f"Deleted card '{card.title}'")
            else:
                messagebox.showerror("Error", "Failed to delete card!")

    def add_subcard_dialog(self, parent_card: Card):
        """Create a real child card under the provided parent card."""
        dialog = CardEditDialog(self.root, f"Add Subcard to '{parent_card.title}'")
        if dialog.result:
            card_data = dialog.result
            try:
                subcard = self.board.create_subcard(
                    parent_card.id,
                    card_data['title'],
                    card_data['description'],
                    card_data['priority'],
                    card_data['project']
                )
                if card_data['assignee']:
                    self.board.edit_card(subcard.id, assignee=card_data['assignee'])

                for tag in card_data['tags']:
                    subcard.add_tag(tag)
                self.board.save_board()

                self.refresh_board()
                self.status_label.config(text=f"Created subcard '{subcard.title}'")
            except ValueError as error:
                messagebox.showerror("Error", str(error))
    
    def show_card_details(self, card: Card):
        """Show detailed information about a card."""
        details = f"""
Card Details:

Title: {card.title}
Description: {card.description or '(no description)'}
Status: {card.status.value}
Priority: {card.priority.value}
Project: {card.project or '(none)'}
Assignee: {card.assignee or '(unassigned)'}
Tags: {', '.join(card.tags) if card.tags else '(no tags)'}

Parent: {self.board.get_parent_card(card).title if self.board.get_parent_card(card) else '(none)'}

Created: {card.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Updated: {card.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
        completed, total = self.board.get_subcard_progress(card.id)
        if total:
            details += "\n\nSubcards:\n"
            for subcard in self.board.get_subcards(card.id):
                tick = "[x]" if self.board.is_card_done(subcard) else "[ ]"
                details += f"{tick} {subcard.title} ({self.board.get_card_location_label(subcard)})\n"
        messagebox.showinfo("Card Details", details.strip())
    
    def search_dialog(self):
        """Show search dialog."""
        query = simpledialog.askstring("Search Cards", "Enter search query:")
        if query:
            results = self.board.search_cards(query)
            if results:
                result_text = f"Found {len(results)} card(s):\n\n"
                for card in results:
                    result_text += f"• [{card.status.value}] {card.title}\n"
                messagebox.showinfo("Search Results", result_text.strip())
            else:
                messagebox.showinfo("Search Results", "No cards found matching your query.")
    
    def filter_priority_dialog(self):
        """Show priority filter dialog."""
        dialog = PriorityFilterDialog(self.root)
        if dialog.result:
            priority = dialog.result
            results = self.board.get_cards_by_priority(priority)
            if results:
                result_text = f"Cards with {priority.value} priority:\n\n"
                for card in results:
                    result_text += f"• [{card.status.value}] {card.title}\n"
                messagebox.showinfo("Filter Results", result_text.strip())
            else:
                messagebox.showinfo("Filter Results", f"No cards found with {priority.value} priority.")
    
    def filter_assignee_dialog(self):
        """Show assignee filter dialog."""
        assignee = simpledialog.askstring("Filter by Assignee", "Enter assignee name:")
        if assignee:
            results = self.board.get_cards_by_assignee(assignee)
            if results:
                result_text = f"Cards assigned to '{assignee}':\n\n"
                for card in results:
                    result_text += f"• [{card.status.value}] {card.title}\n"
                messagebox.showinfo("Filter Results", result_text.strip())
            else:
                messagebox.showinfo("Filter Results", f"No cards found assigned to '{assignee}'.")
    
    def show_statistics(self):
        """Show board statistics."""
        stats = self.board.get_board_stats()
        stats_text = f"""
Board Statistics:

Total Cards: {stats['total_cards']}

By Status:
• To Do: {stats['todo']} cards
• In Progress: {stats['in_progress']} cards
• Review: {stats['review']} cards
• Done: {stats['done']} cards

By Priority:
• Low: {stats['priority_counts'][Priority.LOW]} cards
• Medium: {stats['priority_counts'][Priority.MEDIUM]} cards
• High: {stats['priority_counts'][Priority.HIGH]} cards
• Critical: {stats['priority_counts'][Priority.CRITICAL]} cards
"""
        messagebox.showinfo("Board Statistics", stats_text.strip())
    
    def export_board(self):
        """Export the board to a text file."""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                board_text = self.board.export_board()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(board_text)
                self.status_label.config(text=f"Board exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export board:\n{e}")
    
    def create_backup(self):
        """Create a backup of the board data."""
        backup_path = self.board.storage.backup()
        if backup_path:
            self.status_label.config(text=f"Backup created: {backup_path}")
            messagebox.showinfo("Backup Created", f"Backup saved to:\n{backup_path}")
        else:
            messagebox.showerror("Backup Error", "Failed to create backup!")
    
    def clear_done_cards(self):
        """Clear all cards from the Done column."""
        stats = self.board.get_board_stats()
        done_count = stats['done']
        
        if done_count == 0:
            messagebox.showinfo("Clear Done Cards", "No cards in Done column to clear.")
            return
        
        result = messagebox.askyesno(
            "Clear Done Cards",
            f"This will delete {done_count} card(s) from the Done column.\n\nAre you sure?"
        )
        
        if result:
            cleared = self.board.clear_done_cards()
            self.refresh_board()
            self.status_label.config(text=f"Cleared {cleared} card(s) from Done column")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
🗂️ Kanban Board Manager

A modern drag-and-drop Kanban board application
built with Python and tkinter.

Features:
• Drag and drop cards between columns
• Create, edit, and delete cards
• Priority levels and assignments
• Search and filtering capabilities
• Data persistence and backups

Version 1.0.0
"""
        messagebox.showinfo("About", about_text.strip())

    def show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts_text = (
            "⌨️ Keyboard Shortcuts\n\n"
            f"{self.get_shortcut_label('create_card_dialog')} - New card\n"
            f"{self.get_shortcut_label('export_board')} - Export board\n"
            f"{self.get_shortcut_label('create_backup')} - Create backup\n"
            f"{self.get_shortcut_label('clear_done_cards')} - Clear done cards\n"
            f"{self.get_shortcut_label('search_dialog')} - Search cards\n"
            f"{self.get_shortcut_label('filter_priority_dialog')} - Filter by priority\n"
            f"{self.get_shortcut_label('filter_assignee_dialog')} - Filter by assignee\n"
            f"{self.get_shortcut_label('show_statistics')} - Show statistics\n"
            f"{self.get_shortcut_label('show_shortcuts')} - Show shortcuts\n"
            f"{self.get_shortcut_label('quit')} - Quit application\n\n"
            "Mouse actions:\n"
            "Double-click card - Edit card\n"
            "Right-click card - Context menu"
        )
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)
    
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


## @brief Modal dialog for creating or editing card details.
class CardEditDialog:
    """Dialog for creating and editing cards."""
    
    def __init__(self, parent, title: str, card: Card = None,
                 board: KanbanBoard = None, on_change=None):
        self.result = None
        self.card = card
        self.board = board
        self.on_change = on_change
        self.subcards = []
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        dialog_height = 660 if self._supports_subcard_management() else 500
        self.dialog.geometry(f"430x{dialog_height}")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg='white')
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui(card)
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_ui(self, card: Card):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, bg='white', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        tk.Label(main_frame, text="Title*", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        self.title_entry = tk.Entry(main_frame, font=('Arial', 10), width=50)
        self.title_entry.pack(fill='x', pady=(0, 10))
        
        # Description
        tk.Label(main_frame, text="Description", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        self.desc_text = tk.Text(main_frame, height=6, width=50, font=('Arial', 9))
        self.desc_text.pack(fill='x', pady=(0, 10))
        
        # Priority
        tk.Label(main_frame, text="Priority", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        self.priority_var = tk.StringVar()
        priority_frame = tk.Frame(main_frame, bg='white')
        priority_frame.pack(fill='x', pady=(0, 10))
        
        for priority in Priority:
            rb = tk.Radiobutton(priority_frame, text=priority.value.title(),
                               variable=self.priority_var, value=priority.value,
                               bg='white', font=('Arial', 9))
            rb.pack(side='left', padx=(0, 15))
        
        # Assignee
        tk.Label(main_frame, text="Assignee", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        self.assignee_entry = tk.Entry(main_frame, font=('Arial', 10), width=50)
        self.assignee_entry.pack(fill='x', pady=(0, 10))

        # Project
        tk.Label(main_frame, text="Project", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        self.project_entry = tk.Entry(main_frame, font=('Arial', 10), width=50)
        self.project_entry.pack(fill='x', pady=(0, 10))
        
        # Tags
        tk.Label(main_frame, text="Tags (comma-separated)", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        self.tags_entry = tk.Entry(main_frame, font=('Arial', 10), width=50)
        self.tags_entry.pack(fill='x', pady=(0, 20))

        if self._supports_subcard_management():
            self._build_subcards_section(main_frame)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(fill='x')
        
        tk.Button(button_frame, text="Cancel", command=self.cancel,
                 bg='#F44336', fg='white', font=('Arial', 10),
                 padx=20, pady=5).pack(side='right', padx=(10, 0))
        
        tk.Button(button_frame, text="Save", command=self.save,
                 bg='#4CAF50', fg='white', font=('Arial', 10),
                 padx=20, pady=5).pack(side='right')
        
        # Populate fields if editing existing card
        if card:
            self.title_entry.insert(0, card.title)
            self.desc_text.insert('1.0', card.description)
            self.priority_var.set(card.priority.value)
            if card.assignee:
                self.assignee_entry.insert(0, card.assignee)
            if card.project:
                self.project_entry.insert(0, card.project)
            if card.tags:
                self.tags_entry.insert(0, ', '.join(card.tags))
        else:
            self.priority_var.set(Priority.MEDIUM.value)
        
        # Focus on title field
        self.title_entry.focus()

    def _supports_subcard_management(self) -> bool:
        """Return whether the current dialog should allow subcard management."""
        return self.board is not None and self.card is not None and not self.card.parent_id

    def _build_subcards_section(self, parent):
        """Render subcard management controls for a top-level card."""
        tk.Label(parent, text="Subcards", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')

        subcards_frame = tk.Frame(parent, bg='white')
        subcards_frame.pack(fill='both', expand=True, pady=(0, 20))

        list_frame = tk.Frame(subcards_frame, bg='white')
        list_frame.pack(fill='both', expand=True)

        self.subcards_listbox = tk.Listbox(list_frame, height=7, font=('Arial', 9), activestyle='dotbox')
        self.subcards_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.subcards_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.subcards_listbox.configure(yscrollcommand=scrollbar.set)

        actions_frame = tk.Frame(subcards_frame, bg='white')
        actions_frame.pack(fill='x', pady=(8, 0))

        tk.Button(actions_frame, text="Add Subcard", command=self.add_subcard,
                 bg='#1976D2', fg='white', font=('Arial', 9),
                 padx=14, pady=4).pack(side='left')
        tk.Button(actions_frame, text="Delete Selected", command=self.delete_selected_subcard,
                 bg='#F44336', fg='white', font=('Arial', 9),
                 padx=14, pady=4).pack(side='left', padx=(8, 0))

        self.refresh_subcards_list()

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
        dialog = CardEditDialog(self.dialog, f"Add Subcard to '{self.card.title}'")
        if not dialog.result:
            return

        card_data = dialog.result
        try:
            subcard = self.board.create_subcard(
                self.card.id,
                card_data['title'],
                card_data['description'],
                card_data['priority'],
                card_data['project'] or parent_project,
            )
            if card_data['assignee']:
                self.board.edit_card(subcard.id, assignee=card_data['assignee'])

            for tag in card_data['tags']:
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
        if not messagebox.askyesno(
            "Delete Subcard",
            f"Delete subcard '{subcard.title}'?",
            parent=self.dialog,
        ):
            return

        self.board.delete_card(subcard.id)
        self.refresh_subcards_list()
        if self.on_change:
            self.on_change()
    
    def save(self):
        """Save the card data."""
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Error", "Title is required!")
            return
        
        description = self.desc_text.get('1.0', tk.END).strip()
        priority = Priority(self.priority_var.get())
        assignee = self.assignee_entry.get().strip() or None
        project = self.project_entry.get().strip() or None
        
        tags_text = self.tags_entry.get().strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []
        
        self.result = {
            'title': title,
            'description': description,
            'priority': priority,
            'assignee': assignee,
            'project': project,
            'tags': tags
        }
        
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()


## @brief Modal dialog for selecting a priority filter.
class PriorityFilterDialog:
    """Dialog for filtering by priority."""
    
    def __init__(self, parent):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Filter by Priority")
        self.dialog.geometry("300x200")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg='white')
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        self.setup_ui()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        main_frame = tk.Frame(self.dialog, bg='white', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        tk.Label(main_frame, text="Select Priority Level:", 
                font=('Arial', 10, 'bold'), bg='white').pack(anchor='w', pady=(0, 15))
        
        self.priority_var = tk.StringVar()
        self.priority_var.set(Priority.MEDIUM.value)
        
        for priority in Priority:
            rb = tk.Radiobutton(main_frame, text=priority.value.title(),
                               variable=self.priority_var, value=priority.value,
                               bg='white', font=('Arial', 9))
            rb.pack(anchor='w', pady=2)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(fill='x', pady=(20, 0))
        
        tk.Button(button_frame, text="Cancel", command=self.cancel,
                 bg='#F44336', fg='white', font=('Arial', 10),
                 padx=20, pady=5).pack(side='right', padx=(10, 0))
        
        tk.Button(button_frame, text="Filter", command=self.filter,
                 bg='#4CAF50', fg='white', font=('Arial', 10),
                 padx=20, pady=5).pack(side='right')
    
    def filter(self):
        """Apply the filter."""
        self.result = Priority(self.priority_var.get())
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()