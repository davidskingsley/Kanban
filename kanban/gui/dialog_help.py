## @file
#  @brief Help and command-reference dialogs for the PySide6 multi-board GUI.
"""!Help and command-reference dialogs for the PySide6 GUI."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSizePolicy, QTextBrowser

from .. import __version__
from .common import (
	add_dialog_footer,
	build_dialog_shell,
	create_dialog_hint_label,
	create_dialog_section_label,
)


class AboutDialog(QDialog):
	"""!Application help and version dialog."""

	def __init__(self, parent: Optional[QDialog] = None, version: str = __version__):
		"""!Init."""
		super().__init__(parent)
		self.setWindowTitle('About Kanban')
		self.resize(700, 620)

		content_layout = build_dialog_shell(
			self,
			'About Kanban',
			'Multi-board planning for day-to-day work. This dialog covers the current release, the main workflow, and the keyboard shortcuts that matter most.',
		)

		content_layout.addWidget(create_dialog_section_label('Version'))
		self.version_label = QLabel(f'Kanban Version {version}')
		self.version_label.setObjectName('AboutVersion')
		self.version_label.setStyleSheet(
			'background: rgba(125, 59, 20, 0.10); color: #6f3d1c; border: 1px solid rgba(125, 59, 20, 0.18); border-radius: 12px; padding: 8px 12px; font-size: 10pt; font-weight: 700;'
		)
		content_layout.addWidget(self.version_label)

		content_layout.addWidget(create_dialog_section_label('How To Use'))
		self.usage_label = QLabel(
			'<b>1.</b> Create or switch to a board, then shape the workflow with custom columns.<br>'
			'<b>2.</b> Add cards into active columns and use selection to edit, move, archive, or delete the current card.<br>'
			'<b>3.</b> Use the toolbar filters and search field to narrow what is visible by text, priority, assignee, type, tag, or due state.<br>'
			'<b>4.</b> Open card details to manage descriptions, dates, tags, checklist items, timestamped notes, attachments, and subcards.<br>'
			'<b>5.</b> Use the Cards menu to manage reusable card types and project records shared across the board.<br>'
			'<b>6.</b> Open the Action Log for the full audit trail, or use the selected-card action log when you want history for one card only.<br>'
			'<b>7.</b> Use the Due Date View, Archived Cards dialog, and Board Statistics screens to review progress and deadlines.'
		)
		self.usage_label.setObjectName('AboutUsage')
		self.usage_label.setWordWrap(True)
		self.usage_label.setTextFormat(Qt.TextFormat.RichText)
		self.usage_label.setStyleSheet('color: #4f4134;')
		content_layout.addWidget(self.usage_label)

		content_layout.addWidget(create_dialog_section_label('Keyboard Shortcuts'))
		self.shortcuts_label = QLabel(
			'<b>Ctrl+N</b> New board<br>'
			'<b>Ctrl+Shift+O</b> Load board from folder<br>'
			'<b>Ctrl+Shift+S</b> Export current board<br>'
			'<b>Ctrl+Shift+E</b> Export all boards<br>'
			'<b>Ctrl+Shift+I</b> Import boards<br>'
			'<b>Ctrl+O</b> Switch board<br>'
			'<b>F5</b> Refresh boards<br>'
			'<b>Ctrl+R</b> Rename current board<br>'
			'<b>Ctrl+Shift+D</b> Delete current board<br>'
			'<b>Ctrl+Shift+T</b> Due Date View<br>'
			'<b>Ctrl+Shift+L</b> Action Log<br>'
			'<b>Ctrl+I</b> Board statistics<br>'
			'<b>Ctrl+Shift+N</b> New card<br>'
			'<b>Ctrl+Shift+J</b> Add subcard to the selected card<br>'
			'<b>Ctrl+E</b> Edit selected card<br>'
			'<b>Ctrl+M</b> Move selected card<br>'
			'<b>Ctrl+D</b> Delete selected card<br>'
			'<b>Ctrl+Shift+K</b> Archive done cards<br>'
			'<b>Ctrl+Shift+C</b> New column<br>'
			'<b>Ctrl+Alt+R</b> Edit selected column<br>'
			'<b>Ctrl+Alt+D</b> Delete selected column<br>'
			'<b>Ctrl+Alt+O</b> Reorder columns<br>'
			'<b>Ctrl+Z</b> Undo current board action<br>'
			'<b>Ctrl+Y</b> Redo current board action<br>'
			'<b>Ctrl+Shift+Z</b> Undo board-management action<br>'
			'<b>Ctrl+Shift+Y</b> Redo board-management action<br>'
			'<b>F1</b> About Kanban<br>'
			'<b>Ctrl+Q</b> Quit application'
		)
		self.shortcuts_label.setObjectName('AboutShortcuts')
		self.shortcuts_label.setWordWrap(True)
		self.shortcuts_label.setTextFormat(Qt.TextFormat.RichText)
		self.shortcuts_label.setStyleSheet('color: #4f4134;')
		content_layout.addWidget(self.shortcuts_label)

		content_layout.addWidget(create_dialog_hint_label('Tip: click a column title or card first to make the relevant card and column actions available.'))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


def build_command_line_guide_html() -> str:
	"""!Return the HTML shown in the command-line guide dialog."""
	return (
		'<h3 style="margin: 0 0 8px 0; color: #6f3d1c;">Start From The Project Folder</h3>'
		'<p style="margin: 0 0 10px 0;">Open a terminal in the Kanban project directory. Both direct Python and <b>uv</b> commands work. The GUI is the default launch mode, and the CLI is enabled with <b>--cli</b>.</p>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'python main.py\n'
		'python main.py --cli\n'
		'python main.py list-boards\n'
		'python main.py create-board --name "Automation" --storage-backend sqlite --switch\n'
		'python main.py create-card --board "Automation" --title "Ship release" --priority high\n'
		'python main.py --boards-dir C:\\Boards\\Kanban\n\n'
		'uv run python main.py\n'
		'uv run python main.py --cli\n'
		'uv run python main.py list-boards\n'
		'uv run python main.py create-board --name "Automation" --storage-backend sqlite --switch\n'
		'uv run python main.py --boards-dir C:\\Boards\\Kanban\n'
		'</pre>'
		'<p style="margin: 10px 0 0 0;">Run <b>python main.py --help</b> or <b>uv run python main.py --help</b> to see the supported command-line options.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Top-Level CLI Options</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>--cli</b>: start the interactive multi-board command-line interface instead of the GUI.</li>'
		'<li><b>--boards-dir DIR</b>: use a different board storage directory for the session. This is useful when keeping work, demo, or archived boards in separate locations.</li>'
		'<li><b>--actor-name NAME</b>: set and save the user name used for board action logging.</li>'
		'<li><b>--lock-action ACTION</b>: choose how direct commands respond to locked boards: <b>cancel</b>, <b>open_read_only</b>, or <b>delete_lock</b>.</li>'
		'<li><b>--help</b>: print the launcher help and exit.</li>'
		'</ul>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Direct-Action CLI Workflow</h3>'
		'<p style="margin: 0 0 10px 0;">Direct commands let one action run immediately without prompts. Use them for scripts, Task Scheduler jobs, or shell automation. Each action is its own subcommand.</p>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>list-boards</b>: print the registered boards, backends, and current-board marker.</li>'
		'<li><b>create-board</b>, <b>switch-board</b>, <b>rename-board</b>, <b>delete-board</b>: automate board management. Destructive commands require <b>--force</b>.</li>'
		'<li><b>convert-board</b>: switch an existing board between JSON and SQLite storage.</li>'
		'<li><b>show-board</b>, <b>show-action-log</b>, <b>show-card-action-log</b>, <b>create-card</b>, <b>edit-card</b>, <b>add-subcard</b>, <b>move-card</b>, <b>delete-card</b>, note commands, archive commands, and checklist item commands: automate current-board work without opening the menu CLI.</li>'
		'<li><b>search-cards</b>, <b>filter-priority</b>, <b>filter-assignee</b>, <b>add-tag</b>, and <b>card-details</b>: retrieve board information directly from scripts and targeted automation.</li>'
		'<li><b>create-column</b>, <b>rename-column</b>, <b>delete-column</b>, <b>reorder-columns</b>, <b>change-column-color</b>, <b>edit-column-flags</b>: automate column maintenance.</li>'
		'<li><b>create-card-type</b>, <b>edit-card-type</b>, <b>delete-card-type</b>, <b>create-backup</b>, <b>cleanup-orphaned-attachments</b>, <b>undo-current-board</b>, <b>redo-current-board</b>: cover the board-level maintenance actions.</li>'
		'</ul>'
		'<p style="margin: 10px 0 0 0;">Run <b>python main.py &lt;direct-command&gt; --help</b> to see the exact flags for one automation action.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Multi-Board CLI Workflow</h3>'
		'<p style="margin: 0 0 10px 0;">The first menu manages boards. If no boards exist, the CLI immediately prompts you to create one. When boards exist, the main menu exposes these actions:</p>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>1. Open current board</b>: enter the board-level card and column manager.</li>'
		'<li><b>2. Switch board</b>: change the active board.</li>'
		'<li><b>3. Create new board</b>: choose a name, optional description, storage backend, and target folder.</li>'
		'<li><b>4. Convert board backend</b>: switch a board between JSON and SQLite storage.</li>'
		'<li><b>5. Rename board</b> and <b>6. Delete board</b>: maintain existing boards.</li>'
		'<li><b>7. Board statistics</b>: review totals across every registered board.</li>'
		'<li><b>8. Export current board</b> and <b>9. Export all boards</b>: write portable board data for backup or migration.</li>'
		'<li><b>10. Import boards</b>: bring exported boards back into the manager.</li>'
		'<li><b>11. Load board from folder</b>: register boards stored outside the default directory.</li>'
		'<li><b>12. Undo</b> and <b>13. Redo</b>: reverse recent board-management operations.</li>'
		'</ul>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Creating Boards From The CLI</h3>'
		'<p style="margin: 0 0 10px 0;">When you create a board, the CLI asks which backend to use. Choose <b>1</b> for the current JSON file backend or <b>2</b> for the SQLite3 backend. It then asks for a storage folder. If you keep the default folder, the board is created under the application boards directory. If you choose another folder, the board is still registered in the manager and can be reopened later.</p>'
		'<p style="margin: 0 0 10px 0;">Load-board-from-folder works with a folder that contains <b>boards_metadata.json</b> or standalone board files. JSON board files and SQLite board files are both supported.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Board-Level CLI Workflow</h3>'
		'<p style="margin: 0 0 10px 0;">After choosing <b>Open current board</b>, the terminal switches to the per-board menu. This view prints the board state, current card statistics, and these actions:</p>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>Cards</b>: create, edit, move, delete, search, filter by priority, filter by assignee, add tags, manage checklists, manage notes, view card details, archive done cards, manage archived cards, add subcards, and view the selected-card action log.</li>'
		'<li><b>Columns</b>: create, rename, delete, reorder, recolor, edit flags, and inspect the current column setup.</li>'
		'<li><b>Card types</b>: view, create, edit, and delete reusable card type presets.</li>'
		'<li><b>Maintenance</b>: create a backup, clean orphaned attachment files, undo, and redo.</li>'
		'</ul>'
		'<p style="margin: 10px 0 0 0;">When the CLI requests dates, use <b>YYYY-MM-DD</b>. If a board is locked by another process, the terminal offers three responses: open read only, delete the lock, or cancel opening the board.</p>'
		'<p style="margin: 10px 0 0 0;">Checklist input accepts pipe-delimited items in the menu CLI, and direct commands can target individual checklist items by the ids printed in <b>card-details</b>. Notes can be edited in the menu CLI or by direct note commands. The action log stores the saved user name plus the date and time of each logged board change, and card-specific views filter those entries by card id.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Practical Notes</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li>Backups, imports, exports, and board loading work with both JSON and SQLite-backed boards.</li>'
		'<li>The CLI is useful when running on a machine without PySide6 or when you want to manage boards entirely from a terminal session.</li>'
		'<li>Managed project CRUD, the archived-card detail dialog, and the filter toolbar are GUI workflows.</li>'
		'<li>Press <b>Ctrl+C</b> to leave the CLI safely. The launcher handles this and exits cleanly.</li>'
		'</ul>'
	)


def build_direct_action_cli_options_html() -> str:
	"""!Return the HTML shown in the direct-action CLI options dialog."""
	return (
		'<h3 style="margin: 0 0 8px 0; color: #6f3d1c;">Direct-Action CLI Options</h3>'
		'<p style="margin: 0 0 10px 0;">These commands run one action immediately without entering the interactive CLI. Use them for scripts, scheduled jobs, and automation. Run <b>python main.py &lt;command&gt; --help</b> to inspect the exact flag set for one command.</p>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Global Options</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li><b>--boards-dir DIR</b>: use a different board registry directory for the session.</li>'
		'<li><b>--actor-name NAME</b>: set and save the user name used for board audit logging.</li>'
		'<li><b>--lock-action ACTION</b>: choose <b>cancel</b>, <b>open_read_only</b>, or <b>delete_lock</b> when a direct command hits a locked board.</li>'
		'</ul>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Board Management Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'list-boards\n'
		'create-board --name NAME [--description TEXT] [--storage-backend json|sqlite] [--target-directory DIR] [--switch]\n'
		'switch-board --board BOARD\n'
		'rename-board --board BOARD --new-name NAME\n'
		'convert-board --board BOARD --storage-backend json|sqlite [--target-directory DIR]\n'
		'delete-board --board BOARD --force\n'
		'board-stats [--board BOARD]\n'
		'export-board [--board BOARD] --output FILE\n'
		'export-all-boards --output FILE\n'
		'import-boards --input FILE --force\n'
		'load-board-from-folder --path PATH [--board BOARD] [--name NAME] [--description TEXT] [--no-switch]\n'
		'undo-board-management\n'
		'redo-board-management\n'
		'show-board [--board BOARD]\n'
		'show-action-log [--board BOARD] [--limit COUNT]\n'
		'show-card-action-log [--board BOARD] --card CARD [--limit COUNT]\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Card Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'create-card [--board BOARD] --title TITLE [--description TEXT] [--priority low|medium|high|critical] [--column COLUMN] [--project NAME] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--color VALUE] [--card-type TYPE] [--assignee NAME] [--tags tag1,tag2] [--todo TEXT]\n'
		'edit-card [--board BOARD] --card CARD [--title TITLE] [--description TEXT | --clear-description] [--priority low|medium|high|critical] [--assignee NAME | --clear-assignee] [--project NAME | --clear-project] [--start-date YYYY-MM-DD | --clear-start-date] [--end-date YYYY-MM-DD | --clear-end-date] [--color VALUE | --clear-color] [--card-type TYPE] [--tags tag1,tag2 | --clear-tags] [--todo TEXT | --clear-todo-list]\n'
		'add-subcard [--board BOARD] --parent-card CARD --title TITLE [--description TEXT] [--priority low|medium|high|critical] [--project NAME] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--color VALUE] [--card-type TYPE] [--assignee NAME] [--tags tag1,tag2] [--todo TEXT]\n'
		'move-card [--board BOARD] --card CARD --column COLUMN [--target-card CARD] [--insert-after]\n'
		'delete-card [--board BOARD] --card CARD --force\n'
		'search-cards [--board BOARD] --query TEXT\n'
		'filter-priority [--board BOARD] --priority low|medium|high|critical\n'
		'filter-assignee [--board BOARD] --assignee NAME\n'
		'add-tag [--board BOARD] --card CARD --tag TAG\n'
		'add-todo-item [--board BOARD] --card CARD --text TEXT [--completed]\n'
		'check-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'uncheck-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'toggle-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'remove-todo-item [--board BOARD] --card CARD --item ITEM\n'
		'card-details [--board BOARD] --card CARD\n'
		'list-notes [--board BOARD] --card CARD\n'
		'add-note [--board BOARD] --card CARD --text TEXT\n'
		'edit-note [--board BOARD] --card CARD --note NOTE --text TEXT\n'
		'delete-note [--board BOARD] --card CARD --note NOTE\n'
		'archive-done-cards [--board BOARD] --force\n'
		'list-archived-cards [--board BOARD]\n'
		'restore-archived-card [--board BOARD] --card CARD\n'
		'delete-archived-card [--board BOARD] --card CARD --force\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Column Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'create-column [--board BOARD] --name NAME [--position INDEX] [--color VALUE] [--completed] [--can-add-card]\n'
		'rename-column [--board BOARD] --column COLUMN --new-name NAME\n'
		'delete-column [--board BOARD] --column COLUMN [--move-cards-to COLUMN]\n'
		'reorder-columns [--board BOARD] --order COLUMN1 COLUMN2 COLUMN3\n'
		'change-column-color [--board BOARD] --column COLUMN --color VALUE\n'
		'edit-column-flags [--board BOARD] --column COLUMN [--completed | --not-completed] [--can-add-card | --cannot-add-card]\n'
		'list-columns [--board BOARD]\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Card Type And Maintenance Commands</h3>'
		'<pre style="background: #f7efe4; border: 1px solid #e2d2bb; border-radius: 10px; padding: 10px;">'
		'list-card-types [--board BOARD]\n'
		'create-card-type [--board BOARD] --name NAME [--description TEXT] [--default-project NAME] [--default-color VALUE]\n'
		'edit-card-type [--board BOARD] --card-type TYPE [--name NAME] [--description TEXT | --clear-description] [--default-project NAME | --clear-default-project] [--default-color VALUE | --clear-default-color]\n'
		'delete-card-type [--board BOARD] --card-type TYPE [--delete-cards] [--replacement-card-type TYPE]\n'
		'create-backup [--board BOARD] [--output FILE]\n'
		'cleanup-orphaned-attachments [--board BOARD]\n'
		'undo-current-board [--board BOARD]\n'
		'redo-current-board [--board BOARD]\n'
		'</pre>'
		'<h3 style="margin: 16px 0 8px 0; color: #6f3d1c;">Notes</h3>'
		'<ul style="margin: 0 0 0 18px; padding: 0;">'
		'<li>Use a board id or an exact board name anywhere a command expects <b>BOARD</b>.</li>'
		'<li>Use exact names or ids for cards, notes, checklist items, columns, and card types when there is any ambiguity.</li>'
		'<li>Destructive commands require <b>--force</b> where shown.</li>'
		'<li>Date values use <b>YYYY-MM-DD</b>.</li>'
		'<li><b>card-details</b> prints checklist item ids, and note listings print note ids, so direct commands can target them exactly.</li>'
		'<li>Managed project CRUD remains a GUI workflow; direct commands can still set project names on cards and card types and now support timestamped card-note automation.</li>'
		'<li>Board mutations append to one persisted audit log with the saved user name plus the action timestamp; card-specific log views filter that history by card id.</li>'
		'<li>The Help menu in the GUI includes this reference alongside the About and Command Line Guide dialogs.</li>'
		'</ul>'
	)


class CommandLineGuideDialog(QDialog):
	"""!Dedicated dialog for command-line usage documentation."""

	def __init__(self, parent: Optional[QDialog] = None):
		"""!Init."""
		super().__init__(parent)
		self.setWindowTitle('Kanban Command Line Guide')
		self.resize(760, 760)

		content_layout = build_dialog_shell(
			self,
			'Command Line Guide',
			'Detailed terminal usage for starting Kanban, managing multiple boards, and operating a board entirely from the command line.',
			scrollable=False,
		)

		self.command_line_help = QTextBrowser()
		self.command_line_help.setObjectName('CommandLineGuideBrowser')
		self.command_line_help.setReadOnly(True)
		self.command_line_help.setOpenExternalLinks(False)
		self.command_line_help.setMinimumHeight(0)
		self.command_line_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.command_line_help.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		self.command_line_help.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.command_line_help.verticalScrollBar().setSingleStep(20)
		self.command_line_help.setStyleSheet(
			'QTextBrowser#CommandLineGuideBrowser {'
			'background: #fffaf2; color: #4f4134; border: 1px solid #d8c6ab; border-radius: 12px; padding: 8px;'
			'}'
		)
		self.command_line_help.setHtml(build_command_line_guide_html())
		content_layout.addWidget(self.command_line_help)

		content_layout.addWidget(create_dialog_hint_label('Tip: use the board-level CLI when you want backup, cleanup, and batch management tasks without opening the GUI.'))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


class DirectActionCliOptionsDialog(QDialog):
	"""!Dedicated dialog for direct-action CLI option documentation."""

	def __init__(self, parent: Optional[QDialog] = None):
		"""!Init."""
		super().__init__(parent)
		self.setWindowTitle('Kanban Direct-Action CLI Options')
		self.resize(860, 780)

		content_layout = build_dialog_shell(
			self,
			'Direct-Action CLI Options',
			'Command-by-command reference for the non-interactive automation interface.',
			scrollable=False,
		)

		self.direct_action_help = QTextBrowser()
		self.direct_action_help.setObjectName('DirectActionCliOptionsBrowser')
		self.direct_action_help.setReadOnly(True)
		self.direct_action_help.setOpenExternalLinks(False)
		self.direct_action_help.setMinimumHeight(0)
		self.direct_action_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.direct_action_help.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		self.direct_action_help.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.direct_action_help.verticalScrollBar().setSingleStep(20)
		self.direct_action_help.setStyleSheet(
			'QTextBrowser#DirectActionCliOptionsBrowser {'
			'background: #fffaf2; color: #4f4134; border: 1px solid #d8c6ab; border-radius: 12px; padding: 8px;'
			'}'
		)
		self.direct_action_help.setHtml(build_direct_action_cli_options_html())
		content_layout.addWidget(self.direct_action_help)

		content_layout.addWidget(create_dialog_hint_label('Tip: start with main.py <command> --help when you need the live argparse output for one action.'))

		self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		self.button_box.accepted.connect(self.accept)
		add_dialog_footer(self, self.button_box)


__all__ = [
	'AboutDialog',
	'CommandLineGuideDialog',
	'DirectActionCliOptionsDialog',
	'build_command_line_guide_html',
	'build_direct_action_cli_options_html',
]