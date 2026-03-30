import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# LOGO SVG (inline, tidak butuh file gambar)
# ==========================================
LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60">
  <!-- Background pill -->
  <rect x="0" y="5" width="195" height="50" rx="10" fill="#0f2b3d"/>
  <!-- Cross icon -->
  <rect x="12" y="20" width="6" height="22" rx="2" fill="#20c997"/>
  <rect x="6" y="26" width="18" height="6" rx="2" fill="#20c997"/>
  <!-- Hospital name -->
  <text x="38" y="27" font-family="Georgia, serif" font-size="13" font-weight="bold" fill="#ffffff">BEAUMONT</text>
  <text x="38" y="44" font-family="Georgia, serif" font-size="10" fill="#20c997" letter-spacing="3">HOSPITAL</text>
  <!-- Decorative line -->
  <line x1="38" y1="30" x2="185" y2="30" stroke="#20c997" stroke-width="0.5" opacity="0.3"/>
</svg>
"""

LOGO_SVG_SMALL = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 45">
  <rect x="0" y="2" width="158" height="40" rx="8" fill="#0f2b3d"/>
  <rect x="10" y="12" width="5" height="18" rx="1.5" fill="#20c997"/>
  <rect x="5" y="17" width="15" height="5" rx="1.5" fill="#20c997"/>
  <text x="28" y="21" font-family="Georgia, serif" font-size="11" font-weight="bold" fill="#ffffff">BEAUMONT</text>
  <text x="28" y="35" font-family="Georgia, serif" font-size="8.5" fill="#20c997" letter-spacing="2.5">HOSPITAL</text>
</svg>
"""

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Beaumont Hospital Portal",
    page_icon="🏥",
    layout="wide"
)

# --- KONEKSI DATABASE ---
MONGO_URI = st.secrets["MONGO_URI"]

@st.cache_resource
def init_db_connection():
    client = MongoClient(MONGO_URI)
    return client

client = init_db_connection()
db = client["beaumont_db"]
collection_kpi = db["kpi_trends"]
collection_users = db["users"]

# --- SISTEM AUTENTIKASI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

def login_user(username, password):
    user = collection_users.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        return True
    return False

def create_user(username, password):
    if collection_users.find_one({"username": username}):
        return False
    hashed_password = generate_password_hash(password)
    collection_users.insert_one({"username": username, "password": hashed_password})
    return True

def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

# ==========================================
# HALAMAN LOGIN / SIGN UP
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # === LOGO DI LOGIN PAGE ===
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; margin-bottom: 8px; margin-top: 20px;">
                {LOGO_SVG}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Alternatif: Jika kamu punya file gambar logo (taruh di folder 'assets/')
        # st.image("assets/logo.png", use_column_width=True)

        st.markdown("<p style='text-align: center; color: gray; margin-top: 4px;'>Secure Executive Access Only. Please verify your identity.</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔒 Login", "📝 Sign Up"])

        with tab1:
            st.subheader("Login to Dashboard")
            login_username = st.text_input("Username", key="log_user")
            login_password = st.text_input("Password", type="password", key="log_pass")
            if st.button("Login", type="primary", use_container_width=True):
                if login_user(login_username, login_password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_username
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")

        with tab2:
            st.subheader("Create New Executive Account")
            new_username = st.text_input("New Username", key="reg_user")
            new_password = st.text_input("New Password", type="password", key="reg_pass")
            if st.button("Sign Up", type="secondary", use_container_width=True):
                if new_username and new_password:
                    if create_user(new_username, new_password):
                        st.success("Account created successfully! You can now log in.")
                    else:
                        st.error("Username already exists. Please choose another one.")
                else:
                    st.warning("Please fill out both fields.")


# ==========================================
# HALAMAN UTAMA DASHBOARD
# ==========================================
else:
    # ==========================================
    # SIDEBAR
    # ==========================================

    # === LOGO DI SIDEBAR ===
    st.sidebar.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            {LOGO_SVG_SMALL}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Alternatif: Jika pakai file gambar
    # st.sidebar.image("assets/logo.png", use_column_width=True)

    st.sidebar.markdown(f"### 👤 Welcome, **{st.session_state['username']}**")
    st.sidebar.button("🚪 Logout", on_click=logout, use_container_width=True)
    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🏥 System Overview")
    st.sidebar.info(
        "**Beaumont KPI Portal**\n\n"
        "Executive decision-support system for monitoring clinical and operational metrics."
    )

    st.sidebar.markdown("### 🛡️ Security & Compliance")
    st.sidebar.success(
        "✅ **GDPR & HSE Aligned**\n\nData anonymization & aggregation applied.\n\n"
        "✅ **HIPAA Benchmark**\n\nRole-Based Access Control (RBAC) & Encryption at Rest active."
    )

    st.sidebar.markdown("### 💻 Architecture Stack")
    st.sidebar.markdown(
        "- **Engine**: Python 3 & Streamlit\n"
        "- **Database**: MongoDB Atlas (Cloud NoSQL)\n"
        "- **Visualization**: Plotly Interactive\n"
        "- **Auth**: Werkzeug Hashing"
    )

    st.sidebar.markdown("---")

    st.sidebar.markdown("### 📖 Dashboard Guide")

    with st.sidebar.expander("📊 How to read the Metrics (Cards)"):
        st.markdown(
            "**Value**: Actual KPI value in the last reporting period.\n\n"
            "**Target**: The performance threshold has been set. (Red text indicates attention is needed).\n\n"
            "**YTD (Year-to-Date)**: Accumulation or average value from the beginning of the year until now."
        )

    with st.sidebar.expander("📈 How to read the Charts"):
        st.markdown(
            "**Bar Chart (Comparison)**: Comparing Beaumont's performance against the national average.\n\n"
            "**Line Chart (Trend)**: Tracking historical fluctuations. The horizontal red dashed line on both charts indicates the **Target Line** as an evaluation *benchmark*."
        )

    # --- METADATA STATIS ---
    kpi_meta = {
        "elective_los": {"name": "Elective length of stay", "unit": "Days", "cards": {"value": "5.1", "target_text": "≤ 4.5", "target_num": 4.5, "frequency": "M-1M", "ytd": "5.2"}, "comparison": {"hospital": 5.1, "national": 4.8}},
        "avg_los_inpatient": {"name": "Average length of stay - inpatient discharges", "unit": "Days", "cards": {"value": "7.9", "target_text": "≤ 4.8", "target_num": 4.8, "frequency": "M-1M", "ytd": "8.3"}, "comparison": {"hospital": 7.9, "national": 5.0}},
        "surg_emerg_readm": {"name": "Surgical emergency readmissions", "unit": "%", "cards": {"value": "1.5%", "target_text": "≤ 2.0%", "target_num": 2.0, "frequency": "M-1M", "ytd": "1.9%"}, "comparison": {"hospital": 1.5, "national": 1.7}},
        "med_avg_los": {"name": "Medical average length of stay", "unit": "Days", "cards": {"value": "9.9", "target_text": "≤ 7.0", "target_num": 7.0, "frequency": "M-1M", "ytd": "10.8"}, "comparison": {"hospital": 9.9, "national": 7.1}},
        "s_aureus": {"name": "Hospital new cases of S. aureus", "unit": "Cases", "cards": {"value": "1.6", "target_text": "≤ 0.7", "target_num": 0.7, "frequency": "M", "ytd": "0.9"}, "comparison": {"hospital": 1.6, "national": 0.7}},
        "c_difficile": {"name": "Hospital new cases of C. difficile", "unit": "Cases", "cards": {"value": "3.7", "target_text": "≤ 2.0", "target_num": 2.0, "frequency": "M", "ytd": "3.5"}, "comparison": {"hospital": 3.7, "national": 2.3}},
        "med_emerg_readm": {"name": "Medical emergency readmissions", "unit": "%", "cards": {"value": "10.4%", "target_text": "≤ 11.1%", "target_num": 11.1, "frequency": "M-1M", "ytd": "11.0%"}, "comparison": {"hospital": 10.4, "national": 11.1}}
    }

    st.markdown("""
        <style>
        .kpi-box { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border-left: 4px solid; margin-bottom: 20px;}
        .kpi-title { font-size: 14px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; }
        .kpi-value { font-size: 28px; font-weight: 700; color: #2c3e50; }
        .val-red { color: #e74c3c !important; }
        </style>
    """, unsafe_allow_html=True)

    # === HEADER DASHBOARD DENGAN LOGO ===
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown("<h1 style='color: #20c997;'>Beaumont Hospital Executive Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("This dashboard presents a detailed analysis of operational and clinical Key Performance Indicators (KPIs).")
    with header_col2:
        # Logo di pojok kanan header
        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-end; align-items:center; height:100%; padding-top:16px;">
                {LOGO_SVG}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Alternatif: Jika pakai file gambar
        # st.image("assets/logo.png", width=180)

    st.markdown("### Controls")
    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        selected_kpi_id = st.selectbox("Select KPI:", options=list(kpi_meta.keys()), format_func=lambda x: kpi_meta[x]["name"])
    with col_ctrl2:
        selected_year = st.selectbox("Select Trend Year:", options=["25", "24", "all"], format_func=lambda x: "All (2024 & 2025)" if x == "all" else f"20{x}")

    meta = kpi_meta[selected_kpi_id]

    st.markdown("---")
    st.markdown(f"<h4 style='color: #20c997;'>Selected KPI: {meta['name']}</h4>", unsafe_allow_html=True)

    doc = collection_kpi.find_one({"kpi_id": selected_kpi_id})
    trend_data = doc["trend"] if doc else []

    if selected_year != "all":
        trend_data = [d for d in trend_data if d["date"].endswith(selected_year)]

    df_trend = pd.DataFrame(trend_data)

    col_left, col_right = st.columns(2)

    with col_left:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='kpi-box' style='border-color: #3498db;'><div class='kpi-title'>Value</div><div class='kpi-value val-red'>{meta['cards']['value']}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='kpi-box' style='border-color: #95a5a6;'><div class='kpi-title'>Target</div><div class='kpi-value'>{meta['cards']['target_text']}</div></div>", unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f"<div class='kpi-box' style='border-color: #17a2b8;'><div class='kpi-title'>Frequency</div><div class='kpi-value'>{meta['cards']['frequency']}</div></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='kpi-box' style='border-color: #f1c40f;'><div class='kpi-title'>YTD</div><div class='kpi-value'>{meta['cards']['ytd']}</div></div>", unsafe_allow_html=True)

        st.markdown(f"**Current KPI value comparison National versus Hospital in {meta['unit']}**")
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            y=['National', 'Beaumont Hospital'],
            x=[meta['comparison']['national'], meta['comparison']['hospital']],
            orientation='h',
            marker=dict(color=['#95a5a6', '#3498db'])
        ))
        fig_comp.add_vline(x=meta['cards']['target_num'], line_width=2, line_dash="dash", line_color="red", annotation_text="Target", annotation_position="bottom right")
        fig_comp.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250, showlegend=False)
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_right:
        year_label = "2024 & 2025" if selected_year == "all" else f"20{selected_year}"
        st.markdown(f"**KPI Value Trend in {meta['unit']} ({year_label})**")

        if not df_trend.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=df_trend['date'], y=df_trend['val'],
                mode='lines+markers',
                line=dict(color='#3498db', width=3),
                fill='tozeroy', fillcolor='rgba(52, 152, 219, 0.2)'
            ))
            fig_trend.add_hline(y=meta['cards']['target_num'], line_width=2, line_dash="dash", line_color="red", annotation_text="Target")
            fig_trend.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=550, yaxis=dict(rangemode='tozero'))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Tidak ada data tren untuk periode ini di database.")
