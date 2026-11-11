import pytest

from features.eyes import (
    BlinkCounter, PerclosTracker, LookingAwayTracker,
    eye_aspect_ratio, average_ear, gaze_ratio_x, is_looking_away,
    RIGHT_EYE_IDX, LEFT_EYE_IDX, RIGHT_IRIS_CENTER_IDX,
)
from tests.conftest import point

OPEN, CLOSED = 0.30, 0.10
FRAME = 0.1  # seconds between frames in these tests


def blink(counter, t):
    """Feed one blink (two closed frames, then open). Returns the time after it."""
    for ear in (CLOSED, CLOSED, OPEN):
        counter.update(ear, t)
        t += FRAME
    return t


def stare(counter, t, seconds):
    """Feed open-eye frames for the given number of seconds."""
    for _ in range(int(seconds / FRAME)):
        counter.update(OPEN, t)
        t += FRAME
    return t


# ---------- BlinkCounter ----------

def test_no_frames_means_zero_blinks():
    assert BlinkCounter().blinks_per_minute() == 0


def test_counts_blinks_in_the_last_minute():
    counter = BlinkCounter()
    t = 0.0
    for _ in range(12):
        t = blink(counter, t)
        t = stare(counter, t, 4)
    assert counter.blinks_per_minute() == 12


def test_a_single_closed_frame_is_not_a_blink():
    counter = BlinkCounter(consec_frames=2)
    counter.update(CLOSED, 0.0)
    counter.update(OPEN, 0.1)
    assert counter.blinks_per_minute() == 0


def test_blink_is_counted_when_the_eye_reopens_not_while_closed():
    counter = BlinkCounter()
    counter.update(CLOSED, 0.0)
    counter.update(CLOSED, 0.1)
    assert counter.blinks_per_minute() == 0
    counter.update(OPEN, 0.2)
    assert counter.blinks_per_minute() == 1


def test_blink_rate_drops_to_zero_when_the_user_stops_blinking():
    """Regression test: the rate used to freeze at its last value, so a user
    staring at the screen without blinking was never flagged for eye fatigue."""
    counter = BlinkCounter()
    t = 0.0
    for _ in range(15):
        t = blink(counter, t)
        t = stare(counter, t, 3.7)
    assert counter.blinks_per_minute() == 15

    stare(counter, t, 120)  # two minutes, no blinks
    assert counter.blinks_per_minute() == 0


def test_old_blinks_are_discarded_so_memory_stays_bounded():
    counter = BlinkCounter(max_window_seconds=60)
    t = 0.0
    for _ in range(500):
        t = blink(counter, t)
        t = stare(counter, t, 2)
    assert len(counter.blink_timestamps) <= 60 / 2.3 + 1


# ---------- PerclosTracker ----------

def test_perclos_is_zero_with_no_samples():
    assert PerclosTracker().perclos() == 0.0


def test_perclos_is_the_fraction_of_closed_frames():
    tracker = PerclosTracker(window_seconds=60)
    for i in range(10):
        tracker.update(CLOSED if i < 3 else OPEN, threshold=0.21, timestamp=i)
    assert tracker.perclos() == pytest.approx(0.3)


def test_perclos_forgets_samples_outside_the_window():
    tracker = PerclosTracker(window_seconds=30)
    for t in range(30):
        tracker.update(CLOSED, 0.21, t)   # eyes closed for 30 s...
    for t in range(30, 100):
        tracker.update(OPEN, 0.21, t)     # ...then open for 70 s
    assert tracker.perclos() == 0.0


# ---------- Eye aspect ratio and gaze ----------

def _face(eye_points_right, eye_points_left, iris_x=None):
    landmarks = {}
    for idx, p in zip(RIGHT_EYE_IDX, eye_points_right):
        landmarks[idx] = p
    for idx, p in zip(LEFT_EYE_IDX, eye_points_left):
        landmarks[idx] = p
    if iris_x is not None:
        landmarks[RIGHT_IRIS_CENTER_IDX] = point(iris_x, 0.5)
    return landmarks


def _eye(height):
    # corner, top1, top2, corner, bottom2, bottom1 — width 1.0, given opening height
    return [point(0, 0), point(0.3, height / 2), point(0.7, height / 2),
            point(1, 0), point(0.7, -height / 2), point(0.3, -height / 2)]


def test_eye_aspect_ratio_matches_the_formula():
    assert eye_aspect_ratio(_face(_eye(0.3), _eye(0.3)), RIGHT_EYE_IDX) == pytest.approx(0.3)


def test_average_ear_averages_both_eyes():
    assert average_ear(_face(_eye(0.2), _eye(0.4))) == pytest.approx(0.3)


def test_eye_aspect_ratio_survives_a_zero_width_eye():
    flat = [point(0, 0)] * 6
    assert eye_aspect_ratio(_face(flat, flat), RIGHT_EYE_IDX) == 0.3


@pytest.mark.parametrize("iris_x, expected", [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (-0.5, 0.0)])
def test_gaze_ratio_is_clamped_between_0_and_1(iris_x, expected):
    assert gaze_ratio_x(_face(_eye(0.3), _eye(0.3), iris_x)) == pytest.approx(expected)


@pytest.mark.parametrize("gaze, away", [(0.5, False), (0.31, False), (0.29, True), (0.71, True), (0.69, False)])
def test_is_looking_away(gaze, away):
    assert is_looking_away(gaze) is away


def test_looking_away_must_be_sustained(clock):
    tracker = LookingAwayTracker(sustain_seconds=20)
    assert tracker.update(True) is False
    clock.advance(19)
    assert tracker.update(True) is False
    clock.advance(1)
    assert tracker.update(True) is True


def test_looking_back_resets_the_looking_away_timer(clock):
    tracker = LookingAwayTracker(sustain_seconds=20)
    tracker.update(True)
    clock.advance(15)
    tracker.update(False)
    clock.advance(15)
    assert tracker.update(True) is False
