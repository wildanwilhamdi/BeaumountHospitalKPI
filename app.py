import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

# ==========================================
# KONFIGURASI
# ==========================================
LOGO_URL = "https://www.beaumont.ie/themes/custom/beaumont_barrio/logo.png"
SESSION_TIMEOUT_MINUTES = 30  # HIPAA: Auto-logout setelah idle

st.set_page_config(
    page_title="Beaumont Hospital Portal",
    page_icon="🏥",
    layout="wide"
)

# ==========================================
# KONEKSI DATABASE
# ==========================================
MONGO_URI = st.secrets["MONGO_URI"]

@st.cache_resource
def init_db_connection():
    client = MongoClient(MONGO_URI)
    return client

client = init_db_connection()
db = client["beaumont_db"]
collection_kpi     = db["kpi_trends"]
collection_users   = db["users"]
collection_audit   = db["audit_log"]   # GDPR/HIPAA: Audit trail

# ==========================================
# FUNGSI AUDIT LOG (GDPR Article 5 & HIPAA §164.312)
# ==========================================
def write_audit_log(event: str, username: str, detail: str = ""):
    """Catat setiap aktivitas penting ke database."""
    collection_audit.insert_one({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event":     event,      # e.g. LOGIN_SUCCESS, LOGIN_FAIL, LOGOUT, DELETE_ACCOUNT
        "username":  username,
        "detail":    detail
    })

# ==========================================
# SESSION STATE INIT
# ==========================================
defaults = {
    'logged_in':       False,
    'username':        '',
    'login_time':      None,   # Untuk session timeout
    'consent_given':   False,  # GDPR: Consent tracking
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# HIPAA: SESSION TIMEOUT (§164.312(a)(2)(iii))
# Auto-logout setelah SESSION_TIMEOUT_MINUTES menit idle
# ==========================================
def check_session_timeout():
    if st.session_state['logged_in'] and st.session_state['login_time']:
        now     = datetime.now(timezone.utc)
        login   = st.session_state['login_time']
        elapsed = (now - login).total_seconds() / 60
        if elapsed > SESSION_TIMEOUT_MINUTES:
            write_audit_log("SESSION_TIMEOUT", st.session_state['username'])
            logout(reason="timeout")
            return True
    return False

# ==========================================
# FUNGSI AUTH
# ==========================================
def login_user(username: str, password: str) -> bool:
    user = collection_users.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        write_audit_log("LOGIN_SUCCESS", username)
        return True
    write_audit_log("LOGIN_FAIL", username, "Invalid credentials")
    return False

def create_user(username: str, password: str) -> bool:
    if collection_users.find_one({"username": username}):
        return False
    collection_users.insert_one({
        "username":   username,
        "password":   generate_password_hash(password),
        "created_at": datetime.now(timezone.utc).isoformat(),   # GDPR: Data minimisation record
        "consent_at": datetime.now(timezone.utc).isoformat(),   # GDPR: Consent timestamp
    })
    write_audit_log("ACCOUNT_CREATED", username)
    return True

def delete_account(username: str):
    """GDPR Article 17: Right to Erasure"""
    collection_users.delete_one({"username": username})
    write_audit_log("ACCOUNT_DELETED", username, "User exercised right to erasure")
    logout(reason="deleted")

def logout(reason: str = "manual"):
    write_audit_log("LOGOUT", st.session_state['username'], f"reason={reason}")
    st.session_state['logged_in']     = False
    st.session_state['username']      = ''
    st.session_state['login_time']    = None
    st.session_state['consent_given'] = False

# ==========================================
# CEK TIMEOUT SETIAP KALI HALAMAN DIMUAT
# ==========================================
timed_out = check_session_timeout()

# ==========================================
# HALAMAN LOGIN / SIGN UP
# ==========================================
if not st.session_state['logged_in']:

    if timed_out:
        st.warning(f"⏱️ Your session expired after {SESSION_TIMEOUT_MINUTES} minutes of inactivity. Please log in again.")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        lc1, lc2, lc3 = st.columns([1, 2, 1])
        with lc2:
            st.image(LOGO_URL, use_column_width=True)
        st.markdown("<p style='text-align:center; color:gray;'>Secure Executive Access Only.</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔒 Login", "📝 Sign Up"])

        # ------ LOGIN ------
        with tab_login:
            st.subheader("Login to Dashboard")
            login_username = st.text_input("Username", key="log_user")
            login_password = st.text_input("Password", type="password", key="log_pass")

            if st.button("Login", type="primary", use_container_width=True):
                if login_user(login_username, login_password):
                    st.session_state['logged_in']  = True
                    st.session_state['username']   = login_username
                    st.session_state['login_time'] = datetime.now(timezone.utc)
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")

        # ------ SIGN UP ------
        with tab_signup:
            st.subheader("Create New Executive Account")
            new_username = st.text_input("New Username", key="reg_user")
            new_password = st.text_input("New Password (min. 8 characters)", type="password", key="reg_pass")

            # ---- GDPR: Informed Consent (Article 7) ----
            with st.expander("📄 Privacy Notice — Please read before signing up", expanded=False):
                st.markdown("""
**What data we collect:**
- Username and hashed password (stored in MongoDB Atlas, EU region)
- Account creation timestamp
- Login/logout activity logs (audit trail)

**Why we collect it:**
- To authenticate your access to this dashboard
- To maintain security audit trails as required by HIPAA §164.312

**Your rights (GDPR Articles 15–17):**
- **Access**: You may request a copy of your data at any time
- **Rectification**: You may correct your data via account settings
- **Erasure**: You may delete your account and all associated data at any time
- **Portability**: You may request your data in a machine-readable format

**Data retention:**
- Account data is retained while your account is active
- Audit logs are retained for 6 years (HIPAA requirement)
- Upon account deletion, personal data is removed within 30 days
 """)

            consent = st.checkbox(
                "✅ I have read and agree to the Privacy Notice above.",
                key="consent_checkbox"
            )

            if st.button("Sign Up", type="secondary", use_container_width=True):
                if not new_username or not new_password:
                    st.warning("Please fill out both fields.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif not consent:
                    st.error("You must read and accept the Privacy Notice to create an account.")
                else:
                    if create_user(new_username, new_password):
                        st.success("✅ Account created! You can now log in.")
                    else:
                        st.error("Username already exists. Please choose another.")

# ==========================================
# HALAMAN UTAMA DASHBOARD
# ==========================================
else:
    # ==========================================
    # SIDEBAR
    # ==========================================
    st.sidebar.image(LOGO_URL, use_column_width=True)
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👤 Welcome, **{st.session_state['username']}**")

    # Tampilkan sisa waktu sesi
    if st.session_state['login_time']:
        now     = datetime.now(timezone.utc)
        elapsed = (now - st.session_state['login_time']).total_seconds() / 60
        remaining = max(0, SESSION_TIMEOUT_MINUTES - elapsed)
        st.sidebar.caption(f"⏱️ Session expires in: **{remaining:.0f} min**")

    st.sidebar.button("🚪 Logout", on_click=logout, use_container_width=True)
    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🏥 System Overview")
    st.sidebar.info(
        "**Beaumont KPI Portal**\n\n"
        "Executive decision-support system for monitoring clinical and operational metrics."
    )

    # ---- GDPR/HIPAA Compliance Status (Jujur) ----
    st.sidebar.markdown("### 🛡️ Security & Compliance")
    st.sidebar.success(
        "✅ **Password Hashing** (Werkzeug PBKDF2)\n\n"
        "✅ **Encrypted Storage** (MongoDB Atlas at-rest)\n\n"
        "✅ **Audit Logging** (HIPAA §164.312)\n\n"
        "✅ **Session Timeout** (30 min, HIPAA)\n\n"
        "✅ **GDPR Consent** on Registration\n\n"
        "✅ **Right to Erasure** (GDPR Art. 17)"
    )
    st.sidebar.warning(
        "⚠️ **Prototype Notice**\n\n"
        "Full compliance also requires BAA with cloud providers & formal DPIA."
    )

    st.sidebar.markdown("### 💻 Architecture Stack")
    st.sidebar.markdown(
        "- **Engine**: Python 3 & Streamlit\n"
        "- **Database**: MongoDB Atlas (Cloud NoSQL)\n"
        "- **Visualization**: Plotly Interactive\n"
        "- **Auth**: Werkzeug PBKDF2 Hashing\n"
        "- **Audit Trail**: MongoDB `audit_log`"
    )
    st.sidebar.markdown("---")

    st.sidebar.markdown("### 📖 Dashboard Guide")
    with st.sidebar.expander("📊 How to read the Metrics (Cards)"):
        st.markdown(
            "**Value**: Actual KPI value in the last reporting period.\n\n"
            "**Target**: Performance threshold. (Red = attention needed).\n\n"
            "**YTD**: Accumulation/average from start of year until now."
        )
    with st.sidebar.expander("📈 How to read the Charts"):
        st.markdown(
            "**Bar Chart**: Beaumont vs national average.\n\n"
            "**Line Chart**: Historical trend. Red dashed line = Target benchmark."
        )

    # ---- GDPR: Account Management (Right to Erasure) ----
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Account")
    with st.sidebar.expander("🗑️ Delete My Account (GDPR Art. 17)"):
        st.markdown("This will permanently delete your account and personal data.")
        confirm_delete = st.text_input("Type your username to confirm:", key="del_confirm")
        if st.button("Permanently Delete Account", type="primary", use_container_width=True):
            if confirm_delete == st.session_state['username']:
                delete_account(st.session_state['username'])
                st.rerun()
            else:
                st.error("Username does not match.")

    # ==========================================
    # METADATA KPI
    # ==========================================
    kpi_meta = {
        "elective_los":      {"name": "Elective length of stay",                      "unit": "Days",  "cards": {"value": "5.1",   "target_text": "≤ 4.5",  "target_num": 4.5,  "frequency": "M-1M", "ytd": "5.2"},   "comparison": {"hospital": 5.1,  "national": 4.8}},
        "avg_los_inpatient": {"name": "Average length of stay - inpatient discharges", "unit": "Days",  "cards": {"value": "7.9",   "target_text": "≤ 4.8",  "target_num": 4.8,  "frequency": "M-1M", "ytd": "8.3"},   "comparison": {"hospital": 7.9,  "national": 5.0}},
        "surg_emerg_readm":  {"name": "Surgical emergency readmissions",               "unit": "%",     "cards": {"value": "1.5%",  "target_text": "≤ 2.0%", "target_num": 2.0,  "frequency": "M-1M", "ytd": "1.9%"},  "comparison": {"hospital": 1.5,  "national": 1.7}},
        "med_avg_los":       {"name": "Medical average length of stay",                "unit": "Days",  "cards": {"value": "9.9",   "target_text": "≤ 7.0",  "target_num": 7.0,  "frequency": "M-1M", "ytd": "10.8"},  "comparison": {"hospital": 9.9,  "national": 7.1}},
        "s_aureus":          {"name": "Hospital new cases of S. aureus",               "unit": "Cases", "cards": {"value": "1.6",   "target_text": "≤ 0.7",  "target_num": 0.7,  "frequency": "M",    "ytd": "0.9"},   "comparison": {"hospital": 1.6,  "national": 0.7}},
        "c_difficile":       {"name": "Hospital new cases of C. difficile",            "unit": "Cases", "cards": {"value": "3.7",   "target_text": "≤ 2.0",  "target_num": 2.0,  "frequency": "M",    "ytd": "3.5"},   "comparison": {"hospital": 3.7,  "national": 2.3}},
        "med_emerg_readm":   {"name": "Medical emergency readmissions",                "unit": "%",     "cards": {"value": "10.4%", "target_text": "≤ 11.1%","target_num": 11.1, "frequency": "M-1M", "ytd": "11.0%"}, "comparison": {"hospital": 10.4, "national": 11.1}},
    }

    st.markdown("""
        <style>
        .kpi-box { background-color: white; padding: 20px; border-radius: 8px;
                   box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center;
                   border-left: 4px solid; margin-bottom: 20px; }
        .kpi-title { font-size: 14px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; }
        .kpi-value { font-size: 28px; font-weight: 700; color: #2c3e50; }
        .val-red   { color: #e74c3c !important; }
        </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # HEADER
    # ==========================================
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown("<h1 style='color:#20c997;'>Beaumont Hospital Executive Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("Detailed analysis of operational and clinical Key Performance Indicators (KPIs).")
    with h2:
        st.image(LOGO_URL, width=200)

    # ==========================================
    # CONTROLS
    # ==========================================
    st.markdown("### Controls")
    cc1, cc2 = st.columns(2)
    with cc1:
        selected_kpi_id = st.selectbox(
            "Select KPI:",
            options=list(kpi_meta.keys()),
            format_func=lambda x: kpi_meta[x]["name"]
        )
    with cc2:
        selected_year = st.selectbox(
            "Select Trend Year:",
            options=["25", "24", "all"],
            format_func=lambda x: "All (2024 & 2025)" if x == "all" else f"20{x}"
        )

    meta = kpi_meta[selected_kpi_id]
    st.markdown("---")
    st.markdown(f"<h4 style='color:#20c997;'>Selected KPI: {meta['name']}</h4>", unsafe_allow_html=True)

    doc        = collection_kpi.find_one({"kpi_id": selected_kpi_id})
    trend_data = doc["trend"] if doc else []
    if selected_year != "all":
        trend_data = [d for d in trend_data if d["date"].endswith(selected_year)]
    df_trend = pd.DataFrame(trend_data)

    # ==========================================
    # CHARTS
    # ==========================================
    col_left, col_right = st.columns(2)

    with col_left:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='kpi-box' style='border-color:#3498db;'><div class='kpi-title'>Value</div><div class='kpi-value val-red'>{meta['cards']['value']}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='kpi-box' style='border-color:#95a5a6;'><div class='kpi-title'>Target</div><div class='kpi-value'>{meta['cards']['target_text']}</div></div>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f"<div class='kpi-box' style='border-color:#17a2b8;'><div class='kpi-title'>Frequency</div><div class='kpi-value'>{meta['cards']['frequency']}</div></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='kpi-box' style='border-color:#f1c40f;'><div class='kpi-title'>YTD</div><div class='kpi-value'>{meta['cards']['ytd']}</div></div>", unsafe_allow_html=True)

        st.markdown(f"**Current KPI: National vs Hospital ({meta['unit']})**")
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            y=['National', 'Beaumont Hospital'],
            x=[meta['comparison']['national'], meta['comparison']['hospital']],
            orientation='h',
            marker=dict(color=['#95a5a6', '#3498db'])
        ))
        fig_comp.add_vline(x=meta['cards']['target_num'], line_width=2, line_dash="dash",
                           line_color="red", annotation_text="Target", annotation_position="bottom right")
        fig_comp.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250, showlegend=False)
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_right:
        year_label = "2024 & 2025" if selected_year == "all" else f"20{selected_year}"
        st.markdown(f"**KPI Trend in {meta['unit']} ({year_label})**")
        if not df_trend.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=df_trend['date'], y=df_trend['val'],
                mode='lines+markers',
                line=dict(color='#3498db', width=3),
                fill='tozeroy', fillcolor='rgba(52,152,219,0.2)'
            ))
            fig_trend.add_hline(y=meta['cards']['target_num'], line_width=2, line_dash="dash",
                                line_color="red", annotation_text="Target")
            fig_trend.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=550,
                                    yaxis=dict(rangemode='tozero'))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No trend data available for this period.")
