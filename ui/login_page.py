from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from storage.auth import UserStore


class LoginPage(QWidget):
    login_success = pyqtSignal(str)  # emits the logged-in user's email

    def __init__(self):
        super().__init__()
        self.user_store = UserStore("focusguard.db")
        self.mode = "login"  # or "signup"

        title = QLabel("FocusGuard")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Sign in to track your posture and eye health")
        subtitle.setObjectName("StatusLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.status_label = QLabel("")
        self.status_label.setObjectName("AlertLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.primary_btn = QPushButton("Log In")
        self.primary_btn.clicked.connect(self.handle_primary_action)

        self.toggle_btn = QPushButton("Need an account? Sign up")
        self.toggle_btn.setObjectName("SecondaryButton")
        self.toggle_btn.clicked.connect(self.toggle_mode)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.status_label)
        layout.addWidget(self.primary_btn)
        layout.addWidget(self.toggle_btn)
        layout.addStretch()

        centered = QHBoxLayout()
        centered.addStretch()
        centered.addLayout(layout)
        centered.addStretch()
        self.setLayout(centered)

    def toggle_mode(self):
        self.status_label.setText("")
        if self.mode == "login":
            self.mode = "signup"
            self.primary_btn.setText("Create Account")
            self.toggle_btn.setText("Already have an account? Log in")
        else:
            self.mode = "login"
            self.primary_btn.setText("Log In")
            self.toggle_btn.setText("Need an account? Sign up")

    def handle_primary_action(self):
        email = self.email_input.text()
        password = self.password_input.text()

        if self.mode == "signup":
            ok, message = self.user_store.create_user(email, password)
            self.status_label.setText(message)
            if ok:
                self.toggle_mode()  # drop them into login mode after successful signup
        else:
            ok, message = self.user_store.verify_user(email, password)
            self.status_label.setText(message)
            if ok:
                self.login_success.emit(email)