"""SQLite layer — stdlib only, single file DB, zero cost."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import DATA_DIR

DB_PATH = Path(DATA_DIR) / "bolkhata.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS shopkeeper (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  shop_name TEXT DEFAULT '',
  language_pref TEXT DEFAULT 'hi-IN',
  voice_profile_path TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS customer (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shopkeeper_id INTEGER NOT NULL REFERENCES shopkeeper(id),
  name TEXT NOT NULL,
  phone TEXT DEFAULT '',
  persona TEXT DEFAULT '',
  voice_id TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS entry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shopkeeper_id INTEGER NOT NULL REFERENCES shopkeeper(id),
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  type TEXT NOT NULL CHECK (type IN ('UDHAAR', 'PAYMENT')),
  amount REAL NOT NULL,
  items_text TEXT DEFAULT '',
  raw_transcript TEXT DEFAULT '',
  status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SETTLED')),
  created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS promise (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  amount REAL NOT NULL,
  due_date TEXT NOT NULL,
  promised_on_call_id INTEGER,
  status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'KEPT', 'BROKEN')),
  created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS call_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  started_at TEXT DEFAULT (datetime('now', 'localtime')),
  duration_sec INTEGER DEFAULT 0,
  transcript TEXT DEFAULT '[]',
  summary TEXT DEFAULT '',
  sentiment TEXT DEFAULT 'neutral',
  excuse_type TEXT DEFAULT '',
  outcome TEXT DEFAULT 'NO_ANSWER',
  promise_id INTEGER
);

CREATE TABLE IF NOT EXISTS day_summary (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day TEXT NOT NULL,
  cash_in REAL DEFAULT 0,
  udhaar_out REAL DEFAULT 0,
  briefing_text TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS claim (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  amount REAL NOT NULL,
  items_text TEXT DEFAULT '',
  status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
  created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
