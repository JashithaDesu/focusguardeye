import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose

# refine_landmarks=True unlocks IRIS landmarks — required later for gaze estimation
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)  # mirror view feels natural for a self-facing camera
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False  # perf: MediaPipe doesn't need to write to this buffer

    face_result = face_mesh.process(rgb)
    pose_result = pose.process(rgb)

    rgb.flags.writeable = True

    if face_result.multi_face_landmarks:
        for landmarks in face_result.multi_face_landmarks:
            mp_drawing.draw_landmarks(
                frame, landmarks, mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1),
            )

    if pose_result.pose_landmarks:
        mp_drawing.draw_landmarks(frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow("FocusGuard — Phase 1 Debug", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()