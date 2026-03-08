import copy
import logging
import pandas as pd

from PyQt5.QtCore import (
	QEvent, QModelIndex, QObject, QRect, QSize, Qt
)
from PyQt5.QtGui import (
	QFocusEvent, QFontMetrics, QKeyEvent, QPainter, 
	QPalette, QResizeEvent, 
	QStandardItem, QStandardItemModel
)
from PyQt5.QtWidgets import (
	QAbstractItemView, QComboBox, QGridLayout, QHeaderView, 
	QLineEdit, QListView,
	QPushButton, QStyle, QStyledItemDelegate, 
	QStyleOptionViewItem, QTableView, QWidget
)
from typing import Callable, Dict, Optional

from Utils.FuriganaManager import Dictionary, Term
from Utils.Navigation import NavigationManager

class DicModel(QStandardItemModel): 

	COLUMNS = ["ID", "Japanese", "Kana", "Division0", "Division1", "Type", "Priority"]

	def __init__(self, parent: Optional[QWidget] = None): 
		super().__init__(0, len(self.COLUMNS), parent)
		self.setHorizontalHeaderLabels(self.COLUMNS)
		self._id_to_row: Dict[int, int] = {}

	def append_row(self, user_id: int, term: Term) -> int: 
		self._id_to_row[user_id] = self.rowCount()

		row = [
			QStandardItem(str(user_id)), QStandardItem(term.jp), QStandardItem(term.kana), 
			QStandardItem(term.div0), QStandardItem(term.div1), QStandardItem(term.term_type), 
			QStandardItem(str(term.pri))
		]

		for i in range(len(row)): 
			row[i].setFlags(Qt.ItemFlag(row[i].flags() & ~Qt.ItemFlag.ItemIsEditable))
		self.appendRow(row)
		return user_id
	
	def remove_row_by_id(self, user_id: int) -> bool: 
		row_idx = self._id_to_row.get(user_id, None)
		if row_idx is None: 
			return False
		try:
			self.removeRow(row_idx)
		finally:
			self._id_to_row.pop(user_id)
			for uid in self._id_to_row.keys(): 
				if self._id_to_row[uid] > row_idx: 
					self._id_to_row[uid] -= 1
		return True
	
	def update_by_Dictionary(self, dic: Dictionary) -> None: 
		self.setRowCount(0)
		self._id_to_row.clear()
		for i, idx in enumerate(dic.dic.index): 
			term = dic.get_term(idx)
			self._id_to_row[idx] = i

			row = [
				QStandardItem(str(idx)), QStandardItem(term.jp), QStandardItem(term.kana), 
				QStandardItem(term.div0), QStandardItem(term.div1), QStandardItem(term.term_type), 
				QStandardItem(str(term.pri))
			]

			for j in range(len(row)): 
				row[j].setFlags(Qt.ItemFlag(row[j].flags() & ~Qt.ItemFlag.ItemIsEditable))
			self.appendRow(row)

	
class DicViewer(QWidget): 

	def __init__(self, dic_path: str, parent: Optional[QWidget] = None): 
		super().__init__(parent)
		self.dic_path = dic_path
		self.model = DicModel(self)
		self.table_view = QTableView(self)
		self.dic = Dictionary(dic_path)
		self.current_dic = self.dic.copy()

		self.model.update_by_Dictionary(self.dic)
		self.table_view.setModel(self.model)

		horizontal_header = self.table_view.horizontalHeader()
		if horizontal_header is not None: 
			for col in range(self.model.columnCount()): 
				horizontal_header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
		vertical_header = self.table_view.verticalHeader()
		if vertical_header is not None: 
			vertical_header.setVisible(False)
		self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

		layout = QGridLayout(self)
		layout.addWidget(self.table_view, 0, 0)
		self.setLayout(layout)

		self._fixed_cols = [0, 5, 6]
		self._elastic_cols = [1, 2, 3, 4]
		self._min_widths = [0, 0, 0, 0, 0, 0, 0]
		self.set_column_modes()

	def append_term(self, term: Term) -> Optional[int]: 
		user_id = self.dic.append(term)
		if user_id is None: 
			return None
		else:
			user_id = self.model.append_row(user_id, term)
			return user_id
	
	def remove_term_by_id(self, user_id: int) -> bool: 
		if self.model.remove_row_by_id(user_id): 
			self.dic.remove(user_id)
			return True
		else: 
			return False
		
	def find_view(self, part: str, label: str) -> None: 
		self.current_dic = self.dic.find(part, label)
		self.model.update_by_Dictionary(self.current_dic)

	def save(self) -> None: 
		self.dic.save()

	def set_column_modes(self) -> None: 
		self.table_view.resizeColumnsToContents()
		header = self.table_view.horizontalHeader()
		if header is not None: 
			for col in range(self.model.columnCount()): 
				width = header.sectionSize(col)
				self._min_widths[col] = width

				self.table_view.setColumnWidth(col, width)
		self.table_view.setMinimumWidth(sum(self._min_widths))

	def resizeEvent(self, event: Optional[QResizeEvent]) -> None: 
		super().resizeEvent(event)
		if len(self._elastic_cols) == 0: 
			return
		
		header = self.table_view.horizontalHeader()
		viewport = self.table_view.viewport()
		if header is not None and viewport is not None:
			total_width = viewport.width()
			fixed_width = sum(self.table_view.columnWidth(col) for col in self._fixed_cols)
			elastic_width = total_width - fixed_width
			elastic_count = len(self._elastic_cols)
			if elastic_width < 0: 
				return
			
			base_width = elastic_width // elastic_count
			remainder = elastic_width % elastic_count
			for i, col in enumerate(self._elastic_cols): 
				width = base_width + (1 if i < remainder else 0)
				final_midth = max(width, self._min_widths[col])
				self.table_view.setColumnWidth(col, final_midth)

	def merge(self, dic: pd.DataFrame) -> None: 
		dic = Dictionary.check(dic)
		for _, row in dic.iterrows(): 
			term = Term(
				row["Japanese"], row["Kana"], row["Division0"], 
				row["Division1"], row["Type"], int(row["Priority"])
			)
			if not self.dic.is_exists(term): 
				self.append_term(term)


class CustomButton(QPushButton): 

	def __init__(self, row: int, col: int, text: str = "", 
			nav_manager: Optional[NavigationManager] = None, 
			parent: Optional[QWidget] = None
		): 
		super().__init__(text, parent)
		self.row = row
		self.col = col
		self._nav_manager = nav_manager
		if self._nav_manager is not None: 
			self._nav_manager.register(self)
		self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

		self.on_click = lambda: None
		self.clicked.connect(self.on_click)
		self.clicked.connect(self.clearFocus)

		self.default_style = (
			"QPushButton { \n"
			"	border: 0.2px solid white; \n"
			"	border-radius: 5px; \n"
			"	padding: 2px; \n"
			"	background-color: white; \n"
			"	color: black; \n"
			"}"
		)
		self.focused_style = (
			"QPushButton { \n"
			"	border: 0.2px solid white; \n"
			"	border-radius: 5px; \n"
			"	padding: 2px; \n"
			"	background-color: #0060E4; \n"
			"	color: white; \n"
			"}"
		)
		self.setStyleSheet(self.default_style)

	def keyPressEvent(self, event: QKeyEvent) -> None: 
		if self._nav_manager is not None and event.key() in (
			Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right
		): 
			dx, dy = {
				Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1), 
				Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0)
			}[Qt.Key(event.key())]
			self._nav_manager.navigate(self, dx, dy)
			return None
		if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return): 
			self.on_click()
			return None
		super().keyPressEvent(event)

	def focusInEvent(self, event: QFocusEvent) -> None: 
		self.setStyleSheet(self.focused_style)
		super().focusInEvent(event)

	def focusOutEvent(self, event: QFocusEvent) -> None: 
		self.setStyleSheet(self.default_style)
		super().focusOutEvent(event)

	def setCursorToEdge(self, dx: int) -> None: 
		pass

	def set_on_click(self, func: Callable[[], None]) -> None: 
		self.clicked.disconnect(self.on_click)
		self.on_click = func
		self.clicked.connect(self.on_click)

class CustomLineEdit(QLineEdit): 

	def __init__(self, row: int, col: int, placeholder: str = "", 
			nav_manager: Optional[NavigationManager] = None, 
			parent: Optional[QWidget] = None
		): 
		super().__init__(parent)
		self.row = row
		self.col = col
		self._nav_manager = nav_manager
		if self._nav_manager is not None:
			self._nav_manager.register(self)
		self.setPlaceholderText(placeholder)

		self.on_return = lambda: None
		self.returnPressed.connect(self.on_return)

	def keyPressEvent(self, event: QKeyEvent) -> None: 
		cursor_pos = self.cursorPosition()

		if self._nav_manager is not None: 
			if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down): 
				dx, dy = {Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}[Qt.Key(event.key())]
				self._nav_manager.navigate(self, dx, dy)
				return None
			else:
				if event.key() == Qt.Key.Key_Left and cursor_pos == 0: 
					self._nav_manager.navigate(self, -1, 0)
					return None
				elif event.key() == Qt.Key.Key_Right and cursor_pos == len(self.text()): 
					self._nav_manager.navigate(self, 1, 0)
					return None
		super().keyPressEvent(event)

	def setCursorToEdge(self, dx: int) -> None: 
		if dx <= 0: 
			self.setCursorPosition(len(self.text()))
		else: 
			self.setCursorPosition(0)

	def set_on_return(self, func: Callable[[], None]) -> None: 
		self.returnPressed.disconnect(self.on_return)
		self.on_return = func
		self.returnPressed.connect(self.on_return)

class FullWidthDelegate(QStyledItemDelegate): 

	def __init__(self, parent: Optional[QObject] = None): 
		super().__init__(parent)
		self.horizontal_margin = 10
		self.vertical_margin = 3
		self.icon_size = 24
		self.icon_spacing = 5

		self.listView: CListView = parent # type: ignore
		self.comboBox: CustomComboBox = self.listView.comboBox if self.listView is not None else None

	def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize: 
		value = index.data(Qt.ItemDataRole.DisplayRole)
		text = str(value)
		fm = QFontMetrics(option.font)

		textWidth = fm.horizontalAdvance(text)
		textHeight = fm.height()

		maxWidth = textWidth if self.listView is None else self.listView.getMaxItemWidth()

		width = maxWidth + 2 * self.horizontal_margin
		height = textHeight + 2 * self.vertical_margin

		if index.data(Qt.ItemDataRole.DecorationRole) is not None: 
			width += self.icon_size + self.icon_spacing
		
		return QSize(width, height)
	
	def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None: 
		opt = QStyleOptionViewItem(option)
		self.initStyleOption(opt, index)
		opt.textElideMode = Qt.TextElideMode.ElideNone

		hbar = self.listView.horizontalScrollBar() if self.listView is not None else None
		hbar_value = hbar.value() if hbar is not None else 0
		maxWidth = self.listView.getMaxItemWidth() if self.listView is not None else opt.rect.width()
		comboBoxWidth = self.comboBox.width() if self.comboBox is not None else 0

		backRect = QRect(opt.rect)
		backRect.setWidth(max(maxWidth, comboBoxWidth))
		backRect.adjust(hbar_value, 0, hbar_value, 0)
		if opt.state & QStyle.StateFlag.State_Selected: 
			painter.fillRect(backRect, opt.palette.highlight())

		cg = QPalette.ColorGroup.Normal if (opt.state & QStyle.StateFlag.State_Enabled) else QPalette.ColorGroup.Disabled
		if opt.state & QStyle.StateFlag.State_Selected: 
			painter.setPen(opt.palette.color(cg, QPalette.ColorRole.HighlightedText))
		else: 
			painter.setPen(opt.palette.color(cg, QPalette.ColorRole.Text))

		textRect = QRect(opt.rect)
		textRect.setWidth(maxWidth)
		textRect.adjust(self.horizontal_margin, self.vertical_margin, -self.horizontal_margin, -self.vertical_margin)

		if opt.icon is not None: 
			iconRect = QRect(textRect.left() + self.horizontal_margin, textRect.top() + self.vertical_margin, self.icon_size, self.icon_size)
			opt.icon.paint(painter, iconRect)
			textRect.setRight(textRect.right() + self.icon_spacing)

		painter.setFont(option.font)
		painter.drawText(textRect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, opt.text)


class CListView(QListView): 

	def __init__(self, parent: Optional[QWidget] = None): 
		super().__init__(parent)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

		self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

		self.setTextElideMode(Qt.TextElideMode.ElideNone)

		self.setMovement(QListView.Movement.Static)
		self.setWrapping(False)
		self.setResizeMode(QListView.ResizeMode.Adjust)
		viewport = self.viewport()
		if viewport is not None: 
			viewport.setAttribute(Qt.WidgetAttribute.WA_StaticContents)

		self.maxItemWidth = 0

		self.comboBox: CustomComboBox = parent
		self.delegate = FullWidthDelegate(self)

		self.keyScrollStep = 20

	def resetMaxItemWidth(self) -> None: 
		self.maxItemWidth = self.recalculateMaxItemWidth()
	
	def getMaxItemWidth(self) -> int: 
		return self.maxItemWidth
	
	def updateGeometries(self) -> None: 
		hbar = self.horizontalScrollBar()
		hBarValue = hbar.value() if hbar is not None else 0
		super().updateGeometries()
		
		viewport = self.viewport()
		if hbar is not None: 
			contentWidth = self.recalculateMaxItemWidth()
			viewportWidth = viewport.width() if viewport is not None else 0
			hbar.setRange(0, max(0, contentWidth - viewportWidth))
			hbar.setPageStep(viewportWidth)

			hbar.setValue(hBarValue)

		if viewport is not None: 
			viewport.update()

	def visualRect(self, index: QModelIndex) -> QRect: 
		rect = super().visualRect(index)
		if rect.isValid(): 
			maxWidth = self.getMaxItemWidth()
			comboBoxWidth = self.comboBox.width() if self.comboBox is not None else 0
			rect.setWidth(max(maxWidth, comboBoxWidth))

		return rect
	
	def recalculateMaxItemWidth(self) -> int: 
		maxWidth = 0
		model = self.model()
		if model is not None: 
			fm = QFontMetrics(self.font())

			for row in range(model.rowCount()): 
				index = model.index(row, 0)
				text = str(index.data(Qt.ItemDataRole.DisplayRole))
				textWidth = fm.horizontalAdvance(text)
				itemWidth = textWidth + 2 * self.delegate.horizontal_margin
				if index.data(Qt.ItemDataRole.DecorationRole) is not None: 
					itemWidth += self.delegate.icon_size + self.delegate.icon_spacing

				maxWidth = max(maxWidth, itemWidth)
		
		return maxWidth
	
	def keyPressEvent(self, event: QKeyEvent) -> None: 
		combo = self.comboBox
		if combo is not None: 
			model = self.model()
			if model is not None:
				if event.key() == Qt.Key.Key_Up: 
					self.setCurrentIndex(model.index((self.currentIndex().row() - 1) % combo.count(), 0))
					return
				elif event.key() == Qt.Key.Key_Down: 
					self.setCurrentIndex(model.index((self.currentIndex().row() + 1) % combo.count(), 0))
					return
				elif event.key() == Qt.Key.Key_Left: 
					logging.info((
						"[CListView.keyPressEvent] [Key_Left] pressed. "
					))
					hbar = self.horizontalScrollBar()
					if hbar is not None:
						hbar.setValue(max(hbar.minimum(), hbar.value() - self.keyScrollStep))
					event.accept()
					return
				elif event.key() == Qt.Key.Key_Right: 
					logging.info((
						"[CListView.keyPressEvent] [Key_Right] pressed. "
					))
					hbar = self.horizontalScrollBar()
					if hbar is not None:
						hbar.setValue(min(hbar.maximum(), hbar.value() + self.keyScrollStep))
					event.accept()
					return
		super().keyPressEvent(event)


class CustomComboBox(QComboBox): 

	def __init__(self, row: int, col: int, editable: bool = False, 
			placeholder: str = "", nav_manager: Optional[NavigationManager] = None, 
			parent: Optional[QWidget] = None
		): 
		super().__init__(parent)
		self.row = row
		self.col = col
		self._nav_manager = nav_manager
		if self._nav_manager is not None: 
			self._nav_manager.register(self)
		self.user_selected = False

		self.setPlaceholderText(placeholder)
		if editable: 
			self.setEditable(True)
			line_edit = self.lineEdit()
			if line_edit is not None: 
				line_edit.setReadOnly(False)
				line_edit.removeEventFilter(self)
				line_edit.installEventFilter(self)
		else: 
			self.setEditable(False)

		self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
		self.listView = CListView(self)
		self.delegate = self.listView.delegate
		self.setView(self.listView)
		self.setItemDelegate(self.delegate)


		model = self.model()
		if model is not None: 
			model.layoutChanged.connect(self.listView.resetMaxItemWidth)


	def keyPressEvent(self, event: QKeyEvent) -> None: 

		def horizontal_move(dx: int) -> bool: 
			if self._nav_manager is not None:
				if self.isEditable(): 
					line_edit = self.lineEdit()
					if line_edit is not None: 
						if dx < 0 and line_edit.cursorPosition() == 0: 
							return self._nav_manager.navigate(self, -1, 0)
						elif dx > 0 and line_edit.cursorPosition() == len(self.currentText()): 
							return self._nav_manager.navigate(self, 1, 0)
						else: 
							line_edit.setCursorPosition(line_edit.cursorPosition() + dx)
							return True
					return False
				else: 
					return self._nav_manager.navigate(self, dx, 0)
			else: 
				return False

		if self._nav_manager is not None: 
			if event.key() == Qt.Key.Key_Up: 
				if self.user_selected: 
					if self.count() == 0: 
						logging.debug((
							"[CustomComboBox.keyPressEvent] [Key_Up] "
							"self.count() == 0"
						))
						return None
					logging.debug((
						"[CustomComboBox.keyPressEvent] [Key_Up] "
						"self.currentIndex(): {}, self.count(): {}, result: {}"
					).format(self.currentIndex(), self.count(), (self.currentIndex() - 1) % self.count()))
					self.setCurrentIndex((self.currentIndex() - 1) % self.count())
					logging.debug((
						"[CustomComboBox.keyPressEvent] [Key_Up] "
						"self.currentIndex(): {}"
					).format(self.currentIndex()))
					return None
				else: 
					self._nav_manager.navigate(self, 0, -1)
					return None
			elif event.key() == Qt.Key.Key_Down: 
				if self.user_selected: 
					if self.count() == 0: 
						logging.debug((
							"[CustomComboBox.keyPressEvent] [Key_Down] "
							"self.count() == 0"
						))
						return None
					logging.debug((
						"[CustomComboBox.keyPressEvent] [Key_Down] "
						"self.currentIndex(): {}, self.count(): {}, result: {}"
					).format(self.currentIndex(), self.count(), (self.currentIndex() + 1) % self.count()))
					self.setCurrentIndex((self.currentIndex() + 1) % self.count())
					logging.debug((
						"[CustomComboBox.keyPressEvent] [Key_Down] "
						"self.currentIndex(): {}"
					).format(self.currentIndex()))
					return None
				else: 
					self._nav_manager.navigate(self, 0, 1)
					return None
			elif event.key() == Qt.Key.Key_Left: 
				horizontal_move(-1)
				return None
			elif event.key() == Qt.Key.Key_Right: 
				horizontal_move(1)
				return None
			elif event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return): 
				if self.user_selected: 
					self.user_selected = False
					self.hidePopup()
				else: 
					self.user_selected = True
					self.showPopup()
				return None
		super().keyPressEvent(event)

	def setCursorToEdge(self, dx: int) -> None: 
		if self.isEditable(): 
			line_edit = self.lineEdit()
			if line_edit is not None: 
				line_edit.selectAll()
				line_edit.setFocus()
				if dx <= 0: 
					line_edit.setCursorPosition(len(self.currentText()))
				else: 
					line_edit.setCursorPosition(0)

	def focusInEvent(self, event: QFocusEvent) -> None: 
		self.user_selected = False
		super().focusInEvent(event)
		self.hidePopup()

	def showPopup(self) -> None: 
		view = self.listView
		if view is not None: 
			super().showPopup()

			view.resetMaxItemWidth()
			popup = view.parentWidget()
			if popup is not None: 
				popup.setMaximumWidth(self.width())
				popup.setMinimumWidth(self.width())

				view.updateGeometry()

		else: 
			super().showPopup()
				

if __name__ == "__main__": 
	pass