import pytest

from features.posture import (
    angle_from_vertical, compute_posture_metrics, calibrate_baseline,
    is_slouching, PostureTracker,
)
from tests.conftest import point


def test_upright_line_is_zero_degrees():
    assert angle_from_vertical(point(0.5, 0.2), point(0.5, 0.8)) == pytest.approx(0.0)


def test_45_degree_lean():
    assert angle_from_vertical(point(0.6, 0.4), point(0.5, 0.5)) == pytest.approx(45.0)


def test_lean_direction_does_not_matter():
    left = angle_from_vertical(point(0.4, 0.2), point(0.5, 0.5))
    right = angle_from_vertical(point(0.6, 0.2), point(0.5, 0.5))
    assert left == pytest.approx(right)


def _pose(ear_x=0.5):
    landmarks = {i: point(0.5, 0.5) for i in range(33)}
    landmarks[7] = point(ear_x, 0.2)        # left ear
    landmarks[11] = point(0.4, 0.4)         # left shoulder
    landmarks[12] = point(0.6, 0.4)         # right shoulder
    landmarks[23] = point(0.4, 0.8)         # left hip
    landmarks[24] = point(0.6, 0.8)         # right hip
    return landmarks


def test_posture_metrics_for_an_upright_person():
    metrics = compute_posture_metrics(_pose())
    assert metrics["neck_angle"] == pytest.approx(0.0)
    assert metrics["torso_angle"] == pytest.approx(0.0)
    assert metrics["shoulder_offset"] == pytest.approx(0.0)


def test_head_forward_increases_neck_angle():
    assert compute_posture_metrics(_pose(ear_x=0.7))["neck_angle"] > 30


def test_baseline_is_the_average_of_samples():
    samples = [{"neck_angle": 10, "torso_angle": 4}, {"neck_angle": 20, "torso_angle": 8}]
    assert calibrate_baseline(samples) == {"neck_angle": 15, "torso_angle": 6}


@pytest.mark.parametrize(
    "neck, torso, slouching",
    [
        (10, 5, False),   # same as baseline
        (25, 5, False),   # neck exactly at threshold (15) is still fine
        (25.1, 5, True),  # neck just over threshold
        (10, 17, False),  # torso exactly at threshold (12) is still fine
        (10, 17.1, True), # torso just over threshold
        (0, 0, False),    # leaning back (negative deviation) is not slouching
    ],
)
def test_is_slouching_compares_against_the_personal_baseline(neck, torso, slouching):
    baseline = {"neck_angle": 10, "torso_angle": 5}
    assert is_slouching({"neck_angle": neck, "torso_angle": torso}, baseline) is slouching


def test_bad_posture_must_be_sustained(clock):
    tracker = PostureTracker(sustain_seconds=8)
    assert tracker.update(True) is False
    clock.advance(7.9)
    assert tracker.update(True) is False
    clock.advance(0.1)
    assert tracker.update(True) is True


def test_sitting_up_resets_the_posture_timer(clock):
    tracker = PostureTracker(sustain_seconds=8)
    tracker.update(True)
    clock.advance(7)
    tracker.update(False)
    clock.advance(7)
    assert tracker.update(True) is False
