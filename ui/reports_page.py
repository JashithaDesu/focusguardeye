from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from reports.weekly import generate_report


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.user_id = None  # set by AppShell after login

        title = QLabel("Weekly Report")
        title.setObjectName("TitleLabel")

        self.summary_label = QLabel("Click Refresh to generate your latest report.")
        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_label.setFixedSize(500, 620)
        self.chart_label.setStyleSheet("background-color: #171c26; border-radius: 6px;")

        refresh_btn = QPushButton("Refresh Report")
        refresh_btn.clicked.connect(self.refresh_report)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.chart_label)
        layout.addWidget(refresh_btn)
        layout.addStretch()
        self.setLayout(layout)

    def refresh_report(self):
        result = generate_report(db_path="focusguard.db", days=7, user_id=self.user_id)

        score = result["wellness_score"]
        sources = result["trigger_sources"]
        summary_text = (
            f"Wellness Score: {score if score is not None else 'N/A — no data yet'}\n"
            f"Metrics logged: {result['metrics_count']}   |   Breaks triggered: {result['breaks_count']}\n"
            f"Break sources: {sources if sources else 'none yet'}"
        )
        self.summary_label.setText(summary_text)

        if result["chart_path"]:
            pixmap = QPixmap(result["chart_path"]).scaled(
                self.chart_label.width(), self.chart_label.height(), Qt.AspectRatioMode.KeepAspectRatio
            )
            self.chart_label.setPixmap(pixmap)
        else:
            self.chart_label.setText("No chart yet — track a session first")