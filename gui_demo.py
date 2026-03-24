#!/usr/bin/env python3
## @file
#  @brief GUI demo launcher with sample Kanban data.
"""GUI demo script for the Kanban Board application."""

from kanban.board import KanbanBoard
from kanban.gui import KanbanGUI
from kanban.models import Priority, Status


## @brief Populate a board with representative tasks for GUI demonstrations.
def create_sample_data(board: KanbanBoard):
    """Create some sample cards for demonstration."""
    
    # Create sample cards
    card1 = board.create_card(
        "Design user interface mockups",
        "Create wireframes and visual designs for the new dashboard",
        Priority.HIGH
    )
    board.edit_card(card1.id, assignee="alice")
    card1.add_tag("design")
    card1.add_tag("ui")
    
    card2 = board.create_card(
        "Implement user authentication",
        "Set up login system with JWT tokens and password hashing",
        Priority.CRITICAL
    )
    board.edit_card(card2.id, assignee="bob")
    card2.add_tag("backend")
    card2.add_tag("security")
    board.move_card(card2.id, Status.IN_PROGRESS)
    
    card3 = board.create_card(
        "Write unit tests for API",
        "Create comprehensive test suite for all API endpoints",
        Priority.MEDIUM
    )
    board.edit_card(card3.id, assignee="charlie")
    card3.add_tag("testing")
    card3.add_tag("api")
    board.move_card(card3.id, Status.IN_PROGRESS)
    
    card4 = board.create_card(
        "Set up CI/CD pipeline",
        "Configure automated testing and deployment workflow",
        Priority.HIGH
    )
    board.edit_card(card4.id, assignee="alice")
    card4.add_tag("devops")
    card4.add_tag("automation")
    board.move_card(card4.id, Status.REVIEW)
    
    card5 = board.create_card(
        "Database schema optimization",
        "Analyze and optimize database queries for better performance",
        Priority.LOW
    )
    board.edit_card(card5.id, assignee="bob")
    card5.add_tag("database")
    card5.add_tag("performance")
    board.move_card(card5.id, Status.DONE)
    
    card6 = board.create_card(
        "Update documentation",
        "Revise API documentation and add installation guide",
        Priority.MEDIUM
    )
    board.edit_card(card6.id, assignee="charlie")
    card6.add_tag("docs")
    
    card7 = board.create_card(
        "Mobile app responsiveness",
        "Ensure all views work correctly on mobile devices",
        Priority.HIGH
    )
    board.edit_card(card7.id, assignee="alice")
    card7.add_tag("mobile")
    card7.add_tag("responsive")
    
    card8 = board.create_card(
        "Fix login redirect bug",
        "Users are redirected to wrong page after successful login",
        Priority.CRITICAL
    )
    board.edit_card(card8.id, assignee="bob")
    card8.add_tag("bugfix")
    card8.add_tag("urgent")
    board.move_card(card8.id, Status.REVIEW)
    
    board.save_board()
    print("Sample data created successfully!")


## @brief Launch the single-board GUI demo after seeding sample data.
def main():
    """Launch the GUI demo with sample data."""
    print("🗂️ Kanban Board GUI Demo")
    print("=" * 30)
    
    # Create a demo board
    board = KanbanBoard("demo_kanban.json")
    
    # Check if board is empty and create sample data
    stats = board.get_board_stats()
    if stats['total_cards'] == 0:
        print("Creating sample data...")
        create_sample_data(board)
    else:
        print("Using existing board data...")
    
    print("\nLaunching GUI interface...")
    print("\nGUI Features to try:")
    print("• Drag and drop cards between columns")
    print("• Double-click cards to edit them")
    print("• Right-click for context menu")
    print("• Use menu bar for search, filter, and export")
    print("• Check status bar for updates")
    print("\nKeyboard shortcuts:")
    print("• Ctrl+N: Create new card")
    print("• Ctrl+F: Search cards")
    print("• Ctrl+Q: Exit application")
    
    # Launch GUI
    gui = KanbanGUI(board)
    gui.run()


if __name__ == "__main__":
    main()