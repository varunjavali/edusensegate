import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, threading, time
from datetime import datetime
from scanner import get_live_macs
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")
from ui_approve import approve_window
from export_csv import export_today

# ------------------------------------------------------------------
# ACTIVE  : roll_no -> datetime when they connected (open session)
# LAST_SEEN: roll_no -> datetime when last seen on network
# GRACE_SECONDS: seconds before "Disconnected" becomes permanent
# ------------------------------------------------------------------
ACTIVE = {}
LAST_SEEN = {}
GRACE_SECONDS = 60  # 1 minute grace — adjust as needed


def faculty_panel():
    root = tk.Tk()
    root.title("EduSense Gate – Faculty Dashboard")
    root.geometry("1000x600")
    root.configure(bg="#f0f4f8")

    # ── LOGIN ──────────────────────────────────────────────────────
    login_frame = tk.Frame(root, bg="#f0f4f8")
    login_frame.pack(expand=True)

    tk.Label(login_frame, text="EduSense Gate",
             font=("Segoe UI", 22, "bold"), bg="#f0f4f8", fg="#1a1a2e").pack(pady=10)
    tk.Label(login_frame, text="Faculty Login",
             font=("Segoe UI", 13), bg="#f0f4f8", fg="#555").pack(pady=2)

    tk.Label(login_frame, text="Username", bg="#f0f4f8").pack(pady=(15, 2))
    username = tk.Entry(login_frame, font=("Segoe UI", 12), width=28)
    username.pack()

    tk.Label(login_frame, text="Password", bg="#f0f4f8").pack(pady=(10, 2))
    password = tk.Entry(login_frame, show="*", font=("Segoe UI", 12), width=28)
    password.pack()

    def do_login():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM faculty WHERE username=? AND password=?",
            (username.get(), password.get())
        )
        if cur.fetchone():
            login_frame.destroy()
            open_dashboard()
        else:
            messagebox.showerror("Error", "Invalid login")
        conn.close()

    tk.Button(login_frame, text="Login", bg="#0078D7", fg="white",
              font=("Segoe UI", 11, "bold"), width=20,
              command=do_login).pack(pady=20)

    # ── DASHBOARD ─────────────────────────────────────────────────
    def open_dashboard():
        frame = tk.Frame(root, bg="#f0f4f8")
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Top bar
        top = tk.Frame(frame, bg="#f0f4f8")
        top.pack(fill="x")
        tk.Label(top, text="📡 Live Attendance Dashboard",
                 font=("Segoe UI", 17, "bold"),
                 bg="#f0f4f8").pack(side="left")
        tk.Button(top, text="Logout", bg="#e74c3c", fg="white",
                  font=("Segoe UI", 10),
                  command=lambda: [setattr(root, '_quit', True), root.destroy()]
                  ).pack(side="right")

        # Buttons row
        btn_frame = tk.Frame(frame, bg="#f0f4f8")
        btn_frame.pack(fill="x", pady=8)

        tk.Button(btn_frame, text="👨‍🏫 Approve Students",
                  bg="#8e44ad", fg="white", font=("Segoe UI", 10, "bold"),
                  command=lambda: approve_window(root)).pack(side="left", padx=4)

        tk.Button(btn_frame, text="💾 Export CSV Today",
                  bg="#27ae60", fg="white", font=("Segoe UI", 10, "bold"),
                  command=export_today).pack(side="left", padx=4)

        # Status bar
        status_var = tk.StringVar(value="🔄 Scanning...")
        tk.Label(frame, textvariable=status_var,
                 font=("Segoe UI", 9), bg="#f0f4f8", fg="#777").pack(anchor="w")

        # ── TABLE ──
        cols = ("Roll No", "Name", "Date", "In Time", "Out Time", "Duration", "Status")
        table = ttk.Treeview(frame, columns=cols, show="headings", height=18)

        widths = [100, 160, 100, 90, 90, 90, 160]
        for c, w in zip(cols, widths):
            table.heading(c, text=c)
            table.column(c, width=w, anchor="center")

        # Color tags
        table.tag_configure("present",      background="#d4edda", foreground="#155724")
        table.tag_configure("disconnected", background="#fff3cd", foreground="#856404")
        table.tag_configure("absent",       background="#f8d7da", foreground="#721c24")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scroll.set)
        table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        # ── BACKGROUND SCAN LOOP (every 10s) ──────────────────────
        def scan_loop():
            while True:
                try:
                    live_macs = get_live_macs()   # set of MAC addresses alive NOW
                    now = datetime.now()
                    date = now.strftime("%Y-%m-%d")
                    time_now = now.strftime("%H:%M:%S")

                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()

                    cur.execute("""
                        SELECT roll_no, name, mac_address
                        FROM students WHERE approved=1 AND mac_address IS NOT NULL
                    """)
                    students = cur.fetchall()

                    for roll, name, mac in students:
                        if not mac:
                            continue

                        # Normalize MAC format — handle both d6-24-3a and d6:24:3a
                        mac_norm = mac.lower().replace("-", ":").strip()

                        if mac_norm in live_macs:
                            # ── STUDENT IS ON NETWORK ──
                            LAST_SEEN[roll] = now

                            # Check if there's already an open session today
                            cur.execute("""
                                SELECT id FROM attendance_sessions
                                WHERE roll_no=? AND date=? AND out_time IS NULL
                            """, (roll, date))
                            open_session = cur.fetchone()

                            if not open_session:
                                # New connection — open session
                                ACTIVE[roll] = now
                                cur.execute("""
                                    INSERT INTO attendance_sessions
                                    (roll_no, name, date, in_time, out_time, duration, status)
                                    VALUES (?, ?, ?, ?, NULL, NULL, 'present')
                                """, (roll, name, date, time_now))
                                print(f"✅ {roll} CONNECTED at {time_now}")

                            elif roll not in ACTIVE:
                                # Reconnected after brief disconnect — reopen
                                ACTIVE[roll] = now

                        else:
                            # ── STUDENT NOT ON NETWORK ──
                            if roll in ACTIVE:
                                # Was connected — now gone
                                in_time_dt = ACTIVE[roll]
                                duration = int((now - in_time_dt).total_seconds())

                                cur.execute("""
                                    UPDATE attendance_sessions
                                    SET out_time=?, duration=?, status='disconnected'
                                    WHERE roll_no=? AND date=? AND out_time IS NULL
                                """, (time_now, duration, roll, date))

                                ACTIVE.pop(roll, None)
                                LAST_SEEN[roll] = now
                                print(f"🔴 {roll} DISCONNECTED at {time_now}")

                    conn.commit()
                    conn.close()
                    status_var.set(f"✅ Last scan: {time_now}  |  Live: {len(live_macs)} devices")

                except Exception as e:
                    status_var.set(f"⚠️ Scan error: {e}")
                    print(f"Scan error: {e}")

                time.sleep(10)

        # ── UI REFRESH (every 2s) ──────────────────────────────────
        def refresh_ui():
            table.delete(*table.get_children())
            now = datetime.now()
            date = now.strftime("%Y-%m-%d")

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            # Get latest session per student
            cur.execute("""
                SELECT s.roll_no, s.name, s.date, s.in_time, s.out_time,
                       s.duration, s.status
                FROM attendance_sessions s
                INNER JOIN (
                    SELECT roll_no, MAX(id) AS max_id
                    FROM attendance_sessions
                    WHERE date=?
                    GROUP BY roll_no
                ) latest ON s.roll_no = latest.roll_no AND s.id = latest.max_id
                ORDER BY s.roll_no
            """, (date,))
            sessions = cur.fetchall()

            # Track who has a session today
            seen_rolls = set()
            for roll, name, d, in_time, out_time, duration, status in sessions:
                seen_rolls.add(roll)

                # Determine display status
                if out_time is None and roll in ACTIVE:
                    display_status = "🟢 In Class"
                    tag = "present"
                elif out_time is not None:
                    last = LAST_SEEN.get(roll)
                    if last:
                        secs_ago = int((now - last).total_seconds())
                        if secs_ago <= GRACE_SECONDS:
                            display_status = f"🟡 Disconnected ({secs_ago}s ago)"
                            tag = "disconnected"
                        else:
                            mins_ago = secs_ago // 60
                            display_status = f"🔴 Left {mins_ago}m ago"
                            tag = "absent"
                    else:
                        display_status = "🔴 Left"
                        tag = "absent"
                else:
                    display_status = "🟡 Disconnected"
                    tag = "disconnected"

                dur_str = f"{duration}s" if duration else "—"

                table.insert("", "end",
                             values=(roll, name, d, in_time, out_time or "—", dur_str, display_status),
                             tags=(tag,))

            # Show ALL approved students — those with no session today show as Absent
            cur.execute("""
                SELECT roll_no, name FROM students
                WHERE approved=1
            """)
            for roll, name in cur.fetchall():
                if roll not in seen_rolls:
                    table.insert("", "end",
                                 values=(roll, name, date, "—", "—", "—", "🔴 Absent"),
                                 tags=("absent",))

            conn.close()
            root.after(2000, refresh_ui)

        threading.Thread(target=scan_loop, daemon=True).start()
        refresh_ui()

    root.mainloop()


if __name__ == "__main__":
    faculty_panel()