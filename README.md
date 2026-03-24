# Multi-Board Kanban Manager 🗂️

A feature-rich **multi-board** Kanban application with both **modern drag-and-drop GUI** and command-line interfaces, built with Python 3.12. Organize multiple projects efficiently with separate Kanban boards!

## Features ✨

### �️ **Multi-Board Management**
- **Multiple Boards**: Create and manage separate Kanban boards for different projects
- **Board Switching**: Easily switch between boards with a dropdown selector
- **Board Operations**: Create, rename, delete, and organize multiple boards
- **Cross-Board Statistics**: View statistics across all your boards
- **Data Isolation**: Each board maintains its own independent data
### 📋 **Custom Column Management**
- **Dynamic Columns**: Create, rename, delete, and reorder columns for each board
- **Custom Colors**: Assign different colors to columns for visual organization
- **Flexible Workflows**: Adapt board structure to your specific workflow needs
- **Column Positions**: Reorder columns by dragging or using position controls
- **Legacy Support**: Maintains compatibility with traditional To Do/In Progress/Review/Done structure
### 🖱️ **Drag & Drop GUI Interface**
- **Visual Kanban Board**: Four-column layout with beautiful card designs
- **Drag & Drop**: Seamlessly move cards between columns with mouse
- **Interactive Cards**: Double-click to edit, right-click for context menu
- **Priority Indicators**: Color-coded priority bars on each card
- **Real-time Updates**: Instant visual feedback with status bar notifications
- **Board Selector**: Quick board switching via toolbar dropdown

### 📋 **Core Task Management**
- **Full CRUD Operations**: Create, edit, move, and delete cards
- **Flexible Workflow**: Use default four-column layout or create custom columns
- **Priority Levels**: Low, Medium, High, and Critical with visual indicators
- **Task Assignment**: Assign cards to team members
- **Tagging System**: Organize cards with custom tags
- **Search & Filter**: Find cards by content, priority, or assignee
- **Drag & Drop**: Move cards between any custom or default columns

### 💾 **Multi-Board Data Management**
- **Independent Storage**: Each board has its own data file
- **Backup System**: Export and import all boards for backup
- **Board Metadata**: Centralized board information and switching
- **External Board Loading**: Open a board from another folder without copying it into the default boards directory
- **Lock Files**: Each open board uses a side-by-side `.lock` file to protect writes
- **Read-Only Fallback**: If another process already has the board open, it loads read-only
- **Legacy Support**: Single-board mode for backward compatibility
- **Default Storage Root**: Application data is stored under `$HOME/.kanban-ds`

### ⌨️ **Dual Interface Support**
- **Multi-Board GUI**: Modern interface with board management (default)
- **Multi-Board CLI**: Command-line interface for headless environments
- **Single-Board Mode**: Legacy mode for existing workflows
- **Keyboard Shortcuts**: Ctrl+N (new board), Ctrl+O (switch board), Ctrl+Q (quit)

## Installation 🚀

1. **Clone or download** this project to your local machine
2. **Ensure Python 3.8+** is installed on your system
3. **Navigate** to the project directory:
   ```bash
   cd Kanban
   ```

## Usage 💻

### �️ **Multi-Board Mode (Default)**

Launch the multi-board interface with board management:

```bash
python main.py
```

**Multi-Board GUI Features:**
- **Board Selector**: Dropdown to switch between boards
- **Board Management**: Create, rename, delete boards via toolbar
- **Drag & Drop**: Click and drag cards between columns
- **Statistics**: View stats across all boards
- **Export/Import**: Backup and restore all boards

### ⌨️ **Multi-Board CLI Mode**

For command-line board management:

```bash
python main.py --cli
```

### 🔄 **Single-Board Mode (Legacy)**

Use traditional single-board mode:

```bash
python main.py --single-board
```

### 🎯 **Demo with Sample Data**

Try the GUI with pre-populated sample cards:

```bash
python gui_demo.py
```

### 🛠️ **Command Options**

```bash
python main.py [options]

Options:
  --cli              Use multi-board CLI interface
  --single-board     Use legacy single-board mode  
  --data-file FILE   Specify data file (single-board mode only)
  --boards-dir DIR   Specify boards directory (multi-board mode)
  --help             Show help message
```

Default storage locations:
- Multi-board mode: `$HOME/.kanban-ds/boards`
- Single-board mode: `$HOME/.kanban-ds/kanban_data.json`

External board loading:
- GUI: use `Boards -> Load Board From Folder`
- Multi-board CLI: use `9. Load board from folder`
- You can select a folder containing `boards_metadata.json` or standalone board `.json` files
- External boards remain in their original location and are registered by reference
- If a board is already open in another process, it will open read-only until that lock is released

## Migration Guide 🔄

### **Upgrading from Single-Board to Multi-Board**

If you have an existing `kanban_data.json` file from previous versions:

1. **Backup your data**: Copy your existing `kanban_data.json` file
2. **Run multi-board mode**: Start with `python main.py` (default)
3. **Create your first board**: The app will guide you to create a new board
4. **Import old data**: 
   - Use single-board mode: `python main.py --single-board`
   - Or manually recreate your cards in the new multi-board system

### **Backward Compatibility**

- **Existing workflows**: Use `--single-board` flag to maintain current setup
- **Data preservation**: Old local `kanban_data.json` files remain untouched unless explicitly passed via `--data-file`
- **Gradual migration**: Switch to multi-board when ready

## Multi-Board GUI Interface Guide 🗂️

### **Main Window Layout**

```
┌─────────────────────────────────────────────────────────────┐
│ Boards  Tools  Help                               [Menu]    │
├─────────────────────────────────────────────────────────────│
│ Current Board: [My Project ▼] [New Board] [Rename] [Delete] │
├─────────────────────────────────────────────────────────────│
│  To Do        │ In Progress   │   Review      │    Done     │
│ ┌───────────┐ │ ┌───────────┐ │ ┌───────────┐ │ ┌─────────┐ │
│ │🔴 Task A  │ │ │🟡 Task B  │ │ │🟠 Task C  │ │ │🟢 Task D│ │
│ │[@alice]   │ │ │[@bob]     │ │ │[@charlie] │ │ │[@alice] │ │
│ │#urgent    │ │ │#backend   │ │ │#review    │ │ │#done    │ │
│ └───────────┘ │ └───────────┘ │ └───────────┘ │ └─────────┘ │
│               │               │               │             │
│   [+ Add]     │   [+ Add]     │   [+ Add]     │   [+ Add]   │
├─────────────────────────────────────────────────────────────│
│ Board: My Project                             📊 12 cards    │
└─────────────────────────────────────────────────────────────┘
```

### **Board Management**

- **Board Selector**: Dropdown to choose active board
- **Quick Actions**: Toolbar buttons for board operations
- **Board Info**: Status bar shows current board statistics
- **Menu Options**: Full board management via menu bar

### **Multi-Board Operations**

1. **Create Board**: Click "New Board" or use Boards menu
2. **Switch Board**: Select from dropdown or Ctrl+O
3. **Rename Board**: Use toolbar button or menu option  
4. **Delete Board**: Safe deletion with confirmation
5. **Statistics**: View cross-board analytics
6. **Export/Import**: Backup all boards to single file

### **Column Management**

1. **Create Column**: Right-click on column headers or use Tools menu
2. **Rename Column**: Double-click column header or right-click menu
3. **Delete Column**: Right-click menu with card migration options
4. **Reorder Columns**: Drag column headers to reposition
5. **Change Colors**: Right-click column header to select color
│ └───────────┘ │ └───────────┘ │ └───────────┘ │ └─────────┘ │
│               │               │               │             │
│   [+ Add]     │   [+ Add]     │   [+ Add]     │   [+ Add]   │
├─────────────────────────────────────────────────────────────│
│ Ready                                      12 cards total   │
└─────────────────────────────────────────────────────────────┘
```

### **Card Interactions**

- **🖱️ Single Click**: Select card
- **🖱️ Double Click**: Edit card details
- **🖱️ Right Click**: Show context menu (Edit, Delete, View Details)
- **🖱️ Drag & Drop**: Move between columns
- **⌨️ Keyboard**: Use shortcuts for quick actions

### **Visual Indicators**

- **🔴 Critical**: Red priority bar
- **🟠 High**: Orange priority bar  
- **🟡 Medium**: Yellow priority bar
- **🟢 Low**: Green priority bar
- **@username**: Assignee badge
- **#tag**: Tag labels

## Example Workflows 💡

### **1. Creating Your First Board**

**GUI Mode:**
1. Run `python main.py`
2. Click "File" → "New Card" or press Ctrl+N  
3. Fill in card details: title, description, priority, assignee
4. Drag cards between columns as work progresses
5. Use search (Ctrl+F) to find specific cards

**CLI Mode:**
1. Run `python main.py --cli`
2. Choose option 1 to create cards
3. Use option 3 to move cards between columns
4. Use options 11-16 for column management
5. Use option 5 to search for cards

### **2. Custom Column Workflow Setup**

**Creating a Development Workflow:**
1. Create board: "Web Development Project"
2. Add custom columns: "Backlog" → "Design" → "Development" → "Testing" → "Review" → "Deployed"
3. Assign colors: Backlog (Gray), Design (Purple), Development (Blue), Testing (Orange), Review (Red), Deployed (Green)
4. Create cards for each phase of development
5. Move cards through your custom workflow

**CLI Column Management:**
```bash
# Run CLI mode
python main.py --cli

# Use these options:
# 11. Create new column
# 12. Rename column  
# 13. Delete column
# 14. Reorder columns
# 15. Change column color
# 16. View columns
```

### **3. Team Collaboration Workflow**

- Create cards assigned to team members: "alice", "bob", "charlie"
- Use priority levels to indicate urgency
- Filter by assignee to see individual workloads
- Export board state for status meetings

### **4. Drag & Drop Operations**

1. **Moving Cards**: Click and drag any card to a different column (custom or default)
2. **Visual Feedback**: Columns highlight when dragging over them
3. **Automatic Save**: Changes are saved instantly
4. **Status Updates**: Status bar shows confirmation of moves
5. **Column Management**: Right-click column headers for management options

## Technical Details 🔧

- **Language**: Python 3.8+ (tested with 3.12+)
- **GUI Framework**: Tkinter (included with Python)
- **Dependencies**: Uses only Python standard library
- **Data Format**: JSON for easy portability and backup
- **Architecture**: Modular design with separation of concerns

## Project Structure 📁

```
Kanban/
├── main.py                    # 🚀 Application entry point (multi-board launcher)
├── gui_demo.py                # 🎯 GUI demonstration with sample data
├── example_usage.py           # 📚 API usage examples
├── test_multiboard.py         # 🧪 Multi-board functionality test
├── kanban/
│   ├── __init__.py            # 📦 Package initialization
│   ├── models.py              # 🏗️ Data models (Card, Column, Priority, Status)
│   ├── board.py               # 🧠 Single board logic & operations
│   ├── board_manager.py       # 🗂️ Multi-board management system
│   ├── storage.py             # 💾 Data persistence & backups
│   ├── cli.py                 # ⌨️ Single-board command-line interface
│   ├── multi_board_cli.py     # 🗂️ Multi-board command-line interface
│   ├── gui.py                 # 🖱️ Single-board drag-and-drop GUI
│   └── multi_board_gui.py     # 🗂️ Multi-board GUI with board management
├── requirements.txt           # 📋 Dependencies (minimal)
# Multi-Board Kanban Manager 🗂️

A Python Kanban application with both GUI and CLI workflows. It supports multiple boards, custom columns, drag-and-drop card movement, external board loading, and read-only fallback when a board is already open elsewhere.

## Features

### 🗂️ Multi-Board Management
- Create, rename, switch, and delete separate boards
- View board-level statistics and summaries
- Keep board data isolated per project
- Load external boards by reference instead of copying them

### 📋 Task and Column Management
- Create, edit, move, and delete cards
- Assign priorities, assignees, and tags
- Create, rename, delete, recolor, and reorder custom columns
- Use the legacy single-board workflow when needed

### 🖱️ GUI Support
- Drag and drop cards between columns
- Use context menus and dialogs for common actions
- See keyboard shortcuts directly in the application menus
- View read-only state in the GUI when a lock is active

### 💾 Storage and Safety
- Store runtime data under `$HOME/.kanban-ds`
- Export and import boards for backup
- Use per-board `.lock` files to prevent conflicting writes
- Open a board read-only if another process already owns the lock

## Installation

1. Clone or download the project.
2. Use Python 3.8 or newer.
3. Change into the project directory.

```bash
cd Kanban
```

## Usage

### Multi-Board GUI

```bash
python main.py
```

Use this as the default mode for board switching, drag-and-drop management, statistics, backups, and external board loading.

### Multi-Board CLI

```bash
python main.py --cli
```

Use this for headless environments or quick terminal-based management.

### Single-Board Mode

```bash
python main.py --single-board
```

Add `--cli` as well if you want the legacy single-board CLI.

### Demo Scripts

```bash
python gui_demo.py
python demo_multiboard.py
python example_usage.py
```

## Command Options

```bash
python main.py [options]

Options:
  --cli              Use command-line mode
  --single-board     Use legacy single-board mode
  --data-file FILE   Specify a custom data file for single-board mode
  --boards-dir DIR   Specify a custom boards directory for multi-board mode
  --help             Show help message
```

## Storage

Default runtime storage locations:
- Multi-board mode: `$HOME/.kanban-ds/boards`
- Single-board mode: `$HOME/.kanban-ds/kanban_data.json`

External board loading:
- GUI: `Boards -> Load Board From Folder`
- Multi-board CLI: `9. Load board from folder`
- You can select either a folder containing `boards_metadata.json` or a folder with standalone board `.json` files
- External boards remain in their original location and are registered by reference
- If a board is already open in another process, it opens read-only until that lock is released

## Multi-Board GUI Guide

### Main Areas
- Menu bar for boards, cards, filters, columns, tools, and help
- Toolbar board selector for switching the active board
- Summary area showing card counts, completed counts, and read-only status
- Board canvas with draggable cards and per-column add-card actions

### Common Actions
1. Create a board from the Boards menu.
2. Load an external board with `Boards -> Load Board From Folder`.
3. Switch boards from the dropdown or with `Ctrl+O`.
4. Double-click a card to edit it.
5. Right-click cards or columns for context actions.

### Visual Indicators
- Priority bars show urgency from low to critical
- Assignees display as `@name`
- Tags display as `#tag`
- Read-only mode is shown when another process holds the lock

## Keyboard Shortcuts

### Multi-Board GUI
| Shortcut | Action |
|----------|---------|
| `Ctrl+N` | Create new board |
| `Ctrl+Shift+O` | Load board from folder |
| `Ctrl+O` | Switch board |
| `Ctrl+R` | Rename current board |
| `Ctrl+Shift+D` | Delete current board |
| `Ctrl+I` | Board statistics |
| `Ctrl+Q` | Quit application |

### Single-Board GUI
| Shortcut | Action |
|----------|---------|
| `Ctrl+N` | Create new card |
| `Ctrl+E` | Export board |
| `Ctrl+B` | Create backup |
| `Ctrl+F` | Search cards |
| `Ctrl+I` | Show statistics |
| `F1` | Show keyboard shortcuts |
| `Ctrl+Q` | Quit application |

### Mouse Actions
| Action | Result |
|--------|--------|
| Double-click card | Edit card |
| Right-click card | Open card context menu |
| Drag and drop | Move card between columns |

## Project Structure

```text
Kanban/
├── main.py
├── gui_demo.py
├── demo_multiboard.py
├── example_usage.py
├── README.md
├── requirements.txt
├── demo_kanban.json
├── example_kanban.json
├── kanban_data.json
└── kanban/
    ├── __init__.py
    ├── board.py
    ├── board_manager.py
    ├── cli.py
    ├── gui.py
    ├── models.py
    ├── multi_board_cli.py
    ├── multi_board_gui.py
    └── storage.py
```

## Development Notes

- The project uses only the Python standard library
- Data is stored as JSON
- The application supports both legacy fixed columns and custom-column workflows
- Lock handling lives in the storage layer so both GUI and CLI flows respect read-only mode

## Troubleshooting

1. GUI will not start:
   Try `python -m tkinter` to confirm Tkinter is available, or run `python main.py --cli`.
2. Permission errors:
   Check write access to `$HOME/.kanban-ds` or the external board folder, and verify the board file and adjacent `.lock` file are writable.
3. Board opens read-only:
   Another process currently owns the lock. Close that instance or reopen the board after the lock is released.
4. Backup or import problems:
   Verify the target path exists and that the JSON files are not corrupted.

## License

This project is intended for educational and personal use. Modify and distribute it as needed.