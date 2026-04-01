# Copilot Instructions

Use this repository as a multi-surface Kanban application with three user-facing entry points: desktop GUI, interactive multi-board CLI, and direct-action CLI automation.

## Core Rules

- Prefer targeted edits over broad refactors.
- Preserve compatibility facades such as `kanban/board.py` and `kanban/multi_board_gui.py`.
- Do not touch generated or environment directories unless the task explicitly requires it: `.venv/`, `.ruff_cache/`, `build/`, `dist/`, and `__pycache__/`.
- Use `uv` for install, lint, and test commands unless there is a strong reason not to.

## Architecture Shortcuts

- `main.py`: top-level launcher and argparse help.
- `kanban/board_manager.py`: multi-board registry, import/export, backend conversion, and lock-aware board loading.
- `kanban/cli.py`: interactive board-level terminal workflows.
- `kanban/multi_board_cli.py`: board-selection and multi-board terminal workflows.
- `kanban/direct_cli.py`: direct command registration.
- `kanban/direct_cli_*`: direct command implementations and support helpers.
- `kanban/gui/`: current GUI implementation.

## Keep In Sync

- If you change direct CLI commands, update the parser, the implementation mixin, `kanban/gui/dialog_help.py`, and `README.md`.
- If you change interactive CLI menu behavior, update both the visible menu text and the handler mapping in `kanban/cli.py`.
- If you change top-level launch behavior or global CLI flags, update `main.py` help text and `README.md`.
- If you change notes, checklists, archives, card types, project assignment, or board-management flows, check whether both GUI and CLI documentation still match.

## Validation Defaults

- Direct CLI changes: `uv run python -m unittest tests.test_direct_cli`
- Broader shared logic changes: `uv run python -m unittest discover -s tests`
- Lint when behavior changes touch multiple modules: `uv run ruff check .`

## Testing Notes

- GUI tests run with offscreen Qt. CI sets `QT_QPA_PLATFORM=offscreen`, and `tests/gui_test_case.py` also defaults that environment variable.
- Prefer focused `unittest` updates for the changed surface instead of unrelated test churn.

## Working Style

- This repo has some existing complexity and static-analysis debt, especially in `kanban/cli.py`. Do not expand scope to fix unrelated warnings unless the task calls for it.
- Keep user-facing wording concise and aligned across README, argparse help, and the in-app Help dialogs.
- Before committing, run the smallest relevant validation for the changed surface.