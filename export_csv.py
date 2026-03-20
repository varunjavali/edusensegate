import csv
import sqlite3
from datetime import datetime

CSV_FILE = "attendance_log.csv"

def export_today():
    today = datetime.now().strftime("%Y-%m-%d")
    day_name = datetime.now().strftime("%A")

    conn = sqlite3.connect("attendance.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT roll_no, name, SUM(duration)
    FROM attendance_sessions
    WHERE date=?
    GROUP BY roll_no
    """, (today,))

    rows = cur.fetchall()
    conn.close()

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        for roll, name, total_sec in rows:
            total_min = total_sec // 60
            writer.writerow([
                roll,
                name,
                today,
                day_name,
                f"{total_min} min"
            ])

def calculate_weekly_percentage():
    conn = sqlite3.connect("attendance.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT roll_no, name, COUNT(DISTINCT date)
    FROM attendance_sessions
    GROUP BY roll_no
    """)
    data = cur.fetchall()
    conn.close()

    WEEK_CLASSES = 5  # configurable

    report = []
    for roll, name, days_present in data:
        percent = (days_present / WEEK_CLASSES) * 100
        status = "RED" if percent < 60 else "OK"
        report.append((roll, name, percent, status))

    return report
