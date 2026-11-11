import numpy as np
import time
from collections import deque

# Standard MediaPipe Face Mesh eye-contour landmark indices (6 points per eye,
# ordered to match the classic EAR formulation: [left_corner, top1, top2, right_corner, bottom2, bottom1])
RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]

# Iris center landmarks — only available when FaceMesh is created with refine_landmarks=True
LEFT_IRIS_CENTER_IDX = 468
RIGHT_IRIS_CENTER_IDX = 473


def _dist(p1, p2):
    return np.linalg.norm(np.array([p1.x, p1.y]) - np.array([p2.x, p2.y]))


def eye_aspect_ratio(landmarks, eye_indices):
    pts = [landmarks[i] for i in eye_indices]
    vertical_1 = _dist(pts[1], pts[5])
    vertical_2 = _dist(pts[2], pts[4])
    horizontal = _dist(pts[0], pts[3])
    if horizontal == 0:
        return 0.3  # fallback, avoids divide-by-zero on a bad frame
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def average_ear(landmarks):
    """Average EAR across both eyes — more stable than either eye alone."""
    right = eye_aspect_ratio(landmarks, RIGHT_EYE_IDX)
    left = eye_aspect_ratio(landmarks, LEFT_EYE_IDX)
    return (right + left) / 2.0


def gaze_ratio_x(landmarks):
    """Roughly 0 = looking hard left, 0.5 = center, 1 = looking hard right.
    Requires refine_landmarks=True for iris landmarks to exist."""
    right_iris = landmarks[RIGHT_IRIS_CENTER_IDX]
    right_corner_l = landmarks[RIGHT_EYE_IDX[0]]
    right_corner_r = landmarks[RIGHT_EYE_IDX[3]]

     # Don't assume which corner has the smaller x — just take min/max directly
    left_x = min(right_corner_l.x, right_corner_r.x)
    right_x = max(right_corner_l.x, right_corner_r.x)
    eye_width = right_x - left_x 

    if eye_width < 1e-6:  # guards against near-zero, not just exactly zero
        return 0.5

    ratio = (right_iris.x - left_x) / eye_width
    return max(0.0, min(1.0, ratio))  # clamp so it can never leave the valid 0-1 range



def is_looking_away(gaze_x, gaze_edge_threshold=0.3):
    return gaze_x < gaze_edge_threshold or gaze_x > (1 - gaze_edge_threshold)


class BlinkCounter:
    def __init__(self, ear_threshold=0.21, consec_frames=2, max_window_seconds=60):
        self.ear_threshold = ear_threshold
        self.consec_frames = consec_frames
        self.max_window_seconds = max_window_seconds
        self.frame_counter = 0
        self.blink_timestamps = deque()
        self.last_timestamp = None  # time of the most recent frame, blink or not

    def update(self, ear_value, timestamp):
        self.last_timestamp = timestamp
        if ear_value < self.ear_threshold:
            self.frame_counter += 1
        else:
            if self.frame_counter >= self.consec_frames:
                self.blink_timestamps.append(timestamp)
            self.frame_counter = 0
        # Drop blinks that can no longer fall inside any window, so memory stays bounded
        cutoff = timestamp - self.max_window_seconds
        while self.blink_timestamps and self.blink_timestamps[0] < cutoff:
            self.blink_timestamps.popleft()

    def blinks_per_minute(self, window_seconds=60):
        # The window ends at the latest FRAME, not the latest blink. Otherwise the rate
        # freezes when the user stops blinking, and low-blink fatigue is never detected.
        if self.last_timestamp is None:
            return 0
        cutoff = self.last_timestamp - window_seconds
        return sum(1 for t in self.blink_timestamps if t >= cutoff)


class PerclosTracker:
    def __init__(self, window_seconds=60):
        self.window_seconds = window_seconds
        self.samples = deque()  # (timestamp, is_closed)

    def update(self, ear_value, threshold, timestamp):
        self.samples.append((timestamp, ear_value < threshold))
        cutoff = timestamp - self.window_seconds
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()

    def perclos(self):
        if not self.samples:
            return 0.0
        closed = sum(1 for _, is_closed in self.samples if is_closed)
        return closed / len(self.samples)


class LookingAwayTracker:
    """Same sustained-detection pattern as PostureTracker — a single glance
    away shouldn't count as a break; it needs to hold for N seconds."""

    def __init__(self, sustain_seconds=20):
        self.sustain_seconds = sustain_seconds
        self.away_since = None

    def update(self, is_away_frame):
        now = time.time()
        if is_away_frame:
            if self.away_since is None:
                self.away_since = now
            return (now - self.away_since) >= self.sustain_seconds
        else:
            self.away_since = None
            return False