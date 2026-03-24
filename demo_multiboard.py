#!/usr/bin/env python3
## @file
#  @brief Demo data generator for multi-board Kanban workflows.
"""Multi-board demo script for populating sample boards."""

import os

from kanban.board_manager import BoardManager
from kanban.models import Priority


## @brief Create several sample boards with representative task data.
def create_demo_boards():
    """Create demo boards with sample data."""
    print("🎯 Creating Multi-Board Demo...")
    
    # Create board manager in a demo directory
    demo_dir = "demo_multiboard"
    if os.path.exists(demo_dir):
        import shutil
        shutil.rmtree(demo_dir)
    
    board_manager = BoardManager(demo_dir)
    
    # Create Personal Tasks board
    print("\n📋 Creating 'Personal Tasks' board...")
    personal_id = board_manager.create_board("Personal Tasks", "Daily life management")
    personal_board = board_manager.get_current_board()
    
    # Add personal tasks
    card1 = personal_board.create_card("Morning workout", "30-minute gym session", Priority.HIGH)
    card2 = personal_board.create_card("Grocery shopping", "Weekly groceries and household items", Priority.MEDIUM)
    card3 = personal_board.create_card("Call mom", "Weekly family check-in", Priority.LOW)
    card4 = personal_board.create_card("Read book", "Continue reading 'The Pragmatic Programmer'", Priority.LOW)
    
    # Move some cards to different statuses
    personal_board.move_card(card1.id, personal_board.columns[list(personal_board.columns.keys())[1]].status)  # In Progress
    personal_board.move_card(card4.id, personal_board.columns[list(personal_board.columns.keys())[3]].status)  # Done
    
    # Create Work Project board
    print("📋 Creating 'Work Project' board...")
    work_id = board_manager.create_board("Work Project", "Q1 Product Development")
    board_manager.switch_board(work_id)
    work_board = board_manager.get_current_board()
    
    # Add work tasks
    card1 = work_board.create_card("API Design", "Design REST API endpoints for user management", Priority.CRITICAL)
    card2 = work_board.create_card("Database Schema", "Create tables for user and product data", Priority.HIGH)
    card3 = work_board.create_card("Unit Tests", "Write comprehensive test suite", Priority.MEDIUM)
    card4 = work_board.create_card("Documentation", "Update API documentation", Priority.LOW)
    card5 = work_board.create_card("Code Review", "Review pull request #123", Priority.HIGH)
    
    # Add assignees and tags
    work_board.edit_card(card1.id, assignee="alice")
    work_board.edit_card(card2.id, assignee="bob")
    work_board.edit_card(card3.id, assignee="charlie")
    work_board.edit_card(card4.id, assignee="alice")
    work_board.edit_card(card5.id, assignee="bob")
    
    # Add tags
    card1.add_tag("backend")
    card1.add_tag("api")
    card2.add_tag("database")
    card3.add_tag("testing")
    card4.add_tag("docs")
    card5.add_tag("review")
    
    # Move some cards
    work_board.move_card(card2.id, work_board.columns[list(work_board.columns.keys())[1]].status)  # In Progress
    work_board.move_card(card5.id, work_board.columns[list(work_board.columns.keys())[2]].status)  # Review
    
    # Create Side Project board
    print("📋 Creating 'Side Project' board...")
    side_id = board_manager.create_board("Side Project", "Personal app development")
    board_manager.switch_board(side_id)
    side_board = board_manager.get_current_board()
    
    # Add side project tasks
    card1 = side_board.create_card("App Concept", "Brainstorm app features and user flow", Priority.MEDIUM)
    card2 = side_board.create_card("UI Mockups", "Create wireframes and design mockups", Priority.MEDIUM)
    card3 = side_board.create_card("Tech Stack", "Choose frameworks and tools", Priority.HIGH)
    
    # Move concept to done
    side_board.move_card(card1.id, side_board.columns[list(side_board.columns.keys())[3]].status)  # Done
    
    # Show summary
    print("\n🌟 Demo boards created successfully!")
    print("\nTo explore the demo:")
    print("  🖱️  GUI Mode: python main.py --boards-dir demo_multiboard")
    print("  ⌨️  CLI Mode: python main.py --cli --boards-dir demo_multiboard")
    
    return board_manager


## @brief Print a summary of the demo boards created by the script.
def show_demo_stats(board_manager):
    """Show statistics for demo boards."""
    print("\n📊 Demo Board Statistics:")
    print("=" * 50)
    
    boards = board_manager.get_board_list()
    total_cards = 0
    
    for board in boards:
        # Switch to board to get fresh stats
        board_manager.switch_board(board['id'])
        current_board = board_manager.get_current_board()
        stats = current_board.get_board_stats()
        
        print(f"\n📋 {board['name']}")
        print(f"   📝 {board['description']}")
        print(f"   📊 {stats['total_cards']} total cards")
        print(f"   📝 To Do: {stats['todo']}")
        print(f"   ⚡ In Progress: {stats['in_progress']}")
        print(f"   🔍 Review: {stats['review']}")
        print(f"   ✅ Done: {stats['done']}")
        
        total_cards += stats['total_cards']
    
    print(f"\n🌟 Total: {total_cards} cards across {len(boards)} boards")


if __name__ == "__main__":
    board_manager = create_demo_boards()
    show_demo_stats(board_manager)