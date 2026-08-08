import { PoseLandmarker, FaceLandmarker, FilesetResolver, DrawingUtils } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs";
import { computePostureMetrics, calibrateBaseline, isSlouching, PostureTracker } from "./posture.js";
import { averageEAR, gazeRatioX, BlinkCounter, PerclosTracker } from "./eyes.js";
import { BreakEngine, computeEyeFatigueSignal } from "./breakEngine.js";

const EAR_THRESHOLD = 0.21;
const CALIBRATION_SECONDS = 5;
const BREAK_DURATION_SECONDS = 20;

const statusEl = document.getElementById("status");
const postureEl = document.getElementById("postureText");
const eyeEl = document.getElementById("eyeText");
const alertEl = document.getElementById("alertText");
const video = document.getElementById("videoFeed");
const canvas = document.getElementById("overlay");
const ctx = canvas.getContext("2d");
const drawingUtils = new DrawingUtils(ctx);
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const MESSAGES = {
    timer: ["🦉", "Time for your 20-20-20 break!", "Look at something 20 feet away"],
    posture_signal: ["🐢", "Posture check!", "You've been slouching — sit up and stretch"],
    eye_fatigue_signal: ["👀", "Your eyes look tired", "Look away from the screen for a moment"],
};

let poseLandmarker, faceLandmarker;
let stream = null;
let mode = "idle"; // idle -> calibrating -> tracking
let calibSamples = [];
let calibStart = 0;
let baseline = null;
let sessionStart = 0;
let lastLogTime = 0;

let postureTracker, perclosTracker, blinkCounter, breakEngine;

async function loadModels() {
    const fileset = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm");

    poseLandmarker = await PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task", delegate: "GPU" },
        runningMode: "VIDEO", numPoses: 1,
    });

    faceLandmarker = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task", delegate: "GPU" },
        runningMode: "VIDEO", numFaces: 1,
    });
}

startBtn.addEventListener("click", startTracking);
stopBtn.addEventListener("click", stopTracking);

async function startTracking() {
    if (!poseLandmarker) {
        statusEl.textContent = "Status: Loading models…";
        await loadModels();
    }

    if (Notification.permission !== "granted") await Notification.requestPermission();

    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        video.srcObject = stream;
    } catch (err) {
        statusEl.textContent = "Status: Camera access failed — " + err.message;
        return;
    }

    await fetch("/api/start-session", { method: "POST" });

    postureTracker = new PostureTracker(8);
    perclosTracker = new PerclosTracker(30);
    blinkCounter = new BlinkCounter(EAR_THRESHOLD);
    breakEngine = new BreakEngine(20 * 60, 15);

    mode = "calibrating";
    calibSamples = [];
    calibStart = performance.now() / 1000;
    baseline = null;
    sessionStart = performance.now() / 1000;
    lastLogTime = 0;

    statusEl.textContent = "Status: Calibrating — sit normally for 5 seconds";
    video.addEventListener("loadeddata", () => requestAnimationFrame(loop), { once: true });
}

function stopTracking() {
    if (stream) stream.getTracks().forEach(t => t.stop());
    mode = "idle";
    fetch("/api/end-session", { method: "POST" });
    statusEl.textContent = "Status: Stopped";
    postureEl.textContent = "Posture: —";
    eyeEl.textContent = "Eye strain: —";
    alertEl.textContent = "";
}

let lastVideoTime = -1;

function loop() {
    if (mode === "idle") return;

    if (video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;
        const now = performance.now() / 1000;
        const poseResult = poseLandmarker.detectForVideo(video, performance.now());
        const faceResult = faceLandmarker.detectForVideo(video, performance.now());

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (poseResult.landmarks?.[0]) {
            drawingUtils.drawLandmarks(poseResult.landmarks[0], { radius: 3, color: "#00FF00" });
            drawingUtils.drawConnectors(poseResult.landmarks[0], PoseLandmarker.POSE_CONNECTIONS, { color: "#00FF00" });
        }

        if (mode === "calibrating") {
            handleCalibration(poseResult, now);
        } else if (mode === "tracking") {
            handleTracking(poseResult, faceResult, now);
        }
    }
    requestAnimationFrame(loop);
}

function handleCalibration(poseResult, now) {
    if (poseResult.landmarks?.[0]) calibSamples.push(computePostureMetrics(poseResult.landmarks[0]));

    const elapsed = now - calibStart;
    statusEl.textContent = `Status: Calibrating — ${Math.max(0, CALIBRATION_SECONDS - elapsed).toFixed(0)}s left`;

    if (elapsed >= CALIBRATION_SECONDS) {
        if (calibSamples.length > 0) {
            baseline = calibrateBaseline(calibSamples);
            mode = "tracking";
            statusEl.textContent = "Status: Tracking…";
        } else {
            statusEl.textContent = "Status: Calibration failed — no pose detected";
            stopTracking();
        }
    }
}

function handleTracking(poseResult, faceResult, now) {
    let postureBadSustained = false;
    let eyeFatigue = false;
    const metrics = {};

    if (poseResult.landmarks?.[0] && baseline) {
        const m = computePostureMetrics(poseResult.landmarks[0]);
        const bad = isSlouching(m, baseline);
        postureBadSustained = postureTracker.update(bad);
        metrics.neck_angle = m.neckAngle;
        metrics.torso_angle = m.torsoAngle;

        const neckDev = m.neckAngle - baseline.neckAngle;
        const torsoDev = m.torsoAngle - baseline.torsoAngle;
        postureEl.textContent = `Posture: neck_dev=${neckDev.toFixed(1)}° torso_dev=${torsoDev.toFixed(1)}°` + (postureBadSustained ? "  ⚠ SLOUCHING" : "");
    } else {
        postureEl.textContent = "Posture: no pose detected";
    }

    if (faceResult.faceLandmarks?.[0]) {
        const landmarks = faceResult.faceLandmarks[0];
        const ear = averageEAR(landmarks);
        blinkCounter.update(ear, now);
        perclosTracker.update(ear, EAR_THRESHOLD, now);
        const blinkRate = blinkCounter.blinksPerMinute();
        const perclos = perclosTracker.perclos();

        eyeFatigue = computeEyeFatigueSignal(perclos, blinkRate, now - sessionStart);
        metrics.ear = ear;
        metrics.blink_rate = blinkRate;
        metrics.perclos = perclos;

        eyeEl.textContent = `Eye strain: EAR=${ear.toFixed(2)}  blinks/min=${blinkRate}  PERCLOS=${(perclos * 100).toFixed(1)}%`;
    } else {
        eyeEl.textContent = "Eye strain: no face detected";
    }

    if (now - lastLogTime >= 1.0 && Object.keys(metrics).length > 0) {
        fetch("/api/log-metrics", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(metrics) });
        lastLogTime = now;
    }

    const result = breakEngine.check(postureBadSustained, eyeFatigue);
    if (result) {
        alertEl.textContent = `BREAK TRIGGERED — ${result.triggerSource}`;
        fetch("/api/log-break", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ trigger_source: result.triggerSource }) });
        showBreakPopup(result.triggerSource);
        showBrowserNotification(result.triggerSource);
    }
}

function showBrowserNotification(source) {
    if (Notification.permission === "granted") {
        const [, headline, subtext] = MESSAGES[source] || MESSAGES.timer;
        new Notification("FocusGuard — " + headline, { body: subtext });
    }
}

function showBreakPopup(source) {
    const [emoji, headline, subtext] = MESSAGES[source] || MESSAGES.timer;
    const popup = document.getElementById("breakPopup");
    document.getElementById("popupEmoji").textContent = emoji;
    document.getElementById("popupHeadline").textContent = headline;
    document.getElementById("popupSubtext").textContent = subtext;

    let remaining = BREAK_DURATION_SECONDS;
    document.getElementById("popupCountdown").textContent = remaining;
    popup.style.display = "block";

    const tick = setInterval(() => {
        remaining--;
        document.getElementById("popupCountdown").textContent = Math.max(0, remaining);
        if (remaining <= 0) {
            clearInterval(tick);
            popup.style.display = "none";
        }
    }, 1000);
}