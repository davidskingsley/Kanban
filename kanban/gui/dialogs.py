## @file
#  @brief Dialog facade used by the PySide6 multi-board GUI.
"""Public dialog facade for the PySide6 GUI."""

from PySide6.QtWidgets import QMessageBox

from .dialog_card import AttachmentDropFrame, CardDialog
from .dialog_help import AboutDialog, CommandLineGuideDialog, DirectActionCliOptionsDialog
from .dialog_management import (
	BoardDialog,
	CardTypeDialog,
	CardTypesBrowserDialog,
	ColumnDialog,
	ProjectDialog,
	ProjectsBrowserDialog,
	ReorderColumnsDialog,
)
from .dialog_overview import ArchivedCardInfoDialog, ArchivedCardsDialog, DueDateViewDialog
from .dialog_primitives import (
	DueTimelineDelegate,
	OptionalDateField,
	SubcardListItemContainer,
	SubcardRowWidget,
	SubcardsListWidget,
)

__all__ = [
	'AboutDialog',
	'ArchivedCardInfoDialog',
	'ArchivedCardsDialog',
	'AttachmentDropFrame',
	'BoardDialog',
	'CardDialog',
	'CardTypeDialog',
	'CardTypesBrowserDialog',
	'ColumnDialog',
	'CommandLineGuideDialog',
	'DirectActionCliOptionsDialog',
	'DueDateViewDialog',
	'DueTimelineDelegate',
	'OptionalDateField',
	'ProjectDialog',
	'ProjectsBrowserDialog',
	'QMessageBox',
	'ReorderColumnsDialog',
	'SubcardListItemContainer',
	'SubcardRowWidget',
	'SubcardsListWidget',
]
