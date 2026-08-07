from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton, QLabel

from ui.login_page import LoginPage
from ui.dashboard_page import DashboardPage
from ui.reports_page import ReportsPage


class AppShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusGuard")
        self.resize(760, 720)

        self.stack = QStackedWidget()

        self.login_page = LoginPage()
        self.dashboard_page = DashboardPage()
        self.reports_page = ReportsPage()

        self.stack.addWidget(self.login_page)     # index 0
        self.stack.addWidget(self.dashboard_page)  # index 1
        self.stack.addWidget(self.reports_page)    # index 2

        self.nav_bar = self._build_nav_bar()
        self.nav_bar.setVisible(False)  # hidden until logged in

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.nav_bar)
        layout.addWidget(self.stack)
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.login_page.login_success.connect(self.handle_login)
        self.stack.setCurrentIndex(0)

    def _build_nav_bar(self):
        bar = QWidget()
        bar.setObjectName("NavBar")
        self.user_label = QLabel("")
        dashboard_btn = QPushButton("Dashboard")
        dashboard_btn.setObjectName("SecondaryButton")
        dashboard_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        reports_btn = QPushButton("Reports")
        reports_btn.setObjectName("SecondaryButton")
        reports_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("DangerButton")
        logout_btn.clicked.connect(self.handle_logout)

        layout = QHBoxLayout()
        layout.addWidget(self.user_label)
        layout.addStretch()
        layout.addWidget(dashboard_btn)
        layout.addWidget(reports_btn)
        layout.addWidget(logout_btn)
        bar.setLayout(layout)
        return bar

    def handle_login(self, email):
        self.user_label.setText(f"Logged in as {email}")
        self.nav_bar.setVisible(True)
        self.stack.setCurrentIndex(1)  # go straight to Dashboard after login

    def handle_logout(self):
        self.dashboard_page.stop_tracking()
        self.nav_bar.setVisible(False)
        self.stack.setCurrentIndex(0)