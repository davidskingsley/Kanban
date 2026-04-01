## @file
#  @brief Shared dialog widgets and delegates for the PySide6 multi-board GUI.
"""Shared dialog widgets and delegates for the PySide6 GUI."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import QDate, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
	QAbstractItemView,
	QCheckBox,
	QDateEdit,
	QFrame,
	QHBoxLayout,
	QPushButton,
	QStyle,
	QStyledItemDelegate,
	QWidget,
)

from .common import PropagatingListWidget, due_state_colors


class DueTimelineDelegate(QStyledItemDelegate):
	"""Paint a gantt-style schedule bar inside the due-date table."""

	def __init__(self, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.range_start = date.today() - timedelta(days=3)
		self.range_end = date.today() + timedelta(days=10)

	def set_range(self, start_date: date, end_date: date):
		self.range_start = start_date
		self.range_end = end_date

	def paint(self, painter: QPainter, option, index):
		payload = index.data(Qt.ItemDataRole.UserRole) or {}
		painter.save()

		if option.state & QStyle.StateFlag.State_Selected:
			painter.fillRect(option.rect, option.palette.highlight())
		else:
			background = QColor('#fffdfa' if index.row() % 2 == 0 else '#fbf3e8')
			painter.fillRect(option.rect, background)

		content_rect = QRectF(option.rect.adjusted(10, 10, -10, -10))
		if content_rect.width() <= 0 or content_rect.height() <= 0:
			painter.restore()
			return

		total_days = max(1, (self.range_end - self.range_start).days + 1)
		day_width = content_rect.width() / total_days
		today = date.today()

		for day_index in range(total_days):
			day = self.range_start + timedelta(days=day_index)
			left = content_rect.left() + (day_index * day_width)
			right = content_rect.left() + ((day_index + 1) * day_width)
			day_rect = QRectF(left, content_rect.top(), max(1.0, right - left), content_rect.height())
			if day.weekday() >= 5:
				painter.fillRect(day_rect, QColor(244, 236, 224, 165))
			if day == today:
				painter.setPen(QPen(QColor('#a63c30'), 2))
				marker_x = day_rect.left() + (day_rect.width() / 2)
				painter.drawLine(int(marker_x), int(content_rect.top()), int(marker_x), int(content_rect.bottom()))
			elif day_index > 0:
				painter.setPen(QPen(QColor('#eadfcd'), 1))
				painter.drawLine(int(day_rect.left()), int(content_rect.top()), int(day_rect.left()), int(content_rect.bottom()))

		painter.setPen(QPen(QColor('#d7c5ac'), 1))
		painter.drawRoundedRect(content_rect, 10, 10)

		start_date = payload.get('start_date')
		end_date = payload.get('end_date')
		state = str(payload.get('state') or '')
		label = str(payload.get('label') or '')

		if not start_date and not end_date:
			painter.setPen(QColor('#7a6c5f'))
			painter.drawText(content_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, 'No scheduled dates')
			painter.restore()
			return

		bar_start = start_date or end_date
		bar_end = end_date or start_date
		if bar_start is None:
			bar_start = today
		if bar_end is None:
			bar_end = bar_start
		if bar_end < bar_start:
			bar_start, bar_end = bar_end, bar_start

		bar_start = max(bar_start, self.range_start)
		bar_end = min(bar_end, self.range_end)
		start_offset = (bar_start - self.range_start).days
		end_offset = (bar_end - self.range_start).days + 1
		bar_left = content_rect.left() + (start_offset * day_width) + 2
		bar_right = content_rect.left() + (end_offset * day_width) - 2
		bar_width = max(10.0, bar_right - bar_left)
		bar_rect = QRectF(bar_left, content_rect.top() + 8, bar_width, max(18.0, content_rect.height() - 16))

		bar_background, bar_foreground = due_state_colors(state)
		painter.setBrush(QColor(bar_background).darker(104))
		painter.setPen(QPen(QColor(bar_foreground).darker(105), 1))
		if start_date and end_date and start_date != end_date:
			painter.drawRoundedRect(bar_rect, 8, 8)
		else:
			center_x = bar_rect.center().x()
			milestone = QRectF(center_x - 7, bar_rect.center().y() - 7, 14, 14)
			painter.drawEllipse(milestone)

		painter.setPen(QColor(bar_foreground))
		text_rect = bar_rect.adjusted(8, 0, -8, 0)
		if start_date and end_date and start_date != end_date and text_rect.width() > 72:
			painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
		else:
			trailing_rect = QRectF(min(content_rect.right() - 120, bar_rect.right() + 8), content_rect.top(), 120, content_rect.height())
			painter.drawText(trailing_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)

		painter.restore()


class SubcardsListWidget(PropagatingListWidget):
	"""List widget that keeps custom subcard rows sized to the current viewport width."""

	def __init__(self, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		self.verticalScrollBar().setSingleStep(20)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self.refresh_item_sizes()

	def refresh_item_sizes(self):
		available_width = self.viewport().width() - 12
		if available_width <= 0:
			return
		for index in range(self.count()):
			item = self.item(index)
			widget = self.itemWidget(item)
			if widget is None:
				continue
			if isinstance(widget, SubcardListItemContainer):
				widget.apply_width(available_width)
				widget.updateGeometry()
				height = widget.heightForWidth(available_width)
			else:
				widget.setFixedWidth(available_width)
				widget.updateGeometry()
				height = widget.heightForWidth(available_width) if widget.hasHeightForWidth() else widget.sizeHint().height()
			widget.setMinimumHeight(height)
			item.setSizeHint(QSize(available_width, height))


class SubcardListItemContainer(QWidget):
	"""Full-width row container that adds bottom-only spacing for subcards."""

	BOTTOM_SPACING = 5

	def __init__(self, row_widget: 'SubcardRowWidget', parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.row_widget = row_widget
		self._layout = QHBoxLayout(self)
		self._layout.setContentsMargins(0, 0, 0, self.BOTTOM_SPACING)
		self._layout.setSpacing(0)
		self._layout.addWidget(row_widget)

	def apply_width(self, row_width: int):
		margins = self._layout.contentsMargins()
		content_width = max(120, row_width - margins.left() - margins.right())
		self.setFixedWidth(row_width)
		self.row_widget.setFixedWidth(content_width)
		self.row_widget.updateGeometry()

	def hasHeightForWidth(self) -> bool:
		return True

	def heightForWidth(self, width: int) -> int:
		margins = self._layout.contentsMargins()
		content_width = max(120, width - margins.left() - margins.right())
		row_height = self.row_widget.heightForWidth(content_width) if self.row_widget.hasHeightForWidth() else self.row_widget.sizeHint().height()
		return row_height + margins.top() + margins.bottom()

	def sizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else self.row_widget.sizeHint().width()
		return QSize(width, self.heightForWidth(width))

	def minimumSizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else self.row_widget.minimumSizeHint().width()
		return QSize(width, self.heightForWidth(width))


class SubcardRowWidget(QFrame):
	"""Custom row widget for the subcards panel that supports proper height-for-width sizing."""

	def hasHeightForWidth(self) -> bool:
		return True

	def heightForWidth(self, width: int) -> int:
		layout = self.layout()
		if layout is None:
			return super().sizeHint().height()
		return max(layout.totalHeightForWidth(max(width, 180)), super().minimumSizeHint().height())

	def sizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else super().sizeHint().width()
		return QSize(width, self.heightForWidth(width))

	def minimumSizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else super().minimumSizeHint().width()
		return QSize(width, self.heightForWidth(width))


class OptionalDateField(QWidget):
	"""A checkbox-controlled date input."""

	def __init__(self, label: str, initial_value: Optional[date] = None, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.checkbox = QCheckBox(label)
		self.editor = QDateEdit()
		self.clear_button = QPushButton('Clear')
		self.editor.setCalendarPopup(True)
		self.editor.setDisplayFormat('yyyy-MM-dd')
		self.editor.setSpecialValueText('')
		self.editor.setWrapping(False)
		self.editor.setEnabled(initial_value is not None)
		self.clear_button.setEnabled(initial_value is not None)
		self.clear_button.setFixedWidth(60)

		initial_qdate = QDate.currentDate()
		if initial_value is not None:
			initial_qdate = QDate(initial_value.year, initial_value.month, initial_value.day)
			self.checkbox.setChecked(True)
		self.editor.setDate(initial_qdate)

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(8)
		layout.addWidget(self.checkbox)
		layout.addWidget(self.editor, 1)
		layout.addWidget(self.clear_button)
		self.checkbox.toggled.connect(self._set_enabled_state)
		self.clear_button.clicked.connect(self.clear)

	def _set_enabled_state(self, checked: bool):
		self.editor.setEnabled(checked)
		self.clear_button.setEnabled(checked)
		if checked:
			if not self.editor.date().isValid():
				self.editor.setDate(QDate.currentDate())
			self.editor.setFocus(Qt.FocusReason.TabFocusReason)
			self.editor.selectAll()

	def clear(self):
		self.checkbox.setChecked(False)
		self.editor.setDate(QDate.currentDate())

	def value(self) -> Optional[date]:
		if not self.checkbox.isChecked():
			return None
		selected = self.editor.date()
		return date(selected.year(), selected.month(), selected.day())
__all__ = [
	'DueTimelineDelegate',
	'OptionalDateField',
	'SubcardListItemContainer',
	'SubcardRowWidget',
	'SubcardsListWidget',
]