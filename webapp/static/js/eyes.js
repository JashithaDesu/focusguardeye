const RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144];
const LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380];
const RIGHT_IRIS_CENTER_IDX = 473;

function dist(p1, p2) {
    return Math.hypot(p1.x - p2.x, p1.y - p2.y);
}

function eyeAspectRatio(landmarks, idx) {
    const pts = idx.map(i => landmarks[i]);
    const v1 = dist(pts[1], pts[5]);
    const v2 = dist(pts[2], pts[4]);
    const h = dist(pts[0], pts[3]);
    if (h === 0) return 0.3;
    return (v1 + v2) / (2 * h);
}

export function averageEAR(landmarks) {
    const right = eyeAspectRatio(landmarks, RIGHT_EYE_IDX);
    const left = eyeAspectRatio(landmarks, LEFT_EYE_IDX);
    return (right + left) / 2;
}

export function gazeRatioX(landmarks) {
    const iris = landmarks[RIGHT_IRIS_CENTER_IDX];
    const cA = landmarks[RIGHT_EYE_IDX[0]];
    const cB = landmarks[RIGHT_EYE_IDX[3]];
    const leftX = Math.min(cA.x, cB.x);
    const rightX = Math.max(cA.x, cB.x);
    const width = rightX - leftX;
    if (width < 1e-6) return 0.5;
    const ratio = (iris.x - leftX) / width;
    return Math.max(0, Math.min(1, ratio));
}

export class BlinkCounter {
    constructor(earThreshold = 0.21, consecFrames = 2, maxWindowSeconds = 60) {
        this.earThreshold = earThreshold;
        this.consecFrames = consecFrames;
        this.maxWindowSeconds = maxWindowSeconds;
        this.frameCounter = 0;
        this.blinkTimestamps = [];
        this.lastTimestamp = null; // time of the most recent frame, blink or not
    }
    update(earValue, timestamp) {
        this.lastTimestamp = timestamp;
        if (earValue < this.earThreshold) {
            this.frameCounter++;
        } else {
            if (this.frameCounter >= this.consecFrames) this.blinkTimestamps.push(timestamp);
            this.frameCounter = 0;
        }
        // Drop blinks that can no longer fall inside any window, so memory stays bounded
        const cutoff = timestamp - this.maxWindowSeconds;
        while (this.blinkTimestamps.length && this.blinkTimestamps[0] < cutoff) this.blinkTimestamps.shift();
    }
    blinksPerMinute(windowSeconds = 60) {
        // The window ends at the latest FRAME, not the latest blink. Otherwise the rate
        // freezes when the user stops blinking, and low-blink fatigue is never detected.
        if (this.lastTimestamp === null) return 0;
        const cutoff = this.lastTimestamp - windowSeconds;
        return this.blinkTimestamps.filter(t => t >= cutoff).length;
    }
}

export class PerclosTracker {
    constructor(windowSeconds = 30) {
        this.windowSeconds = windowSeconds;
        this.samples = [];
    }
    update(earValue, threshold, timestamp) {
        this.samples.push([timestamp, earValue < threshold]);
        const cutoff = timestamp - this.windowSeconds;
        while (this.samples.length && this.samples[0][0] < cutoff) this.samples.shift();
    }
    perclos() {
        if (this.samples.length === 0) return 0;
        const closed = this.samples.filter(s => s[1]).length;
        return closed / this.samples.length;
    }
}