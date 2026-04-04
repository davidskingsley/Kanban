#!/usr/bin/env python3
## @file
#  @brief Standalone API usage example for the Kanban board package.
"""!Example usage of the Kanban Board application."""

from kanban.board import KanbanBoard
from kanban.models import Priority, Status


## @brief Demonstrate core board operations without starting the GUI or CLI.
def main():
    """!Demonstrate API usage of the Kanban board."""
    
    print("🗂️ Kanban Board API Example")
    print("=" * 40)
    
    # Initialize a board with a custom data file
    board = KanbanBoard("example_kanban.json")
    
    # Create some example cards
    print("\n1. Creating cards...")
    card1 = board.create_card(
        "Set up development environment", 
        "Install Python, IDE, and dependencies",
        Priority.HIGH
    )
    
    card2 = board.create_card(
        "Write unit tests",
        "Create comprehensive test suite",
        Priority.MEDIUM
    )
    
    card3 = board.create_card(
        "Deploy to production",
        "Set up CI/CD pipeline and deploy",
        Priority.CRITICAL
    )
    
    # Edit cards - add assignees and tags
    print("2. Editing cards...")
    board.edit_card(card1.id, assignee="alice")
    board.edit_card(card2.id, assignee="bob")
    board.edit_card(card3.id, assignee="charlie")
    
    # Add tags
    card1.add_tag("setup")
    card1.add_tag("environment")
    card2.add_tag("testing")
    card2.add_tag("quality")
    card3.add_tag("deployment")
    card3.add_tag("urgent")
    board.save_board()
    
    # Move cards through the workflow
    print("3. Moving cards through workflow...")
    board.move_card(card1.id, Status.IN_PROGRESS)
    board.move_card(card2.id, Status.IN_PROGRESS)
    board.move_card(card1.id, Status.DONE)  # Alice finished setup
    
    # Display current board state
    print("\n4. Current board state:")
    print(board.export_board())
    
    # Show statistics
    print("\n5. Board statistics:")
    stats = board.get_board_stats()
    print(f"Total cards: {stats['total_cards']}")
    print(f"To Do: {stats['todo']}")
    print(f"In Progress: {stats['in_progress']}")
    print(f"Review: {stats['review']}")
    print(f"Done: {stats['done']}")
    
    # Search functionality
    print("\n6. Searching for cards...")
    test_cards = board.search_cards("test")
    print(f"Cards containing 'test': {len(test_cards)}")
    for card in test_cards:
        print(f"  - {card.title}")
    
    # Filter by priority
    print("\n7. Critical priority cards:")
    critical_cards = board.get_cards_by_priority(Priority.CRITICAL)
    for card in critical_cards:
        print(f"  - {card.title} (assigned to: {card.assignee})")
    
    # Filter by assignee
    print("\n8. Cards assigned to 'bob':")
    bob_cards = board.get_cards_by_assignee("bob")
    for card in bob_cards:
        print(f"  - {card.title} ({card.status.value})")
    
    print("\n✅ Example completed! Check 'example_kanban.json' for saved data.")


if __name__ == "__main__":
    main()