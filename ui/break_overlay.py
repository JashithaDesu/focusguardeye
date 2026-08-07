from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve

MESSAGES = {
    "timer": ("🦉", "Time for your 20-20-20 break!", "Look at something 20 feet away"),
    "posture_signal": ("🐢", "Posture check!", "You've been slouching — sit up and stretch"),
    "eye_fatigue_signal": ("👀", "Your eyes look tired", "Look away from the screen for a moment"),
    "manual": ("🦉", "Test notification", "This is what a break alert looks like"),
}


class BreakOverlay(QWidget):
    def __init__(self, trigger_source="timer", duration_seconds=20):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.duration_seconds = duration_seconds
        self.remaining = duration_seconds

        emoji, headline, subtext = MESSAGES.get(trigger_source, MESSAGES["timer"])

        self.setStyleSheet("""
            QWidget { background-color: #2d3748; border-radius: 16px; }
            QLabel#Emoji { font-size: 64px; }
            QLabel#Headline { font-size: 18px; font-weight: bold; color: #4fd1c5; }
            QLabel#Subtext { font-size: 13px; color: #e8ecf1; }
            QLabel#Countdown { font-size: 28px; font-weight: bold; color: #fc8181; }
        """)

        emoji_label = QLabel(emoji)
        emoji_label.setObjectName("Emoji")
        emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        headline_label = QLabel(headline)
        headline_label.setObjectName("Headline")
        headline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtext_label = QLabel(subtext)
        subtext_label.setObjectName("Subtext")
        subtext_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.countdown_label = QLabel(str(self.remaining))
        self.countdown_label.setObjectName("Countdown")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(emoji_label)
        layout.addWidget(headline_label)
        layout.addWidget(subtext_label)
        layout.addWidget(self.countdown_label)
        layout.setContentsMargins(30, 24, 30, 24)
        self.setLayout(layout)

        self.resize(320, 260)
        self._position_bottom_right()

        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self._tick)
        self.tick_timer.start(1000)

        self._start_bounce()
        self.show()

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen().geometry()
        self.base_x = screen.width() - self.width() - 40
        self.base_y = screen.height() - self.height() - 80
        self.move(self.base_x, self.base_y)

    def _start_bounce(self):
        self.bounce_anim = QPropertyAnimation(self, b"pos")
        self.bounce_anim.setDuration(900)
        self.bounce_anim.setStartValue(QPoint(self.base_x, self.base_y))
        self.bounce_anim.setEndValue(QPoint(self.base_x, self.base_y - 12))
        self.bounce_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.bounce_anim.setLoopCount(-1)
        self.bounce_anim.start()

    def _tick(self):
        self.remaining -= 1
        self.countdown_label.setText(str(max(0, self.remaining)))
        if self.remaining <= 0:
            self.tick_timer.stop()
            self.bounce_anim.stop()
            self.close()