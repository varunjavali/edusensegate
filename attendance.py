import sqlite3, csv
from datetime import datetime

def mark_attendance(roll, status):
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    conn = sqlite3.connect("attendance.db")
    cur = conn.cursor()

    if status == "IN":
        cur.execute("""
            INSERT INTO attendance
            (roll_no, date, in_time, out_time, duration)
            VALUES (?, ?, ?, NULL, NULL)
        """, (roll, date, time))
    else:
        cur.execute("""
            UPDATE attendance
            SET out_time=?, duration=(
                strftime('%s', ?) - strftime('%s', in_time)
            )
            WHERE roll_no=? AND date=? AND out_time IS NULL
        """, (time, time, roll, date))

    conn.commit()
    conn.close()

def export_csv():
    conn = sqlite3.connect("attendance.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendance")
    rows = cur.fetchall()
    conn.close()

    with open("attendance.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Roll", "Date", "In", "Out", "Seconds"])
        writer.writerows(rows)
