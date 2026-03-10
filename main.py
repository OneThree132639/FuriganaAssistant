import logging
import os
import platform
import sys

from pathlib import Path
from PyQt5.QtWidgets import QApplication

from Utils.FAGUI import MainWindow

def get_config_dir(app_name: str) -> Path: 
	if platform.system() == "Windows": 
		return Path.home() / "AppData" / "Roaming" / app_name
	elif platform.system() == "Darwin": 
		return Path.home() / "Library" / "Application Support" / app_name
	else: 
		return Path.home() / ".config" / app_name
	
def get_resource_path() -> str: 
	try: 
		return sys._MEIPASS # type: ignore
	except Exception: 
		return os.path.dirname(os.path.abspath(__file__))

	
if __name__ == "__main__": 

	resource_dir = os.path.join(get_resource_path(), "resources")
	
	logging.basicConfig(
		level=logging.INFO, 
		format="[%(asctime)s] %(levelname)s: %(message)s", 
		datefmt="%Y-%m-%d %H:%M:%S"
	)
	
	config_dir = get_config_dir("FuriganaAssistant")
	config_dir.mkdir(parents=True, exist_ok=True)
	app = QApplication(sys.argv)
	window = MainWindow(
		str(config_dir), resource_dir
	)
	window.show()
	sys.exit(app.exec_())