import time
import cv2
import mediapipe as mp
from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

from ui.notify import send_break_alert
from features.posture import compute_posture_metrics, calibrate_baseline, is_slouching, PostureTracker
from features.eyes import average_ear, PerclosTracker, BlinkCounter
from engine.break_engine import BreakEngine, compute_eye_fatigue_signal
from storage.db import MetricsStore

EAR_THRESHOLD = 0.21
CALIBRATION_SECONDS = 5
LOG_INTERVAL = 1.0


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusGuard")
        self.resize(720, 620)

        # --- widgets ---
        self.video_label = QLabel("No feed yet — click Start Tracking")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedSize(640, 360)
        self.video_label.setStyleSheet("background-color: #222; color: white;")

        self.status_label = QLabel("Status: Idle")
        self.posture_label = QLabel("Posture: —")
        self.eye_label = QLabel("Eye strain: —")
        self.alert_label = QLabel("")
        self.alert_label.setStyleSheet("color: red; font-weight: bold;")

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
        layout.addWidget(self.alert_label)
        layout.addLayout(button_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # --- video state ---
        self.cap = None
        self.video_source = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # --- MediaPipe models (created once, reused every frame) ---
        self.pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5,
        )
        self.mp_drawing = mp.solutions.drawing_utils

        # --- detection/engine state (created fresh each time tracking starts) ---
        self.posture_tracker = None
        self.perclos_tracker = None
        self.blink_counter = None
        self.break_engine = None
        self.store = None
        self.session_id = None
        self.session_start = None

        # --- calibration state machine ---
        self.mode = "idle"  # idle -> calibrating -> tracking
        self.calibration_samples = []
        self.calib_start_time = None
        self.baseline = None

        self.last_log_time = 0

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

        # Fresh state every time tracking starts
        self.posture_tracker = PostureTracker(sustain_seconds=8)
        self.perclos_tracker = PerclosTracker(window_seconds=30)
        self.blink_counter = BlinkCounter(ear_threshold=EAR_THRESHOLD)
        self.break_engine = BreakEngine(timer_interval_seconds=20 * 60, min_gap_seconds=15)

        self.store = MetricsStore("focusguard.db")
        self.session_start = time.time()
        self.session_id = self.store.start_session(self.session_start)
        self.last_log_time = 0

        self.mode = "calibrating"
        self.calibration_samples = []
        self.calib_start_time = time.time()
        self.baseline = None

        self.timer.start(33)  # ~30 fps
        self.status_label.setText("Status: Calibrating — sit normally for 5 seconds")

    def stop_tracking(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        if self.store and self.session_id:
            self.store.end_session(self.session_id, time.time())
            self.store.close()
        self.mode = "idle"
        self.status_label.setText("Status: Stopped")
        self.video_label.setText("No feed — click Start Tracking")
        self.posture_label.setText("Posture: —")
        self.eye_label.setText("Eye strain: —")
        self.alert_label.setText("")

    def update_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            self.stop_tracking()
            return

        frame = cv2.flip(frame, 1) if isinstance(self.video_source, int) else frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        now = time.time()

        if self.mode == "calibrating":
            self._handle_calibration(rgb, now)
        elif self.mode == "tracking":
            frame = self._handle_tracking(frame, rgb, now)

        rgb_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.shape[2] == 3 else frame
        h, w, ch = rgb_display.shape
        qt_image = QImage(rgb_display.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio
        )
        self.video_label.setPixmap(pixmap)

    def _handle_calibration(self, rgb, now):
        pose_result = self.pose.process(rgb)
        if pose_result.pose_landmarks:
            self.calibration_samples.append(compute_posture_metrics(pose_result.pose_landmarks.landmark))

        elapsed = now - self.calib_start_time
        self.status_label.setText(f"Status: Calibrating — {max(0, CALIBRATION_SECONDS - elapsed):.0f}s left")

        if elapsed >= CALIBRATION_SECONDS:
            if self.calibration_samples:
                self.baseline = calibrate_baseline(self.calibration_samples)
                self.mode = "tracking"
                self.status_label.setText("Status: Tracking…")
            else:
                self.status_label.setText("Status: Calibration failed — no pose detected. Restart tracking.")
                self.stop_tracking()

    def _handle_tracking(self, frame, rgb, now):
        pose_result = self.pose.process(rgb)
        face_result = self.face_mesh.process(rgb)

        posture_bad_sustained = False
        eye_fatigue = False
        metrics_snapshot = {}

        if pose_result.pose_landmarks and self.baseline:
            metrics = compute_posture_metrics(pose_result.pose_landmarks.landmark)
            bad_frame = is_slouching(metrics, self.baseline)
            posture_bad_sustained = self.posture_tracker.update(bad_frame)
            metrics_snapshot["neck_angle"] = metrics["neck_angle"]
            metrics_snapshot["torso_angle"] = metrics["torso_angle"]

            neck_dev = metrics["neck_angle"] - self.baseline["neck_angle"]
            torso_dev = metrics["torso_angle"] - self.baseline["torso_angle"]
            posture_text = f"Posture: neck_dev={neck_dev:.1f}° torso_dev={torso_dev:.1f}°"
            if posture_bad_sustained:
                posture_text += "  ⚠ SLOUCHING"
            self.posture_label.setText(posture_text)

            self.mp_drawing.draw_landmarks(frame, pose_result.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        else:
            self.posture_label.setText("Posture: no pose detected")

        if face_result.multi_face_landmarks:
            landmarks = face_result.multi_face_landmarks[0].landmark
            ear = average_ear(landmarks)
            self.blink_counter.update(ear, now)
            self.perclos_tracker.update(ear, EAR_THRESHOLD, now)
            blink_rate = self.blink_counter.blinks_per_minute()
            perclos = self.perclos_tracker.perclos()

            eye_fatigue = compute_eye_fatigue_signal(
                perclos, blink_rate, session_elapsed_seconds=now - self.session_start
            )
            metrics_snapshot["ear"] = ear
            metrics_snapshot["blink_rate"] = blink_rate
            metrics_snapshot["perclos"] = perclos

            self.eye_label.setText(
                f"Eye strain: EAR={ear:.2f}  blinks/min={blink_rate}  PERCLOS={perclos*100:.1f}%"
            )
        else:
            self.eye_label.setText("Eye strain: no face detected")

        if now - self.last_log_time >= LOG_INTERVAL and metrics_snapshot:
            self.store.log_metrics(
                self.session_id, now,
                neck_angle=metrics_snapshot.get("neck_angle"),
                torso_angle=metrics_snapshot.get("torso_angle"),
                ear=metrics_snapshot.get("ear"),
                blink_rate=metrics_snapshot.get("blink_rate"),
                perclos=metrics_snapshot.get("perclos"),
            )
            self.last_log_time = now

        result = self.break_engine.check(posture_bad_sustained, eye_fatigue)
        if result:
            self.alert_label.setText(f"BREAK TRIGGERED — {result['trigger_source']}")
            self.store.log_break(self.session_id, result["trigger_time"], result["trigger_source"])
            send_break_alert(result["trigger_source"])

        return frame