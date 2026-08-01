import sys
import os

# Allow this service to import your existing reports/weekly.py without duplicating logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, send_file, request
from app import generate_report

app = Flask(__name__)

DB_PATH = os.environ.get("FOCUSGUARD_DB_PATH", "/data/focusguard.db")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/report/weekly")
def weekly_report():
    days = request.args.get("days", default=7, type=int)

    if not os.path.exists(DB_PATH):
        return jsonify({"error": f"Database not found at {DB_PATH}"}), 404

    result = generate_report(db_path=DB_PATH, days=days)

    # Don't return the raw file path from the container's filesystem —
    # give the caller a URL they can actually fetch instead
    result["chart_url"] = "/report/weekly/chart" if result.get("chart_path") else None
    result.pop("chart_path", None)

    return jsonify(result)


@app.route("/report/weekly/chart")
def weekly_chart():
    chart_path = "reports/output/weekly_trends.png"
    if not os.path.exists(chart_path):
        return jsonify({"error": "No chart generated yet — call /report/weekly first"}), 404
    return send_file(chart_path, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)