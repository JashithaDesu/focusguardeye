function angleFromVertical(pTop, pBottom) {
    const dx = pTop.x - pBottom.x;
    const dy = pTop.y - pBottom.y;
    return Math.abs(Math.atan2(dx, dy)) * (180 / Math.PI);
}

function midpoint(p1, p2) {
    return { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
}

export function computePostureMetrics(landmarks) {
    const ear = landmarks[7];
    const shoulderL = landmarks[11];
    const shoulderR = landmarks[12];
    const hipL = landmarks[23];
    const hipR = landmarks[24];

    const shoulderMid = midpoint(shoulderL, shoulderR);
    const hipMid = midpoint(hipL, hipR);

    return {
        neckAngle: angleFromVertical(ear, shoulderMid),
        torsoAngle: angleFromVertical(shoulderMid, hipMid),
    };
}

export function calibrateBaseline(samples) {
    const neckSum = samples.reduce((sum, s) => sum + s.neckAngle, 0);
    const torsoSum = samples.reduce((sum, s) => sum + s.torsoAngle, 0);
    return {
        neckAngle: neckSum / samples.length,
        torsoAngle: torsoSum / samples.length,
    };
}

export function isSlouching(current, baseline, neckThreshold = 15, torsoThreshold = 12) {
    const neckDev = current.neckAngle - baseline.neckAngle;
    const torsoDev = current.torsoAngle - baseline.torsoAngle;
    return neckDev > neckThreshold || torsoDev > torsoThreshold;
}

export class PostureTracker {
    constructor(sustainSeconds = 8) {
        this.sustainSeconds = sustainSeconds;
        this.badSince = null;
    }
    update(isBadFrame) {
        const now = performance.now() / 1000;
        if (isBadFrame) {
            if (this.badSince === null) this.badSince = now;
            return (now - this.badSince) >= this.sustainSeconds;
        } else {
            this.badSince = null;
            return false;
        }
    }
}