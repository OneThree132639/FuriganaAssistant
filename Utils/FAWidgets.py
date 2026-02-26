import logging

from PyQt5.QtCore import QEvent, QModelIndex, QObject, QSize, Qt
from PyQt5.QtGui import (
	QFocusEvent, QFontMetrics, QKeyEvent, QResizeEvent, 
	QStandardItem, QStandardItemModel
)
from PyQt5.QtWidgets import (
	QAbstractItemView, QComboBox, QGridLayout, QHeaderView, QLineEdit, 
	QPushButton, QStyledItemDelegate, QStyleOptionViewItem, QTableView, QWidget
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
		
	def find_view(self, part: str) -> None: 
		self.current_dic = self.dic.find(part)
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

class PopUpKeyFilter(QObject): 

	_installed_views = set()

	def __init__(self, parent: Optional[QComboBox] = None): 
		super().__init__(parent)
		self.combo = parent
		self._view_id = id(parent.view()) if parent is not None and parent.view() is not None else None

		if self._view_id is not None: 
			logging.debug((
				"[PopUpKeyFilter] "
				"Created for view: {}, combo: {}. "
			).format(self._view_id, id(self.combo)))
			if self._view_id in PopUpKeyFilter._installed_views: 
				logging.warning((
					"[PopUpKeyFilter] "
					"View: {} already has a filter. "
				).format(self._view_id))
			PopUpKeyFilter._installed_views.add(self._view_id)
			logging.debug((
				"[PopUpKeyFilter] "
				"Current _installed_views: {}"
			).format(PopUpKeyFilter._installed_views))

	def eventFilter(self, obj: QObject, event: QEvent) -> bool: 
		if self.combo is not None and event.type() == QEvent.Type.KeyPress: 
			key_event = QKeyEvent(event) # type: ignore
			key = key_event.key()
			if key in (Qt.Key.Key_Up, Qt.Key.Key_Down): 
				self.handle_direction_key(self.combo, Qt.Key(key))
				return True
		return super().eventFilter(obj, event)

	def handle_direction_key(self, combo: QComboBox, key: Qt.Key) -> bool: 
		view = combo.view()
		if view is None or not view.isVisible(): 
			return False
		current = view.currentIndex().row()
		model = view.model()
		if model is None: 
			return False
		if current < 0:
			current = 0
		if combo.count() == 0: 
			logging.warning((
				"[PopUpKeyFilter] "
				"No items in combo, filtered. "
			))
			return False
		if key == Qt.Key.Key_Up: 
			logging.debug((
				"[PopUpKeyFilter] [Qt.Key.KeyUp] Id: {}. "
				"From {} to {}. "
			).format(self._view_id, current, (current - 1) % combo.count()))
			view.setCurrentIndex(model.index((current - 1) % combo.count(), 0))
			return True
		elif key == Qt.Key.Key_Down: 
			logging.debug((
				"[PopUpKeyFilter] [Qt.Key.KeyDown] Id: {}. "
				"From {} to {}. "
			).format(self._view_id, current, (current + 1) % combo.count()))
			view.setCurrentIndex(model.index((current + 1) % combo.count(), 0))
			return True
		return False
	
class ScrollableElideDelegate(QStyledItemDelegate): 
	def __init__(
			self, 
			parent: Optional[QWidget] = None, 
			elide_mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight, 
			enable_scroll: bool = False
		): 
		super().__init__(parent)
		self._elide_mode = elide_mode
		self._enable_scroll = enable_scroll

	def initStyleOption(self, 
			option: QStyleOptionViewItem, 
			index: QModelIndex
		) -> None:
		super().initStyleOption(option, index)
		option.textElideMode = self._elide_mode
		if self._enable_scroll: 
			option.textElideMode = Qt.TextElideMode.ElideNone

	def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize: 
		size = super().sizeHint(option, index)
		if self._enable_scroll: 
			text = index.data(Qt.ItemDataRole.DisplayRole)
			if text is not None: 
				font = option.font
				metrics = QFontMetrics(font)
				text_width = metrics.horizontalAdvance(text) + 20
				size.setWidth(max(size.width(), text_width))

		return size
		

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

		self._popup_filter_installed = False

		# self._set_delegate()

	def _set_delegate(self) -> None: 
		self._delegate = ScrollableElideDelegate(
			self, elide_mode=Qt.TextElideMode.ElideRight, enable_scroll=True
		)
		view = self.view()
		if view is not None: 
			self._apply_view_settings(view)
		else: 
			pass

	def _apply_view_settings(self, view: QAbstractItemView) -> None: 
		view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
		view.setItemDelegate(self._delegate)
		view.setMaximumWidth(600)


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
		view = self.view()
		if view is not None: 
			if not self._popup_filter_installed: 
				view.installEventFilter(PopUpKeyFilter(self))
				self._popup_filter_installed = True
				logging.debug((
					"[CustomComboBox.showPopUp] "
					"Filter installed for combo: {}. "
				).format(id(self)))

			'''
			view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
			view.setItemDelegate(self._delegate)
			view.updateGeometry()
			'''
		
		super().showPopup()
				

if __name__ == "__main__": 
	pass