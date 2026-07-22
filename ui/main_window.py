from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
import cv2
from notify import send_break_alert


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusGuard")
        self.resize(720, 560)

        # --- widgets ---
        self.video_label = QLabel("No feed yet — click Start Tracking")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedSize(640, 360)
        self.video_label.setStyleSheet("background-color: #222; color: white;")

        self.status_label = QLabel("Status: Idle")
        self.posture_label = QLabel("Posture: —")
        self.eye_label = QLabel("Eye strain: —")

        start_btn = QPushButton("Start Tracking")
        start_btn.clicked.connect(self.start_tracking)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self.stop_tracking)

        load_video_btn = QPushButton("Load Test Video…")
        load_video_btn.clicked.connect(self.load_video_file)

        test_notify_btn = QPushButton("Test Break Notification")
        test_notify_btn.clicked.connect(lambda: send_break_alert("manual"))

        button_row = QHBoxLayout()
        button_row.addWidget(start_btn)
        button_row.addWidget(stop_btn)
        button_row.addWidget(load_video_btn)
        button_row.addWidget(test_notify_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.posture_label)
        layout.addWidget(self.eye_label)
        layout.addLayout(button_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # --- state ---
        self.cap = None
        self.video_source = 0  # default: camera index 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def load_video_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select test video", "", "Videos (*.mp4 *.avi *.mov)")
        if path:
            self.video_source = path
            self.status_label.setText(f"Status: Video source set ({path.split('/')[-1]})")

    def start_tracking(self):
        self.cap = cv2.VideoCapture(self.video_source, cv2.CAP_DSHOW if isinstance(self.video_source, int) else cv2.CAP_ANY)
        if not self.cap.isOpened():
            self.status_label.setText("Status: Failed to open source — no camera detected, load a test video instead")
            return
        self.timer.start(33)  # ~30 fps
        self.status_label.setText("Status: Tracking…")

    def stop_tracking(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        self.status_label.setText("Status: Stopped")
        self.video_label.setText("No feed — click Start Tracking")

    def update_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            # end of video file, or camera dropped — stop cleanly instead of crashing
            self.stop_tracking()
            return

        # --- placeholder until Phase 2/3/4 exist ---
        # perception_results = run_pose_and_face_mesh(frame)
        # posture_metrics = compute_posture_metrics(perception_results)
        # eye_metrics = compute_eye_metrics(perception_results)
        # break_result = break_engine.check(...)
        # if break_result: send_break_alert(break_result["trigger_source"])
        self.posture_label.setText("Posture: (Phase 2 not wired in yet)")
        self.eye_label.setText("Eye strain: (Phase 3 not wired in yet)")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio
        )
        self.video_label.setPixmap(pixmap)