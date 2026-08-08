export class BreakEngine {
    constructor(timerIntervalSeconds = 20 * 60, minGapSeconds = 15) {
        this.timerInterval = timerIntervalSeconds;
        this.minGapSeconds = minGapSeconds;
        this.lastBreakTime = performance.now() / 1000;
    }
    check(postureBadSustained, eyeFatigueSignal) {
        const now = performance.now() / 1000;
        const elapsed = now - this.lastBreakTime;
        if (elapsed < this.minGapSeconds) return null;
        if (elapsed >= this.timerInterval) return this._trigger("timer");
        if (postureBadSustained) return this._trigger("posture_signal");
        if (eyeFatigueSignal) return this._trigger("eye_fatigue_signal");
        return null;
    }
    _trigger(source) {
        this.lastBreakTime = performance.now() / 1000;
        return { triggerSource: source };
    }
}

export function computeEyeFatigueSignal(perclosValue, blinksPerMinute, sessionElapsedSeconds,
                                          perclosThreshold = 0.4, lowBlinkThreshold = 8, gracePeriodSeconds = 30) {
    if (sessionElapsedSeconds < gracePeriodSeconds) return perclosValue > perclosThreshold;
    return perclosValue > perclosThreshold || blinksPerMinute < lowBlinkThreshold;
}