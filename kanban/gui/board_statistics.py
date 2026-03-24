## @file
#  @brief Board statistics and toolbar summary helpers for the multi-board GUI shell.
"""Board statistics helpers for the multi-board application."""

import tkinter as tk
from tkinter import ttk, messagebox

from .common import bind_mousewheel


def get_completed_count(stats, board=None):
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



def update_board_info(app, stats=None, board=None):
    """Update the toolbar summary for the current board."""
    if not hasattr(app, 'board_info_var'):
        return

    current_board = board
    if current_board is None and app.current_board_gui is not None:
        current_board = getattr(app.current_board_gui, 'board', None)
    if current_board is None:
        current_board = app.board_manager.get_current_board()

    if stats is None:
        if current_board is not None:
            stats = current_board.get_board_stats()
        else:
            boards = app.board_manager.get_board_list()
            stats = next((item.get('stats') for item in boards if item.get('is_current')), None)

    if not stats:
        if current_board is None:
            app.board_info_var.set("No board selected")
            return
        stats = current_board.get_board_stats()

    if not stats:
        app.board_info_var.set("0 cards | 0 completed")
        return

    total_cards = stats.get('total_cards', 0)
    done_count = get_completed_count(stats, current_board)
    access_suffix = " | read only" if current_board is not None and current_board.is_read_only() else ""
    info_text = f"{total_cards} cards | {done_count} completed{access_suffix}"
    app.board_info_var.set(info_text)



def build_board_statistics_text(board_manager):
    """Build the statistics text shown in the board statistics dialog."""
    boards = board_manager.get_board_list()

    total_cards = 0
    total_todos = 0
    total_in_progress = 0
    total_review = 0
    total_done = 0
    stats_lines = ["📊 BOARD STATISTICS", "=" * 50, ""]

    for board in boards:
        stats_lines.append(f"📋 {board['name']}")
        if board['description']:
            stats_lines.append(f"   📝 {board['description']}")

        current_marker = " (current)" if board['is_current'] else ""
        stats_lines.append(f"   Status: Active{current_marker}")

        if 'stats' in board:
            stats = board['stats']
            stats_lines.append(f"   📊 Total cards: {stats['total_cards']}")

            todo_count = stats.get('To Do', stats.get('todo', 0))
            in_progress_count = stats.get('In Progress', stats.get('in_progress', 0))
            review_count = stats.get('Review', stats.get('review', 0))
            done_count = stats.get('Done', stats.get('done', 0))

            stats_lines.append(f"   📝 To Do: {todo_count}")
            stats_lines.append(f"   ⚡ In Progress: {in_progress_count}")
            stats_lines.append(f"   🔍 Review: {review_count}")
            stats_lines.append(f"   ✅ Done: {done_count}")

            total_cards += stats['total_cards']
            total_todos += todo_count
            total_in_progress += in_progress_count
            total_review += review_count
            total_done += done_count
        else:
            stats_lines.append("   📊 (Statistics not available)")

        stats_lines.append("")

    stats_lines.extend(
        [
            "🌟 OVERALL SUMMARY",
            "=" * 30,
            f"📋 Total boards: {len(boards)}",
            f"📊 Total cards: {total_cards}",
            f"📝 Total To Do: {total_todos}",
            f"⚡ Total In Progress: {total_in_progress}",
            f"🔍 Total Review: {total_review}",
            f"✅ Total Done: {total_done}",
        ]
    )
    return "\n".join(stats_lines)



def show_board_statistics(app):
    """Show statistics for all boards."""
    boards = app.board_manager.get_board_list()
    if not boards:
        messagebox.showinfo("Statistics", "No boards available!")
        return

    stats_window = tk.Toplevel(app.root)
    stats_window.title("Board Statistics")
    stats_window.geometry("500x400")
    stats_window.configure(bg='#F5F5F5')

    text_frame = tk.Frame(stats_window, bg='#F5F5F5')
    text_frame.pack(fill='both', expand=True, padx=10, pady=10)

    text_widget = tk.Text(text_frame, font=('Courier', 10), bg='white')
    scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    bind_mousewheel(text_widget)
    bind_mousewheel(text_frame, text_widget)

    text_widget.insert(tk.END, build_board_statistics_text(app.board_manager))
    text_widget.config(state='disabled')

    text_widget.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')
