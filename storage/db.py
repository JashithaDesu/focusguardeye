import sqlite3
import os


class MetricsStore:
    def __init__(self, db_path="focusguard.db"):
        self.conn = sqlite3.connect(db_path)
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path) as f:
            self.conn.executescript(f.read())
        self._migrate()

    def _migrate(self):
        # Databases created before sessions had an owner are upgraded in place.
        # Their old sessions keep user_id NULL, so they are never shown to any user.
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(sessions)")]
        if "user_id" not in columns:
            self.conn.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER")
            self.conn.commit()

    def start_session(self, start_time, user_id=None):
        cur = self.conn.execute(
            "INSERT INTO sessions (user_id, start_time) VALUES (?, ?)", (user_id, start_time)
        )
        self.conn.commit()
        return cur.lastrowid

    def session_belongs_to(self, session_id, user_id):
        row = self.conn.execute(
            "SELECT 1 FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id)
        ).fetchone()
        return row is not None

    def end_session(self, session_id, end_time):
        self.conn.execute(
            "UPDATE sessions SET end_time = ? WHERE id = ?", (end_time, session_id)
        )
        self.conn.commit()

    def log_metrics(self, session_id, timestamp, neck_angle=None, torso_angle=None,
                     ear=None, blink_rate=None, perclos=None, looking_away=False):
        self.conn.execute(
            """INSERT INTO metrics
               (session_id, timestamp, neck_angle, torso_angle, ear, blink_rate, perclos, looking_away)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, timestamp, neck_angle, torso_angle, ear, blink_rate, perclos, int(looking_away)),
        )
        self.conn.commit()

    def log_break(self, session_id, trigger_time, trigger_source, compliant=True):
        self.conn.execute(
            "INSERT INTO breaks (session_id, trigger_time, trigger_source, compliant) VALUES (?, ?, ?, ?)",
            (session_id, trigger_time, trigger_source, int(compliant)),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()