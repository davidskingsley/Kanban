## @file
#  @brief Embedded board widgets used by the PySide6 multi-board GUI.
"""Board-view widgets for the PySide6 GUI."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import QMimeData, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QCursor, QDrag, QPainter, QPen
from PySide6.QtWidgets import (
	QApplication,
	QFrame,
	QGraphicsDropShadowEffect,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QMenu,
	QPushButton,
	QVBoxLayout,
	QWidget,
)

from ..board import KanbanBoard
from .common import (
	clamp_drag_hotspot,
	clipped_description,
	clipped_title,
	contrasting_text_color,
	create_drag_preview,
	file_paths_from_mime_data,
	format_card_text,
	handle_scrollable_wheel_event,
	priority_accent,
	priority_label,
	resolve_hex_color,
	rgba_color,
	schedule_summary,
	secondary_text_color,
)


class CardTile(QFrame):
	"""Structured card widget used inside each column list."""

	def __init__(self, board: KanbanBoard, card, selected: bool = False,
				 file_drop_callback=None, select_callback=None,
				 edit_callback=None, context_action_callback=None,
				 parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.board = board
		self.card = card
		self.selected = selected
		self.file_drop_callback = file_drop_callback
		self.select_callback = select_callback
		self.edit_callback = edit_callback
		self.context_action_callback = context_action_callback
		self.compact_text = False
		self._drop_highlight = False

		self.background = resolve_hex_color(card.color, '#fffaf3')
		self.foreground = contrasting_text_color(self.background)
		self.muted = secondary_text_color(self.background)
		self.priority_color = priority_accent(card.priority)
		self.selection_color = self._selection_color_for_background()
		self.border_color = self.selection_color if selected else ('#a63c30' if card.has_past_end_date() and not board.is_card_done(card) else '#d7c4aa')

		self.setObjectName('CardTile')
		self.setAcceptDrops(True)
		self._build_ui()
		self._apply_shadow()
		self._apply_style()

	def _create_badge(self, text: str, background: str, foreground: str, border: Optional[str] = None) -> QLabel:
		label = QLabel(text)
		label.setFixedHeight(24)
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		label.setStyleSheet(
			f"""
			background: {background};
			color: {foreground};
			border: 1px solid {border or background};
			border-radius: 9px;
			padding: 3px 8px;
			font-size: 6.5pt;
			font-weight: 700;
			"""
		)
		return label

	def _selection_color_for_background(self) -> str:
		background = QColor(self.background)
		if self.foreground == '#ffffff':
			selection = background.lighter(170)
		else:
			selection = background.darker(230)
		return selection.name()

	def set_compact_text(self, compact_text: bool):
		if self.compact_text == compact_text:
			return
		self.compact_text = compact_text
		self._apply_text_styles()
		self.updateGeometry()

	def _build_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(14, 14, 14, 14)
		layout.setSpacing(10)

		priority_bar = QFrame()
		priority_bar.setFixedHeight(6)
		priority_bar.setStyleSheet(f'background: {self.priority_color}; border-radius: 3px;')
		layout.addWidget(priority_bar)

		header_row = QWidget()
		header_layout = QHBoxLayout(header_row)
		header_layout.setContentsMargins(0, 0, 0, 0)
		header_layout.setSpacing(6)
		header_layout.addWidget(
			self._create_badge(
				priority_label(self.card.priority).upper(),
				rgba_color(self.priority_color, 0.14),
				self.priority_color,
				rgba_color(self.priority_color, 0.30),
			)
		)

		card_type = self.board.get_card_type(self.card.card_type_id)
		if card_type is None:
			card_type = self.board.get_default_card_type()
		if card_type is not None:
			header_layout.addWidget(
				self._create_badge(
					card_type.name,
					rgba_color(self.foreground, 0.08),
					self.foreground,
					rgba_color(self.foreground, 0.12),
				)
			)

		if self.card.has_past_end_date() and not self.board.is_card_done(self.card):
			header_layout.addWidget(
				self._create_badge('LATE', 'rgba(166, 60, 48, 0.14)', '#a63c30', 'rgba(166, 60, 48, 0.28)')
			)
		if self.selected:
			header_layout.addWidget(
				self._create_badge(
					'SELECTED',
					rgba_color(self.selection_color, 0.18),
					self.selection_color,
					rgba_color(self.selection_color, 0.40),
				)
			)
		header_layout.addStretch(1)
		if self.card.assignee:
			header_layout.addWidget(
				self._create_badge(
					f'@{self.card.assignee}',
					rgba_color(self.foreground, 0.08),
					self.foreground,
					rgba_color(self.foreground, 0.12),
				)
			)
		layout.addWidget(header_row)

		self.title_label = QLabel(clipped_title(self.card.title))
		self.title_label.setWordWrap(True)
		layout.addWidget(self.title_label)

		meta_parts = []
		if self.card.project:
			meta_parts.append(self.card.project)
		parent_card = self.board.get_parent_card(self.card)
		if parent_card is not None:
			meta_parts.append(f'Subcard of {parent_card.title}')
		if meta_parts:
			self.meta_label = QLabel(' | '.join(meta_parts))
			self.meta_label.setWordWrap(True)
			layout.addWidget(self.meta_label)
		else:
			self.meta_label = None

		description = clipped_description(self.card.description)
		if description:
			self.description_label = QLabel(description)
			self.description_label.setWordWrap(True)
			layout.addWidget(self.description_label)
		else:
			self.description_label = None

		schedule_parts = []
		schedule_text = schedule_summary(self.card)
		if schedule_text:
			schedule_parts.append(schedule_text)
		if self.card.has_past_end_date() and not self.board.is_card_done(self.card):
			schedule_parts.append('Late')
		if parent_card is None:
			completed, total = self.board.get_subcard_progress(self.card.id)
			if total:
				schedule_parts.append(f'Subcards {completed}/{total}')
		if schedule_parts:
			self.schedule_label = QLabel(' | '.join(schedule_parts))
			self.schedule_label.setWordWrap(True)
			layout.addWidget(self.schedule_label)
		else:
			self.schedule_label = None

		if self.card.tags:
			self.tags_label = QLabel(' '.join(f'#{tag}' for tag in self.card.tags))
			self.tags_label.setWordWrap(True)
			layout.addWidget(self.tags_label)
		else:
			self.tags_label = None

		footer_badges = []
		if self.card.notes:
			footer_badges.append(
				self._create_badge(
					f'{len(self.card.notes)} note' + ('' if len(self.card.notes) == 1 else 's'),
					rgba_color(self.foreground, 0.06),
					self.muted,
					rgba_color(self.foreground, 0.09),
				)
			)
		if self.card.attachments:
			footer_badges.append(
				self._create_badge(
					f'{len(self.card.attachments)} attachment' + ('' if len(self.card.attachments) == 1 else 's'),
					rgba_color(self.foreground, 0.06),
					self.muted,
					rgba_color(self.foreground, 0.09),
				)
			)
		if footer_badges:
			footer_row = QWidget()
			footer_layout = QHBoxLayout(footer_row)
			footer_layout.setContentsMargins(0, 0, 0, 0)
			footer_layout.setSpacing(6)
			for badge in footer_badges:
				footer_layout.addWidget(badge)
			footer_layout.addStretch(1)
			layout.addWidget(footer_row)

		self._apply_text_styles()

	def _apply_text_styles(self):
		title_size = '8.5pt' if self.compact_text else '9pt'
		meta_size = '6.5pt' if self.compact_text else '7pt'
		body_size = '7pt' if self.compact_text else '7.5pt'
		tag_size = '7.5pt' if self.compact_text else '8pt'
		schedule_padding = '6px 8px' if self.compact_text else '7px 9px'

		self.title_label.setStyleSheet(
			f'font-size: {title_size}; font-weight: 700; color: {self.foreground}; background: transparent;'
		)
		if self.meta_label is not None:
			self.meta_label.setStyleSheet(
				f'color: {self.muted}; background: transparent; font-size: {meta_size}; font-weight: 600;'
			)
		if self.description_label is not None:
			self.description_label.setStyleSheet(
				f'color: {self.muted}; background: transparent; font-size: {body_size};'
			)
		if self.schedule_label is not None:
			self.schedule_label.setStyleSheet(
				f'color: {self.foreground}; background: {rgba_color(self.foreground, 0.055)}; '
				f'border: 1px solid {rgba_color(self.foreground, 0.08)}; border-radius: 10px; padding: {schedule_padding}; font-size: {body_size};'
			)
		if self.tags_label is not None:
			self.tags_label.setStyleSheet(
				f'color: {self.foreground}; background: {rgba_color(self.priority_color, 0.08)}; '
				f'border-radius: 10px; padding: 6px 8px; font-weight: 600; font-size: {tag_size};'
			)

	def _apply_shadow(self):
		shadow = QGraphicsDropShadowEffect(self)
		shadow.setBlurRadius(30 if self.selected else 24)
		shadow.setOffset(0, 7 if self.selected else 5)
		shadow_color = QColor(self.selection_color) if self.selected else QColor(64, 39, 21, 38)
		if self.selected:
			shadow_color.setAlpha(84)
		shadow.setColor(shadow_color)
		self.setGraphicsEffect(shadow)

	def _apply_style(self):
		active_border = '#3e7a5e' if self._drop_highlight else self.border_color
		soft_top = QColor(self.background).lighter(108 if self.selected else 104).name()
		soft_bottom = QColor(self.background).darker(100 if self.selected else 102).name()
		border_width = 3 if self.selected and not self._drop_highlight else 2
		self.setStyleSheet(
			f"""
			QFrame#CardTile {{
				background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
					stop:0 {soft_top}, stop:0.62 {self.background}, stop:1 {soft_bottom});
				border: {border_width}px solid {active_border};
				border-radius: 14px;
			}}
			"""
		)

	def dragEnterEvent(self, event):
		if self.file_drop_callback is None:
			event.ignore()
			return
		paths = file_paths_from_mime_data(event.mimeData())
		if not paths:
			event.ignore()
			return
		self._drop_highlight = True
		self._apply_style()
		event.acceptProposedAction()

	def dragLeaveEvent(self, event):
		self._drop_highlight = False
		self._apply_style()
		super().dragLeaveEvent(event)

	def dropEvent(self, event):
		paths = file_paths_from_mime_data(event.mimeData())
		self._drop_highlight = False
		self._apply_style()
		if not paths or self.file_drop_callback is None:
			event.ignore()
			return
		self.file_drop_callback(self.card.id, paths)
		event.acceptProposedAction()

	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			event.ignore()
			return
		super().mousePressEvent(event)

	def mouseDoubleClickEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton and self.edit_callback is not None:
			self.edit_callback(self.card.id)
			event.accept()
			return
		super().mouseDoubleClickEvent(event)

	def contextMenuEvent(self, event):
		menu = QMenu(self)
		edit_action = menu.addAction('Edit Card')
		add_subcard_action = None
		if self.context_action_callback is not None and not self.card.parent_id:
			add_subcard_action = menu.addAction('Add Subcard')
		chosen_action = menu.exec(event.globalPos())
		if chosen_action is None:
			event.ignore()
			return
		if chosen_action == edit_action and self.edit_callback is not None:
			self.edit_callback(self.card.id)
			event.accept()
			return
		if chosen_action == add_subcard_action and self.context_action_callback is not None:
			self.context_action_callback(self.card.id, 'add_subcard')
			event.accept()
			return
		super().contextMenuEvent(event)

	def sizeHint(self) -> QSize:
		width = self.width() if self.width() > 0 else super().sizeHint().width()
		return QSize(width, self.heightForWidth(width))

	def minimumSizeHint(self) -> QSize:
		hint = super().minimumSizeHint()
		width = self.width() if self.width() > 0 else max(hint.width(), super().sizeHint().width())
		return QSize(width, self.heightForWidth(width))

	def hasHeightForWidth(self) -> bool:
		return True

	def heightForWidth(self, width: int) -> int:
		layout = self.layout()
		if layout is None:
			return max(super().sizeHint().height(), 156)
		constrained_width = max(width, 120)
		return max(layout.totalHeightForWidth(constrained_width), 156)


class CardListItemContainer(QWidget):
	"""Full-width row container that keeps card clearance on the scrollbar side only."""
	BOTTOM_SPACING = 14

	def __init__(self, card_widget: CardTile, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.card_widget = card_widget
		self._layout = QHBoxLayout(self)
		self._layout.setContentsMargins(0, 0, 0, self.BOTTOM_SPACING)
		self._layout.setSpacing(0)
		self._layout.addWidget(card_widget)
		self._layout.addStretch(1)

	def apply_widths(self, row_width: int, card_width: int, right_clearance: int):
		self.setFixedWidth(row_width)
		self._layout.setContentsMargins(0, 0, right_clearance, self.BOTTOM_SPACING)
		self.card_widget.setFixedWidth(card_width)
		self.card_widget.updateGeometry()

	def heightForWidth(self, width: int) -> int:
		margins = self._layout.contentsMargins()
		card_width = max(120, width - margins.right())
		return self.card_widget.heightForWidth(card_width) + margins.bottom()


class CardListWidget(QListWidget):
	CARD_MIME_TYPE = 'application/x-kanban-card'
	DROP_INDICATOR_MARGIN = 10
	DROP_INDICATOR_SPACING = 5
	DROP_INDICATOR_THICKNESS = 4
	BASE_CONTENT_GUTTER = 6
	SCROLLBAR_CLEARANCE = 14

	def __init__(self, column_id: Optional[str] = None, board_view=None, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.column_id = column_id
		self.board_view = board_view
		self._drop_highlight = False
		self._drop_indicator_y: Optional[int] = None
		self._drop_indicator_line = QFrame(self.viewport())
		self._drop_indicator_line.setObjectName('CardDropIndicatorLine')
		self._drop_indicator_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
		self._drop_indicator_line.setStyleSheet('background: #3e7a5e; border-radius: 2px;')
		self._drop_indicator_line.hide()
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.setDragEnabled(True)
		self.setAcceptDrops(True)
		self.viewport().setAcceptDrops(True)
		self.setDropIndicatorShown(False)
		self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
		self.verticalScrollBar().setSingleStep(24)
		self.setSpacing(0)
		self.verticalScrollBar().rangeChanged.connect(lambda _minimum, _maximum: self.refresh_card_sizes())

	def _apply_drop_style(self):
		self.setStyleSheet(
			"""
			QListWidget {
				background: transparent;
				border: none;
				border-radius: 14px;
				padding: 0;
				outline: 0;
			}
			QListWidget::item {
				background: transparent;
				border: none;
				padding: 0;
				margin: 0;
			}
			QListWidget::item:selected {
				background: transparent;
				border: none;
			}
			"""
		)

	def startDrag(self, supported_actions):
		item = self.currentItem()
		if item is None:
			return
		payload = item.data(Qt.ItemDataRole.UserRole) or {}
		card_id = payload.get('card_id')
		if not card_id:
			return
		mime_data = QMimeData()
		mime_payload = {'card_id': card_id, 'source_column_id': payload.get('column_id') or self.column_id}
		mime_data.setData(self.CARD_MIME_TYPE, json.dumps(mime_payload).encode('utf-8'))

		drag = QDrag(self)
		drag.setMimeData(mime_data)
		widget = self.itemWidget(item)
		if widget is not None:
			preview_widget = widget.card_widget if isinstance(widget, CardListItemContainer) else widget
			preview = create_drag_preview(preview_widget.grab())
			drag.setPixmap(preview)
			drag.setHotSpot(clamp_drag_hotspot(preview_widget.mapFromGlobal(QCursor.pos()), preview.size()))
		drag.exec(Qt.DropAction.MoveAction)

	def dragEnterEvent(self, event):
		if event.mimeData().hasFormat(self.CARD_MIME_TYPE):
			self._drop_highlight = True
			self._apply_drop_style()
			self._update_drop_indicator(event.position().toPoint())
			event.acceptProposedAction()
			return
		event.ignore()

	def dragMoveEvent(self, event):
		if event.mimeData().hasFormat(self.CARD_MIME_TYPE):
			self._update_drop_indicator(event.position().toPoint())
			event.acceptProposedAction()
			return
		event.ignore()

	def _indicator_y_for_point(self, point: QPoint) -> int:
		if self.count() == 0:
			return self.DROP_INDICATOR_MARGIN + 2
		item = self.itemAt(point)
		if item is None:
			last_rect = self.visualItemRect(self.item(self.count() - 1))
			return last_rect.bottom() + self.DROP_INDICATOR_SPACING
		item_rect = self.visualItemRect(item)
		insert_after = point.y() > item_rect.center().y()
		return item_rect.bottom() + self.DROP_INDICATOR_SPACING if insert_after else item_rect.top() - self.DROP_INDICATOR_SPACING

	def _update_drop_indicator(self, point: QPoint):
		indicator_y = self._indicator_y_for_point(point)
		max_y = max(self.DROP_INDICATOR_MARGIN, self.viewport().height() - self.DROP_INDICATOR_MARGIN)
		self._drop_indicator_y = max(self.DROP_INDICATOR_MARGIN, min(indicator_y, max_y))
		self._position_drop_indicator_line()

	def _clear_drop_indicator(self):
		self._drop_indicator_y = None
		self._drop_indicator_line.hide()

	def _position_drop_indicator_line(self):
		if self._drop_indicator_y is None:
			self._drop_indicator_line.hide()
			return
		x_start = self.DROP_INDICATOR_MARGIN
		line_width = max(1, self.viewport().width() - (2 * self.DROP_INDICATOR_MARGIN))
		y_pos = self._drop_indicator_y - (self.DROP_INDICATOR_THICKNESS // 2)
		self._drop_indicator_line.setGeometry(x_start, y_pos, line_width, self.DROP_INDICATOR_THICKNESS)
		self._drop_indicator_line.show()
		self._drop_indicator_line.raise_()

	def _drop_target_details(self, point):
		item = self.itemAt(point)
		if item is None:
			return None, True
		payload = item.data(Qt.ItemDataRole.UserRole) or {}
		item_rect = self.visualItemRect(item)
		insert_after = point.y() > item_rect.center().y()
		return payload.get('card_id'), insert_after

	def dragLeaveEvent(self, event):
		self._drop_highlight = False
		self._apply_drop_style()
		self._clear_drop_indicator()
		super().dragLeaveEvent(event)

	def dropEvent(self, event):
		self._drop_highlight = False
		self._apply_drop_style()
		self._clear_drop_indicator()
		if not event.mimeData().hasFormat(self.CARD_MIME_TYPE) or self.board_view is None:
			event.ignore()
			return
		payload = json.loads(bytes(event.mimeData().data(self.CARD_MIME_TYPE)).decode('utf-8'))
		target_card_id, insert_after = self._drop_target_details(event.position().toPoint())
		self.board_view.handle_card_drop(
			payload.get('card_id'),
			payload.get('source_column_id'),
			self.column_id,
			target_card_id=target_card_id,
			insert_after=insert_after,
		)
		event.acceptProposedAction()

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self.refresh_card_sizes()
		self._position_drop_indicator_line()

	def wheelEvent(self, event):
		handle_scrollable_wheel_event(self, event, lambda: super(CardListWidget, self).wheelEvent(event))

	def _card_content_clearance_width(self) -> int:
		scroll_bar = self.verticalScrollBar()
		if scroll_bar.maximum() <= 0 and not scroll_bar.isVisible():
			return self.BASE_CONTENT_GUTTER
		return self.SCROLLBAR_CLEARANCE

	def refresh_card_sizes(self):
		row_width = self.viewport().width()
		right_clearance = self._card_content_clearance_width()
		card_width = row_width - 2 - right_clearance
		if card_width <= 0:
			return
		for index in range(self.count()):
			item = self.item(index)
			widget = self.itemWidget(item)
			if widget is None:
				continue
			if isinstance(widget, CardListItemContainer):
				widget.card_widget.set_compact_text(right_clearance >= self.SCROLLBAR_CLEARANCE)
				widget.apply_widths(row_width, card_width, right_clearance)
				height = widget.heightForWidth(row_width)
				widget.setMinimumHeight(height)
				item.setSizeHint(QSize(row_width, height))
				continue
			widget.setFixedWidth(card_width)
			widget.updateGeometry()
			height = widget.heightForWidth(card_width) if widget.hasHeightForWidth() else widget.sizeHint().height()
			widget.setMinimumHeight(height)
			item.setSizeHint(QSize(card_width, height))


class ColumnTitleButton(QPushButton):
	def __init__(
		self,
		text: str,
		click_callback=None,
		double_click_callback=None,
		drag_callback=None,
		drag_target: Optional[QWidget] = None,
		parent: Optional[QWidget] = None,
	):
		super().__init__(text, parent)
		self._double_click_callback = double_click_callback
		self._drag_callback = drag_callback
		self._drag_target = drag_target
		self._press_pos = None
		self.setCursor(Qt.CursorShape.PointingHandCursor)
		self.setFlat(True)
		if click_callback is not None:
			self.clicked.connect(click_callback)

	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self._press_pos = event.position().toPoint()
		super().mousePressEvent(event)

	def _maybe_start_drag(self, current_pos: QPoint, buttons: Qt.MouseButtons) -> bool:
		if self._press_pos is None or self._drag_callback is None:
			return False
		if not (buttons & Qt.MouseButton.LeftButton):
			return False
		if (current_pos - self._press_pos).manhattanLength() < QApplication.startDragDistance():
			return False
		drag_origin = self._press_pos
		if self._drag_target is not None:
			drag_origin = self.mapTo(self._drag_target, self._press_pos)
		self._press_pos = None
		self._drag_callback(drag_origin)
		return True

	def mouseMoveEvent(self, event):
		if self._maybe_start_drag(event.position().toPoint(), event.buttons()):
			event.accept()
			return
		super().mouseMoveEvent(event)

	def mouseReleaseEvent(self, event):
		self._press_pos = None
		super().mouseReleaseEvent(event)

	def mouseDoubleClickEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton and self._double_click_callback is not None:
			self._double_click_callback()
			event.accept()
			return
		super().mouseDoubleClickEvent(event)


class ColumnAddButton(QPushButton):
	def __init__(self, accent_color: str, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.accent_color = resolve_hex_color(accent_color, '#8f4a1d')
		self.setObjectName('ColumnAddButton')
		self.setToolTip('Add card')
		self.setCursor(Qt.CursorShape.PointingHandCursor)
		self.setFixedSize(28, 28)
		self.setStyleSheet(
			f"QPushButton#ColumnAddButton {{ background: {rgba_color(self.accent_color, 0.14)}; border: 1px solid {rgba_color(self.accent_color, 0.28)}; border-radius: 14px; }}"
			f"QPushButton#ColumnAddButton:hover {{ background: {rgba_color(self.accent_color, 0.22)}; border-color: {rgba_color(self.accent_color, 0.40)}; }}"
			f"QPushButton#ColumnAddButton:pressed {{ background: {rgba_color(self.accent_color, 0.30)}; }}"
		)

	def paintEvent(self, event):
		super().paintEvent(event)
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		pen = QPen(QColor(self.accent_color))
		pen.setWidth(2)
		pen.setCapStyle(Qt.PenCapStyle.RoundCap)
		painter.setPen(pen)
		center_x = self.width() / 2
		center_y = self.height() / 2
		arm = 5
		painter.drawLine(QPointF(center_x - arm, center_y), QPointF(center_x + arm, center_y))
		painter.drawLine(QPointF(center_x, center_y - arm), QPointF(center_x, center_y + arm))
		painter.end()


class ColumnGroupBox(QGroupBox):
	COLUMN_MIME_TYPE = 'application/x-kanban-column'
	DRAG_HANDLE_HEIGHT = 56
	DROP_INDICATOR_MARGIN = 10
	DROP_INDICATOR_THICKNESS = 5

	def __init__(self, title: str, column_id: str, board_view, selected: bool, parent: Optional[QWidget] = None):
		super().__init__(title, parent)
		self.column_id = column_id
		self.board_view = board_view
		self.selected = selected
		self._drop_highlight = False
		self._drop_indicator_x: Optional[int] = None
		self._drop_indicator_line = QFrame(self)
		self._drop_indicator_line.setObjectName('ColumnDropIndicatorLine')
		self._drop_indicator_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
		self._drop_indicator_line.setStyleSheet('background: #3e7a5e; border-radius: 2px;')
		self._drop_indicator_line.hide()
		self._press_pos = None
		self.setAcceptDrops(True)
		shadow = QGraphicsDropShadowEffect(self)
		shadow.setBlurRadius(30)
		shadow.setOffset(0, 8)
		shadow.setColor(QColor(74, 49, 30, 26))
		self.setGraphicsEffect(shadow)
		self._apply_style()

	def _apply_style(self):
		border_color = '#3e7a5e' if self._drop_highlight else ('#7d3b14' if self.selected else '#ccb391')
		self.setStyleSheet(
			f"""
			QGroupBox {{
				background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
					stop:0 #fdf7ed, stop:1 #f3e6d5);
				border: 2px solid {border_color};
				border-radius: 18px;
				margin-top: 12px;
				padding-top: 0px;
			}}
			"""
		)

	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= self.DRAG_HANDLE_HEIGHT:
			self._press_pos = event.position().toPoint()
		super().mousePressEvent(event)

	def mouseMoveEvent(self, event):
		if self._press_pos is None:
			super().mouseMoveEvent(event)
			return
		if not (event.buttons() & Qt.MouseButton.LeftButton):
			super().mouseMoveEvent(event)
			return
		if (event.position().toPoint() - self._press_pos).manhattanLength() < QApplication.startDragDistance():
			super().mouseMoveEvent(event)
			return
		self.start_drag_from_hotspot(self._press_pos)
		super().mouseMoveEvent(event)

	def start_drag_from_hotspot(self, hot_spot: QPoint):
		mime_data = QMimeData()
		mime_data.setData(self.COLUMN_MIME_TYPE, self.column_id.encode('utf-8'))
		drag = QDrag(self)
		drag.setMimeData(mime_data)
		preview = create_drag_preview(self.grab())
		drag.setPixmap(preview)
		drag.setHotSpot(clamp_drag_hotspot(hot_spot, preview.size()))
		self._press_pos = None
		drag.exec(Qt.DropAction.MoveAction)

	def mouseReleaseEvent(self, event):
		self._press_pos = None
		super().mouseReleaseEvent(event)

	def mouseDoubleClickEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 34:
			self.board_view.handle_column_double_click(self.column_id)
			event.accept()
			return
		super().mouseDoubleClickEvent(event)

	def dragEnterEvent(self, event):
		if event.mimeData().hasFormat(self.COLUMN_MIME_TYPE):
			self._drop_highlight = True
			self._apply_style()
			self._update_drop_indicator(event.position().x())
			event.acceptProposedAction()
			return
		event.ignore()

	def dragMoveEvent(self, event):
		if event.mimeData().hasFormat(self.COLUMN_MIME_TYPE):
			self._update_drop_indicator(event.position().x())
			event.acceptProposedAction()
			return
		event.ignore()

	def _update_drop_indicator(self, x_pos: float):
		insert_after = x_pos > (self.width() / 2)
		self._drop_indicator_x = self.width() - self.DROP_INDICATOR_MARGIN if insert_after else self.DROP_INDICATOR_MARGIN
		self._position_drop_indicator_line()

	def _clear_drop_indicator(self):
		self._drop_indicator_x = None
		self._drop_indicator_line.hide()

	def _position_drop_indicator_line(self):
		if self._drop_indicator_x is None:
			self._drop_indicator_line.hide()
			return
		x_pos = self._drop_indicator_x - (self.DROP_INDICATOR_THICKNESS // 2)
		line_height = max(1, self.height() - 36)
		self._drop_indicator_line.setGeometry(x_pos, 18, self.DROP_INDICATOR_THICKNESS, line_height)
		self._drop_indicator_line.show()
		self._drop_indicator_line.raise_()

	def dragLeaveEvent(self, event):
		self._drop_highlight = False
		self._apply_style()
		self._clear_drop_indicator()
		super().dragLeaveEvent(event)

	def dropEvent(self, event):
		self._drop_highlight = False
		self._apply_style()
		self._clear_drop_indicator()
		if not event.mimeData().hasFormat(self.COLUMN_MIME_TYPE):
			event.ignore()
			return
		dragged_column_id = bytes(event.mimeData().data(self.COLUMN_MIME_TYPE)).decode('utf-8')
		insert_after = event.position().x() > (self.width() / 2)
		self.board_view.handle_column_drop(dragged_column_id, self.column_id, insert_after)
		event.acceptProposedAction()

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._position_drop_indicator_line()


__all__ = [
	'CardListWidget',
	'CardTile',
	'ColumnAddButton',
	'ColumnGroupBox',
	'ColumnTitleButton',
	'format_card_text',
]
