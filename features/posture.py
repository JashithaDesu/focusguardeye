import math
import time


def angle_from_vertical(p_top, p_bottom):
    """Angle (degrees) between the line p_top->p_bottom and true vertical.
    0 degrees = perfectly upright."""
    dx = p_top.x - p_bottom.x
    dy = p_top.y - p_bottom.y
    return math.degrees(math.atan2(abs(dx), abs(dy)))


def shoulder_symmetry_offset(left_shoulder, right_shoulder):
    """Vertical difference between shoulders — flags sideways leaning."""
    return abs(left_shoulder.y - right_shoulder.y)


def _midpoint(p1, p2):
    class Point:
        pass
    m = Point()
    m.x = (p1.x + p2.x) / 2
    m.y = (p1.y + p2.y) / 2
    m.z = (p1.z + p2.z) / 2
    return m


def compute_posture_metrics(landmarks):
    """landmarks: MediaPipe Pose's landmark list (results.pose_landmarks.landmark)"""
    ear = landmarks[7]           # left ear
    shoulder_l = landmarks[11]
    shoulder_r = landmarks[12]
    hip_l = landmarks[23]
    hip_r = landmarks[24]

    shoulder_mid = _midpoint(shoulder_l, shoulder_r)
    hip_mid = _midpoint(hip_l, hip_r)

    return {
        "neck_angle": angle_from_vertical(ear, shoulder_mid),
        "torso_angle": angle_from_vertical(shoulder_mid, hip_mid),
        "shoulder_offset": shoulder_symmetry_offset(shoulder_l, shoulder_r),
    }


def calibrate_baseline(metric_samples):
    """metric_samples: list of dicts from compute_posture_metrics(), collected over ~5s"""
    keys = metric_samples[0].keys()
    return {k: sum(s[k] for s in metric_samples) / len(metric_samples) for k in keys}


def is_slouching(current, baseline, neck_threshold=15, torso_threshold=12):
    neck_dev = current["neck_angle"] - baseline["neck_angle"]
    torso_dev = current["torso_angle"] - baseline["torso_angle"]
    return neck_dev > neck_threshold or torso_dev > torso_threshold


class PostureTracker:
    """Requires bad posture to be sustained for N seconds before flagging —
    avoids false alarms from momentary head turns or reaching for something."""

    def __init__(self, sustain_seconds=8):
        self.sustain_seconds = sustain_seconds
        self.bad_since = None

    def update(self, is_bad_frame):
        now = time.time()
        if is_bad_frame:
            if self.bad_since is None:
                self.bad_since = now
            return (now - self.bad_since) >= self.sustain_seconds
        else:
            self.bad_since = None
            return False