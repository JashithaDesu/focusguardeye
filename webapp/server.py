import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, render_template, request, redirect, session, send_file, jsonify
from storage.auth import UserStore
from storage.db import MetricsStore
from reports.weekly import generate_report
import time

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "dev-secret-change-this-later"

DB_PATH = "focusguard.db"


def require_login():
    return "email" in session


@app.route("/")
def index():
    return redirect("/dashboard") if require_login() else redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        store = UserStore(DB_PATH)
        ok, message = store.verify_user(request.form["email"], request.form["password"])
        store.close()
        if ok:
            session["email"] = request.form["email"].strip().lower()
            return redirect("/dashboard")
        return render_template("login.html", error=message)
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        store = UserStore(DB_PATH)
        ok, message = store.create_user(request.form["email"], request.form["password"])
        store.close()
        if ok:
            return render_template("signup.html", message=message)
        return render_template("signup.html", error=message)
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
def dashboard():
    if not require_login():
        return redirect("/login")
    return render_template("dashboard.html")


@app.route("/profile")
def profile():
    if not require_login():
        return redirect("/login")
    name_part = session["email"].split("@")[0]
    display_name = name_part.replace(".", " ").replace("_", " ").title()
    return render_template("profile.html", display_name=display_name)


@app.route("/reports")
def reports():
    if not require_login():
        return redirect("/login")
    report = generate_report(db_path=DB_PATH, days=7)
    return render_template("reports.html", report=report)

@app.route("/report-chart")
def report_chart():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    chart_path = os.path.join(project_root, "reports", "output", "weekly_trends.png")
    if not os.path.exists(chart_path):
        return "No chart yet", 404
    return send_file(chart_path, mimetype="image/png")

@app.route("/api/start-session", methods=["POST"])
def api_start_session():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401
    store = MetricsStore(DB_PATH)
    session_id = store.start_session(time.time())
    store.close()
    session["active_session_id"] = session_id
    return jsonify({"session_id": session_id})


@app.route("/api/end-session", methods=["POST"])
def api_end_session():
    session_id = session.get("active_session_id")
    if session_id:
        store = MetricsStore(DB_PATH)
        store.end_session(session_id, time.time())
        store.close()
        session.pop("active_session_id", None)
    return jsonify({"status": "ended"})


@app.route("/api/log-metrics", methods=["POST"])
def api_log_metrics():
    session_id = session.get("active_session_id")
    if not session_id:
        return jsonify({"error": "no active session"}), 400
    data = request.get_json()
    store = MetricsStore(DB_PATH)
    store.log_metrics(
        session_id, time.time(),
        neck_angle=data.get("neck_angle"),
        torso_angle=data.get("torso_angle"),
        ear=data.get("ear"),
        blink_rate=data.get("blink_rate"),
        perclos=data.get("perclos"),
    )
    store.close()
    return jsonify({"status": "logged"})


@app.route("/api/log-break", methods=["POST"])
def api_log_break():
    session_id = session.get("active_session_id")
    if not session_id:
        return jsonify({"error": "no active session"}), 400
    data = request.get_json()
    store = MetricsStore(DB_PATH)
    store.log_break(session_id, time.time(), data.get("trigger_source", "unknown"))
    store.close()
    return jsonify({"status": "logged"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)