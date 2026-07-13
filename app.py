import os
import io
import base64
from datetime import datetime

import gradio as gr

from backend.auth import (
    login_user,
    register_user,
    send_reset_email,
    get_github_login_url,
    complete_github_login,
)
from backend.prediction import predict_image

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from backend import database as db_module
except ImportError:
    db_module = None

try:
    from backend import auth as auth_module
except ImportError:
    auth_module = None


CLASSES = ["Potholes", "Cracks", "Patch", "Surface Defects"]
SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]
SEVERITY_COLOR = {
    "Low": "#2ecc71",
    "Medium": "#f39c12",
    "High": "#e74c3c",
    "Critical": "#8b0000",
    "---": "#b0b0b0",
}
ACCENT = "#6C5CE7"

APP_URL = os.getenv("APP_URL", "https://amruthjakku-surface-crack-detection.hf.space/login")

# Lazy-cached GitHub OAuth URL so we don't call Supabase at import time
_GITHUB_LOGIN_URL = None

def _get_github_url():
    global _GITHUB_LOGIN_URL
    if _GITHUB_LOGIN_URL is None:
        try:
            _GITHUB_LOGIN_URL = get_github_login_url(redirect_to=APP_URL)
        except Exception:
            _GITHUB_LOGIN_URL = "#"
    return _GITHUB_LOGIN_URL


CUSTOM_CSS = """
:root {
    --accent: #6C5CE7;
    --accent-light: #8B7CF7;
    --accent-dark: #4A3DB8;
    --accent-glow: rgba(108, 92, 231, 0.12);
    --sidebar-bg: #1a1a2e;
    --sidebar-hover: #25254B;
    --sidebar-active: #2D2D5E;
    --sidebar-text: #9B9BB5;
    --sidebar-text-active: #FFFFFF;
    --surface: #F0F2F8;
    --bg-card: #FFFFFF;
    --text-primary: #1A1A2E;
    --text-secondary: #7A7A9E;
    --text-muted: #B0B0C8;
    --border-light: #E8EAF0;
    --radius: 12px;
    --radius-lg: 16px;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.06);
    --shadow-lg: 0 8px 32px rgba(0,0,0,0.1);
}
.gradio-container { font-family: 'Inter', -apple-system, sans-serif !important; background: var(--surface) !important; }
footer { display: none !important; }

/* ---- Auth ---- */
.auth-container {
    min-height: 100vh;
    background: linear-gradient(-45deg, #1a1a2e, #16213e, #0f3460, #1a1a2e);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
    display: flex !important;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}
@keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
.auth-box {
    background: rgba(255,255,255,0.97);
    backdrop-filter: blur(20px);
    border-radius: var(--radius-lg);
    padding: 2.5rem 2rem;
    width: 100%;
    max-width: 420px;
    box-shadow: var(--shadow-lg);
    animation: slideUpFade 0.4s ease-out;
}
@keyframes slideUpFade { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.auth-title { text-align: center; font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem; }
.auth-subtitle { text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1.5rem; }
.auth-error { background: #FEF2F2; color: #DC2626; padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem; text-align: center; border: 1px solid #FECACA; animation: shake 0.3s ease; }
.auth-success { background: #F0FDF4; color: #16A34A; padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem; text-align: center; border: 1px solid #BBF7D0; }
@keyframes shake { 0%,100% { transform: translateX(0); } 25% { transform: translateX(-4px); } 75% { transform: translateX(4px); } }
.auth-divider { display: flex; align-items: center; gap: 1rem; margin: 1rem 0; color: var(--text-muted); font-size: 0.8rem; }
.auth-divider::before, .auth-divider::after { content: ''; flex: 1; border-top: 1px solid var(--border-light); }

/* Landing hero */
.landing-hero { text-align: center; padding: 1.5rem 0.5rem; }
.landing-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #fff 0%, #a78bfa 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 1rem; line-height: 1.2; }
.landing-desc { font-size: 1rem; color: #C0C0D0; max-width: 520px; margin: 0 auto 2rem; line-height: 1.7; }

/* GitHub link */
.auth-github-link a { display: block; text-align: center; padding: 0.6rem; border-radius: 8px; border: 1px solid #D0D0E0; background: #24292E; color: white !important; text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; }
.auth-github-link a:hover { background: #1B1F23; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }

/* ---- Sidebar ---- */
.sidebar { background: var(--sidebar-bg) !important; border-right: 1px solid rgba(255,255,255,0.05); padding: 1.5rem 0 !important; }
.sidebar-inner { padding: 0 0.75rem; height: 100%; display: flex; flex-direction: column; }
.app-logo { font-size: 1rem; font-weight: 700; color: #fff; padding: 0 0.5rem; margin-bottom: 0.15rem; }
.app-tagline { font-size: 0.72rem; color: var(--sidebar-text); padding: 0 0.5rem; margin-bottom: 1.5rem; }
.nav-group { display: flex; flex-direction: column; gap: 2px; }
.nav-btn { display: flex; align-items: center; gap: 0.6rem; width: 100%; padding: 0.6rem 0.75rem; border: none; border-radius: 8px; background: transparent; color: var(--sidebar-text); font-size: 0.85rem; cursor: pointer; transition: all 0.15s; text-align: left; border-left: 3px solid transparent; }
.nav-btn:hover { background: var(--sidebar-hover); color: #ccc; }
.nav-btn.active { background: var(--sidebar-active); color: var(--sidebar-text-active); border-left-color: var(--accent); font-weight: 600; }
.sidebar-footer { margin-top: auto; padding: 1rem 0.75rem 0; border-top: 1px solid rgba(255,255,255,0.06); }
.sidebar-user-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--accent); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.85rem; flex-shrink: 0; }
.sidebar-user-name { font-size: 0.82rem; color: #ddd; font-weight: 500; line-height: 1.2; }
.sidebar-user-email { font-size: 0.7rem; color: var(--sidebar-text); }

/* ---- App content ---- */
.app-container { background: var(--surface); }
.content-area { padding: 1.5rem 2rem; }

/* ---- Cards ---- */
.card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 1.25rem 1.5rem; box-shadow: var(--shadow-sm); margin-bottom: 1rem; transition: box-shadow var(--transition); }
.card:hover { box-shadow: var(--shadow-md); }
.card-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }

/* Stat grid */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 1.25rem 1rem; box-shadow: var(--shadow-sm); text-align: center; transition: all var(--transition); position: relative; overflow: hidden; }
.stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat-icon { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 10px; font-size: 1.1rem; margin-bottom: 0.5rem; }
.stat-value { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.stat-label { font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px; }

/* ---- Page headers ---- */
.page-title { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); }
.page-sub { color: var(--text-secondary); font-size: 0.85rem; margin-top: -4px; margin-bottom: 1.25rem; }

/* ---- Pill ---- */
.pill { display: inline-block; padding: 3px 12px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; color: white; }

/* ---- Upload zone ---- */
.upload-zone { border: 2px dashed #D0D0E0; border-radius: var(--radius); padding: 2rem 1rem; text-align: center; transition: all var(--transition); cursor: pointer; }
.upload-zone:hover { border-color: var(--accent); background: var(--accent-glow); }
.upload-zone-icon { font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.4; }
.upload-zone-text { font-size: 0.85rem; color: var(--text-secondary); }
.upload-zone-sub { font-size: 0.72rem; color: var(--text-muted); margin-top: 4px; }

/* ---- Progress bars ---- */
.progress-track { background: #E8EAF0; border-radius: 999px; height: 20px; overflow: hidden; margin-bottom: 6px; }
.progress-fill { height: 100%; border-radius: 999px; transition: width 0.4s ease; }
.progress-label { font-size: 0.78rem; display: flex; justify-content: space-between; margin-bottom: 2px; }

/* ---- Feature grid ---- */
.feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1rem 0; }
.feat-card { background: #F8F9FE; border-radius: var(--radius); padding: 1rem; text-align: center; }
.feat-card .fi { font-size: 1.5rem; margin-bottom: 0.4rem; }
.feat-card .ft { font-weight: 600; font-size: 0.85rem; color: var(--text-primary); }
.feat-card .fd { font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px; }

/* ---- Team ---- */
.team-row { display: flex; gap: 1rem; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid var(--border-light); }
.team-row:last-child { border-bottom: none; }
.team-av { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.9rem; color: white; flex-shrink: 0; }

/* ---- Modal ---- */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 9999; animation: fadeIn 0.2s ease; }
.modal-box { background: white; border-radius: var(--radius-lg); padding: 2rem; max-width: 380px; width: 90%; text-align: center; box-shadow: var(--shadow-lg); animation: scaleUp 0.25s ease; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }

/* ---- Activity ---- */
.act-item { display: flex; gap: 0.75rem; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid var(--border-light); }
.act-item:last-child { border-bottom: none; }
.act-thumb { width: 48px; height: 48px; border-radius: 8px; object-fit: cover; flex-shrink: 0; }
.act-info { flex: 1; min-width: 0; }
.act-class { font-weight: 600; font-size: 0.85rem; color: var(--text-primary); }
.act-meta { font-size: 0.75rem; color: var(--text-secondary); }
.act-time { font-size: 0.72rem; color: var(--text-muted); flex-shrink: 0; }
"""


def compute_stats(history):
    total = len(history)
    cracks = sum(1 for h in history if h.get("predicted_class", "").lower() != "no crack")
    no_cracks = total - cracks
    avg_conf = (sum(h.get("confidence", 0) for h in history) / total) if total else 0.0
    return total, cracks, no_cracks, avg_conf


def class_distribution(history):
    counts = {c: 0 for c in CLASSES}
    for h in history:
        cls = h.get("predicted_class", "")
        for c in CLASSES:
            if c.lower() in cls.lower():
                counts[c] += 1
                break
    return counts


def severity_distribution(history):
    counts = {s: 0 for s in SEVERITY_ORDER}
    for h in history:
        sev = h.get("severity_label")
        if sev in counts:
            counts[sev] += 1
    total = sum(counts.values())
    return counts, total


def stat_card_html(icon, icon_bg, label, value):
    return f"""<div class="stat-card">
    <div class="stat-icon" style="background:{icon_bg}18; color:{icon_bg};">{icon}</div>
    <div class="stat-value">{value}</div>
    <div class="stat-label">{label}</div>
    <div style="position:absolute;top:0;left:0;right:0;height:3px;background:{icon_bg};border-radius:16px 16px 0 0;"></div>
</div>"""


def donut_chart(counts):
    labels = [k for k, v in counts.items() if v > 0]
    values = [v for v in counts.values() if v > 0]
    if not values or not PLOTLY_AVAILABLE:
        return None
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.6,
        marker=dict(colors=["#6C5CE7", "#00b894", "#fdcb6e", "#e17055"]),
        textinfo="none",
    )])
    fig.update_layout(
        showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=220,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def severity_bars_html(counts, total_):
    html = '<div class="card"><div class="card-title">Severity Overview</div>'
    for sev in SEVERITY_ORDER:
        n = counts.get(sev, 0)
        pct = (n / total_ * 100) if total_ else 0
        html += f"""<div class="progress-label"><span>{sev}</span><span>{n}</span></div>
<div class="progress-track"><div class="progress-fill" style="width:{pct}%;background:{SEVERITY_COLOR.get(sev, '#999')};"></div></div>"""
    html += "</div>"
    return html


def load_prediction_history(user_id, session_history):
    if db_module and hasattr(db_module, "get_user_analyses") and user_id:
        try:
            records = db_module.get_user_analyses(user_id)
            if records:
                return records
        except Exception:
            pass
    return session_history


def save_prediction_record(user_id, record, session_history):
    session_history.insert(0, record)
    if db_module and hasattr(db_module, "save_analysis") and user_id:
        try:
            db_module.save_analysis(user_id, record)
        except Exception:
            pass
    return session_history


# =========================================================================
# GRADIO APP
# =========================================================================
with gr.Blocks(
    title="Surface Crack Detection",
    fill_height=True,
) as app:

    # ---- State ----
    auth_token = gr.State(None)
    user_info = gr.State({})
    prediction_history = gr.State([])

    # Clear OAuth code from URL on any load (uses head injection via launch js)
    gr.HTML("<!-- OAuth cleanup handled via launch -->")

    # =====================================================================
    # AUTH SECTION
    # =====================================================================
    with gr.Column(elem_classes="auth-container", visible=True) as auth_section:

        # ----- Landing -----
        with gr.Column(elem_classes="auth-box", visible=True) as landing_col:
            gr.HTML(
                '<div class="landing-hero">'
                '<div style="font-size:3rem;margin-bottom:0.5rem;">🛣️</div>'
                '<div class="landing-title">Surface Crack Detection</div>'
                '<div class="landing-desc">AI-powered detection and classification of road and bridge surface defects using Deep Learning and Computer Vision.</div>'
                '</div>'
            )
            go_login_btn = gr.Button("Login", variant="primary", size="lg")

        # ----- Login -----
        with gr.Column(elem_classes="auth-box", visible=False) as login_col:
            gr.HTML('<div class="auth-title">🔐 Welcome Back</div>')
            gr.HTML('<div class="auth-subtitle">Sign in to your account</div>')
            login_error = gr.HTML("", visible=False, elem_classes="auth-error")
            login_email = gr.Textbox(label="Email", placeholder="you@example.com")
            login_password = gr.Textbox(label="Password", placeholder="••••••••", type="password")
            login_btn = gr.Button("Sign In", variant="primary", size="lg")
            gr.HTML('<div class="auth-divider">or continue with</div>')
            github_link = gr.HTML("", elem_classes="auth-github-link")
            with gr.Row():
                show_forgot_btn = gr.Button("Forgot Password?", size="lg")
                show_register_from_login_btn = gr.Button("Create Account", size="lg")

        # ----- Register -----
        with gr.Column(elem_classes="auth-box", visible=False) as register_col:
            gr.HTML('<div class="auth-title">📝 Create Account</div>')
            gr.HTML('<div class="auth-subtitle">Join Surface Crack Detection</div>')
            register_msg = gr.HTML("", visible=False)
            reg_name = gr.Textbox(label="Full Name", placeholder="John Doe")
            reg_email = gr.Textbox(label="Email", placeholder="you@example.com")
            reg_phone = gr.Textbox(label="Phone Number", placeholder="+1 234 567 890")
            reg_password = gr.Textbox(label="Password", placeholder="Min. 6 characters", type="password")
            reg_confirm = gr.Textbox(label="Confirm Password", placeholder="••••••••", type="password")
            register_btn = gr.Button("Create Account", variant="primary", size="lg")
            back_to_login_btn = gr.Button("← Back to Login", size="lg")

        # ----- Forgot Password -----
        with gr.Column(elem_classes="auth-box", visible=False) as forgotpwd_col:
            gr.HTML('<div class="auth-title">🔒 Forgot Password</div>')
            gr.HTML('<div class="auth-subtitle">Enter your registered email</div>')
            forgot_msg = gr.HTML("", visible=False)
            forgot_email = gr.Textbox(label="Email Address", placeholder="you@example.com")
            send_reset_btn = gr.Button("Send Reset Link", variant="primary", size="lg")
            back_to_login2_btn = gr.Button("← Back to Login", size="lg")

    # =====================================================================
    # MAIN APP SECTION
    # =====================================================================
    with gr.Column(elem_classes="app-container", visible=False) as app_section:
        with gr.Row(equal_height=False):
            # ---- Sidebar ----
            with gr.Column(scale=1, elem_classes="sidebar", min_width=220):
                with gr.Column(elem_classes="sidebar-inner"):
                    gr.HTML('<div class="app-logo">🛣️ Surface Crack Detection</div>')
                    gr.HTML('<div class="app-tagline">Detect &amp; analyze road surface cracks</div>')
                    nav_btn_html = gr.HTML(
                        '<div class="nav-group">'
                        '<button class="nav-btn active" data-page="Dashboard">🏠  Dashboard</button>'
                        '<button class="nav-btn" data-page="Predict">🔍  Predict</button>'
                        '<button class="nav-btn" data-page="User">👤  User</button>'
                        '<button class="nav-btn" data-page="About Us">ℹ️  About Us</button>'
                        '<button class="nav-btn" data-page="Logout" style="margin-top:0.5rem;color:#ef4444;">🚪  Logout</button>'
                        '</div>'
                    )
                    nav_state = gr.Textbox(value="Dashboard", visible=False, elem_id="nav-state")
                    gr.HTML('<div class="sidebar-footer" id="sidebar-footer"></div>')
                    user_sidebar_info = gr.HTML("")

            # ---- Content ----
            with gr.Column(scale=4, elem_classes="content-area"):
                # Dashboard
                with gr.Column(visible=True) as dashboard_page:
                    gr.HTML('<div class="page-title">Dashboard</div>')
                    gr.HTML('<div class="page-sub">Upload an image to detect and analyze surface defects.</div>')
                    dash_stats = gr.HTML("")
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=1):
                            gr.HTML('<div class="card"><div class="card-title">📸 Upload &amp; Predict</div><p style="font-size:0.82rem;color:var(--text-secondary);margin:0;">Upload a road or bridge surface image to detect defects.</p></div>')
                            dash_upload = gr.Image(type="pil", height=300, show_label=False, container=False)
                            dash_run = gr.Button("🔍 Run Prediction", variant="primary", size="lg")
                        with gr.Column(scale=1):
                            dash_recent = gr.HTML('<div class="card"><div class="card-title">📋 Recent Prediction</div><p style="color:var(--text-secondary);font-size:0.85rem;">No predictions yet. Upload an image above.</p></div>')
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=1):
                            gr.HTML('<div class="card" style="padding-bottom:1rem;"><div class="card-title">📊 Class Distribution</div></div>')
                            dash_chart = gr.Plot(None, show_label=False, container=False)
                        with gr.Column(scale=1):
                            dash_severity = gr.HTML('<div class="card"><div class="card-title">⚠️ Severity Overview</div><p style="color:var(--text-secondary);font-size:0.85rem;">No data yet.</p></div>')

                # Predict
                with gr.Column(visible=False) as predict_page:
                    gr.HTML('<div class="page-title">Predict</div>')
                    gr.HTML('<div class="page-sub">Run a detailed analysis on a single image.</div>')
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=1):
                            gr.HTML('<div class="card"><div class="card-title">📸 Select &amp; Upload</div></div>')
                            pred_class_selector = gr.Radio(CLASSES, value=CLASSES[0], label="Expected category", container=False)
                            pred_upload = gr.Image(type="pil", height=300, show_label=False, container=False)
                            pred_run = gr.Button("🔍 Run Prediction", variant="primary", size="lg")
                        with gr.Column(scale=1):
                            pred_results = gr.HTML('<div class="card"><div class="card-title">📋 Results</div><p style="color:var(--text-secondary);font-size:0.85rem;">Run a prediction to see results here.</p></div>')
                    pred_report = gr.HTML("")

                # User
                with gr.Column(visible=False) as user_page:
                    gr.HTML('<div class="page-title">User</div>')
                    gr.HTML('<div class="page-sub">Manage your profile and account settings.</div>')
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=1):
                            user_profile = gr.HTML('<div class="card"><div class="card-title">👤 Profile</div><p style="color:var(--text-secondary);font-size:0.85rem;">Loading...</p></div>')
                        with gr.Column(scale=1):
                            user_stats = gr.HTML('<div class="card"><div class="card-title">📊 Statistics</div><p style="color:var(--text-secondary);font-size:0.85rem;">Loading...</p></div>')
                    user_activity = gr.HTML('<div class="card"><div class="card-title">📜 Recent Activity</div><p style="color:var(--text-secondary);font-size:0.85rem;">No activity yet.</p></div>')

                # About Us
                with gr.Column(visible=False) as about_page:
                    gr.HTML('<div class="page-title">About Us</div>')
                    gr.HTML('<div class="page-sub">Learn more about our project and team.</div>')
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=3):
                            gr.HTML(
                                '<div class="card">'
                                '<div class="card-title">🎯 Project Overview</div>'
                                '<p style="font-size:0.9rem;color:var(--text-secondary);line-height:1.6;">'
                                'Surface Crack Detection is an AI-powered application designed to '
                                'identify and classify surface defects in road and concrete images. '
                                'The system uses a deep learning model to detect cracks, potholes, '
                                'patches, and other surface defects with high accuracy.</p>'
                                '<div class="feature-grid">'
                                '<div class="feat-card"><div class="fi">⚙️</div><div class="ft">AI Powered</div><div class="fd">Deep learning model for accurate detection</div></div>'
                                '<div class="feat-card"><div class="fi">🛡️</div><div class="ft">High Accuracy</div><div class="fd">Trained on diverse datasets for reliable results</div></div>'
                                '<div class="feat-card"><div class="fi">⚡</div><div class="ft">Easy to Use</div><div class="fd">Simple interface for quick, efficient analysis</div></div>'
                                '</div>'
                                '<p style="margin-top:1rem;"><strong>Technologies Used</strong><br>'
                                '<span style="color:var(--text-secondary);font-size:0.85rem;">🐍 Python · 🔥 PyTorch · 🎈 Gradio · 👁️ OpenCV · 🖼️ PIL · 🔢 NumPy · 🐼 Pandas · 📈 Scikit-learn</span></p>'
                                '</div>'
                            )
                        with gr.Column(scale=2):
                            gr.HTML(
                                '<div class="card">'
                                '<div class="card-title">👥 Our Team</div>'
                                '<div class="team-row"><div class="team-av" style="background:#6C5CE7;">AP</div><div><strong>Arvind Parsapuram</strong><br><span style="font-size:0.8rem;color:var(--text-secondary);">Developer &amp; Designer</span></div></div>'
                                '<div class="team-row"><div class="team-av" style="background:#00b894;">ML</div><div><strong>Team Member</strong><br><span style="font-size:0.8rem;color:var(--text-secondary);">ML Engineer</span></div></div>'
                                '<div class="team-row"><div class="team-av" style="background:#fdcb6e;color:#333;">DE</div><div><strong>Team Member</strong><br><span style="font-size:0.8rem;color:var(--text-secondary);">Data Engineer</span></div></div>'
                                '</div>'
                                '<div class="card">'
                                '<div class="card-title">📁 Repository</div>'
                                '<p style="font-size:0.85rem;color:var(--text-secondary);">'
                                'This project is part of the ACE Bootcamp — Team 7.<br>'
                                'Built with ❤️ using open-source technologies.</p>'
                                '</div>'
                            )

        # ---- Logout confirmation modal ----
        with gr.Column(visible=False) as logout_modal:
            gr.HTML(
                '<div class="modal-overlay">'
                '<div class="modal-box">'
                '<div style="font-size:2.5rem;margin-bottom:0.5rem;">🚪</div>'
                '<h3 style="margin:0 0 0.25rem;">Logout</h3>'
                '<p style="color:var(--text-secondary);font-size:0.9rem;margin:0 0 1.5rem;">Are you sure you want to logout?</p>'
                '</div></div>'
            )
            with gr.Row():
                cancel_logout_btn = gr.Button("Cancel", size="lg")
                confirm_logout_btn = gr.Button("Yes, Logout", variant="primary", size="lg")

    # =====================================================================
    # EVENTS — Auth Navigation
    # =====================================================================
    def show_login():
        return [gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)]
    def show_register():
        return [gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)]
    def show_forgot():
        return [gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)]

    nav_auth_outputs = [landing_col, login_col, register_col, forgotpwd_col]

    go_login_btn.click(fn=show_login, outputs=nav_auth_outputs)
    back_to_login_btn.click(fn=show_login, outputs=nav_auth_outputs)
    back_to_login2_btn.click(fn=show_login, outputs=nav_auth_outputs)
    show_forgot_btn.click(fn=show_forgot, outputs=nav_auth_outputs)
    show_register_from_login_btn.click(fn=show_register, outputs=nav_auth_outputs)

    # =====================================================================
    # EVENTS — Login
    # =====================================================================
    def handle_login(email, password):
        if not email or not password:
            return gr.update(visible=True, value="Please enter both email and password."), None, {}
        try:
            result = login_user(email=email, password=password)
            if result.get("success"):
                return gr.update(visible=False), result["access_token"], result["user"]
            return gr.update(visible=True, value=result.get("message", "Invalid credentials")), None, {}
        except Exception as e:
            return gr.update(visible=True, value=str(e)), None, {}

    def after_login_success(token, user):
        if token:
            return gr.update(visible=False), gr.update(visible=True)
        return gr.update(), gr.update()

    login_btn.click(
        fn=handle_login,
        inputs=[login_email, login_password],
        outputs=[login_error, auth_token, user_info],
    ).then(
        fn=after_login_success,
        inputs=[auth_token, user_info],
        outputs=[auth_section, app_section],
    ).then(
        fn=lambda u: (lambda n=u.get("full_name","User"), e=u.get("email",""): (
            f'<div class="sidebar-footer" style="display:flex;align-items:center;gap:0.6rem;">'
            f'<div class="sidebar-user-avatar">{n[0].upper() if n else "U"}</div>'
            f'<div><div class="sidebar-user-name">{n}</div>'
            f'<div class="sidebar-user-email">{e}</div></div></div>'
        ))(),
        inputs=[user_info],
        outputs=[user_sidebar_info],
    ).then(
        fn=lambda h: _refresh_dashboard(h),
        inputs=[prediction_history],
        outputs=[dash_stats, dash_recent, dash_chart, dash_severity],
    )

    # =====================================================================
    # EVENTS — Register
    # =====================================================================
    def handle_register(name, email, phone, password, confirm):
        if not name or not email or not password:
            return gr.update(visible=True, value="Please fill in all required fields.")
        if password != confirm:
            return gr.update(visible=True, value="Passwords do not match.")
        if len(password) < 6:
            return gr.update(visible=True, value="Password must be at least 6 characters.")
        try:
            result = register_user(email=email, password=password, full_name=name)
            if result.get("success"):
                return gr.update(visible=True, value="✅ " + result.get("message", "Registration successful! Please check your email."))
            return gr.update(visible=True, value="Registration failed.")
        except Exception as e:
            return gr.update(visible=True, value=str(e))

    register_btn.click(
        fn=handle_register,
        inputs=[reg_name, reg_email, reg_phone, reg_password, reg_confirm],
        outputs=[register_msg],
    )

    # =====================================================================
    # EVENTS — Forgot Password
    # =====================================================================
    def handle_forgot(email):
        if not email:
            return gr.update(visible=True, value="Please enter your email address.")
        try:
            result = send_reset_email(email=email)
            if result.get("success"):
                return gr.update(visible=True, value="✅ " + result.get("message", "Reset link sent."))
            return gr.update(visible=True, value="Failed to send reset link.")
        except Exception as e:
            return gr.update(visible=True, value=str(e))

    send_reset_btn.click(fn=handle_forgot, inputs=[forgot_email], outputs=[forgot_msg])

    # =====================================================================
    # EVENTS — GitHub OAuth
    # =====================================================================
    def gen_github_link():
        url = _get_github_url()
        return f'<a href="{url}" style="display:block; text-align:center; padding:0.65rem; border-radius:8px; background:#24292E; color:white; text-decoration:none; font-size:0.9rem; font-weight:500; transition:all 0.2s;">Login with GitHub</a>'

    def check_oauth(request: gr.Request):
        code = request.query_params.get("code")
        if code:
            try:
                result = complete_github_login(code)
                if result.get("success"):
                    return result["access_token"], result["user"], gr.update(visible=False), gr.update(visible=True)
            except Exception:
                pass
        return None, {}, gr.update(), gr.update()

    app.load(
        fn=check_oauth,
        outputs=[auth_token, user_info, auth_section, app_section],
    )

    app.load(fn=gen_github_link, outputs=[github_link])

    # =====================================================================
    # NAVIGATION
    # =====================================================================
    def navigate(choice, user):
        if "Logout" in choice:
            return [gr.update(visible=False)] * 4 + [gr.update(visible=True), gr.update(), "Login"]
        dash_v = "Dashboard" in choice
        pred_v = "Predict" in choice
        user_v = "User" in choice
        about_v = "About" in choice
        name = user.get("full_name", "User")
        email = user.get("email", "")
        initial = name[0].upper() if name else "U"
        user_sidebar = (
            f'<div class="sidebar-footer" style="display:flex;align-items:center;gap:0.6rem;">'
            f'<div class="sidebar-user-avatar">{initial}</div>'
            f'<div><div class="sidebar-user-name">{name}</div>'
            f'<div class="sidebar-user-email">{email}</div></div></div>'
        )
        return [
            gr.update(visible=dash_v),
            gr.update(visible=pred_v),
            gr.update(visible=user_v),
            gr.update(visible=about_v),
            gr.update(visible=False),
            user_sidebar,
            choice,
        ]

    nav_state.change(
        fn=navigate,
        inputs=[nav_state, user_info],
        outputs=[dashboard_page, predict_page, user_page, about_page, logout_modal, user_sidebar_info, nav_state],
    )

    # =====================================================================
    # DASHBOARD — Run Prediction
    # =====================================================================
    def _recent_card(history):
        if not history:
            return '<div class="card"><div class="card-title">📋 Recent Prediction</div><p style="color:var(--text-secondary);font-size:0.85rem;">No predictions yet. Upload an image above.</p></div>'
        latest = history[0]
        sev = latest.get("severity_label", "---")
        thumb = latest.get("thumbnail")
        img_html = ""
        if thumb:
            b64 = base64.b64encode(thumb).decode()
            img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%; border-radius:10px; margin-bottom:0.75rem;box-shadow:var(--shadow-sm);">'
        return f"""<div class="card"><div class="card-title">📋 Recent Prediction</div>
        <div style="position:relative;">
        {img_html}
        <span class="pill" style="position:absolute;top:12px;right:12px;background:{SEVERITY_COLOR.get(sev, '#999')};">{sev}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
        <div><strong style="font-size:1rem;">{latest["predicted_class"]}</strong><br>
        <span style="color:var(--text-secondary);font-size:0.82rem;">{latest["confidence"]:.1%} confidence</span></div>
        <span style="color:var(--text-muted);font-size:0.75rem;">{latest.get("timestamp", "")}</span>
        </div></div>"""

    def _refresh_dashboard(history):
        total, cracks, no_cracks, avg_conf = compute_stats(history)
        stats = "".join(
            stat_card_html(icon, bg, label, val)
            for icon, bg, label, val in [
                ("📷", ACCENT, "Total Analyses", total),
                ("⚠️", "#e74c3c", "Cracks Detected", cracks),
                ("✅", "#2ecc71", "No Cracks", no_cracks),
                ("🎯", "#3498db", "Avg. Confidence", f"{avg_conf:.1%}"),
            ]
        )
        recent = _recent_card(history)
        dist = class_distribution(history)
        chart = donut_chart(dist)
        sev_counts, sev_total = severity_distribution(history)
        severity = severity_bars_html(sev_counts, sev_total)
        return stats, recent, chart, severity

    def run_dash_prediction(img, history):
        if img is None:
            return history, gr.update(), gr.update(), gr.update(), gr.update()
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        result = predict_image(image_bytes=buf.getvalue(), filename="upload.jpg")
        if result.get("success"):
            record = {
                "predicted_class": result["predicted_class"],
                "confidence": result["confidence"],
                "class_probabilities": result["class_probabilities"],
                "severity_label": result["severity_label"],
                "severity_score": result["severity_score"],
                "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                "thumbnail": buf.getvalue(),
                "filename": "upload.jpg",
            }
            history.insert(0, record)
            stats, recent, chart, severity = _refresh_dashboard(history)
            return history, stats, recent, chart, severity
        return history, gr.update(), gr.update(), gr.update(), gr.update()

    dash_run.click(
        fn=run_dash_prediction,
        inputs=[dash_upload, prediction_history],
        outputs=[prediction_history, dash_stats, dash_recent, dash_chart, dash_severity],
    )

    # =====================================================================
    # PREDICT PAGE
    # =====================================================================
    def run_predict_prediction(img, selected_class, history):
        if img is None:
            return gr.update(), gr.update()
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        result = predict_image(image_bytes=buf.getvalue(), filename="predict.jpg")
        if not result.get("success"):
            return gr.update(value="<div class='card' style='color:#dc2626;'>Prediction failed.</div>"), gr.update()

        predicted_class = result["predicted_class"]
        confidence = result["confidence"]
        class_probs = result["class_probabilities"]
        severity_label = result["severity_label"]
        severity_score = result["severity_score"]

        record = {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "class_probabilities": class_probs,
            "severity_label": severity_label,
            "severity_score": severity_score,
            "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "thumbnail": buf.getvalue(),
            "filename": "predict.jpg",
        }
        history.insert(0, record)

        sev_color = SEVERITY_COLOR.get(severity_label, "#999")
        results_html = f"""<div class="card">
        <div class="card-title">✅ Prediction Result</div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:1.3rem;font-weight:700;color:var(--accent);">{predicted_class}</span>
        <span style="font-size:1.1rem;font-weight:600;">{confidence:.1%}</span>
        </div>
        </div>
        <div class="card"><div class="card-title">📊 Class Probabilities</div>"""
        for cls, prob in class_probs.items():
            pct = prob * 100
            results_html += f"""<div class="progress-label"><span>{cls}</span><span>{prob:.1%}</span></div>
<div class="progress-track"><div class="progress-fill" style="width:{pct}%;background:{ACCENT};"></div></div>"""
        results_html += f"""</div>
        <div class="card" style="border-left:4px solid {sev_color};">
        <div style="display:flex;justify-content:space-between;align-items:center;">
        <div><span style="font-size:0.85rem;color:var(--text-secondary);">Severity Level</span><br>
        <span style="font-size:1.2rem;font-weight:700;color:{sev_color};">{severity_label}</span></div>
        <div style="text-align:right;"><span style="font-size:0.85rem;color:var(--text-secondary);">Severity Score</span><br>
        <span style="font-size:1.1rem;font-weight:600;">{severity_score:.2f} / 1.00</span></div>
        </div></div>"""

        report = f"""SURFACE CRACK DETECTION REPORT
===============================
Selected Category: {selected_class}
Predicted Class: {predicted_class}
Confidence: {confidence:.1%}
Severity Level: {severity_label}
Severity Score: {severity_score:.2f}

Class Probabilities:
"""
        for cls, prob in class_probs.items():
            report += f"  {cls}: {prob:.1%}\n"

        report_html = f"""<div class="card">
        <div class="card-title">📄 Final Report</div>
        <textarea style="width:100%;height:140px;border:1px solid var(--border-light);border-radius:8px;padding:0.75rem;font-family:monospace;font-size:0.82rem;color:var(--text-primary);resize:none;" readonly>{report}</textarea>
        <div style="margin-top:0.75rem;"><a href="data:text/plain;charset=utf-8,{report.replace(' ', '%20').replace('\n', '%0A')}" download="final_report.txt" style="display:inline-flex;align-items:center;gap:0.4rem;padding:0.5rem 1.2rem;background:var(--accent);color:white;border-radius:8px;text-decoration:none;font-size:0.85rem;font-weight:500;transition:all 0.2s;">📥 Download Report</a></div>
        </div>"""

        return gr.update(value=results_html), gr.update(value=report_html)

    pred_run.click(
        fn=run_predict_prediction,
        inputs=[pred_upload, pred_class_selector, prediction_history],
        outputs=[pred_results, pred_report],
    )

    # =====================================================================
    # USER PAGE — Refresh
    # =====================================================================
    def refresh_user(user, history):
        total, cracks, no_cracks, avg_conf = compute_stats(history)
        name = user.get("full_name", "User")
        email = user.get("email", "")
        initial = name[0].upper() if name else "U"

        stats = f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
        {stat_card_html("📊", ACCENT, "Analyses Performed", total)}
        {stat_card_html("⚠️", "#e74c3c", "Cracks Detected", cracks)}
        {stat_card_html("✅", "#2ecc71", "No Cracks", no_cracks)}
        {stat_card_html("🎯", "#3498db", "Avg. Confidence", f"{avg_conf:.1%}")}
        </div>"""

        profile = f"""<div class="card" style="text-align:center;">
        <div class="sidebar-user-avatar" style="width:56px;height:56px;font-size:1.3rem;margin:0 auto 0.75rem;">{initial}</div>
        <div class="card-title" style="margin-bottom:0.25rem;">{name}</div>
        <p style="color:var(--text-secondary);font-size:0.85rem;margin:0;">{email}</p>
        <span class="pill" style="background:var(--accent-glow);color:var(--accent);border:1px solid var(--accent);margin-top:0.5rem;">Developer</span>
        </div>"""

        activity = '<div class="card"><div class="card-title">📜 Recent Activity</div>'
        if history:
            for h in history[:5]:
                thumb = h.get("thumbnail")
                img_html = ""
                if thumb:
                    b64 = base64.b64encode(thumb).decode()
                    img_html = f'<img class="act-thumb" src="data:image/jpeg;base64,{b64}">'
                activity += f"""<div class="act-item">
                {img_html}
                <div class="act-info"><div class="act-class">{h["predicted_class"]}</div><div class="act-meta">{h["confidence"]:.1%} confidence</div></div>
                <div class="act-time">{h.get("timestamp", "")}</div>
                </div>"""
        else:
            activity += '<p style="color:var(--text-secondary);font-size:0.85rem;">No activity yet.</p>'
        activity += "</div>"

        return stats, profile, activity

    nav_state.change(
        fn=refresh_user,
        inputs=[user_info, prediction_history],
        outputs=[user_stats, user_profile, user_activity],
    )

    # =====================================================================
    # LOGOUT
    # =====================================================================
    def cancel_logout():
        return [gr.update()] * 4 + [gr.update(visible=False), "Dashboard"]

    cancel_logout_btn.click(
        fn=cancel_logout,
        outputs=[dashboard_page, predict_page, user_page, about_page, logout_modal, nav_state],
    )

    def do_logout():
        return [None, {}, gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "Dashboard"]

    confirm_logout_btn.click(
        fn=do_logout,
        outputs=[auth_token, user_info, app_section, auth_section, landing_col, login_col, register_col, forgotpwd_col, nav_state],
    )

if __name__ == "__main__":
    app.launch(
        server_port=8501,
        server_name="0.0.0.0",
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(),
        head="""
<script>
document.addEventListener("DOMContentLoaded", function() {
  setTimeout(function() {
    var group = document.querySelector(".nav-group");
    if (!group) return;
    group.addEventListener("click", function(e) {
      var btn = e.target.closest(".nav-btn");
      if (!btn) return;
      document.querySelectorAll(".nav-btn").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var inp = document.querySelector("#nav-state input");
      if (inp) {
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        nativeInputValueSetter.call(inp, btn.getAttribute("data-page"));
        inp.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
  }, 500);
});
</script>
""",
    )