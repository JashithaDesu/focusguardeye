import pytest

from engine.break_engine import BreakEngine, compute_eye_fatigue_signal


# ---------- BreakEngine ----------

def test_no_break_when_nothing_is_wrong(clock):
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(60)
    assert engine.check(posture_bad_sustained=False, eye_fatigue_signal=False) is None


def test_timer_break_fires_exactly_at_the_interval(clock):
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(1199)
    assert engine.check(False, False) is None
    clock.advance(1)
    result = engine.check(False, False)
    assert result == {"trigger_time": clock.now, "trigger_source": "timer"}


def test_posture_and_eye_signals_are_blocked_during_the_minimum_gap(clock):
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(14)
    assert engine.check(True, True) is None


def test_posture_signal_fires_once_the_gap_has_passed(clock):
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(15)
    assert engine.check(True, False)["trigger_source"] == "posture_signal"


def test_eye_fatigue_signal_fires_when_posture_is_fine(clock):
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(20)
    assert engine.check(False, True)["trigger_source"] == "eye_fatigue_signal"


def test_priority_is_timer_then_posture_then_eyes(clock):
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(1200)
    assert engine.check(True, True)["trigger_source"] == "timer"

    clock.advance(15)
    assert engine.check(True, True)["trigger_source"] == "posture_signal"


def test_a_break_resets_the_timer(clock):
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(600)
    engine.check(True, False)          # posture break at t=600
    clock.advance(1199)
    assert engine.check(False, False) is None
    clock.advance(1)
    assert engine.check(False, False)["trigger_source"] == "timer"


def test_sustained_slouching_triggers_again_after_each_gap(clock):
    """Documents current behaviour: continuous slouching re-alerts every min_gap seconds.
    If that's not the intended user experience, this test should change with the design."""
    engine = BreakEngine(timer_interval_seconds=1200, min_gap_seconds=15)
    clock.advance(15)
    assert engine.check(True, False) is not None
    clock.advance(14)
    assert engine.check(True, False) is None
    clock.advance(1)
    assert engine.check(True, False) is not None


# ---------- compute_eye_fatigue_signal ----------

@pytest.mark.parametrize(
    "perclos, blinks, elapsed, expected",
    [
        (0.10, 15, 600, False),  # healthy eyes
        (0.41, 15, 600, True),   # eyes closed too often
        (0.40, 15, 600, False),  # threshold itself is not fatigue (strictly greater)
        (0.10, 7, 600, True),    # too few blinks
        (0.10, 8, 600, False),   # threshold itself is not fatigue (strictly less)
        (0.10, 0, 29, False),    # low blinks ignored during the grace period
        (0.10, 0, 30, True),     # ...and counted once the grace period ends
        (0.50, 15, 5, True),     # PERCLOS still counts during the grace period
    ],
)
def test_eye_fatigue_signal(perclos, blinks, elapsed, expected):
    assert compute_eye_fatigue_signal(perclos, blinks, elapsed) is expected
