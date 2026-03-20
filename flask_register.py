from flask import Flask, request, render_template_string, redirect, url_for
import sqlite3, subprocess, re, os
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "attendance.db")

# ── HELPERS ────────────────────────────────────────────────────────
def get_mac(ip):
    try:
        out = subprocess.check_output("arp -a", shell=True).decode()
        m = re.search(rf"{ip}.*?([a-f0-9\-]{{17}})", out, re.I)
        return m.group(1).lower() if m else None
    except:
        return None

def get_db():
    return sqlite3.connect(DB_PATH)

# ── REGISTER PAGE ──────────────────────────────────────────────────
REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EduSense Gate - Register</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3;
           display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    .card { background: #161b22; border: 1px solid #30363d; padding: 32px 28px;
            border-radius: 16px; width: 100%; max-width: 380px; margin: 20px; }
    .logo { text-align: center; font-size: 1.3rem; font-weight: 700;
            margin-bottom: 6px; color: #e6edf3; }
    .sub  { text-align: center; color: #8b949e; font-size: 0.9rem; margin-bottom: 28px; }
    label { display: block; font-size: 0.82rem; color: #8b949e; margin-bottom: 5px;
            letter-spacing: 0.5px; text-transform: uppercase; }
    input { width: 100%; padding: 11px 14px; background: #0d1117; border: 1px solid #30363d;
            border-radius: 8px; font-size: 1rem; color: #e6edf3; margin-bottom: 18px; }
    input:focus { outline: none; border-color: #58a6ff; }
    .btn  { width: 100%; padding: 13px; background: #238636; color: white; border: none;
            border-radius: 8px; font-size: 1rem; font-weight: 700; cursor: pointer; }
    .btn:hover { background: #2ea043; }
    .msg  { margin-top: 18px; padding: 12px 14px; border-radius: 8px; font-size: 0.9rem; text-align:center; }
    .success { background: #0f2318; border: 1px solid #238636; color: #3fb950; }
    .error   { background: #1c0f0f; border: 1px solid #da3633; color: #f85149; }
    .class-link { display:block; text-align:center; margin-top:16px;
                  color:#58a6ff; font-size:0.9rem; text-decoration:none; }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">🎓 EduSense Gate</div>
    <div class="sub">Student Registration</div>
    <form method="post">
      <label>Roll No</label>
      <input name="roll" placeholder="e.g. 2024-CS-001" required>
      <label>Full Name</label>
      <input name="name" placeholder="Your full name" required>
      <button class="btn" type="submit">Register</button>
    </form>
    {% if msg %}
      <div class="msg {{ msg_class }}">{{ msg }}</div>
    {% endif %}
    <a class="class-link" href="/class">📡 Join Active Class →</a>
  </div>
</body>
</html>
"""

# ── CLASS JOIN PAGE ────────────────────────────────────────────────
CLASS_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EduSense Gate - Join Class</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3;
           display: flex; justify-content: center; align-items: flex-start;
           min-height: 100vh; padding: 30px 16px; }
    .wrap { width: 100%; max-width: 420px; }
    .header { text-align: center; margin-bottom: 28px; }
    .header .logo { font-size: 1.3rem; font-weight: 700; color: #e6edf3; }
    .header .sub  { color: #8b949e; font-size: 0.88rem; margin-top: 4px; }

    /* Student info card */
    .student-card {
      background: #161b22; border: 1px solid #30363d; border-radius: 12px;
      padding: 16px 18px; margin-bottom: 24px; display: flex; align-items: center; gap: 14px;
    }
    .avatar { width: 44px; height: 44px; background: #238636; border-radius: 50%;
              display: flex; align-items: center; justify-content: center;
              font-size: 1.3rem; flex-shrink: 0; }
    .stu-name { font-weight: 700; font-size: 1rem; color: #e6edf3; }
    .stu-roll { font-size: 0.82rem; color: #8b949e; margin-top: 2px; }

    /* Section label */
    .sec { font-size: 0.72rem; font-weight: 700; letter-spacing: 2px;
           text-transform: uppercase; color: #8b949e; margin-bottom: 12px; }

    /* Class button */
    .class-btn {
      display: block; width: 100%;
      background: #0f2318; border: 2px solid #238636;
      border-radius: 14px; padding: 20px 18px;
      margin-bottom: 12px; text-decoration: none;
      cursor: pointer; text-align: left;
      transition: all 0.2s;
    }
    .class-btn:hover { background: #1a3a28; border-color: #3fb950; transform: translateY(-1px); }
    .class-btn .subj { font-size: 1.15rem; font-weight: 700; color: #3fb950; margin-bottom: 4px; }
    .class-btn .meta { font-size: 0.82rem; color: #388e3c; }
    .class-btn .join-lbl {
      display: inline-block; margin-top: 12px;
      background: #238636; color: #fff; border: none;
      border-radius: 8px; padding: 10px 24px;
      font-size: 0.95rem; font-weight: 700; width: 100%; text-align: center;
    }

    /* Already joined */
    .joined-btn {
      display: block; width: 100%;
      background: #161b22; border: 2px solid #30363d;
      border-radius: 14px; padding: 20px 18px;
      margin-bottom: 12px; text-align: left;
    }
    .joined-btn .subj { font-size: 1.15rem; font-weight: 700; color: #8b949e; margin-bottom: 4px; }
    .joined-btn .meta { font-size: 0.82rem; color: #8b949e; }
    .joined-lbl {
      display: inline-block; margin-top: 12px;
      background: #21262d; color: #8b949e;
      border-radius: 8px; padding: 10px 24px;
      font-size: 0.9rem; font-weight: 600; width: 100%; text-align: center;
    }

    /* No class */
    .empty { background: #161b22; border: 2px dashed #30363d; border-radius: 14px;
             padding: 40px 20px; text-align: center; color: #8b949e; }
    .empty .icon { font-size: 2.5rem; margin-bottom: 10px; }
    .empty .title { font-size: 1rem; font-weight: 600; color: #e6edf3; margin-bottom: 6px; }
    .empty .hint  { font-size: 0.85rem; }

    /* Error / success */
    .msg  { padding: 14px; border-radius: 10px; font-size: 0.9rem; text-align:center; margin-bottom:16px; }
    .success { background: #0f2318; border: 1px solid #238636; color: #3fb950; }
    .error   { background: #1c0f0f; border: 1px solid #da3633; color: #f85149; }
    .warn    { background: #1c1a0f; border: 1px solid #9e6a03; color: #d29922; }

    .back { display:block; text-align:center; color:#58a6ff;
            font-size:0.85rem; margin-top:20px; text-decoration:none; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="logo">🎓 EduSense Gate</div>
      <div class="sub">Join Active Class</div>
    </div>

    {% if msg %}
      <div class="msg {{ msg_class }}">{{ msg }}</div>
    {% endif %}

    {% if not student %}
      <div class="empty">
        <div class="icon">🔒</div>
        <div class="title">Not Registered</div>
        <div class="hint">Your device is not registered or approved yet.<br>Please register first.</div>
      </div>
      <a class="back" href="/">← Register here</a>

    {% else %}
      <!-- Student info -->
      <div class="student-card">
        <div class="avatar">{{ student.name[0].upper() }}</div>
        <div>
          <div class="stu-name">{{ student.name }}</div>
          <div class="stu-roll">Roll No: {{ student.roll }}</div>
        </div>
      </div>

      <div class="sec">Active Classes</div>

      {% if not classes %}
        <div class="empty">
          <div class="icon">📭</div>
          <div class="title">No Active Class</div>
          <div class="hint">Wait for your faculty to start a class session.</div>
        </div>
      {% endif %}

      {% for cls in classes %}
        {% if cls.already_joined %}
          <div class="joined-btn">
            <div class="subj">📚 {{ cls.subject }}</div>
            <div class="meta">Started at {{ cls.start_time }} &nbsp;·&nbsp; by {{ cls.started_by }}</div>
            <div class="joined-lbl">✅ Already Joined</div>
          </div>
        {% else %}
          <form method="post">
            <input type="hidden" name="class_id" value="{{ cls.id }}">
            <button class="class-btn" type="submit">
              <div class="subj">📚 {{ cls.subject }}</div>
              <div class="meta">Started at {{ cls.start_time }} &nbsp;·&nbsp; by {{ cls.started_by }}</div>
              <div class="join-lbl">🟢 Join Class</div>
            </button>
          </form>
        {% endif %}
      {% endfor %}

      <a class="back" href="/">← Back to Registration</a>
    {% endif %}
  </div>
</body>
</html>
"""

# ── ROUTES ─────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def register():
    msg = ""
    msg_class = ""
    if request.method == "POST":
        roll = request.form["roll"].strip()
        name = request.form["name"].strip()
        ip   = request.remote_addr
        mac  = get_mac(ip)

        if not mac:
            msg = "Connect to the college WiFi first, then retry."
            msg_class = "error"
        else:
            try:
                conn = get_db(); cur = conn.cursor()

                cur.execute("SELECT roll_no, name, approved FROM students WHERE mac_address=?", (mac,))
                existing_mac = cur.fetchone()

                if existing_mac:
                    ex_roll, ex_name, approved = existing_mac
                    msg = (f"Device approved as '{ex_name}' (Roll: {ex_roll})."
                           if approved else
                           f"Device pending as '{ex_name}' (Roll: {ex_roll}). Await approval.")
                    msg_class = "error"
                    conn.close()
                else:
                    cur.execute("SELECT mac_address FROM students WHERE roll_no=?", (roll,))
                    if cur.fetchone():
                        msg = f"Roll No '{roll}' already registered from another device."
                        msg_class = "error"
                        conn.close()
                    else:
                        cur.execute("""
                            INSERT INTO students (roll_no, name, ip_address, mac_address, approved)
                            VALUES (?, ?, ?, ?, 0)
                        """, (roll, name, ip, mac))
                        conn.commit(); conn.close()
                        msg = "Registered! Awaiting faculty approval."
                        msg_class = "success"
            except Exception as e:
                msg = f"Error: {e}"; msg_class = "error"

    return render_template_string(REGISTER_HTML, msg=msg, msg_class=msg_class)


@app.route("/class", methods=["GET", "POST"])
def join_class():
    ip  = request.remote_addr
    mac = get_mac(ip)
    msg = ""
    msg_class = ""
    student = None
    classes  = []

    today    = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    if not mac:
        return render_template_string(CLASS_HTML, student=None, classes=[],
                                      msg="Connect to college WiFi first.", msg_class="error")

    conn = get_db(); cur = conn.cursor()

    # Check if student is registered and approved
    cur.execute("""
        SELECT roll_no, name FROM students
        WHERE mac_address=? AND approved=1
    """, (mac,))
    stu = cur.fetchone()

    if stu:
        student = {"roll": stu[0], "name": stu[1]}

        # Get all active classes today
        cur.execute("""
            SELECT id, subject, start_time, started_by
            FROM class_sessions
            WHERE date=? AND status='active'
            ORDER BY id ASC
        """, (today,))
        active_classes = cur.fetchall()

        for cls_id, subject, start_time, started_by in active_classes:
            # Check if already joined this class
            cur.execute("""
                SELECT id FROM attendance_sessions
                WHERE roll_no=? AND date=? AND subject=?
            """, (stu[0], today, subject))
            already_joined = cur.fetchone() is not None

            classes.append({
                "id": cls_id,
                "subject": subject,
                "start_time": start_time,
                "started_by": started_by,
                "already_joined": already_joined
            })

        # Handle join button press
        if request.method == "POST":
            class_id = request.form.get("class_id")
            if class_id:
                cur.execute("""
                    SELECT id, subject FROM class_sessions
                    WHERE id=? AND date=? AND status='active'
                """, (class_id, today))
                cls_row = cur.fetchone()

                if cls_row:
                    _, subject = cls_row

                    # Check not already joined
                    cur.execute("""
                        SELECT id FROM attendance_sessions
                        WHERE roll_no=? AND date=? AND subject=?
                    """, (stu[0], today, subject))

                    if cur.fetchone():
                        msg = f"You already joined {subject}!"
                        msg_class = "warn"
                    else:
                        # Insert attendance session — timer starts now
                        cur.execute("""
                            INSERT INTO attendance_sessions
                            (roll_no, name, date, subject, in_time, out_time, duration, status)
                            VALUES (?, ?, ?, ?, ?, NULL, NULL, 'present')
                        """, (stu[0], stu[1], today, subject, time_now))
                        conn.commit()
                        msg = f"✅ Joined {subject}! Your attendance is now being tracked."
                        msg_class = "success"

                        # Refresh classes list
                        cur.execute("""
                            SELECT id, subject, start_time, started_by
                            FROM class_sessions WHERE date=? AND status='active'
                        """, (today,))
                        classes = []
                        for cid, subj, st, sb in cur.fetchall():
                            cur.execute("SELECT id FROM attendance_sessions WHERE roll_no=? AND date=? AND subject=?",
                                        (stu[0], today, subj))
                            classes.append({
                                "id": cid, "subject": subj, "start_time": st,
                                "started_by": sb, "already_joined": cur.fetchone() is not None
                            })
                else:
                    msg = "Class no longer active."; msg_class = "error"

    conn.close()
    return render_template_string(CLASS_HTML, student=student, classes=classes,
                                  msg=msg, msg_class=msg_class)


if __name__ == "__main__":
    print(f"📁 Using database: {DB_PATH}")
    print(f"📱 Register : http://YOUR-IP:5000/")
    print(f"📡 Join Class: http://YOUR-IP:5000/class")
    app.run(host="0.0.0.0", port=5000, debug=False)