import cv2
import mediapipe as mp
import time
from features.eyes import (
    average_ear, gaze_ratio_x, is_looking_away,
    BlinkCounter, PerclosTracker, LookingAwayTracker
)

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# refine_landmarks=True is REQUIRED here — it's what unlocks the iris landmarks used for gaze
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

EAR_THRESHOLD = 0.21
blink_counter = BlinkCounter(ear_threshold=EAR_THRESHOLD)
perclos_tracker = PerclosTracker(window_seconds=30)
away_tracker = LookingAwayTracker(sustain_seconds=5)  # shortened for quick testing

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    status_lines = ["No face detected"]

    if result.multi_face_landmarks:
        landmarks = result.multi_face_landmarks[0].landmark
        now = time.time()

        ear = average_ear(landmarks)
        blink_counter.update(ear, now)
        perclos_tracker.update(ear, EAR_THRESHOLD, now)
        gaze_x = gaze_ratio_x(landmarks)
        away_frame = is_looking_away(gaze_x)
        sustained_away = away_tracker.update(away_frame)

        status_lines = [
            f"EAR: {ear:.3f}",
            f"Blinks/min: {blink_counter.blinks_per_minute()}",
            f"PERCLOS: {perclos_tracker.perclos()*100:.1f}%",
            f"Gaze x: {gaze_x:.2f}  {'(edge)' if away_frame else '(center)'}",
        ]
        if sustained_away:
            status_lines.append(">>> LOOKING AWAY (sustained) <<<")

        mp_drawing.draw_landmarks(
            frame, result.multi_face_landmarks[0], mp_face_mesh.FACEMESH_CONTOURS,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1),
        )

    for i, line in enumerate(status_lines):
        cv2.putText(frame, line, (10, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("FocusGuard — Eye Strain Test", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()