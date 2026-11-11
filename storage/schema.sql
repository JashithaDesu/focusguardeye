CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    start_time REAL NOT NULL,
    end_time REAL
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    neck_angle REAL,
    torso_angle REAL,
    ear REAL,
    blink_rate REAL,
    perclos REAL,
    looking_away INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS breaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    trigger_time REAL NOT NULL,
    trigger_source TEXT NOT NULL,
    compliant INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);