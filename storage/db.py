import sqlite3
import os


class MetricsStore:
    def __init__(self, db_path="focusguard.db"):
        self.conn = sqlite3.connect(db_path)
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path) as f:
            self.conn.executescript(f.read())

    def start_session(self, start_time):
        cur = self.conn.execute(
            "INSERT INTO sessions (start_time) VALUES (?)", (start_time,)
        )
        self.conn.commit()
        return cur.lastrowid

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