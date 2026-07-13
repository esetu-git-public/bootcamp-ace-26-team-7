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
    verify_access_token,
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
    --bg-dark: #1a1a2e;
    --bg-card: #ffffff;
    --text-primary: #1e1e2f;
    --text-secondary: #8a8a9a;
    --border-light: #eee;
}
.gradio-container { font-family: 'Inter', 'Segoe UI', sans-serif !important; }

/* Auth layout */
.auth-container {
    min-height: 100vh;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    display: flex !important;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}
.auth-box {
    background: white;
    border-radius: 16px;
    padding: 2.5rem 2rem;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.auth-title { text-align: center; font-size: 1.8rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem; }
.auth-subtitle { text-align: center; color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.5rem; }
.auth-error { background: #fee2e2; color: #dc2626; padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem; text-align: center; }
.auth-success { background: #dcfce7; color: #16a34a; padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem; text-align: center; }
.auth-divider { display: flex; align-items: center; gap: 1rem; margin: 1rem 0; color: var(--text-secondary); font-size: 0.8rem; }
.auth-divider::before, .auth-divider::after { content: ''; flex: 1; border-top: 1px solid var(--border-light); }

/* Landing hero */
.landing-hero { text-align: center; padding: 2rem 1rem; }
.landing-title { font-size: 2.8rem; font-weight: 700; color: white; text-shadow: 2px 2px 8px rgba(0,0,0,0.5); margin-bottom: 1rem; }
.landing-desc { font-size: 1.15rem; color: #e0e0e0; max-width: 600px; margin: 0 auto 2rem; line-height: 1.6; }

/* App layout */
.app-container { background: #f5f5f9; min-height: 100vh; }
.sidebar { background: white; border-right: 1px solid var(--border-light); padding: 1.5rem 0.75rem !important; }
.app-logo { font-size: 1.05rem; font-weight: 700; color: var(--text-primary); }
.app-tagline { font-size: 0.8rem; color: var(--text-secondary); margin-top: -4px; margin-bottom: 1.5rem; }

/* Cards */
.card { background: white; border: 1px solid var(--border-light); border-radius: 14px; padding: 1.1rem 1.3rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04); margin-bottom: 1rem; }
.stat-value { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 0.8rem; color: var(--text-secondary); }
.stat-icon { display: inline-block; border-radius: 10px; padding: 6px 9px; font-size: 1rem; margin-bottom: 6px; }

.page-title { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); }
.page-sub { color: var(--text-secondary); margin-top: -6px; margin-bottom: 1.2rem; }

.pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; color: white; }

footer { display: none !important; }
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
    return f"""<div class="card" style="text-align:center;">
        <span class="stat-icon" style="background:{icon_bg}22; color:{icon_bg};">{icon}</span>
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
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
    html = '<div class="card">'
    for sev in SEVERITY_ORDER:
        n = counts.get(sev, 0)
        pct = (n / total_ * 100) if total_ else 0
        html += f"""<p style="margin-bottom:2px;">{sev}</p>
        <div style="background:#eee; border-radius:999px; height:18px; margin-bottom:8px; overflow:hidden;">
            <div style="background:{SEVERITY_COLOR.get(sev, '#999')}; width:{pct}%; height:100%; border-radius:999px;"></div>
        </div>"""
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
    css=CUSTOM_CSS,
    title="Surface Crack Detection",
    theme=gr.themes.Soft(),
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
                '<div class="landing-title">🛣️ Surface Crack Detection System</div>'
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
                gr.HTML('<div class="app-logo">🛣️ Surface Crack Detection</div>')
                gr.HTML('<div class="app-tagline">Detect &amp; analyze road surface cracks</div>')
                nav_radio = gr.Radio(
                    choices=["🏠  Dashboard", "🔍  Predict", "👤  User", "ℹ️  About Us", "🚪  Logout"],
                    value="🏠  Dashboard",
                    label=None,
                    container=False,
                )
                user_sidebar_info = gr.HTML("")

            # ---- Content ----
            with gr.Column(scale=4):
                # Dashboard
                with gr.Column(visible=True) as dashboard_page:
                    gr.HTML('<div class="page-title">Dashboard</div>')
                    gr.HTML('<div class="page-sub">Detect and analyze surface cracks in images</div>')
                    dash_stats = gr.HTML("")
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=1):
                            gr.HTML('<div class="card"><div class="card-title">Upload &amp; Predict</div></div>')
                            dash_upload = gr.Image(type="pil", label="Drag & drop an image here", height=300)
                            dash_run = gr.Button("Run Prediction", variant="primary", size="lg")
                        with gr.Column(scale=1):
                            dash_recent = gr.HTML('<div class="card"><p style="color:var(--text-secondary);">No predictions yet.</p></div>')
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=1):
                            dash_chart = gr.Plot(None, label="Class Distribution")
                        with gr.Column(scale=1):
                            dash_severity = gr.HTML('<div class="card"><p style="color:var(--text-secondary);">No predictions yet.</p></div>')

                # Predict
                with gr.Column(visible=False) as predict_page:
                    gr.HTML('<div class="page-title">Predict</div>')
                    gr.HTML('<div class="page-sub">Run a detailed analysis on a single image</div>')
                    pred_class_selector = gr.Radio(CLASSES, value=CLASSES[0], label="Category you expect", container=False)
                    pred_upload = gr.Image(type="pil", label="Upload Image", height=350)
                    pred_run = gr.Button("Run Prediction", variant="primary", size="lg")
                    pred_results = gr.HTML("")
                    pred_report = gr.HTML("")

                # User
                with gr.Column(visible=False) as user_page:
                    gr.HTML('<div class="page-title">User</div>')
                    gr.HTML('<div class="page-sub">Manage your profile and account settings</div>')
                    user_stats = gr.HTML("")
                    user_profile = gr.HTML("")
                    user_activity = gr.HTML("")

                # About Us
                with gr.Column(visible=False) as about_page:
                    gr.HTML('<div class="page-title">About Us</div>')
                    gr.HTML('<div class="page-sub">Learn more about our project and team</div>')
                    gr.HTML(
                        '<div class="card">'
                        '<h3>Project Overview</h3>'
                        '<p>Surface Crack Detection is an AI-powered application designed to '
                        'identify and classify surface defects in road and concrete images. '
                        'The system uses a deep learning model to detect cracks, potholes, '
                        'patches, and other surface defects with high accuracy.</p>'
                        '<div style="display:flex; gap:1rem; margin-top:1rem;">'
                        '<div><strong>⚙️ AI Powered</strong><br><span style="color:var(--text-secondary);font-size:0.85rem;">Deep learning model for accurate detection</span></div>'
                        '<div><strong>🛡️ High Accuracy</strong><br><span style="color:var(--text-secondary);font-size:0.85rem;">Trained on diverse datasets for reliable results</span></div>'
                        '<div><strong>⚡ Easy to Use</strong><br><span style="color:var(--text-secondary);font-size:0.85rem;">Simple interface for quick, efficient analysis</span></div>'
                        '</div>'
                        '<p style="margin-top:1rem;"><strong>Technologies Used</strong><br>'
                        '🐍 Python · 🔥 PyTorch · 🎈 Gradio · 👁️ OpenCV · 🖼️ PIL · 🔢 NumPy · 🐼 Pandas · 📈 Scikit-learn</p>'
                        '</div>'
                        '<div class="card">'
                        '<h3>Our Team</h3>'
                        '<p><strong>Arvind Parsapuram</strong> — Developer &amp; Designer<br>'
                        '<span style="color:var(--text-secondary);font-size:0.85rem;">Frontend development, UI/UX design and integration</span></p>'
                        '<p><strong>Team Member</strong> — ML Engineer<br>'
                        '<span style="color:var(--text-secondary);font-size:0.85rem;">Model training, optimization and testing</span></p>'
                        '<p><strong>Team Member</strong> — Data Engineer<br>'
                        '<span style="color:var(--text-secondary);font-size:0.85rem;">Data collection, preprocessing and management</span></p>'
                        '</div>'
                    )

        # ---- Logout confirmation modal ----
        with gr.Column(visible=False) as logout_modal:
            gr.HTML(
                '<div style="position:fixed; inset:0; background:rgba(0,0,0,0.4); display:flex; align-items:center; justify-content:center; z-index:9999;">'
                '<div class="card" style="max-width:380px; text-align:center; padding:2rem;">'
                '<h3>🚪 Logout</h3>'
                '<p>Are you sure you want to logout?</p>'
                '<div style="display:flex; gap:0.5rem; justify-content:center; margin-top:1rem;">'
                '</div></div></div>'
            )
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
        fn=lambda u: f'<div style="padding-top:1rem; border-top:1px solid #eee;"><strong>{u.get("full_name", "User")}</strong><br><span style="font-size:0.8rem;color:var(--text-secondary);">{u.get("email", "")}</span></div>',
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
        return f'<a href="{url}" style="display:block; text-align:center; padding:0.6rem; border-radius:10px; border:1px solid #d0d0d0; background:white; color:#333; text-decoration:none; font-size:1rem; font-weight:500; width:100%;">Login with GitHub</a>'

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
            return [gr.update(visible=False)] * 4 + [gr.update(visible=True), gr.update()]
        dash_v = "Dashboard" in choice
        pred_v = "Predict" in choice
        user_v = "User" in choice
        about_v = "About" in choice
        user_sidebar = f'<div style="padding-top:1rem; border-top:1px solid #eee;"><strong>{user.get("full_name", "User")}</strong><br><span style="font-size:0.8rem;color:var(--text-secondary);">{user.get("email", "")}</span></div>'
        return [
            gr.update(visible=dash_v),
            gr.update(visible=pred_v),
            gr.update(visible=user_v),
            gr.update(visible=about_v),
            gr.update(visible=False),
            user_sidebar,
        ]

    nav_radio.change(
        fn=navigate,
        inputs=[nav_radio, user_info],
        outputs=[dashboard_page, predict_page, user_page, about_page, logout_modal, user_sidebar_info],
    )

    # =====================================================================
    # DASHBOARD — Run Prediction
    # =====================================================================
    def _recent_card(history):
        if not history:
            return '<div class="card"><h4>Recent Prediction</h4><p style="color:var(--text-secondary);">No predictions yet.</p></div>'
        latest = history[0]
        sev = latest.get("severity_label", "---")
        thumb = latest.get("thumbnail")
        img_html = ""
        if thumb:
            b64 = base64.b64encode(thumb).decode()
            img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%; border-radius:8px; margin-bottom:0.5rem;">'
        return f"""<div class="card"><h4>Recent Prediction</h4>
        {img_html}
        <p><strong>Class:</strong> {latest["predicted_class"]}</p>
        <p><strong>Confidence:</strong> {latest["confidence"]:.1%}</p>
        <p><strong>Severity:</strong> <span class="pill" style="background:{SEVERITY_COLOR.get(sev, '#999')}">{sev}</span></p>
        <p style="color:var(--text-secondary);font-size:0.85rem;">{latest.get("timestamp", "")}</p></div>"""

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

    def run_dash_prediction(img, history, token):
        if not verify_access_token(token):
            return history, gr.update(), gr.update(), gr.update(), gr.update()
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
        inputs=[dash_upload, prediction_history, auth_token],
        outputs=[prediction_history, dash_stats, dash_recent, dash_chart, dash_severity],
    )

    # =====================================================================
    # PREDICT PAGE
    # =====================================================================
    def run_predict_prediction(img, selected_class, history, token):
        if not verify_access_token(token):
            return gr.update(value="<div class='card' style='color:#dc2626;'>Please log in to use this feature.</div>"), gr.update()
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
        <h3 style="color:var(--accent);">✅ {predicted_class}</h3>
        <p><strong>Confidence:</strong> {confidence:.1%}</p>
        </div>
        <div class="card"><h4>Class Probabilities</h4>"""
        for cls, prob in class_probs.items():
            pct = prob * 100
            results_html += f"""<p style="margin-bottom:2px;">{cls}</p>
            <div style="background:#eee; border-radius:999px; height:18px; margin-bottom:8px; overflow:hidden;">
                <div style="background:{ACCENT}; width:{pct}%; height:100%; border-radius:999px;"></div>
            </div>"""
        results_html += f"""</div>
        <div class="card">
        <h3 style="color:{sev_color};">Severity: {severity_label}</h3>
        <p><strong>Score:</strong> {severity_score:.2f} / 1.00</p>
        </div>"""

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

        encoded_report = report.replace(' ', '%20').replace('\n', '%0A')
        report_html = f"""<div class="card">
                <h4>Final Report</h4>
                <textarea style="width:100%; height:150px; border:1px solid #ddd; border-radius:8px; padding:0.5rem; font-family:monospace; font-size:0.85rem;" readonly>{report}</textarea>
                <div style="margin-top:0.5rem;"><a href="data:text/plain;charset=utf-8,{encoded_report}" download="final_report.txt" style="display:inline-block; padding:0.4rem 1rem; background:var(--accent); color:white; border-radius:8px; text-decoration:none;">📥 Download Report</a></div>
                </div>"""

        return gr.update(value=results_html), gr.update(value=report_html)

    pred_run.click(
        fn=run_predict_prediction,
        inputs=[pred_upload, pred_class_selector, prediction_history, auth_token],
        outputs=[pred_results, pred_report],
    )

    # =====================================================================
    # USER PAGE — Refresh
    # =====================================================================
    def refresh_user(user, history):
        total, cracks, no_cracks, avg_conf = compute_stats(history)
        stats = f"""<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
        {stat_card_html("📊", ACCENT, "Analyses Performed", total)}
        {stat_card_html("⚠️", "#e74c3c", "Cracks Detected", cracks)}
        {stat_card_html("✅", "#2ecc71", "No Cracks", no_cracks)}
        {stat_card_html("🎯", "#3498db", "Avg. Confidence", f"{avg_conf:.1%}")}
        </div>"""

        profile = f"""<div class="card">
        <h4>Profile Information</h4>
        <p><strong>Full Name:</strong> {user.get("full_name", "User")}</p>
        <p><strong>Email:</strong> {user.get("email", "")}</p>
        <p><strong>Role:</strong> Developer</p>
        </div>"""

        activity = '<div class="card"><h4>Recent Activity</h4>'
        if history:
            for h in history[:5]:
                thumb = h.get("thumbnail")
                img_html = ""
                if thumb:
                    b64 = base64.b64encode(thumb).decode()
                    img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:60px; height:60px; border-radius:8px; object-fit:cover;">'
                activity += f"""<div style="display:flex; gap:0.75rem; align-items:center; padding:0.5rem 0; border-bottom:1px solid #eee;">
                {img_html}
                <div><strong>{h["predicted_class"]}</strong><br><span style="font-size:0.8rem;color:var(--text-secondary);">{h["confidence"]:.1%} confidence</span></div>
                <div style="margin-left:auto; font-size:0.8rem;color:var(--text-secondary);">{h.get("timestamp", "")}</div>
                </div>"""
        else:
            activity += '<p style="color:var(--text-secondary);">No activity yet.</p>'
        activity += "</div>"

        return stats, profile, activity

    nav_radio.change(
        fn=refresh_user,
        inputs=[user_info, prediction_history],
        outputs=[user_stats, user_profile, user_activity],
    )

    # =====================================================================
    # LOGOUT
    # =====================================================================
    def cancel_logout():
        return [gr.update()] * 4 + [gr.update(visible=False), "🏠  Dashboard"]

    cancel_logout_btn.click(
        fn=cancel_logout,
        outputs=[dashboard_page, predict_page, user_page, about_page, logout_modal, nav_radio],
    )

    def do_logout():
        return [None, {}, gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "🏠  Dashboard"]

    confirm_logout_btn.click(
        fn=do_logout,
        outputs=[auth_token, user_info, app_section, auth_section, landing_col, login_col, register_col, forgotpwd_col, nav_radio],
    )

if __name__ == "__main__":
    app.launch()