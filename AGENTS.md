# AGENTS.md

## Purpose

This repository is a multi-surface Kanban application with a desktop GUI, an interactive terminal UI, and a direct-action CLI. Use this file as the shared working guide for coding agents operating in this repo.

## Project Snapshot

- Runtime: Python 3.9 through 3.14
- Dependency and task runner: `uv`
- GUI: `PySide6`
- Tests: `unittest`
- Linting: `ruff`
- CI: GitHub Actions on Ubuntu with `QT_QPA_PLATFORM=offscreen`

Primary launch modes:

- GUI: `uv run python main.py`
- Interactive multi-board CLI: `uv run python main.py --cli`
- Direct-action CLI: `uv run python main.py <command> ...`

## Key Architecture

Entry points and top-level orchestration:

- `main.py` chooses between GUI, interactive CLI, and direct-action CLI.
- `kanban/board_manager.py` owns multi-board metadata, board registration, import/export, backend conversion, undo/redo for board-management actions, and board locking behavior.

Board model and persistence:

- `kanban/board.py` is a public facade that re-exports `KanbanBoard` from `kanban/board_core.py`.
- Board behavior is split across modules such as `kanban/board_cards.py`, `kanban/board_columns.py`, `kanban/board_catalog.py`, and `kanban/board_persistence.py`.
- `kanban/models.py` contains the core data models, including cards, notes, checklist items, and related entities.
- `kanban/storage.py` contains storage backend helpers and lock handling primitives.

GUI surface:

- `kanban/multi_board_gui.py` is a compatibility wrapper that imports the split GUI package.
- `kanban/gui/` contains the current GUI implementation.
- Help and command reference text lives in `kanban/gui/dialog_help.py`.

CLI surfaces:

- `kanban/multi_board_cli.py` handles multi-board terminal workflows.
- `kanban/cli.py` handles board-level interactive terminal workflows.
- `kanban/direct_cli.py` registers direct-action subcommands.
- Direct command implementation is split across `kanban/direct_cli_board_commands.py`, `kanban/direct_cli_card_commands.py`, `kanban/direct_cli_structure_commands.py`, and `kanban/direct_cli_support.py`.

## Working Conventions

- Keep changes targeted. This repo already has some pre-existing complexity and static-analysis debt, especially in `kanban/cli.py`. Do not expand scope to fix unrelated warnings unless the task requires it.
- Preserve facade modules such as `kanban/board.py` and `kanban/multi_board_gui.py`. They exist for compatibility and should not be removed casually.
- Treat generated or local-environment directories as off-limits unless the task explicitly targets them: `.venv/`, `.ruff_cache/`, `build/`, `dist/`, and `__pycache__/`.
- Prefer small, local edits over broad refactors. The project was recently split into smaller modules, so keep related code in its current layer instead of collapsing modules back together.

## Keep In Sync

When you add or change a user-facing feature, check the related surfaces together.

- If you change launcher behavior or top-level CLI options, update `main.py` help text and `README.md`.
- If you change direct CLI commands, update `kanban/direct_cli.py`, the relevant direct CLI command mixin, `kanban/gui/dialog_help.py`, and `README.md`.
- If you change interactive CLI menu options, update both the printed menu and the handler mapping in `kanban/cli.py`.
- If you change note, checklist, archive, board-management, or card-type workflows, verify whether both GUI and CLI documentation still describe the feature correctly.

## Validation Workflow

Use `uv` commands unless there is a strong reason not to.

Common validation commands:

- Install dependencies: `uv sync --all-groups`
- Lint: `uv run ruff check .`
- Full test suite: `uv run python -m unittest discover -s tests`
- Direct CLI regression suite: `uv run python -m unittest tests.test_direct_cli`

GUI-specific note:

- GUI tests require offscreen Qt. CI sets `QT_QPA_PLATFORM=offscreen`, and `tests/gui_test_case.py` also defaults that environment variable.

Validation minimums by change type:

- Documentation-only changes: sanity-check the touched docs/help text for accuracy and consistency.
- Direct CLI changes: run `uv run python -m unittest tests.test_direct_cli`.
- Shared board/model/storage changes: run `uv run python -m unittest discover -s tests`.
- When code paths are broad or risky, run `uv run ruff check .` before finishing.

## Testing Guidance

- Add or update focused `unittest` coverage for behavior changes when practical.
- For direct CLI changes, prefer adding coverage in `tests/test_direct_cli.py`.
- For GUI regressions, use the existing GUI regression test modules and the shared `GuiTestCase` in `tests/gui_test_case.py`.
- If a change affects lock handling, import/export, or board registration, validate through `BoardManager` paths rather than only checking the UI layer.

## Commit Workflow

- Do not create commits unless the user explicitly asks.
- Before committing, make sure the relevant validation for the touched surface has run successfully.
- Keep commits focused on one feature or fix area. Do not bundle unrelated cleanup with user-requested behavior changes.
- Prefer commit messages that describe the user-visible change or architectural intent plainly, for example `Add CLI note management` or `Update help text for direct CLI commands`.

## Review Expectations

- When reviewing changes, prioritize behavioral regressions, stale help text, missing tests, and inconsistencies across GUI, interactive CLI, and direct CLI surfaces.
- Pay particular attention to features that span multiple layers, such as notes, checklists, archives, card types, project assignment, board import/export, and lock handling.
- If a change updates a command, menu item, or workflow in one surface but not the others, treat that as a likely issue rather than a documentation-only omission.

## Change Checklist

Before wrapping up a task, quickly verify the following when relevant:

- The implementation lives in the correct module split rather than being added to an unrelated facade.
- Help text, README content, and CLI parser descriptions still match the implemented behavior.
- The smallest relevant test target has been run.
- No generated, environment, or build-output directories were edited accidentally.

## Feature-Specific Notes

- The app supports both JSON and SQLite board storage. Do not assume one backend.
- External boards can be registered from folders or standalone files. Be careful with path handling and metadata updates.
- Board locks are a real workflow. Direct CLI commands use `--lock-action`, while the interactive multi-board CLI prompts the user.
- Notes, checklists, archived cards, subcards, card types, and managed projects span multiple layers. Changes in one layer often need documentation and regression updates in another.

## Good Defaults For Agents

- Read the relevant module split before editing behavior.
- Validate the smallest affected test surface first, then run broader checks if the change touches shared flows.
- Favor compatibility and documentation updates when changing commands or menus.
- Keep user-facing text concise and consistent across the README, argparse help, and in-app Help dialogs.