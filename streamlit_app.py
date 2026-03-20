import streamlit as st
import sqlite3, time, os, csv
from datetime import datetime
from scanner import get_live_macs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")
GRACE_SECONDS = 60
PRESENT_PCT = 80

st.set_page_config(page_title="EduSense Gate", layout="wide")

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stToolbar"] {
    background-color: #0d1117 !important; color: #e6edf3 !important;
}
#MainMenu, footer, [data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stTabs"] button {
    font-size: 0.95rem !important; font-weight: 600 !important;
    color: #8b949e !important; padding: 10px 20px !important; border-radius: 0 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #e6edf3 !important; border-bottom: 2px solid #58a6ff !important;
}
[data-testid="stExpander"] {
    background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px !important;
}
.stButton > button {
    background-color: #21262d !important; color: #e6edf3 !important;
    border: 1px solid #30363d !important; border-radius: 6px !important;
    padding: 6px 16px !important; font-size: 0.85rem !important;
}
.stButton > button:hover { background-color: #30363d !important; border-color: #58a6ff !important; }
button[kind="primary"] { background-color: #da3633 !important; border-color: #da3633 !important; }
[data-testid="stDataFrame"] { background: #161b22 !important; }
[data-testid="stTextInput"] input { background: #161b22 !important; border-color: #30363d !important; color: #e6edf3 !important; }
.stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px 24px; text-align: center; }
.stat-card .num { font-size: 2.2rem; font-weight: 700; line-height: 1; }
.stat-card .lbl { font-size: 0.8rem; color: #8b949e; margin-top: 6px; letter-spacing: 0.5px; }
.class-card { background: #0f2318; border: 1px solid #238636; border-radius: 10px; padding: 16px 20px; margin-bottom: 10px; }
.class-card-title { font-size: 1.1rem; font-weight: 700; color: #3fb950; }
.class-card-meta  { color: #388e3c; font-size: 0.85rem; margin-top: 4px; }
.card-present { background: #0f2318; border: 1px solid #238636; border-radius: 8px; padding: 12px 16px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
.card-present .cname { color: #3fb950; font-weight: 700; }
.card-present .cmeta { color: #388e3c; font-size: 0.82rem; }
.card-present .cbadge { background: #238636; color: #fff; border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.card-absent { background: #1c0f0f; border: 1px solid #da3633; border-radius: 8px; padding: 12px 16px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
.card-absent .cname  { color: #f85149; font-weight: 700; }
.card-absent .cmeta  { color: #da3633; font-size: 0.82rem; }
.card-absent .cbadge { background: #da3633; color: #fff; border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.card-disconnected { background: #1c1a0f; border: 1px solid #9e6a03; border-radius: 8px; padding: 12px 16px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
.card-disconnected .cname  { color: #d29922; font-weight: 700; }
.card-disconnected .cmeta  { color: #9e6a03; font-size: 0.82rem; }
.card-disconnected .cbadge { background: #9e6a03; color: #fff; border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.pbar-wrap { background: #21262d; border-radius: 20px; height: 6px; width: 100%; margin-top: 5px; }
.pbar-fill  { height: 6px; border-radius: 20px; }
.badge-admin   { background:#1f6feb; color:#fff; border-radius:20px; padding:2px 12px; font-size:0.75rem; font-weight:700; }
.badge-faculty { background:#238636; color:#fff; border-radius:20px; padding:2px 12px; font-size:0.75rem; font-weight:700; }
.subj-tag { background:#1f2937; border:1px solid #374151; border-radius:6px; padding:3px 10px; font-size:0.82rem; color:#93c5fd; font-weight:600; }
.sec-head { font-size: 0.75rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #8b949e; margin: 20px 0 12px 0; }
</style>
""", unsafe_allow_html=True)


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def fmt_duration(seconds):
    if not seconds: return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    elif s < 3600:
        m, s = divmod(s, 60); return f"{m}m {s}s"
    else:
        h, r = divmod(s, 3600); m, s = divmod(r, 60); return f"{h}h {m}m"


def pct_color(pct):
    if pct >= 80:
        return "#3fb950"
    elif pct >= 50:
        return "#d29922"
    return "#f85149"


for k, v in [("logged_in", False), ("role", None), ("username", None),
             ("active", {}), ("last_seen", {}), ("viewing_class_id", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════
# LOGIN — rendered alone, dashboard never touched
# ══════════════════════════════════════════════════════════════════
if not st.session_state.get("logged_in"):
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;margin-top:80px;margin-bottom:28px;">
            <div style="font-size:2rem;margin-bottom:8px;">🎓</div>
            <div style="font-size:1.5rem;font-weight:700;color:#e6edf3;margin-bottom:4px;">EduSense Gate</div>
            <div style="color:#8b949e;font-size:0.9rem;">Sign in to continue</div>
        </div>
        """, unsafe_allow_html=True)

        login_error = st.session_state.get("login_error", "")
        if login_error:
            st.error(login_error)
            st.session_state["login_error"] = ""

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            if st.form_submit_button("Sign In", use_container_width=True):
                conn = get_conn();
                cur = conn.cursor()
                cur.execute("SELECT username, role FROM users WHERE username=? AND password=?", (username, password))
                row = cur.fetchone();
                conn.close()
                if row:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = row[0]
                    st.session_state["role"] = row[1]
                    st.rerun()
                else:
                    st.session_state["login_error"] = "Invalid username or password"
                    st.rerun()
else:
    conn = get_conn();
    cur = conn.cursor()
    role = st.session_state["role"]
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()
    time_now = now.strftime("%H:%M:%S")

    cur.execute(
        "SELECT id, start_time, started_by, subject FROM class_sessions WHERE date=? AND status='active' ORDER BY id ASC",
        (today,))
    all_active_classes = cur.fetchall()
    active_class = all_active_classes[-1] if all_active_classes else None

    # ── HEADER ─────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([6, 3, 1])
    with c1:
        st.markdown('<div style="font-size:1.5rem;font-weight:700;padding-top:12px;">📡 EduSense Gate</div>',
                    unsafe_allow_html=True)
    with c2:
        badge = "badge-admin" if role == "admin" else "badge-faculty"
        txt = "ADMIN" if role == "admin" else "FACULTY"
        st.markdown(
            f'<div style="text-align:right;padding-top:14px;color:#8b949e;font-size:0.85rem;"><span class="{badge}">{txt}</span> &nbsp; {st.session_state["username"]}</div>',
            unsafe_allow_html=True)
    with c3:
        st.write("")
        if st.button("Logout"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    st.markdown("<hr style='border-color:#21262d;margin:8px 0 20px 0'>", unsafe_allow_html=True)

    # ── STATS ──────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM students WHERE approved=1")
    total_approved = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM students WHERE approved=0")
    total_pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT roll_no) FROM attendance_sessions WHERE date=? AND out_time IS NULL", (today,))
    present_now = cur.fetchone()[0]

    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(
        f'<div class="stat-card"><div class="num" style="color:#3fb950">{present_now}</div><div class="lbl">IN CLASS NOW</div></div>',
        unsafe_allow_html=True)
    s2.markdown(
        f'<div class="stat-card"><div class="num" style="color:#58a6ff">{total_approved}</div><div class="lbl">APPROVED STUDENTS</div></div>',
        unsafe_allow_html=True)
    s3.markdown(
        f'<div class="stat-card"><div class="num" style="color:#f85149">{total_approved - present_now}</div><div class="lbl">ABSENT TODAY</div></div>',
        unsafe_allow_html=True)
    s4.markdown(
        f'<div class="stat-card"><div class="num" style="color:#d29922">{len(all_active_classes)}</div><div class="lbl">ACTIVE CLASSES</div></div>',
        unsafe_allow_html=True)

    st.write("")

    # ══════════════════════════════════════════════════════════════════
    # ADMIN TABS
    # ══════════════════════════════════════════════════════════════════
    if role == "admin":
        tab1, tab2, tab3, tab4 = st.tabs(["🏫  Live Classes", "👨‍🎓  Students", "📜  Attendance History", "⚙️  Settings"])

        with tab1:
            if not all_active_classes:
                st.markdown(
                    '<div style="background:#161b22;border:2px dashed #30363d;border-radius:10px;padding:40px;text-align:center;color:#8b949e;margin-top:20px;"><div style="font-size:2rem;margin-bottom:10px;">📭</div><div style="font-size:1rem;font-weight:600;">No Active Classes</div><div style="font-size:0.85rem;margin-top:6px;">Classes will appear here when faculty starts a session</div></div>',
                    unsafe_allow_html=True)
            else:
                for cls_id, cls_start, cls_by, cls_subj in all_active_classes:
                    cls_dt = datetime.strptime(f"{today} {cls_start}", "%Y-%m-%d %H:%M:%S")
                    cls_elapsed = int((now - cls_dt).total_seconds())
                    cur.execute(
                        "SELECT COUNT(DISTINCT roll_no) FROM attendance_sessions WHERE date=? AND subject=? AND out_time IS NULL",
                        (today, cls_subj))
                    cls_present = cur.fetchone()[0]
                    is_viewing = st.session_state.viewing_class_id == cls_id

                    st.markdown(f"""
                    <div class="class-card">
                        <span class="subj-tag">📚 {cls_subj}</span>
                        <div class="class-card-title" style="margin-top:8px;">🟢 Class in Progress</div>
                        <div class="class-card-meta">Started by <b>{cls_by}</b> at <b>{cls_start}</b> &nbsp;·&nbsp; Running <b>{fmt_duration(cls_elapsed)}</b> &nbsp;·&nbsp; <b>{cls_present}</b>/{total_approved} students joined</div>
                    </div>""", unsafe_allow_html=True)

                    if st.button("🔼 Hide Attendance" if is_viewing else "👁️ View Live Attendance",
                                 key=f"view_{cls_id}"):
                        st.session_state.viewing_class_id = None if is_viewing else cls_id
                        st.rerun()

                    if is_viewing:
                        st.markdown(f"<div class='sec-head'>Live Attendance — {cls_subj}</div>", unsafe_allow_html=True)
                        cur.execute("SELECT roll_no, name FROM students WHERE approved=1 ORDER BY name")
                        present_rows = [];
                        absent_rows = []
                        for roll, name in cur.fetchall():
                            cur.execute(
                                "SELECT in_time FROM attendance_sessions WHERE roll_no=? AND date=? AND subject=? AND out_time IS NULL",
                                (roll, today, cls_subj))
                            open_row = cur.fetchone()
                            cur.execute(
                                "SELECT COALESCE(SUM(duration),0) FROM attendance_sessions WHERE roll_no=? AND date=? AND subject=? AND out_time IS NOT NULL",
                                (roll, today, cls_subj))
                            past_dur = cur.fetchone()[0] or 0
                            if open_row:
                                try:
                                    in_dt = datetime.strptime(f"{today} {open_row[0]}", "%Y-%m-%d %H:%M:%S")
                                    cur_dur = int((now - in_dt).total_seconds())
                                except:
                                    cur_dur = 0
                                total_att = past_dur + cur_dur
                                pct = min(100, int(total_att / cls_elapsed * 100)) if cls_elapsed > 0 else 0
                                present_rows.append((roll, name, total_att, pct))
                            else:
                                absent_rows.append((roll, name, 0, 0))

                        cp, ca = st.columns(2)
                        with cp:
                            st.markdown(
                                f"<div style='color:#3fb950;font-weight:700;margin-bottom:8px;'>✅ Joined ({len(present_rows)})</div>",
                                unsafe_allow_html=True)
                            for roll, name, total_att, pct in present_rows:
                                color = pct_color(pct)
                                st.markdown(
                                    f'<div class="card-present"><div style="flex:1"><div class="cname">{name}</div><div class="cmeta">Roll: {roll} &nbsp;·&nbsp; {fmt_duration(total_att)} &nbsp;·&nbsp; {pct}%</div><div class="pbar-wrap"><div class="pbar-fill" style="width:{pct}%;background:{color}"></div></div></div><div class="cbadge">JOINED</div></div>',
                                    unsafe_allow_html=True)
                        with ca:
                            st.markdown(
                                f"<div style='color:#f85149;font-weight:700;margin-bottom:8px;'>❌ Not Joined ({len(absent_rows)})</div>",
                                unsafe_allow_html=True)
                            for roll, name, _, __ in absent_rows:
                                st.markdown(
                                    f'<div class="card-absent"><div style="flex:1"><div class="cname">{name}</div><div class="cmeta">Roll: {roll} &nbsp;·&nbsp; Has not joined yet</div></div><div class="cbadge">ABSENT</div></div>',
                                    unsafe_allow_html=True)
                        st.markdown("---")

        with tab2:
            cur.execute("SELECT roll_no, name, mac_address, approved FROM students ORDER BY approved ASC, name ASC")
            students_all = cur.fetchall()
            if not students_all:
                st.info("No students registered yet.")
            else:
                pending = [(r, n, m, a) for r, n, m, a in students_all if not a]
                approved = [(r, n, m, a) for r, n, m, a in students_all if a]

                if pending:
                    st.markdown(f"<div class='sec-head'>Pending Approval ({len(pending)})</div>",
                                unsafe_allow_html=True)
                    for roll, name, mac, _ in pending:
                        c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 1, 1])
                        c1.markdown(f"**{roll}**");
                        c2.write(name)
                        c3.markdown(f"<code style='color:#58a6ff;font-size:0.8rem'>{mac or 'No MAC'}</code>",
                                    unsafe_allow_html=True)
                        if c4.button("✅", key=f"apr_{roll}", help="Approve"):
                            cur.execute("UPDATE students SET approved=1 WHERE roll_no=?", (roll,))
                            conn.commit();
                            st.rerun()
                        if c5.button("🗑️", key=f"del_{roll}", help="Delete"):
                            st.session_state[f"confirm_del_{roll}"] = True;
                            st.rerun()
                        if st.session_state.get(f"confirm_del_{roll}"):
                            st.warning(f"Delete **{name}** ({roll}) and all their records?")
                            y, n_ = st.columns(2)
                            if y.button("Yes, Delete", key=f"yes_{roll}", type="primary"):
                                cur.execute("DELETE FROM students WHERE roll_no=?", (roll,))
                                cur.execute("DELETE FROM attendance_sessions WHERE roll_no=?", (roll,))
                                conn.commit();
                                st.session_state.pop(f"confirm_del_{roll}", None)
                                st.success("Deleted.");
                                time.sleep(1);
                                st.rerun()
                            if n_.button("Cancel", key=f"no_{roll}"):
                                st.session_state.pop(f"confirm_del_{roll}", None);
                                st.rerun()

                st.markdown(f"<div class='sec-head'>Approved Students ({len(approved)})</div>", unsafe_allow_html=True)
                if not approved:
                    st.info("No approved students yet.")
                else:
                    h1, h2, h3, h4 = st.columns([2, 3, 3, 1])
                    h1.markdown("<small style='color:#8b949e'>ROLL NO</small>", unsafe_allow_html=True)
                    h2.markdown("<small style='color:#8b949e'>NAME</small>", unsafe_allow_html=True)
                    h3.markdown("<small style='color:#8b949e'>MAC ADDRESS</small>", unsafe_allow_html=True)
                    h4.markdown("<small style='color:#8b949e'>DELETE</small>", unsafe_allow_html=True)
                    for roll, name, mac, _ in approved:
                        c1, c2, c3, c4 = st.columns([2, 3, 3, 1])
                        c1.markdown(f"**{roll}**");
                        c2.write(name)
                        c3.markdown(f"<code style='color:#58a6ff;font-size:0.8rem'>{mac or 'No MAC'}</code>",
                                    unsafe_allow_html=True)
                        if c4.button("🗑️", key=f"del_a_{roll}", help="Delete"):
                            st.session_state[f"confirm_del_{roll}"] = True;
                            st.rerun()
                        if st.session_state.get(f"confirm_del_{roll}"):
                            st.warning(f"Delete **{name}** ({roll}) and all their records?")
                            y, n_ = st.columns(2)
                            if y.button("Yes, Delete", key=f"yes_a_{roll}", type="primary"):
                                cur.execute("DELETE FROM students WHERE roll_no=?", (roll,))
                                cur.execute("DELETE FROM attendance_sessions WHERE roll_no=?", (roll,))
                                conn.commit();
                                st.session_state.pop(f"confirm_del_{roll}", None)
                                st.success("Deleted.");
                                time.sleep(1);
                                st.rerun()
                            if n_.button("Cancel", key=f"no_a_{roll}"):
                                st.session_state.pop(f"confirm_del_{roll}", None);
                                st.rerun()

        with tab3:
            st.markdown("<div class='sec-head'>Filter Records</div>", unsafe_allow_html=True)
            f1, f2, f3 = st.columns(3)
            cur.execute("SELECT DISTINCT subject FROM attendance_sessions WHERE subject IS NOT NULL ORDER BY subject")
            subjects = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT roll_no, name FROM students WHERE approved=1 ORDER BY name")
            stu_opts = ["All Students"] + [f"{r} — {n}" for r, n in cur.fetchall()]
            with f1:
                sel_subject = st.selectbox("Subject", ["All Subjects"] + subjects)
            with f2:
                sel_student = st.selectbox("Student", stu_opts)
            with f3:
                sel_date = st.date_input("Date", value=None)

            query = "SELECT roll_no,name,date,subject,in_time,out_time,duration,status FROM attendance_sessions WHERE 1=1"
            params = []
            if sel_subject != "All Subjects": query += " AND subject=?"; params.append(sel_subject)
            if sel_student != "All Students": query += " AND roll_no=?"; params.append(sel_student.split(" — ")[0])
            if sel_date: query += " AND date=?"; params.append(str(sel_date))
            query += " ORDER BY date DESC, id DESC"
            cur.execute(query, params);
            rows = cur.fetchall()

            if rows:
                import pandas as pd

                df = pd.DataFrame([{"Roll": r[0], "Name": r[1], "Date": r[2], "Subject": r[3] or "—",
                                    "In": r[4] or "—", "Out": r[5] or "—", "Duration": fmt_duration(r[6]),
                                    "Status": "✅ Present" if r[7] == "present" else "❌ Absent" if r[
                                                                                                      7] == "absent" else "🟡 " +
                                                                                                                          r[
                                                                                                                              7]}
                                   for r in rows])
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("<div class='sec-head'>Summary by Subject</div>", unsafe_allow_html=True)
                cur.execute(
                    "SELECT roll_no,name,subject,COUNT(*) as total,SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) as pres FROM attendance_sessions WHERE status IN ('present','absent') GROUP BY roll_no,subject ORDER BY name,subject")
                summ = cur.fetchall()
                if summ:
                    sdf = pd.DataFrame(
                        [{"Roll": r[0], "Name": r[1], "Subject": r[2] or "—", "Classes": r[3], "Present": r[4],
                          "Attendance %": f"{int(r[4] / r[3] * 100) if r[3] else 0}%",
                          "Flag": "✅" if (r[4] / r[3] * 100 if r[3] else 0) >= 75 else "⚠️ Low"} for r in summ])
                    st.dataframe(sdf, use_container_width=True, hide_index=True)
                if st.button("💾 Export CSV"):
                    csv_path = os.path.join(BASE_DIR, "attendance.csv")
                    with open(csv_path, "w", newline="") as f:
                        w = csv.writer(f);
                        w.writerow(["Roll", "Name", "Date", "Subject", "In", "Out", "Duration", "Status"])
                        for r in rows: w.writerow(
                            [r[0], r[1], r[2], r[3] or "—", r[4] or "—", r[5] or "—", fmt_duration(r[6]), r[7]])
                    st.success(f"✅ Saved to {csv_path}")
            else:
                st.info("No records found.")

        with tab4:
            st.markdown("<div class='sec-head'>Danger Zone</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Clear all attendance records**")
                st.caption("Removes all session data. Students stay registered.")
                if st.button("🧹 Clear Attendance", use_container_width=True):
                    cur.execute("DELETE FROM attendance_sessions");
                    conn.commit();
                    st.success("Cleared.")
            with c2:
                st.markdown("**Reset all approvals**")
                st.caption("Sets all students back to pending.")
                if st.button("🔄 Reset Approvals", use_container_width=True):
                    cur.execute("UPDATE students SET approved=0");
                    conn.commit();
                    st.success("Reset.")

    # ══════════════════════════════════════════════════════════════════
    # FACULTY
    # ══════════════════════════════════════════════════════════════════
    elif role == "faculty":
        st.markdown('<div class="sec-head">Class Session</div>', unsafe_allow_html=True)

        if active_class:
            class_id, start_time_str, started_by, subject = active_class
            start_dt = datetime.strptime(f"{today} {start_time_str}", "%Y-%m-%d %H:%M:%S")
            class_elapsed = int((now - start_dt).total_seconds())
            st.markdown(
                f'<div class="class-card"><span class="subj-tag">📚 {subject}</span><div class="class-card-title" style="margin-top:8px;">🟢 Class in Progress</div><div class="class-card-meta">Started at <b>{start_time_str}</b> &nbsp;·&nbsp; Running <b>{fmt_duration(class_elapsed)}</b></div></div>',
                unsafe_allow_html=True)

            if st.button("🔴 End Class"):
                class_duration = class_elapsed
                cur.execute(
                    "SELECT roll_no, name, in_time FROM attendance_sessions WHERE date=? AND subject=? AND out_time IS NULL",
                    (today, subject))
                present_count = absent_count = 0
                for roll, name, in_time_str in cur.fetchall():
                    try:
                        in_dt = datetime.strptime(f"{today} {in_time_str}", "%Y-%m-%d %H:%M:%S")
                        attended = int((now - in_dt).total_seconds())
                    except:
                        attended = 0
                    status = "present" if (
                                              attended / class_duration * 100 if class_duration else 0) >= PRESENT_PCT else "absent"
                    if status == "present":
                        present_count += 1
                    else:
                        absent_count += 1
                    cur.execute(
                        "UPDATE attendance_sessions SET out_time=?,duration=?,status=? WHERE roll_no=? AND date=? AND subject=? AND out_time IS NULL",
                        (time_now, attended, status, roll, today, subject))
                cur.execute("SELECT roll_no,name FROM students WHERE approved=1")
                for roll, name in cur.fetchall():
                    cur.execute("SELECT id FROM attendance_sessions WHERE roll_no=? AND date=? AND subject=?",
                                (roll, today, subject))
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO attendance_sessions (roll_no,name,date,subject,in_time,out_time,duration,status) VALUES (?,?,?,?,'—',?,0,'absent')",
                            (roll, name, today, subject, time_now))
                        absent_count += 1
                cur.execute("UPDATE class_sessions SET end_time=?,duration=?,status='ended' WHERE id=?",
                            (time_now, class_duration, class_id))
                conn.commit()
                st.session_state.active = {};
                st.session_state.last_seen = {}
                st.success(f"✅ Done! Present: {present_count} | Absent: {absent_count}")
                time.sleep(2);
                st.rerun()
        else:
            st.markdown(
                '<div style="background:#161b22;border:2px dashed #30363d;border-radius:10px;padding:24px;text-align:center;color:#8b949e;margin-bottom:16px;">No active class &nbsp;·&nbsp; Enter subject and click Start Class</div>',
                unsafe_allow_html=True)
            with st.form("start_class_form"):
                subject_input = st.text_input("Subject Name", placeholder="e.g. Data Structures, DBMS...")
                if st.form_submit_button("🟢 Start Class"):
                    if not subject_input.strip():
                        st.error("Please enter a subject name.")
                    else:
                        cur.execute(
                            "INSERT INTO class_sessions (date,subject,start_time,started_by,status) VALUES (?,?,?,?,'active')",
                            (today, subject_input.strip(), time_now, st.session_state["username"]))
                        conn.commit();
                        st.session_state.active = {};
                        st.session_state.last_seen = {}
                        st.success(f"✅ Started: {subject_input.strip()}");
                        time.sleep(1);
                        st.rerun()

        st.markdown('<div class="sec-head">Live Attendance</div>', unsafe_allow_html=True)
        if not active_class:
            st.info("⏳ Start a class to see live attendance.")
        else:
            class_id, start_time_str, _, subject = active_class
            start_dt = datetime.strptime(f"{today} {start_time_str}", "%Y-%m-%d %H:%M:%S")
            class_duration = int((now - start_dt).total_seconds())

            try:
                live_macs = get_live_macs()
            except:
                live_macs = set()

            last_seen = st.session_state.get("last_seen", {})

            cur.execute("SELECT roll_no, name, mac_address FROM students WHERE approved=1 ORDER BY name")
            present_cards = [];
            disconnected_cards = [];
            absent_cards = []

            for roll, name, mac in cur.fetchall():
                mac_norm = mac.lower().replace("-", ":").strip() if mac else ""
                cur.execute(
                    "SELECT in_time FROM attendance_sessions WHERE roll_no=? AND date=? AND subject=? AND out_time IS NULL",
                    (roll, today, subject))
                open_row = cur.fetchone()
                cur.execute(
                    "SELECT COALESCE(SUM(duration),0) FROM attendance_sessions WHERE roll_no=? AND date=? AND subject=? AND out_time IS NOT NULL",
                    (roll, today, subject))
                past_dur = cur.fetchone()[0] or 0

                # Update last_seen if MAC is live right now
                if mac_norm and mac_norm in live_macs:
                    last_seen[roll] = now

                if open_row:
                    # Student joined via button — calculate time from join
                    try:
                        join_dt = datetime.strptime(f"{today} {open_row[0]}", "%Y-%m-%d %H:%M:%S")
                        cur_dur = int((now - join_dt).total_seconds())
                    except:
                        cur_dur = 0
                    total_att = past_dur + cur_dur
                    pct = min(100, int(total_att / class_duration * 100)) if class_duration > 0 else 0

                    if mac_norm and mac_norm in live_macs:
                        # MAC on network — IN CLASS
                        present_cards.append((roll, name, total_att, pct))
                    else:
                        # MAC not seen — check grace period
                        last = last_seen.get(roll)
                        secs_ago = int((now - last).total_seconds()) if last else 9999
                        disconnected_cards.append((roll, name, total_att, pct, secs_ago))
                else:
                    # Never joined via button — also show as left/absent
                    last = last_seen.get(roll)
                    secs_ago = int((now - last).total_seconds()) if last else 9999
                    absent_cards.append((roll, name, secs_ago))

            st.session_state["last_seen"] = last_seen

            # ── IN CLASS ──
            if present_cards:
                st.markdown(
                    f"<div style='color:#3fb950;font-weight:700;margin-bottom:8px;font-size:0.9rem;'>🟢 In Class ({len(present_cards)})</div>",
                    unsafe_allow_html=True)
                for roll, name, total_att, pct in present_cards:
                    color = pct_color(pct)
                    st.markdown(
                        f'<div class="card-present"><div style="flex:1"><div class="cname">{name}</div><div class="cmeta">Roll: {roll} &nbsp;·&nbsp; {fmt_duration(total_att)} &nbsp;·&nbsp; {pct}%</div><div class="pbar-wrap"><div class="pbar-fill" style="width:{pct}%;background:{color}"></div></div></div><div class="cbadge">IN CLASS</div></div>',
                        unsafe_allow_html=True)

            # ── DISCONNECTED ──
            if disconnected_cards:
                st.markdown(
                    f"<div style='color:#d29922;font-weight:700;margin:12px 0 8px;font-size:0.9rem;'>🟡 Disconnected ({len(disconnected_cards)})</div>",
                    unsafe_allow_html=True)
                for roll, name, total_att, pct, secs_ago in disconnected_cards:
                    color = pct_color(pct)
                    grace_left = max(0, GRACE_SECONDS - secs_ago)
                    if secs_ago <= GRACE_SECONDS:
                        meta = f"Roll: {roll} &nbsp;·&nbsp; {fmt_duration(total_att)} &nbsp;·&nbsp; WiFi lost {secs_ago}s ago &nbsp;·&nbsp; Grace: {grace_left}s left"
                        badge = "GRACE PERIOD"
                        card_cls = "card-disconnected"
                    else:
                        meta = f"Roll: {roll} &nbsp;·&nbsp; {fmt_duration(total_att)} &nbsp;·&nbsp; {pct}% &nbsp;·&nbsp; Left class"
                        badge = "LEFT"
                        card_cls = "card-disconnected"
                    st.markdown(
                        f'<div class="{card_cls}"><div style="flex:1"><div class="cname">{name}</div><div class="cmeta">{meta}</div><div class="pbar-wrap"><div class="pbar-fill" style="width:{pct}%;background:{color}"></div></div></div><div class="cbadge">{badge}</div></div>',
                        unsafe_allow_html=True)

            # ── NOT JOINED / LEFT ──
            if absent_cards:
                st.markdown(
                    f"<div style='color:#f85149;font-weight:700;margin:12px 0 8px;font-size:0.9rem;'>🔴 Left / Not Joined ({len(absent_cards)})</div>",
                    unsafe_allow_html=True)
                for roll, name, secs_ago in absent_cards:
                    if secs_ago < 9999:
                        meta = f"Roll: {roll} &nbsp;·&nbsp; Left {secs_ago // 60}m {secs_ago % 60}s ago"
                    else:
                        meta = f"Roll: {roll} &nbsp;·&nbsp; Left the class"
                    st.markdown(
                        f'<div class="card-absent"><div style="flex:1"><div class="cname">{name}</div><div class="cmeta">{meta}</div></div><div class="cbadge">LEFT</div></div>',
                        unsafe_allow_html=True)

    conn.close()
    time.sleep(10)
    st.rerun()