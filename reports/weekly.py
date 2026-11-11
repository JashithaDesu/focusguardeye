import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # renders to file without needing a display window
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta

from storage.db import MetricsStore


def load_data(db_path="focusguard.db", days=7, user_id=None):
    """Pulls metrics and breaks from the last N days into pandas DataFrames.
    With a user_id, only that user's sessions are included."""
    MetricsStore(db_path).close()  # creates/upgrades the tables, so a brand-new database doesn't crash
    conn = sqlite3.connect(db_path)
    cutoff = (datetime.now() - timedelta(days=days)).timestamp()

    if user_id is None:
        metrics = pd.read_sql_query(
            "SELECT * FROM metrics WHERE timestamp >= ?", conn, params=(cutoff,)
        )
        breaks = pd.read_sql_query(
            "SELECT * FROM breaks WHERE trigger_time >= ?", conn, params=(cutoff,)
        )
    else:
        metrics = pd.read_sql_query(
            """SELECT m.* FROM metrics m JOIN sessions s ON m.session_id = s.id
               WHERE m.timestamp >= ? AND s.user_id = ?""",
            conn, params=(cutoff, user_id),
        )
        breaks = pd.read_sql_query(
            """SELECT b.* FROM breaks b JOIN sessions s ON b.session_id = s.id
               WHERE b.trigger_time >= ? AND s.user_id = ?""",
            conn, params=(cutoff, user_id),
        )
    conn.close()

    if not metrics.empty:
        metrics["date"] = pd.to_datetime(metrics["timestamp"], unit="s").dt.date
    if not breaks.empty:
        breaks["date"] = pd.to_datetime(breaks["trigger_time"], unit="s").dt.date

    return metrics, breaks


def compute_wellness_score(metrics, breaks):
    if metrics.empty:
        return None

    avg_neck_angle = metrics["neck_angle"].dropna().mean()
    avg_perclos = metrics["perclos"].dropna().mean()
    compliance_rate = breaks["compliant"].mean() if not breaks.empty else 1.0

    avg_neck_angle = 0 if pd.isna(avg_neck_angle) else avg_neck_angle
    avg_perclos = 0 if pd.isna(avg_perclos) else avg_perclos
    compliance_rate = 0 if pd.isna(compliance_rate) else compliance_rate

    posture_score = max(0, 100 - avg_neck_angle * 2)
    eye_score = max(0, 100 - avg_perclos * 200)
    break_score = compliance_rate * 100

    return round(0.4 * posture_score + 0.4 * eye_score + 0.2 * break_score, 1)


def summarize_trigger_sources(breaks):
    if breaks.empty:
        return {}
    return breaks["trigger_source"].value_counts().to_dict()


def render_weekly_charts(metrics, out_path="reports/output/weekly_trends.png"):
    if metrics.empty:
        print("No metrics data available to chart yet.")
        if os.path.exists(out_path):
            os.remove(out_path)  # don't keep showing an old chart when there's no recent data
        return None
    os.makedirs(os.path.dirname(out_path), exist_ok=True)  # NEW — ensures the folder exists before saving
    daily = metrics.groupby("date").agg(
        avg_neck_angle=("neck_angle", "mean"),
        avg_torso_angle=("torso_angle", "mean"),
        avg_perclos=("perclos", "mean"),
        avg_blink_rate=("blink_rate", "mean"),
    )

    fig, axes = plt.subplots(3, 1, figsize=(8, 10))

    daily["avg_neck_angle"].plot(ax=axes[0], marker="o", title="Neck Angle (daily avg, degrees)")
    axes[0].set_ylabel("degrees")

    daily["avg_perclos"].plot(ax=axes[1], marker="o", color="orange", title="PERCLOS (daily avg)")
    axes[1].set_ylabel("fraction closed")

    daily["avg_blink_rate"].plot(ax=axes[2], marker="o", color="green", title="Blink Rate (daily avg, blinks/min)")
    axes[2].set_ylabel("blinks/min")

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close(fig)
    print(f"Chart saved to {out_path}")
    return out_path


def chart_path_for(user_id=None):
    name = "weekly_trends.png" if user_id is None else f"weekly_trends_user{int(user_id)}.png"
    return os.path.join("reports", "output", name)


def generate_report(db_path="focusguard.db", days=7, user_id=None, out_path=None):
    metrics, breaks = load_data(db_path, days, user_id)
    score = compute_wellness_score(metrics, breaks)
    sources = summarize_trigger_sources(breaks)
    chart_path = render_weekly_charts(metrics, out_path or chart_path_for(user_id))

    print("\n=== FocusGuard Weekly Report ===")
    print(f"Period: last {days} day(s)")
    print(f"Metrics rows: {len(metrics)}  |  Break events: {len(breaks)}")
    print(f"Wellness Score: {score if score is not None else 'N/A — no data yet'}")
    print(f"Break triggers by source: {sources}")
    if chart_path:
        print(f"Trend chart: {chart_path}")
    print("================================\n")

    return {
        "wellness_score": score,
        "trigger_sources": sources,
        "chart_path": chart_path,
        "metrics_count": len(metrics),
        "breaks_count": len(breaks),
    }


if __name__ == "__main__":
    generate_report()