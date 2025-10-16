import sqlite3
import time
from datetime import datetime
from pathlib import Path
from threading import Event


DB_PATH = Path(__file__).with_name("schedule.db")
STOP = Event()


### Cursed decorator to manage DB connection ###
def with_conn(fn):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)  # autocommit
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.row_factory = sqlite3.Row
            return fn(conn, *args, **kwargs)
        finally:
            conn.close()

    return wrapper


@with_conn
def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            run_time_utc TEXT NOT NULL,
            payload TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_schedule_time
        ON schedule (run_time_utc)
        """
    )


@with_conn
def insert_job(conn, label, payload=None):
    conn.execute(
        "INSERT INTO schedule (label, run_time_utc, payload) VALUES (?, ?, ?)",
        (label, datetime.utcnow().isoformat(timespec="seconds") + "Z", payload),
    )


@with_conn
def count_rows(conn):
    cur = conn.execute("SELECT COUNT(*) AS n FROM schedule")
    return cur.fetchone()["n"]


@with_conn
def latest_rows(conn, limit=5):
    cur = conn.execute(
        "SELECT id, label, run_time_utc, COALESCE(payload, '') AS payload "
        "FROM schedule ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return cur.fetchall()


