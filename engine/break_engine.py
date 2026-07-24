import time


class BreakEngine:
    def __init__(self, timer_interval_seconds=20 * 60, min_gap_seconds=15):
        self.timer_interval = timer_interval_seconds
        self.min_gap_seconds = min_gap_seconds  # NEW: hard cooldown between ANY two triggers
        self.last_break_time = time.time()

    def check(self, posture_bad_sustained, eye_fatigue_signal):
        now = time.time()
        elapsed = now - self.last_break_time

        # NEW: enforce a minimum gap regardless of which condition is true
        if elapsed < self.min_gap_seconds:
            return None

        if elapsed >= self.timer_interval:
            return self._trigger(now, "timer")
        if posture_bad_sustained:
            return self._trigger(now, "posture_signal")
        if eye_fatigue_signal:
            return self._trigger(now, "eye_fatigue_signal")
        return None

    def _trigger(self, now, source):
        self.last_break_time = now
        return {"trigger_time": now, "trigger_source": source}


def compute_eye_fatigue_signal(perclos_value, blinks_per_minute, session_elapsed_seconds,
                                 perclos_threshold=0.4, low_blink_threshold=8, grace_period_seconds=30):
    # NEW: ignore the blink-rate signal until enough time has passed for it to be meaningful
    if session_elapsed_seconds < grace_period_seconds:
        return perclos_value > perclos_threshold
    return perclos_value > perclos_threshold or blinks_per_minute < low_blink_threshold