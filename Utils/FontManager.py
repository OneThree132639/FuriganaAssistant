import json
import logging
import os
import pandas as pd

from matplotlib import font_manager
from fontTools.ttLib import TTCollection, TTFont
from typing import Callable, List, Optional

from PyQt5.QtWidgets import (
	QComboBox, QGridLayout, QLabel, QLineEdit, QTextBrowser,
	QTextEdit, QWidget
)
from PyQt5.QtGui import QIntValidator

class FontManager: 

	def __init__(self): 
		font_files = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
		self.df = pd.DataFrame(font_files, columns=["path"])
		self.df["basename"] = self.df["path"].apply(os.path.basename)
		self.df["font_family"] = self.df["path"].apply(lambda p: self.extract_name(p, 1))
		self.df["font_full_name"] = self.df["path"].apply(lambda p: self.extract_name(p, 4))
		self.df["font_postscript_name"] = self.df["path"].apply(lambda p: self.extract_name(p, 6))

		self.df.drop(self.df[self.df["font_family"].str.startswith(".")].index, inplace=True)
		self.df.drop(self.df[self.df["font_full_name"].str.startswith(".")].index, inplace=True)
		self.df.drop(self.df[self.df["font_postscript_name"].str.startswith(".")].index, inplace=True)

		self.df.sort_values(by=["font_family"], inplace=True)

	def extract_name(self, font_path: str, name_id: int) -> str: 
		platform_configs = [
			(3, 1, 0x409),  # Windows, Unicode BMP (UCS-2), English (United States)
			(1, 0, 0),  # Macintosh, Roman, English
			(3, 1, 0x804),  # Windows, Unicode BMP (UCS-2), Chinese (PRC)
			(3, 10, 0x409)  # Windows, Unicode UCS-4, English (United States)
		]
		try: 
			if font_path.lower().endswith((".ttc", ".otc")): 
				collection = TTCollection(font_path)
				font_count = len(collection.fonts)

				if font_count == 0: 
					logging.warning(f"No fonts found in collection: {font_path}")
					return ""
				
				font = collection.fonts[0]
			else: 
				font = TTFont(font_path)

			name_table = font["name"]

			for plat_id, enc_id, lang_id in platform_configs: 
				name = name_table.getName(name_id, plat_id, enc_id, lang_id)
				if name: 
					try: 
						return name.toUnicode()
					except: 
						logging.warning(f"Failed to decode font name: {name}")
						return ""
					
			return ""
		except Exception as e: 
			logging.error(f"Error occurred while extracting font name: {e}")
			return ""
		
	def to_font_family_list(self) -> List[str]: 
		return self.df["font_family"].dropna().unique().tolist()
	
class RubyTextEdit(QTextBrowser): 

	def __init__(self, parent: Optional[QWidget] = None): 
		super().__init__(parent)
		self.setReadOnly(True)

	def set_ruby_html(self, html_content: str, font_name: str, font_size: int) -> None: 
		styled_html = (
			"<style>\n"
			"	ruby {\n"
			"		display: ruby;\n"
			"		ruby-position: over;\n"
			"	}\n"
			"	rt {\n"
			"		font-size: {}px;\n"
			"		font-family: {};\n"
			"	}\n"
			"	body {\n"
			"		font-size: {}px;\n"
			"		font-family: {};\n"
			"	}\n"
			"</style>\n"
			"{}"
		).format(font_size, font_name, font_size, font_name, html_content)
		self.setHtml(styled_html)

	def ruby_text(self, text: str, furigana_text: str) -> str: 
		return "<ruby>{}<rt>{}</rt></ruby>".format(text, furigana_text)
	
	
class FontSettingsWindow(QWidget): 
	def __init__(self, 
			last_font_name: Optional[str] = None, 
			last_font_size: Optional[int] = None, 
			last_columns: Optional[int] = None, 
			parent: Optional[QWidget] = None
		): 
		super().__init__(parent)
		layout = QGridLayout(self)

		self.font_manager = FontManager()

		self.font_name = QLabel("Font Name: ", self)
		self.font_size = QLabel("Font Size: ", self)
		self.font_name_box = QComboBox(self)
		self.font_size_box = QComboBox(self)
		self.columns_label = QLabel("Columns: ", self)
		self.columns_box = QComboBox(self)
		self.test_text_label = QLabel("Test Text: ", self)
		self.test_text = QLineEdit("Test Text", self)
		self.test_furigana_label = QLabel("Test Furigana: ", self)
		self.test_furigana_text = QLineEdit("Test Furigana Text", self)
		self.show_label = QLabel("Show Window: ", self)
		self.test_type_label = QLabel("Test Type: ", self)
		self.test_type_box = QComboBox(self)
		self.show_window = QTextEdit("", self)

		self.test_text.setText("例文")
		self.test_furigana_text.setText("れいぶん")
		self.show_window.setReadOnly(True)

		font_name_list = self.font_manager.to_font_family_list()
		self.font_name_box.addItems(font_name_list)
		self.font_size_box.addItems(
			[str(i) for i in range(5, 30)]
		)
		self.columns_box.addItems(
			[str(i) for i in range(1, 5)]
		)
		self.test_type_box.addItems(["0", "1", "2"])

		validator = QIntValidator(5, 100, self)
		self.font_size_box.setValidator(validator)

		if last_font_name is not None and last_font_name in font_name_list: 
			self.font_name_box.setCurrentText(last_font_name)
		else: 
			self.font_name_box.setCurrentIndex(0)
		if last_font_size is not None and 5 <= last_font_size <= 100: 
			self.font_size_box.setCurrentText(str(last_font_size))
		else:
			self.font_size_box.setCurrentText("10")
		self.font_size_box.setEditable(True)
		if last_columns is not None and 1 <= last_columns <= 4: 
			self.columns_box.setCurrentText(str(last_columns))
		else:
			self.columns_box.setCurrentIndex(0)
		self.test_type_box.setCurrentIndex(0)

		layout.addWidget(self.font_name, 0, 0)
		layout.addWidget(self.font_name_box, 0, 1)
		layout.addWidget(self.font_size, 1, 0)
		layout.addWidget(self.font_size_box, 1, 1)
		layout.addWidget(self.columns_label, 2, 0)
		layout.addWidget(self.columns_box, 2, 1)
		layout.addWidget(self.test_text_label, 3, 0)
		layout.addWidget(self.test_text, 3, 1)
		layout.addWidget(self.test_furigana_label, 4, 0)
		layout.addWidget(self.test_furigana_text, 4, 1)
		layout.addWidget(self.test_type_label, 5, 0)
		layout.addWidget(self.test_type_box, 5, 1)
		layout.addWidget(self.show_label, 0, 2)
		layout.addWidget(self.show_window, 1, 2, 5, 1)

		self.setLayout(layout)

	def update_show_window(self) -> None: 
		font_name = self.font_name_box.currentText()
		font_size = int(self.font_size_box.currentText())
		test_text = self.test_text.text()
		test_furigana_text = self.test_furigana_text.text()
		test_type = self.test_type_box.currentText()

	def get_current_font_name(self) -> str: 
		return self.font_name_box.currentText()
	
	def get_current_font_size(self) -> int: 
		return int(self.font_size_box.currentText())
	
	def get_current_columns(self) -> int: 
		return int(self.columns_box.currentText())
	
	def set_save_config_func(self, func: Callable[[], None]) -> None: 
		self.font_name_box.currentTextChanged.connect(func)
		self.font_size_box.currentTextChanged.connect(func)
		self.columns_box.currentTextChanged.connect(func)

if __name__ == "__main__": 
	DIRPATH = os.path.dirname(os.path.abspath(__file__))
	SRCPATH = os.path.realpath(os.path.join(DIRPATH, "..", "src"))

	logging.basicConfig(level=logging.ERROR, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

	'''
	font_info_list = get_system_fonts_with_info()
	font_info_list = filter_and_deduplicate(font_info_list)
	output_file = os.path.join(SRCPATH, "fonts.json")
	export_fonts(font_info_list, output_file)
	'''

	
	fm = FontManager()
	fm.df.to_csv(os.path.join(SRCPATH, "fonts.csv"), index=False, encoding="utf-8-sig")