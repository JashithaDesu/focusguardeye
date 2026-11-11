import sqlite3
import time

import pytest

from reports.weekly import generate_report
from storage.db import MetricsStore


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


def _record_session(db_path, user_id, neck_angle, breaks):
    store = MetricsStore(db_path)
    now = time.time()
    sid = store.start_session(now, user_id=user_id)
    store.log_metrics(sid, now, neck_angle=neck_angle, perclos=0.1)
    for _ in range(breaks):
        store.log_break(sid, now, "timer")
    store.close()
    return sid


# ---------- Reports ----------

def test_report_only_contains_the_users_own_data(db_path, tmp_path):
    _record_session(db_path, user_id=1, neck_angle=5, breaks=1)
    _record_session(db_path, user_id=2, neck_angle=40, breaks=3)

    alice = generate_report(db_path, user_id=1, out_path=str(tmp_path / "a.png"))
    bob = generate_report(db_path, user_id=2, out_path=str(tmp_path / "b.png"))

    assert (alice["metrics_count"], alice["breaks_count"]) == (1, 1)
    assert (bob["metrics_count"], bob["breaks_count"]) == (1, 3)
    assert alice["wellness_score"] > bob["wellness_score"]  # Alice sat straighter


def test_a_user_with_no_data_gets_an_empty_report(db_path, tmp_path):
    _record_session(db_path, user_id=1, neck_angle=5, breaks=1)
    report = generate_report(db_path, user_id=99, out_path=str(tmp_path / "c.png"))
    assert report["metrics_count"] == 0
    assert report["wellness_score"] is None
    assert report["chart_path"] is None


def test_old_chart_is_removed_when_there_is_no_recent_data(db_path, tmp_path):
    chart = tmp_path / "old.png"
    chart.write_bytes(b"stale")
    generate_report(db_path, user_id=99, out_path=str(chart))
    assert not chart.exists()


# ---------- Database upgrade ----------

def test_old_database_is_upgraded_without_losing_data(tmp_path):
    db = str(tmp_path / "old.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, start_time REAL NOT NULL, end_time REAL)")
    conn.execute("INSERT INTO sessions (start_time) VALUES (1.0)")
    conn.commit()
    conn.close()

    store = MetricsStore(db)
    new_sid = store.start_session(2.0, user_id=7)
    rows = store.conn.execute("SELECT id, user_id FROM sessions ORDER BY id").fetchall()
    store.close()
    assert rows == [(1, None), (new_sid, 7)]


def test_session_ownership_check(db_path):
    sid = _record_session(db_path, user_id=1, neck_angle=5, breaks=0)
    store = MetricsStore(db_path)
    assert store.session_belongs_to(sid, 1) is True
    assert store.session_belongs_to(sid, 2) is False
    store.close()


# ---------- Web app ----------

@pytest.fixture
def client(db_path, tmp_path, monkeypatch):
    from webapp import server
    monkeypatch.setattr(server, "DB_PATH", db_path)
    monkeypatch.setattr(server, "PROJECT_ROOT", str(tmp_path))
    server.app.config["TESTING"] = True
    return server.app.test_client()


def _signup_and_login(client, email):
    client.post("/signup", data={"email": email, "password": "secret1"})
    client.post("/login", data={"email": email, "password": "secret1"})


def _track(client, neck_angle, breaks):
    client.post("/api/start-session")
    client.post("/api/log-metrics", json={"neck_angle": neck_angle, "perclos": 0.1})
    for _ in range(breaks):
        client.post("/api/log-break", json={"trigger_source": "timer"})
    client.post("/api/end-session")


def test_web_users_see_only_their_own_reports(client):
    _signup_and_login(client, "alice@example.com")
    _track(client, neck_angle=5, breaks=1)
    client.get("/logout")

    _signup_and_login(client, "bob@example.com")
    _track(client, neck_angle=40, breaks=3)
    bob_page = client.get("/reports").get_data(as_text=True)
    client.get("/logout")

    _signup_and_login(client, "alice@example.com")
    alice_page = client.get("/reports").get_data(as_text=True)

    assert "Breaks triggered: 1" in alice_page
    assert "Breaks triggered: 3" in bob_page


def test_chart_requires_login(client):
    assert client.get("/report-chart").status_code == 401


@pytest.mark.parametrize("endpoint", ["/api/start-session", "/api/end-session", "/api/log-metrics", "/api/log-break"])
def test_data_endpoints_require_login(client, endpoint):
    assert client.post(endpoint, json={}).status_code == 401


def test_secret_key_is_not_the_old_hardcoded_value():
    from webapp import server
    assert server.app.secret_key != "dev-secret-change-this-later"
