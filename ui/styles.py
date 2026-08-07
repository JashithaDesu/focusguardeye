APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #dbeeff;
    color: #000000;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
}

QLabel#TitleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #0b5394;
}

QLabel#StatusLabel {
    color: #a0aec0;
    font-size: 12px;
}

QLineEdit {
    background-color: #ffffff;
    border: 1px solid #a0c4e4;
    border-radius: 6px;
    padding: 8px;
    color: #000000;
}

QLineEdit:focus {
    border: 1px solid #0b5394;
}

QPushButton {
     background-color: #0b5394;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #094879;
}

QPushButton:pressed {
    background-color: #063a63;
}

QPushButton#SecondaryButton {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0c4e4;
}

QPushButton#SecondaryButton:hover {
    background-color: #eaf4ff;;
}

QPushButton#DangerButton {
    background-color: #d93025;
    color: white;
}

QPushButton#DangerButton:hover {
    background-color: #b3261e;
}

QLabel#AlertLabel {
    color: #c0392b;
    font-weight: bold;
}

#NavBar {
    background-color: #bcdcff;
}
"""