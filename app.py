import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# 1. KONFIGURASI HALAMAN & TEMA
# ==========================================
st.set_page_config(page_title="Beaumont Hospital Portal", layout="wide")

# Custom CSS untuk tampilan Executive (Teal & Grey)
st.markdown("""
    <style>
    .kpi-box { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border-left: 4px solid; margin-bottom: 20px;}
    .kpi-title { font-size: 14px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #2c3e50; }
    .val-red { color: #e74c3c !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [aria-selected="true"] { background-color: #20c997 !important; color: white !important; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. KONEKSI DATABASE (MONGODB ATLAS)
# ==========================================
MONGO_URI = st.secrets["MONGO_URI"]

@st.cache_resource
def init_db_connection():
    client = MongoClient(MONGO_URI)
    return client

client = init_db_connection()
db = client["beaumont_db"]
collection_kpi = db["kpi_trends"]
collection_users = db["users"]

# ==========================================
# 3. FUNGSI AUTENTIKASI
# ==========================================
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
# 4. LOGIKA TAMPILAN
# ==========================================

if not st.session_state['logged_in']:
    # HALAMAN LOGIN / SIGNUP
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #20c997;'>🏥 Beaumont Hospital</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Executive Information System - Dublin, Ireland</p>", unsafe_allow_html=True)
        
        tab_log, tab_reg = st.tabs(["🔐 Executive Login", "📝 Register Account"])
        
        with tab_log:
            l_user = st.text_input("Username", key="l_u")
            l_pass = st.text_input("Password", type="password", key="l_p")
            if st.button("Access Dashboard", type="primary", use_container_width=True):
                if login_user(l_user, l_pass):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = l_user
                    st.rerun()
                else:
                    st.error("Authentication Failed.")

        with tab_reg:
            r_user = st.text_input("New Username", key="r_u")
            r_pass = st.text_input("New Password", type="password", key="r_p")
            if st.button("Create Account", use_container_width=True):
                if r_user and r_pass:
                    if create_user(r_user, r_pass):
                        st.success("Success! Please Login.")
                    else:
                        st.error("Username already taken.")

else:
    # HALAMAN DASHBOARD UTAMA
    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 👤 User: **{st.session_state['username']}**")
    st.sidebar.button("🚪 Logout", on_click=logout, use_container_width=True)
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("### 🛡️ Compliance")
    st.sidebar.info("**GDPR & HSE Ireland**\n\n**HIPAA Benchmark** for Cyber Security.")
    
    st.sidebar.markdown("### 💻 Architecture")
    st.sidebar.markdown("- Python & Streamlit\n- MongoDB Atlas Cloud\n- Plotly Visuals\n- Werkzeug Hashing")

    # --- MAIN CONTENT ---
    st.markdown("<h1 style='color: #20c997;'>Executive Performance Dashboard</h1>", unsafe_allow_html=True)
    
    # Metadata KPI
    kpi_meta = {
        "elective_los": {"name": "Elective Length of Stay", "unit": "Days", "cards": {"value": "5.1", "target_text": "≤ 4.5", "target_num": 4.5, "frequency": "Monthly", "ytd": "5.2"}, "comparison": {"hospital": 5.1, "national": 4.8}},
        "avg_los_inpatient": {"name": "Avg LOS - Inpatient Discharges", "unit": "Days", "cards": {"value": "7.9", "target_text": "≤ 4.8", "target_num": 4.8, "frequency": "Monthly", "ytd": "8.3"}, "comparison": {"hospital": 7.9, "national": 5.0}},
        "surg_emerg_readm": {"name": "Surgical Emergency Readmissions", "unit": "%", "cards": {"value": "1.5%", "target_text": "≤ 2.0%", "target_num": 2.0, "frequency": "Monthly", "ytd": "1.9%"}, "comparison": {"hospital": 1.5, "national": 1.7}},
        "med_avg_los": {"name": "Medical Average LOS", "unit": "Days", "cards": {"value": "9.9", "target_text": "≤ 7.0", "target_num": 7.0, "frequency": "Monthly", "ytd": "10.8"}, "comparison": {"hospital": 9.9, "national": 7.1}},
        "s_aureus": {"name": "New Cases: S. Aureus", "unit": "Cases", "cards": {"value": "1.6", "target_text": "≤ 0.7", "target_num": 0.7, "frequency": "Monthly", "ytd": "0.9"}, "comparison": {"hospital": 1.6, "national": 0.7}},
        "c_difficile": {"name": "New Cases: C. Difficile", "unit": "Cases", "cards": {"value": "3.7", "target_text": "≤ 2.0", "target_num": 2.0, "frequency": "Monthly", "ytd": "3.5"}, "comparison": {"hospital": 3.7, "national": 2.3}},
        "med_emerg_readm": {"name": "Medical Emergency Readmissions", "unit": "%", "cards": {"value": "10.4%", "target_text": "≤ 11.1%", "target_num": 11.1, "frequency": "Monthly", "ytd": "11.0%"}, "comparison": {"hospital": 10.4, "national": 11.1}}
    }

    # Controls
    c1, c2 = st.columns(2)
    with c1:
        sel_kpi = st.selectbox("Analyze KPI:", options=list(kpi_meta.keys()), format_func=lambda x: kpi_meta[x]["name"])
    with c2:
        sel_year = st.selectbox("Trend Year:", options=["25", "24", "all"], format_func=lambda x: "All Data" if x=="all" else f"20{x}")

    meta = kpi_meta[sel_kpi]
    st.markdown("---")

    # Layout Metrics & Comparison
    col_l, col_r = st.columns(2)
    with col_l:
        ca, cb = st.columns(2)
        with ca:
            st.markdown(f"<div class='kpi-box' style='border-color: #3498db;'><div class='kpi-title'>Current Value</div><div class='kpi-value val-red'>{meta['cards']['value']}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-box' style='border-color: #17a2b8;'><div class='kpi-title'>Frequency</div><div class='kpi-value'>{meta['cards']['frequency']}</div></div>", unsafe_allow_html=True)
        with cb:
            st.markdown(f"<div class='kpi-box' style='border-color: #95a5a6;'><div class='kpi-title'>Target</div><div class='kpi-value'>{meta['cards']['target_text']}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-box' style='border-color: #f1c40f;'><div class='kpi-title'>YTD</div><div class='kpi-value'>{meta['cards']['ytd']}</div></div>", unsafe_allow_html=True)

    with col_r:
        fig_c = go.Figure()
        fig_c.add_trace(go.Bar(y=['National', 'Hospital'], x=[meta['comparison']['national'], meta['comparison']['hospital']], orientation='h', marker_color=['#bdc3c7', '#20c997']))
        fig_c.add_vline(x=meta['cards']['target_num'], line_dash="dash", line_color="red")
        fig_c.update_layout(title="Comparison against National Benchmark", height=300, margin=dict(t=50, b=20, l=0, r=0))
        st.plotly_chart(fig_c, use_container_width=True)

    # Time Trend
    doc = collection_kpi.find_one({"kpi_id": sel_kpi})
    t_data = doc["trend"] if doc else []
    if sel_year != "all":
        t_data = [d for d in t_data if d["date"].endswith(sel_year)]
    df_t = pd.DataFrame(t_data)

    if not df_t.empty:
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=df_t['date'], y=df_t['val'], mode='lines+markers', line=dict(color='#20c997', width=4), fill='tozeroy', fillcolor='rgba(32, 201, 151, 0.1)'))
        fig_t.add_hline(y=meta['cards']['target_num'], line_dash="dash", line_color="red")
        fig_t.update_layout(title=f"Historical Trend Analysis ({sel_year})", height=350)
        st.plotly_chart(fig_t, use_container_width=True)

    # --- BAGIAN TRIASE (ADDITIONAL) ---
    st.markdown("---")
    st.subheader("🚑 Emergency Department (ED) Triage Distribution")
    
    col_tri1, col_tri2 = st.columns([1, 1.5])
    with col_tri1:
        st.write("Triase mengelompokkan pasien berdasarkan tingkat kegawatdaruratan klinis untuk mengoptimalkan alur kerja UGD.")
        st.error("**🔴 P1 (Emergency)**: Resusitasi segera.")
        st.warning("**🟡 P2 (Urgent)**: Penanganan dalam 15-30 menit.")
        st.success("**🟢 P3 (Non-Urgent)**: Kondisi stabil/rutin.")
        st.caption("_Sistem Triase memengaruhi efisiensi Length of Stay (LOS) secara keseluruhan._")

    with col_tri2:
        tri_labels = ["P1 (Emergency)", "P2 (Urgent)", "P3 (Non-Urgent)"]
        tri_values = [12, 38, 50] # Simulasi data triase
        fig_p = go.Figure(data=[go.Pie(labels=tri_labels, values=tri_values, hole=.4, marker_colors=["#e74c3c", "#f1c40f", "#2ecc71"])])
        fig_p.update_layout(height=350, margin=dict(t=0, b=0, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
        st.plotly_chart(fig_p, use_container_width=True)
