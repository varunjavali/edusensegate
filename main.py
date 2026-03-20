import streamlit as st
import sqlite3, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "attendance.db")

st.set_page_config(page_title="EduSense Gate", layout="wide", initial_sidebar_state="collapsed")

# Hide sidebar and nav
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #0d1117 !important; color: #e6edf3 !important;
}
#MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

for k, v in [("logged_in", False), ("role", None), ("username", None),
             ("active", {}), ("last_seen", {}), ("viewing_class_id", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# If already logged in, go straight to dashboard
if st.session_state.logged_in:
    st.switch_page("pages/dashboard.py")
    st.stop()

# ── LOGIN ──────────────────────────────────────────────────────────
_, col, _ = st.columns([1, 2, 1])
with col:
    st.markdown("""
    <div style="text-align:center; margin-top:80px; margin-bottom:28px;">
        <div style="display:inline-block; background:#161b22; border:1px solid #30363d;
                    border-radius:14px; padding:12px 32px; font-size:1.4rem;
                    font-weight:700; color:#e6edf3; margin-bottom:18px;">
            🎓 EduSense Gate
        </div>
        <div style="font-size:1.5rem; font-weight:700; color:#e6edf3; margin-bottom:4px;">Welcome Back</div>
        <div style="color:#8b949e; font-size:0.9rem;">Sign in to continue</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=True):
        username  = st.text_input("Username", placeholder="Enter username")
        password  = st.text_input("Password", type="password", placeholder="Enter password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)
        if submitted:
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute("SELECT username, role FROM users WHERE username=? AND password=?",
                        (username, password))
            row = cur.fetchone()
            conn.close()
            if row:
                st.session_state.logged_in = True
                st.session_state.username  = row[0]
                st.session_state.role      = row[1]
                st.switch_page("pages/dashboard.py")
            else:
                st.error("Invalid username or password")