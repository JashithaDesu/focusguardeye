from plyer import notification

def send_break_alert(trigger_source="manual"):
    messages = {
        "timer": "Time for your 20-20-20 break — look at something 20 ft away.",
        "posture_signal": "Posture check — you've been slouching for a while. Sit up and take a break.",
        "eye_fatigue_signal": "Your eyes look tired — step away from the screen for 20 seconds.",
        "manual": "This is a test notification from FocusGuard.",
    }
    notification.notify(
        title="FocusGuard",
        message=messages.get(trigger_source, "Time for a break!"),
        timeout=10,
    )