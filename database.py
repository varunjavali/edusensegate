import sqlite3, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "attendance.db")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS students (
    roll_no     TEXT PRIMARY KEY,
    name        TEXT,
    ip_address  TEXT,
    mac_address TEXT,
    approved    INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role     TEXT DEFAULT 'faculty'
)
""")

cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('faculty', 'faculty123', 'faculty')")

cur.execute("""
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no    TEXT,
    name       TEXT,
    date       TEXT,
    subject    TEXT,
    in_time    TEXT,
    out_time   TEXT,
    duration   INTEGER,
    status     TEXT DEFAULT 'present'
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no  TEXT,
    date     TEXT,
    in_time  TEXT,
    out_time TEXT,
    duration INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS class_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT,
    subject    TEXT,
    start_time TEXT,
    end_time   TEXT,
    duration   INTEGER,
    started_by TEXT,
    status     TEXT DEFAULT 'active'
)
""")

# Add subject column to existing tables if missing (migration)
try:
    cur.execute("ALTER TABLE attendance_sessions ADD COLUMN subject TEXT")
except: pass
try:
    cur.execute("ALTER TABLE class_sessions ADD COLUMN subject TEXT")
except: pass

conn.commit()
conn.close()

print("✅ Database ready")
print("   Admin login  : admin / admin123")
print("   Faculty login: faculty / faculty123")