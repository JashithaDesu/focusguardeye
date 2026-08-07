import sys
from PyQt6.QtWidgets import QApplication
from ui.app_shell import AppShell
from ui.styles import APP_STYLESHEET

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    window = AppShell()
    window.show()
    sys.exit(app.exec())