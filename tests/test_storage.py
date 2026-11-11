import sqlite3

import pytest

from storage.auth import UserStore
from storage.db import MetricsStore


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


# ---------- UserStore ----------

def test_signup_then_login(db_path):
    store = UserStore(db_path)
    assert store.create_user("Ana@Example.com ", "secret1")[0] is True
    assert store.verify_user("ana@example.com", "secret1")[0] is True


def test_wrong_password_is_rejected(db_path):
    store = UserStore(db_path)
    store.create_user("ana@example.com", "secret1")
    assert store.verify_user("ana@example.com", "secret2")[0] is False


def test_duplicate_email_is_rejected(db_path):
    store = UserStore(db_path)
    store.create_user("ana@example.com", "secret1")
    assert store.create_user("ANA@example.com", "other12")[0] is False


@pytest.mark.parametrize("email, password", [("", "secret1"), ("not-an-email", "secret1"), ("a@b.com", "12345")])
def test_invalid_signups_are_rejected(db_path, email, password):
    assert UserStore(db_path).create_user(email, password)[0] is False


def test_passwords_are_not_stored_in_plain_text(db_path):
    UserStore(db_path).create_user("ana@example.com", "secret1")
    row = sqlite3.connect(db_path).execute("SELECT password_hash, salt FROM users").fetchone()
    assert "secret1" not in row
    assert len(row[1]) == 32  # 16 random bytes as hex


def test_same_password_gets_different_hashes(db_path):
    store = UserStore(db_path)
    store.create_user("a@example.com", "secret1")
    store.create_user("b@example.com", "secret1")
    hashes = sqlite3.connect(db_path).execute("SELECT password_hash FROM users").fetchall()
    assert hashes[0] != hashes[1]


# ---------- MetricsStore ----------

def test_session_metrics_and_breaks_are_saved(db_path):
    store = MetricsStore(db_path)
    sid = store.start_session(100.0)
    store.log_metrics(sid, 101.0, neck_angle=12.5, perclos=0.1)
    store.log_break(sid, 102.0, "timer")
    store.end_session(sid, 200.0)
    store.close()

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT start_time, end_time FROM sessions").fetchone() == (100.0, 200.0)
    assert conn.execute("SELECT neck_angle, perclos, looking_away FROM metrics").fetchone() == (12.5, 0.1, 0)
    assert conn.execute("SELECT trigger_source, compliant FROM breaks").fetchone() == ("timer", 1)


def test_writing_after_close_raises(db_path):
    """Why DashboardPage.stop_tracking() must clear self.store after closing it:
    a second stop (Stop, then Logout) would otherwise crash here."""
    store = MetricsStore(db_path)
    sid = store.start_session(1.0)
    store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        store.end_session(sid, 2.0)
