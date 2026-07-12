import io
from datetime import datetime
 
import streamlit as st
 
from backend.prediction import predict_image
from backend.auth import require_login
 
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
 
# Optional backend hooks — used only if they exist, so this file never
# breaks if you haven't added them yet.
try:
    from backend import database as db_module
except ImportError:
    db_module = None
 
try:
    from backend import auth as auth_module
except ImportError:
    auth_module = None
 
 
# ============================================================================
# PAGE CONFIG + LOGIN GUARD
# ============================================================================
st.set_page_config(page_title="Surface Crack Detection", layout="wide")
require_login()
 
CLASSES = ["Potholes", "Cracks", "Patch", "Surface Defects"]
SEVERITY_ORDER = ["Low", "Medium", "High"]
SEVERITY_COLOR = {
    "Low": "#2ecc71",
    "Medium": "#f39c12",
    "High": "#e74c3c",
    "---": "#b0b0b0",
}
ACCENT = "#6C5CE7"
 
 
# ============================================================================
# SESSION STATE
# ============================================================================
def init_state():
    defaults = {
        "nav": "Dashboard",
        "history": [],           # list of prediction records (this session)
        "confirm_logout": False,
        "last_result": None,     # most recent prediction dict + meta
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
 
 
init_state()
user = st.session_state.get("user", {})
user_id = user.get("id") or user.get("user_id")
 
 
# ============================================================================
# LOAD PERSISTED HISTORY (only if backend.database supports it)
# ============================================================================
def load_history():
    """Prefer persisted history from the DB; fall back to session-only."""
    if db_module and hasattr(db_module, "get_user_analyses") and user_id:
        try:
            records = db_module.get_user_analyses(user_id)
            if records:
                return records
        except Exception:
            pass
    return st.session_state.history
 
 
def save_record(record: dict):
    """Persist to DB if possible, always keep a session copy too."""
    st.session_state.history.insert(0, record)
    if db_module and hasattr(db_module, "save_analysis") and user_id:
        try:
            db_module.save_analysis(user_id, record)
        except Exception:
            pass  # don't let a broken DB call crash the UI
 
 
# ============================================================================
# STYLES
# ============================================================================
st.markdown(f"""
<style>
[data-testid="stSidebarNav"] {{ display: none; }}
[data-testid="stSidebar"] {{
    background-color: #ffffff;
    border-right: 1px solid #eee;
}}
.block-container {{ padding-top: 2rem; }}
 
.app-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: #1e1e2f;
    margin-bottom: 0;
}}
.app-subtitle {{
    font-size: 0.8rem;
    color: #8a8a9a;
    margin-top: -6px;
}}
 
.nav-btn button {{
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    padding: 0.55rem 0.8rem;
    border-radius: 10px;
    font-size: 0.95rem;
    color: #444;
}}
.nav-btn button:hover {{ background: #f2f0fb; color: {ACCENT}; }}
 
.card {{
    background: #ffffff;
    border: 1px solid #eee;
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    margin-bottom: 1rem;
}}
.stat-value {{ font-size: 1.6rem; font-weight: 700; color: #1e1e2f; }}
.stat-label {{ font-size: 0.8rem; color: #8a8a9a; }}
.stat-icon {{
    display:inline-block; border-radius:10px; padding:6px 9px;
    font-size:1rem; margin-bottom:6px;
}}
 
.page-title {{ font-size: 1.6rem; font-weight: 700; color: #1e1e2f; }}
.page-sub {{ color: #8a8a9a; margin-top:-8px; margin-bottom: 1.2rem; }}
 
.pill {{
    display:inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; color: white;
}}
</style>
""", unsafe_allow_html=True)
 
 
# ============================================================================
# SIDEBAR (branding + nav + identity)
# ============================================================================
with st.sidebar:
    st.markdown(
        f'<div class="app-title">🛣️ Surface Crack Detection</div>'
        f'<div class="app-subtitle">Detect & analyze road surface cracks</div>',
        unsafe_allow_html=True,
    )
    st.write("")
 
    nav_items = [
        ("Dashboard", "🏠"),
        ("Predict", "🔍"),
        ("User", "👤"),
        ("About Us", "ℹ️"),
        ("Logout", "🚪"),
    ]
    for label, icon in nav_items:
        st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
        active = st.session_state.nav == label
        if st.button(
            f"{icon}  {label}",
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            if label == "Logout":
                st.session_state.confirm_logout = True
            else:
                st.session_state.nav = label
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
 
    st.write("")
    st.markdown("---")
    st.markdown(f"**{user.get('full_name', 'User')}**")
    st.caption(user.get("email", ""))
 
 
# ============================================================================
# LOGOUT CONFIRMATION DIALOG
# ============================================================================
if st.session_state.confirm_logout:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown("### 🚪 Logout")
        st.write("Are you sure you want to logout?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_logout = False
                st.rerun()
        with c2:
            if st.button("Yes, Logout", use_container_width=True, type="primary"):
                st.session_state.clear()
                st.switch_page("pages/login.py")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()
 
 
# ============================================================================
# SHARED HELPERS
# ============================================================================
def compute_stats(history):
    total = len(history)
    cracks_detected = sum(1 for h in history if h.get("predicted_class", "").lower() != "no crack")
    no_cracks = total - cracks_detected
    avg_conf = (sum(h.get("confidence", 0) for h in history) / total) if total else 0.0
    return total, cracks_detected, no_cracks, avg_conf
 
 
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
 
 
def stat_card(icon, icon_bg, label, value):
    st.markdown(f"""
    <div class="card">
        <span class="stat-icon" style="background:{icon_bg}22; color:{icon_bg};">{icon}</span>
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)
 
 
def donut_chart(counts):
    labels = [k for k, v in counts.items() if v > 0]
    values = [v for v in counts.values() if v > 0]
    if not values:
        st.info("No predictions yet — run a prediction to populate this chart.")
        return
    if PLOTLY_AVAILABLE:
        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=0.6,
            marker=dict(colors=["#6C5CE7", "#00b894", "#fdcb6e", "#e17055"]),
            textinfo="none",
        )])
        fig.update_layout(
            showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=220,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    total = sum(values)
    for label, value in zip(labels, values):
        pct = value / total * 100 if total else 0
        st.write(f"● **{label}** — {value} ({pct:.0f}%)")
 
 
def severity_bars(counts, total):
    for sev in SEVERITY_ORDER:
        n = counts.get(sev, 0)
        pct = (n / total) if total else 0
        st.write(f"{sev}")
        st.progress(pct, text=f"{pct*100:.0f}%")
 
 
# ============================================================================
# PAGE: DASHBOARD
# ============================================================================
def page_dashboard():
    history = load_history()
    total, cracks, no_cracks, avg_conf = compute_stats(history)
 
    st.markdown('<div class="page-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Detect and analyze surface cracks in images</div>', unsafe_allow_html=True)
 
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("📷", "#6C5CE7", "Total Analyses", total)
    with c2:
        stat_card("⚠️", "#e74c3c", "Cracks Detected", cracks)
    with c3:
        stat_card("✅", "#2ecc71", "No Cracks", no_cracks)
    with c4:
        stat_card("🎯", "#3498db", "Avg. Confidence", f"{avg_conf:.1%}")
 
    left, right = st.columns([1.3, 1])
 
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Upload & Predict")
        st.caption("Upload an image to detect surface cracks")
        uploaded_file = st.file_uploader(
            "Drag & drop an image here, or click to browse",
            type=["jpg", "jpeg", "png"],
            key="dash_uploader",
        )
        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)
 
        run = st.button("Run Prediction", use_container_width=True, type="primary", disabled=not uploaded_file)
        if run and uploaded_file:
            with st.spinner("Running prediction..."):
                try:
                    result = predict_image(
                        image_bytes=uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                    )
                except Exception as e:
                    st.error(str(e))
                    result = None
 
            if result and result.get("success"):
                record = {
                    "predicted_class": result["predicted_class"],
                    "confidence": result["confidence"],
                    "class_probabilities": result["class_probabilities"],
                    "severity_label": result["severity_label"],
                    "severity_score": result["severity_score"],
                    "repair_cost": result.get("repair_cost"),
                    "repair_time": result.get("repair_time"),
                    "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                    "thumbnail": uploaded_file.getvalue(),
                    "filename": uploaded_file.name,
                }
                save_record(record)
                st.session_state.last_result = record
                st.success(f"Predicted: **{record['predicted_class']}**  ({record['confidence']:.1%})")
                st.rerun()
            elif result:
                st.error("Prediction failed.")
        st.markdown("</div>", unsafe_allow_html=True)
 
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Recent Prediction")
        latest = history[0] if history else st.session_state.last_result
        if latest:
            st.image(io.BytesIO(latest["thumbnail"]), use_container_width=True)
            sev = latest.get("severity_label", "---")
            st.write(f"**Class:** {latest['predicted_class']}")
            st.write(f"**Confidence:** {latest['confidence']:.1%}")
            st.markdown(
                f"**Severity:** <span class='pill' style='background:{SEVERITY_COLOR.get(sev,'#999')}'>{sev}</span>",
                unsafe_allow_html=True,
            )
            rc = latest.get("repair_cost")
            rt = latest.get("repair_time")
            if rc and rt:
                st.write(f"**Est. Cost:** {rc['display']}")
                st.write(f"**Est. Time:** {rt['display']}")
            st.caption(latest.get("timestamp", ""))
        else:
            st.info("No predictions yet.")
        st.markdown("</div>", unsafe_allow_html=True)
 
    c5, c6 = st.columns(2)
    with c5:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Class Distribution")
        donut_chart(class_distribution(history))
        st.markdown("</div>", unsafe_allow_html=True)
    with c6:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Severity Overview")
        sev_counts, sev_total = severity_distribution(history)
        severity_bars(sev_counts, sev_total)
        st.markdown("</div>", unsafe_allow_html=True)
 
 
# ============================================================================
# PAGE: PREDICT (full detail view — mirrors your original single-page flow,
# including the class-probability bars and the downloadable report)
# ============================================================================
def page_predict():
    st.markdown('<div class="page-title">Predict</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Run a detailed analysis on a single image</div>', unsafe_allow_html=True)
 
    selected_class = st.radio("Category you expect (for your reference only)", CLASSES, horizontal=True)
 
    st.markdown('<div class="card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(f"Upload Image for {selected_class}", type=["jpg", "jpeg", "png"], key="predict_uploader")
    if uploaded_file:
        st.image(uploaded_file, caption=selected_class, use_container_width=False, width=420)
 
    predicted_class, confidence, class_probs, severity_label, severity_score = "---", 0.0, {}, "---", 0.0
    repair_cost, repair_time = None, None
 
    if uploaded_file and st.button("Run Prediction", use_container_width=True, type="primary"):
        with st.spinner("Running prediction..."):
            try:
                result = predict_image(image_bytes=uploaded_file.getvalue(), filename=uploaded_file.name)
                if result.get("success"):
                    predicted_class = result["predicted_class"]
                    confidence = result["confidence"]
                    class_probs = result["class_probabilities"]
                    severity_label = result["severity_label"]
                    severity_score = result["severity_score"]
                    repair_cost = result.get("repair_cost")
                    repair_time = result.get("repair_time")
                    save_record({
                        "predicted_class": predicted_class,
                        "confidence": confidence,
                        "class_probabilities": class_probs,
                        "severity_label": severity_label,
                        "severity_score": severity_score,
                        "repair_cost": repair_cost,
                        "repair_time": repair_time,
                        "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                        "thumbnail": uploaded_file.getvalue(),
                        "filename": uploaded_file.name,
                    })
                else:
                    st.error("Prediction failed.")
            except Exception as e:
                st.error(str(e))
    st.markdown("</div>", unsafe_allow_html=True)
 
    if predicted_class != "---":
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.success(f"**Predicted Class:** {predicted_class}")
        st.metric("Confidence", f"{confidence:.1%}")
        st.subheader("Class Probabilities")
        for cls, prob in class_probs.items():
            st.progress(prob, text=f"{cls}: {prob:.1%}")
        st.markdown("</div>", unsafe_allow_html=True)
 
        st.markdown('<div class="card">', unsafe_allow_html=True)
        color = SEVERITY_COLOR.get(severity_label, "#999")
        st.markdown(f"<h3 style='color:{color};'>Severity: {severity_label}</h3>", unsafe_allow_html=True)
        st.metric("Severity Score", f"{severity_score:.2f} / 1.00")
        st.markdown("</div>", unsafe_allow_html=True)

        # --- Repair cost & time card ---
        if repair_cost and repair_time:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Repair Estimate")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.metric("Estimated Cost", repair_cost["display"])
            with cc2:
                st.metric("Estimated Time", repair_time["display"])
            st.caption("Estimates based on typical US road repair costs (2026). Actual costs vary by region, contractor, and extent of damage.")
            st.markdown("</div>", unsafe_allow_html=True)
 
        report_text = f"""SURFACE CRACK DETECTION REPORT
===============================
Selected Category: {selected_class}
Predicted Class: {predicted_class}
Confidence: {confidence:.1%}
Severity Level: {severity_label}
Severity Score: {severity_score:.2f}
"""
        if repair_cost and repair_time:
            report_text += f"""
Estimated Repair Cost: {repair_cost['display']}
Estimated Repair Time: {repair_time['display']}
Note: Estimates based on typical US road repair costs (2026). Actual costs vary by region, contractor, and extent of damage.
"""
        if class_probs:
            report_text += "\nClass Probabilities:\n"
            for cls, prob in class_probs.items():
                report_text += f"  {cls}: {prob:.1%}\n"
 
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Final Report")
        st.text_area("Report Preview", report_text, height=180)
        st.download_button("Download Report", data=report_text, file_name="final_report.txt", mime="text/plain")
        st.markdown("</div>", unsafe_allow_html=True)
 
 
# ============================================================================
# PAGE: USER
# ============================================================================
def page_user():
    history = load_history()
    total, cracks, no_cracks, avg_conf = compute_stats(history)
 
    st.markdown('<div class="page-title">User</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Manage your profile and account settings</div>', unsafe_allow_html=True)
 
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Profile Information")
        st.file_uploader("Change Photo", type=["jpg", "png"], key="avatar_upload")
        full_name = st.text_input("Full Name", value=user.get("full_name", ""))
        email = st.text_input("Email", value=user.get("email", ""), disabled=True)
        role = st.text_input("Role", value=user.get("role", "Developer"))
 
        if st.button("Update Profile", type="primary"):
            if auth_module and hasattr(auth_module, "update_profile") and user_id:
                try:
                    auth_module.update_profile(user_id, {"full_name": full_name, "role": role})
                    st.session_state.user["full_name"] = full_name
                    st.success("Profile updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update profile: {e}")
            else:
                st.info(
                    "Not wired up yet — add an `update_profile(user_id, fields)` "
                    "function to backend/auth.py to persist this."
                )
        st.markdown("</div>", unsafe_allow_html=True)
 
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Account Statistics")
        cc1, cc2 = st.columns(2)
        with cc1:
            stat_card("📊", "#6C5CE7", "Analyses Performed", total)
            stat_card("✅", "#2ecc71", "No Cracks", no_cracks)
        with cc2:
            stat_card("⚠️", "#e74c3c", "Cracks Detected", cracks)
            stat_card("🎯", "#3498db", "Avg. Confidence", f"{avg_conf:.1%}")
        st.markdown("</div>", unsafe_allow_html=True)
 
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Recent Activity")
    if history:
        for h in history[:5]:
            cols = st.columns([1, 3, 2])
            with cols[0]:
                st.image(io.BytesIO(h["thumbnail"]), use_container_width=True)
            with cols[1]:
                st.write(f"**{h['predicted_class']}**")
                st.caption(f"{h['confidence']:.1%} confidence")
            with cols[2]:
                st.caption(h.get("timestamp", ""))
    else:
        st.info("No activity yet.")
    st.markdown("</div>", unsafe_allow_html=True)
 
 
# ============================================================================
# PAGE: ABOUT US
# ============================================================================
def page_about():
    st.markdown('<div class="page-title">About Us</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Learn more about our project and team</div>', unsafe_allow_html=True)
 
    left, right = st.columns([1.4, 1])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Project Overview")
        st.write(
            "Surface Crack Detection is an AI-powered application designed to "
            "identify and classify surface defects in road and concrete images. "
            "The system uses a deep learning model to detect cracks, potholes, "
            "patches, and other surface defects with high accuracy."
        )
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown("**⚙️ AI Powered**")
            st.caption("Deep learning model for accurate detection")
        with f2:
            st.markdown("**🛡️ High Accuracy**")
            st.caption("Trained on diverse datasets for reliable results")
        with f3:
            st.markdown("**⚡ Easy to Use**")
            st.caption("Simple interface for quick, efficient analysis")
 
        st.write("**Technologies Used**")
        st.write("🐍 Python · 🔥 TensorFlow/PyTorch · 🎈 Streamlit · 👁️ OpenCV · 🖼️ PIL · 🔢 NumPy · 🐼 Pandas · 📈 Scikit-learn")
        st.markdown("</div>", unsafe_allow_html=True)
 
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Our Team")
        st.write("**Arvind Parsapuram** — Developer & Designer")
        st.caption("Frontend development, UI/UX design and integration")
        st.write("**Team Member** — ML Engineer")
        st.caption("Model training, optimization and testing")
        st.write("**Team Member** — Data Engineer")
        st.caption("Data collection, preprocessing and management")
        st.markdown("</div>", unsafe_allow_html=True)
 
 
# ============================================================================
# ROUTER
# ============================================================================
PAGES = {
    "Dashboard": page_dashboard,
    "Predict": page_predict,
    "User": page_user,
    "About Us": page_about,
}
PAGES.get(st.session_state.nav, page_dashboard)()