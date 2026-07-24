import cv2
import mediapipe as mp
import time
from features.posture import compute_posture_metrics, calibrate_baseline, is_slouching, PostureTracker
from features.eyes import average_ear, PerclosTracker, BlinkCounter
from engine.break_engine import BreakEngine, compute_eye_fatigue_signal
from storage.db import MetricsStore

mp_pose = mp.solutions.pose
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                                   min_detection_confidence=0.5, min_tracking_confidence=0.5)

EAR_THRESHOLD = 0.21
posture_tracker = PostureTracker(sustain_seconds=5)
perclos_tracker = PerclosTracker(window_seconds=30)
blink_counter = BlinkCounter(ear_threshold=EAR_THRESHOLD)
break_engine = BreakEngine(timer_interval_seconds=20, min_gap_seconds=15)

store = MetricsStore("focusguard.db")
session_id = store.start_session(time.time())
print(f"Session started — id {session_id}, logging to focusguard.db")

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
session_start = time.time()

print("Calibrating posture... sit normally for 5 seconds.")
calibration_samples = []
calib_start = time.time()
while time.time() - calib_start < 5:
    ok, frame = cap.read()
    if not ok:
        continue
    rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)
    if result.pose_landmarks:
        calibration_samples.append(compute_posture_metrics(result.pose_landmarks.landmark))
    cv2.imshow("FocusGuard — Storage Test", frame)
    cv2.waitKey(1)

baseline = calibrate_baseline(calibration_samples) if calibration_samples else None
print("Baseline:", baseline)

last_alert = ""
last_log_time = 0
LOG_INTERVAL = 1.0  # log metrics roughly once per second, not every frame

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    now = time.time()

    pose_result = pose.process(rgb)
    face_result = face_mesh.process(rgb)

    posture_bad_sustained = False
    eye_fatigue = False
    metrics_snapshot = {}

    if pose_result.pose_landmarks and baseline:
        metrics = compute_posture_metrics(pose_result.pose_landmarks.landmark)
        bad_frame = is_slouching(metrics, baseline)
        posture_bad_sustained = posture_tracker.update(bad_frame)
        metrics_snapshot["neck_angle"] = metrics["neck_angle"]
        metrics_snapshot["torso_angle"] = metrics["torso_angle"]
        mp_drawing.draw_landmarks(frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    if face_result.multi_face_landmarks:
        landmarks = face_result.multi_face_landmarks[0].landmark
        ear = average_ear(landmarks)
        blink_counter.update(ear, now)
        perclos_tracker.update(ear, EAR_THRESHOLD, now)
        eye_fatigue = compute_eye_fatigue_signal(
            perclos_tracker.perclos(),
            blink_counter.blinks_per_minute(),
            session_elapsed_seconds=now - session_start,
        )
        metrics_snapshot["ear"] = ear
        metrics_snapshot["blink_rate"] = blink_counter.blinks_per_minute()
        metrics_snapshot["perclos"] = perclos_tracker.perclos()

    # --- log metrics roughly once per second, not every frame (avoids bloating the DB) ---
    if now - last_log_time >= LOG_INTERVAL and metrics_snapshot:
        store.log_metrics(
            session_id, now,
            neck_angle=metrics_snapshot.get("neck_angle"),
            torso_angle=metrics_snapshot.get("torso_angle"),
            ear=metrics_snapshot.get("ear"),
            blink_rate=metrics_snapshot.get("blink_rate"),
            perclos=metrics_snapshot.get("perclos"),
        )
        last_log_time = now

    result = break_engine.check(posture_bad_sustained, eye_fatigue)
    if result:
        last_alert = f"BREAK TRIGGERED — source: {result['trigger_source']}"
        print(last_alert)
        store.log_break(session_id, result["trigger_time"], result["trigger_source"])

    cv2.putText(frame, last_alert, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    cv2.imshow("FocusGuard — Storage Test", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

store.end_session(session_id, time.time())
store.close()
cap.release()
cv2.destroyAllWindows()
print("Session ended and saved.")