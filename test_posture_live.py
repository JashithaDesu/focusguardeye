import cv2
import mediapipe as mp
import time
from features.posture import compute_posture_metrics, calibrate_baseline, is_slouching, PostureTracker

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
tracker = PostureTracker(sustain_seconds=5)  # shorter for quick testing

# --- Calibration: sit normally for 5 seconds ---
print("Calibrating... sit normally/comfortably for 5 seconds.")
calibration_samples = []
calib_start = time.time()
while time.time() - calib_start < 5:
    ok, frame = cap.read()
    if not ok:
        continue
    rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)
    if result.pose_landmarks:
        metrics = compute_posture_metrics(result.pose_landmarks.landmark)
        calibration_samples.append(metrics)
    cv2.imshow("FocusGuard — Posture Test", frame)
    cv2.waitKey(1)

if not calibration_samples:
    print("No landmarks detected during calibration — check camera/lighting.")
    cap.release()
    cv2.destroyAllWindows()
    exit()

baseline = calibrate_baseline(calibration_samples)
print("Calibration done. Baseline:", {k: round(v, 1) for k, v in baseline.items()})

# --- Live loop ---
while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    status_text = "No pose detected"
    if result.pose_landmarks:
        mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        metrics = compute_posture_metrics(result.pose_landmarks.landmark)
        bad_frame = is_slouching(metrics, baseline)
        sustained_bad = tracker.update(bad_frame)

        status_text = f"neck_dev={metrics['neck_angle']-baseline['neck_angle']:.1f} torso_dev={metrics['torso_angle']-baseline['torso_angle']:.1f}"
        if sustained_bad:
            status_text += "  <<< SLOUCHING (sustained) >>>"

    cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imshow("FocusGuard — Posture Test", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()