import logging
import json
import os
import pandas as pd
import sys

from pathlib import Path
from PyQt5.QtWidgets import (
	QAction, QApplication, QComboBox, QFileDialog, QGridLayout, QLabel, 
	QMainWindow, QMenu, QPushButton, QStackedWidget, QTextEdit, QWidget
)
from typing import Callable, Dict, List, Optional

from Utils.DocxGenerator import DocxGenerator
from Utils.FAWidgets import CustomButton, CustomComboBox, CustomLineEdit, DicViewer
from Utils.FontManager import FontSettingsWindow
from Utils.FuriganaManager import (
	AutoDivisionChoiceOverflowError, AutoDivisionDisabledError, Term, Token0, Token1, Token2
)
from Utils.Navigation import NavigationManager

class FindWindow(QWidget): 

	def __init__(self, dic_path: str, parent: Optional[QWidget] = None): 
		super().__init__(parent)

		layout = QGridLayout(self)
		self._nav_manager = NavigationManager()
		self.part_input = CustomLineEdit(0, 0, 
			"Please enter the part to find. ", self._nav_manager, self
		)
		self.find_button = CustomButton(0, 1, "Find", self._nav_manager, self)
		self.del_index_box = CustomLineEdit(1, 0, 
			"Please enter the ID to delete. ", self._nav_manager, self
		)
		self.del_button = CustomButton(1, 1, "Delete", self._nav_manager, self)
		self.dic_viewer = DicViewer(dic_path, self)
		self.info = QTextEdit("", self)

		self.info.setReadOnly(True)

		layout.addWidget(self.part_input, 0, 0)
		layout.addWidget(self.find_button, 0, 1)
		layout.addWidget(self.del_index_box, 1, 0)
		layout.addWidget(self.del_button, 1, 1)
		layout.addWidget(self.dic_viewer, 2, 0, 2, 2)
		layout.addWidget(self.info, 4, 0, 1, 2)
		self.setLayout(layout)

		self.part_input.set_on_return(self.find_func)
		self.find_button.set_on_click(self.find_func)
		self.del_index_box.set_on_return(self.del_func)
		self.del_button.set_on_click(self.del_func)

	def find_func(self) -> None: 
		part = self.part_input.text()
		self.dic_viewer.find_view(part)

	def del_func(self) -> None: 
		index = self.del_index_box.text()
		if index.isdigit(): 
			user_id = int(index)
			if self.dic_viewer.remove_term_by_id(user_id): 
				self.info.setText(f"Term with ID {user_id} has been deleted. ")
				self.dic_viewer.save()
			else: 
				self.info.setText(f"No term with ID {user_id} found. ")
		else:
			self.info.setText("Invalid ID. Please enter a valid ID. ")
			self.del_index_box.setText("")
			self.del_index_box.setFocus()

	def append_term(self, term: Term) -> Optional[int]: 
		user_id = self.dic_viewer.append_term(term)
		if user_id is None: 
			self.info.setText("Failed to add the term. It may already exist in the dictionary. ")
			return None
		else: 
			self.info.setText(f"Term with ID {user_id} has been added. ")
			return user_id
	
class NewTermWindow(QWidget): 

	def __init__(self, parent: Optional[QWidget] = None): 
		super().__init__(parent)

		layout = QGridLayout(self)
		self._nav_manager = NavigationManager()

		self.jp_input = CustomLineEdit(0, 0, "Japanese", self._nav_manager, self)
		self.kana_input = CustomLineEdit(1, 0, "Kana", self._nav_manager, self)
		self.div0_input = CustomLineEdit(0, 1, "Division0", self._nav_manager, self)
		self.div1_input = CustomLineEdit(1, 1, "Division1", self._nav_manager, self)
		self.type_input = CustomComboBox(2, 0, False, "Type", self._nav_manager, self)
		self.pri_input = CustomComboBox(2, 1, False, "Priority", self._nav_manager, self)
		self.auto_div_selections = CustomComboBox(3, 0, False, "Auto Divide Selections", self._nav_manager, self)
		self.apply_button = CustomButton(4, 0, "Apply Auto Division", self._nav_manager, self)
		self.add_button = CustomButton(5, 0, "Add", self._nav_manager, self)
		self.info = QTextEdit("", self)

		self.type_input.addItems(["名詞", "五段", "上下", "形容", "英語", "固有", "サ変", "カ変"])
		self.pri_input.addItems(["0", "1", "2"])
		self.info.setReadOnly(True)

		layout.addWidget(self.jp_input, 0, 0)
		layout.addWidget(self.kana_input, 1, 0)
		layout.addWidget(self.div0_input, 0, 1)
		layout.addWidget(self.div1_input, 1, 1)
		layout.addWidget(self.type_input, 2, 0)
		layout.addWidget(self.pri_input, 2, 1)
		layout.addWidget(self.auto_div_selections, 3, 0, 1, 2)
		layout.addWidget(self.apply_button, 4, 0, 1, 2)
		layout.addWidget(self.add_button, 5, 0, 1, 2)
		layout.addWidget(self.info, 6, 0, 1, 2)

		self.setLayout(layout)

		self.current_auto_div_results = []

		self.jp_input.textEdited.connect(self.auto_divide)
		self.kana_input.textEdited.connect(self.auto_divide)
		self.div0_input.textEdited.connect(self.auto_divide)
		self.div1_input.textEdited.connect(self.auto_divide)
		self.type_input.currentTextChanged.connect(self.auto_divide)
		self.apply_button.set_on_click(self.apply_auto_division)

	def auto_divide(self) -> None: 
		jp = self.jp_input.text()
		kana = self.kana_input.text()
		div0 = self.div0_input.text()
		div1 = self.div1_input.text()
		term_type = self.type_input.currentText()
		try:
			result_list = Term.auto_divide(jp, kana, term_type)
		except (AutoDivisionChoiceOverflowError, AutoDivisionDisabledError) as e:
			self.info.setText(str(e))
			self.current_auto_div_results = []
			self.auto_div_selections.clear()
			return
		except Exception as e:
			logging.error((
				"[NewTermWindow.auto_divide] Unexpected error during auto division. \n"
				"Error message: {}"
			).format(str(e)))
			raise e
		if result_list is None: 
			return
		valid_result_list = [
			result for result in result_list
			if result[2].startswith(div0) and result[3].startswith(div1)
		]
		self.current_auto_div_results = valid_result_list
		self.auto_div_selections.clear()
		self.auto_div_selections.addItems([
			"Jp: {}, Kn: {}, D0: {}, D1: {}".format(
				result[0], result[1], result[2], result[3]
			) for result in valid_result_list
		])
		self.info.setText((
			"Division of Input: Japanese: {}, Kana: {}, Type: {} is updated. "
			"{} valid auto division results found. "
		).format(jp, kana, term_type, len(valid_result_list)))

	def apply_auto_division(self) -> None: 
		idx = self.auto_div_selections.currentIndex()
		if idx < 0 or idx >= len(self.current_auto_div_results): 
			logging.warning((
				"[NewTermWindow.apply_auto_division] "
				"Invalid auto division selection index: {}, where the range is [0, {}]. "
			).format(idx, len(self.current_auto_div_results) - 1))
			return None
		result = self.current_auto_div_results[idx]
		self.jp_input.setText(result[0])
		self.kana_input.setText(result[1])
		self.div0_input.setText(result[2])
		self.div1_input.setText(result[3])

	def add_term(self) -> Optional[Term]: 
		jp = self.jp_input.text()
		kana = self.kana_input.text()
		div0 = self.div0_input.text()
		div1 = self.div1_input.text()
		term_type = self.type_input.currentText()
		pri = int(self.pri_input.currentText())
		try:
			new_term = Term(jp, kana, div0, div1, term_type, pri)
		except ValueError as e: 
			self.info.setText(str(e))
			return None
		except Exception as e: 
			logging.error((
				"[NewTermWindow.add_term] Unexpected error when creating a new term. \n"
				"jp: {}, kana: {}, div0: {}, div1: {}, term_type: {}, pri: {}. \n"
				"Error message: {}"
			).format(jp, kana, div0, div1, term_type, pri, str(e)))
			raise e
		self.info.setText("Term created successfully. ")
		return new_term
	
	def clear_inputs(self) -> None: 
		self.jp_input.setText("")
		self.kana_input.setText("")
		self.div0_input.setText("")
		self.div1_input.setText("")

		
class MainWindow(QMainWindow): 

	def __init__(self, 
			dic_path: str, text_path: str, json_path: str, 
			parent: Optional[QWidget] = None
		): 
		super().__init__(parent)
		self.setWindowTitle("Furigana Adding Tool")
		self.resize(800, 600)

		self.text_path = text_path
		self.json_path = json_path

		main_widget = QWidget(self)
		layout = QGridLayout(main_widget)
		self.setCentralWidget(main_widget)

		self.window_switch_button_layout = QGridLayout()
		self.stacked_widget = QStackedWidget(self)

		self.viewer_page_button = QPushButton("Dictionary Viewer", self)
		self.input_page_button = QPushButton("Input Text", self)
		self.output_page_button = QPushButton("Output Text", self)
		self.font_page_button = QPushButton("Font Manager", self)

		layout.addLayout(self.window_switch_button_layout, 0, 0)
		layout.addWidget(self.stacked_widget, 1, 0, 4, 1)

		self.find_window = FindWindow(dic_path, self)
		self.viewer_new_term_window = NewTermWindow(self)
		self.input_text_edit = QTextEdit("", self)
		self.output_text_edit = QTextEdit("", self)
		self.output_new_term_window = NewTermWindow(self)
		self.font_settings_window = FontSettingsWindow(
			self.get_config("last_font_name"), 
			int(self.get_config("last_font_size")) if self.get_config("last_font_size").isdigit() else None, 
			int(self.get_config("last_columns")) if self.get_config("last_columns").isdigit() else None, 
			self
		)

		self.add_page(0, 0, self.viewer_page_button, self.viewer_page())
		self.add_page(0, 1, self.input_page_button, self.input_page())
		self.add_page(0, 2, self.output_page_button, self.output_page())
		self.add_page(0, 3, self.font_page_button, self.font_settings_window)

		self.input_text_edit.setPlainText(self.read_input_text())

		self.input_text_edit.setReadOnly(False)
		self.output_text_edit.setReadOnly(True)
		self.input_text_edit.textChanged.connect(self.save_input_text)
		self.output_page_button.clicked.connect(self.update_output_text)
		self.font_settings_window.set_save_config_func(self.save_font_configs)

		menu_bar = self.menuBar()
		if menu_bar is not None:
			file_menu = menu_bar.addMenu("&File")
			if file_menu is not None: 
				self._add_action(
					file_menu, "Read Text from .txt File", "Ctrl+O", 
					"Read input text from a .txt file. ", self.read_txt_func, True
				)
				self._add_action(
					file_menu, "Save as Docx (Type 0)", "Ctrl+0", 
					"Save the output text as a docx file with type 0 formatting. ", 
					self.save_func_gen(self.output_docx_0, "docx")
				)
				self._add_action(
					file_menu, "Save as Docx (Type 1)", "Ctrl+1", 
					"Save the output text as a docx file with type 1 formatting. ", 
					self.save_func_gen(self.output_docx_1, "docx")
				)
				self._add_action(
					file_menu, "Save as Docx (Type 2)", "Ctrl+2", 
					"Save the output text as a docx file with type 2 formatting. ", 
					self.save_func_gen(self.output_docx_2, "docx")
				)
				self._add_action(
					file_menu, "Save as Text", "Ctrl+S", 
					"Save the output text as a plain text file. ", 
					self.save_func_gen(self.output_txt, "txt"), True
				)
				self._add_action(
					file_menu, "Merge new dic", "Ctrl+M", 
					"Merge a data file into current local datas. ", self.merge
				)

	def _add_action(self, 
			menu: QMenu, text: str, quick_key: str, status_tip: str, 
			connect_func: Callable[[], None], is_separator: bool = False
		) -> None: 
		action = QAction(text, self)
		if action is not None:
			action.setShortcut(quick_key)
			action.setStatusTip(status_tip)
			action.triggered.connect(connect_func)
			menu.addAction(action)
			if is_separator: 
				menu.addSeparator()


	def add_page(self, row: int, col: int, button_widget: QPushButton, page_widget: QWidget) -> None: 
		button_widget.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(page_widget))
		self.window_switch_button_layout.addWidget(button_widget, row, col)
		self.stacked_widget.addWidget(page_widget)

	def viewer_page(self, parent: Optional[QWidget] = None) -> QWidget: 
		widget = QWidget(parent)
		layout = QGridLayout(widget)
		
		layout.addWidget(self.find_window, 0, 0, 1, 3)
		layout.addWidget(self.viewer_new_term_window, 0, 3, 1, 1)

		self.viewer_new_term_window.add_button.set_on_click(
			self.add_new_term(self.viewer_new_term_window)
		)

		widget.setLayout(layout)
		return widget
	
	def input_page(self, parent: Optional[QWidget] = None) -> QWidget: 
		widget = QWidget(parent)
		layout = QGridLayout(widget)

		layout.addWidget(self.input_text_edit, 0, 0)

		widget.setLayout(layout)
		return widget
	
	def output_page(self, parent: Optional[QWidget] = None) -> QWidget: 
		widget = QWidget(parent)
		layout = QGridLayout(widget)

		layout.addWidget(self.output_text_edit, 0, 0)
		layout.addWidget(self.output_new_term_window, 0, 1)

		self.output_new_term_window.add_button.set_on_click(
			self.add_new_term(self.output_new_term_window)
		)

		widget.setLayout(layout)
		return widget

	
	def add_new_term(self, new_term_widget: NewTermWindow) -> Callable[[], None]: 
		def add_term_func() -> None: 
			new_term = new_term_widget.add_term()
			if new_term is not None: 
				self.find_window.append_term(new_term)
				self.find_window.dic_viewer.save()
				new_term_widget.clear_inputs()
				new_term_widget.jp_input.setFocus()
				new_term_widget.jp_input.setCursorPosition(0)
		return add_term_func

	def output_text(self, text: str) -> str: 
		text_list = text.split("\n")
		result = "<p>"
		for line in text_list: 
			token_list: List[Token2] = self.find_window.dic_viewer.dic.line_to_tokens2(line)
			for token in token_list: 
				if token.kana is None: 
					if token.is_skip: 
						result += token.jp
					else: 
						for c in token.jp: 
							if Term.is_cjk_unified(c) or Term.is_alpha_num(c): 
								result += "<span style=\"color:red;\">{}</span>".format(c)
							else: 
								result += c
				else: 
					result += "<span style=\"color:blue;\">{}({})</span>".format(token.jp, token.kana)
			result += "<br>"
		result += "</p>"
		return result
	
	def output_txt(self, text: str, output_path: str) -> None: 
		text_list = text.split("\n")
		result = ""
		for line in text_list: 
			token_list: List[Token2] = self.find_window.dic_viewer.dic.line_to_tokens2(line)
			for token in token_list: 
				if token.kana is None: 
					result += token.jp
				else: 
					result += "{}({})".format(token.jp, token.kana)
			result += "\n"
		with open(output_path, "w", encoding="utf-8") as f: 
			f.write(result)
	
	def output_docx_0(self, text: str, output_path: str) -> None: 
		docx_gen = DocxGenerator()
		docx_gen._set_font(
			self.font_settings_window.get_current_font_name(), 
			self.font_settings_window.get_current_font_size()
		)
		docx_gen.set_columns(self.font_settings_window.get_current_columns())
		text_list = text.split("\n")
		for line in text_list: 
			token_list: List[Token0] = self.find_window.dic_viewer.dic.line_to_tokens0(line)
			for token in token_list: 
				if token.kana is None: 
					docx_gen.add_run(token.jp)
				else: 
					docx_gen.add_field0(token.jp, token.kana, token.alignment)
			docx_gen.add_paragraph()
		docx_gen.save(output_path)

	def output_docx_1(self, text: str, output_path: str) -> None: 
		docx_gen = DocxGenerator()
		docx_gen._set_font(
			self.font_settings_window.get_current_font_name(), 
			self.font_settings_window.get_current_font_size()
		)
		docx_gen.set_columns(self.font_settings_window.get_current_columns())
		text_list = text.split("\n")
		for line in text_list: 
			token_list: List[Token1] = self.find_window.dic_viewer.dic.line_to_tokens1(line)
			for token in token_list: 
				if token.down_kana is None: 
					if token.up_kana is None: 
						docx_gen.add_run(token.jp)
					else: 
						docx_gen.add_field1(token.jp, token.up_kana, "")
				elif token.up_kana is not None: 
					docx_gen.add_field1(token.jp, token.up_kana, token.down_kana)
			docx_gen.add_paragraph()
		docx_gen.save(output_path)

	def output_docx_2(self, text: str, output_path: str) -> None: 
		docx_gen = DocxGenerator()
		docx_gen._set_font(
			self.font_settings_window.get_current_font_name(), 
			self.font_settings_window.get_current_font_size()
		)
		docx_gen.set_columns(self.font_settings_window.get_current_columns())
		text_list = text.split("\n")
		for line in text_list: 
			token_list: List[Token2] = self.find_window.dic_viewer.dic.line_to_tokens2(line)
			for token in token_list: 
				if token.kana is None: 
					docx_gen.add_run(token.jp)
				else: 
					docx_gen.add_run("{}({})".format(token.jp, token.kana))
			docx_gen.add_paragraph()
		docx_gen.save(output_path)
	
	def update_output_text(self) -> None: 
		input_text = self.input_text_edit.toPlainText()
		output_text = self.output_text(input_text)
		self.output_text_edit.setHtml(output_text)

	def save_func_gen(self, output_func: Callable[[str, str], None], file_type_key: str) -> Callable[[], None]: 
		file_type = {
			"txt": "Text Files (*.txt)",
			"docx": "Word Documents (*.docx)"
		}

		def save_func() -> None: 
			text = self.input_text_edit.toPlainText()
			options = QFileDialog.Options()
			file_name, _ = QFileDialog.getSaveFileName(
				self, "Save file", self.get_config("last_save_path"), 
				filter=file_type[file_type_key], 
				options=options
			)
			if file_name: 
				try: 
					if not file_name.endswith(".{}".format(file_type_key)): 
						file_name += ".{}".format(file_type_key)
					output_func(text, file_name)
					logging.info((
						"[MainWindow.save_func_gen] Successfully saved the output text to file: {}. "
					).format(file_name))
					self.save_config("last_save_path", os.path.dirname(file_name))
				except Exception as e: 
					logging.error((
						"[MainWindow.save_func_gen] Failed to save the output text to file: {}. \n"
						"Error message: {}"
					).format(file_name, str(e)))
					raise e
		
		return save_func

	def read_input_text(self) -> str: 
		if not os.path.exists(self.text_path): 
			with open(self.text_path, "w", encoding="utf-8") as f:
				f.write("")
		with open(self.text_path, "r", encoding="utf-8") as f: 
			return f.read()
	
	def save_input_text(self) -> None: 
		text = self.input_text_edit.toPlainText()
		with open(self.text_path, "w", encoding="utf-8") as f: 
			f.write(text)

	def get_config(self, key: str) -> str: 
		if not os.path.exists(self.json_path): 
			with open(self.json_path, "w", encoding="utf-8") as f: 
				json.dump({key: ""}, f, indent=4)
			return ""
		with open(self.json_path, "r", encoding="utf-8") as f: 
			config: dict = json.load(f)
			return config.get(key, "")
		
	def save_config(self, key: str, value: str) -> None: 
		if not os.path.exists(self.json_path): 
			with open(self.json_path, "w", encoding="utf-8") as f: 
				json.dump({key: value}, f, indent=4)
		with open(self.json_path, "r", encoding="utf-8") as f: 
			config: dict = json.load(f)
		config[key] = value
		with open(self.json_path, "w", encoding="utf-8") as f: 
			json.dump(config, f, indent=4)

	def read_txt(self, path: str) -> None: 
		if not os.path.exists(path): 
			raise FileNotFoundError(f"File not found: {path}")
		with open(path, "r", encoding="utf-8") as f: 
			self.input_text_edit.setPlainText(f.read())

	def read_txt_func(self) -> None: 
		file_type = "Text Files (*.txt)"
		options = QFileDialog.Options()
		file_name, _ = QFileDialog.getOpenFileName(
			self, "Open file", self.get_config("last_open_path"), 
			filter=file_type, 
			options=options
		)
		if file_name: 
			self.read_txt(file_name)
			self.save_config("last_open_path", os.path.dirname(file_name))

	def save_font_configs(self) -> None: 
		self.save_config(
			"last_font_name", 
			self.font_settings_window.get_current_font_name()
		)
		self.save_config(
			"last_font_size", 
			str(self.font_settings_window.get_current_font_size())
		)
		self.save_config(
			"last_columns", 
			str(self.font_settings_window.get_current_columns())
		)

	def merge(self) -> None: 
		file_type = "Data Files (*.csv; *.xlsx; *.xls; *.json; *.h5; *.pkl)"
		options = QFileDialog.Options()
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select Data File", self.get_config("last_open_path"), 
			filter=file_type, options=options
		)
		if file_path: 
			self.save_config("last_open_path", os.path.dirname(file_path))
			try: 
				suffix = Path(file_path).suffix
				match suffix: 
					case ".csv": 
						df = pd.read_csv(file_path)
					case ".txt": 
						df = pd.read_csv(file_path, sep="\t", encoding="utf-8")
					case ".xlsx" | ".xls": 
						df = pd.read_csv(file_path)
					case ".json": 
						df = pd.read_json(file_path)
					case _:
						raise ValueError((
							"File that can't be transferred to a pd.DataFrame object is chosen: {}. "
						).format(file_path))
				self.find_window.dic_viewer.merge(df)
			except Exception as e: 
				logging.error((
					"[MainWindow.merge_csv] Unexpected error happenned: {} "
					"while read data file: {}. "
				).format(str(e)), file_path)
				

			


if __name__ == "__main__": 
	logging.basicConfig(
		level=logging.DEBUG, 
		format="[%(asctime)s] %(levelname)s: %(message)s", 
		datefmt="%Y-%m-%d %H:%M:%S"
	)
	DIRPATH = os.path.dirname(os.path.abspath(__file__))
	app = QApplication(sys.argv)
	window = MainWindow(
		os.path.join(DIRPATH, "..", "src", "dictionary_test.csv"), 
		os.path.join(DIRPATH, "..", "src", "input_test.txt"), 
		os.path.join(DIRPATH, "..", "src", "config.json")
	)
	window.show()
	sys.exit(app.exec_())