from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class ProfilePage(QWidget):
    def __init__(self):
        super().__init__()

        title = QLabel("Profile")
        title.setObjectName("TitleLabel")

        self.name_label = QLabel("")
        self.name_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addSpacing(30)
        layout.addWidget(self.name_label)
        layout.addStretch()
        self.setLayout(layout)

    def set_user(self, email):
        name_part = email.split("@")[0]
        display_name = name_part.replace(".", " ").replace("_", " ").title()
        self.name_label.setText(display_name)