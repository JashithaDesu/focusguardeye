import sqlite3
import hashlib
import os
import time


def _hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    ).hex()
    return pwd_hash, salt


class UserStore:
    def __init__(self, db_path="focusguard.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        self.conn.commit()

    def create_user(self, email, password):
        email = email.strip().lower()
        if not email or "@" not in email:
            return False, "Enter a valid email address"
        if len(password) < 6:
            return False, "Password must be at least 6 characters"

        pwd_hash, salt = _hash_password(password)
        try:
            self.conn.execute(
                "INSERT INTO users (email, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                (email, pwd_hash, salt, time.time()),
            )
            self.conn.commit()
            return True, "Account created — you can log in now"
        except sqlite3.IntegrityError:
            return False, "An account with this email already exists"

    def verify_user(self, email, password):
        email = email.strip().lower()
        row = self.conn.execute(
            "SELECT password_hash, salt FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return False, "No account found with this email"
        stored_hash, salt = row
        check_hash, _ = _hash_password(password, salt)
        if check_hash == stored_hash:
            return True, "Login successful"
        return False, "Incorrect password"

    def close(self):
        self.conn.close()