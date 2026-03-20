import sqlite3, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "attendance.db")
conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM attendance_sessions WHERE in_time != '—' AND out_time IS NULL")
conn.commit()
conn.close()
print("✅ Cleared stale records")