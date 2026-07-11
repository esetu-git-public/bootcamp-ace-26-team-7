import streamlit as st
from backend.prediction import predict_image
from backend.auth import require_login

st.set_page_config(layout="wide")
require_login()

with st.sidebar:
    user = st.session_state.get("user", {})
    st.write(f"👤 {user.get('full_name', 'User')}")
    st.caption(user.get("email", ""))
    if st.button("Logout"):
        st.session_state.pop("access_token", None)
        st.session_state.pop("user", None)
        st.switch_page("pages/login.py")

hide_streamlit_style = """
<style>
[data-testid="stSidebarNav"] {display: none;}
.main-title { text-align:center; color:black; }
@media (prefers-color-scheme: dark) {
    .main-title { color:white; }
}
</style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ---------------- SIDEBAR (ONLY CLASS SELECTOR) ----------------
selected_class = st.sidebar.radio(
    "Select Class",
    ["POTHOLES", "CRACK", "PATCH", "SURFACE DEFECTS"]
)
# ---------------- LOGOUT BUTTON ----------------
st.markdown("""
<style>
div[data-testid="stButton"]{
    margin-top: -40px;
}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([17, 1])

with col2:
    if st.button("Logout"):
        st.session_state.clear()      # Clear all session data
        st.switch_page("pages/login.py")    # Redirect to Login page

# ---------------- MAIN TITLE ----------------
st.markdown(
    '<h1 class="main-title">Surface Crack Detection</h1>',
    unsafe_allow_html=True
)

st.write("")

# ---------------- SELECTED CLASS DISPLAY ----------------
st.markdown(f"## {selected_class}")

uploaded_file = st.file_uploader(
    f"Upload Image for {selected_class}",
    type=["jpg", "png"]
)

if uploaded_file:
    st.image(uploaded_file, caption=f"{selected_class} Image")

st.write("---")

# # ---------------- DATA PROCESSED ----------------
#st.header("Data Processed")
#st.write({
#    "Total Images": 306,
#    "Classes": ["Cracks", "Patch", "Potholes", "Surface Defects"],
#    "Preprocessing Steps": ["Resize 224x224", "Normalization", "Augmentation (Flip, Rotate, ColorJitter)"]
#})
#st.write("---")

# ---------------- PREDICTION ----------------
st.header("Prediction")

predicted_class = "---"
confidence = 0.0
class_probs = {}
severity_label = "---"
severity_score = 0.0

if uploaded_file and st.button("Run Prediction", use_container_width=True):
    with st.spinner("Running prediction..."):
        try:
            result = predict_image(
                image_bytes=uploaded_file.getvalue(),
                filename=uploaded_file.name,
            )
            if result.get("success"):
                predicted_class = result["predicted_class"]
                confidence = result["confidence"]
                class_probs = result["class_probabilities"]
                severity_label = result["severity_label"]
                severity_score = result["severity_score"]
            else:
                st.error("Prediction failed.")
        except Exception as e:
            st.error(str(e))

if predicted_class != "---":
    st.success(f"**Predicted Class:** {predicted_class}")
    st.metric("Confidence", f"{confidence:.1%}")

    st.subheader("Class Probabilities")
    for cls, prob in class_probs.items():
        st.progress(prob, text=f"{cls}: {prob:.1%}")

st.write("---")

# ---------------- SEVERITY ----------------
st.header("Severity")
if severity_label != "---":
    sev_color = {"Low": "green", "Medium": "orange", "High": "red", "Critical": "darkred"}
    color = sev_color.get(severity_label, "gray")
    st.markdown(f"<h2 style='color:{color};'>{severity_label}</h2>", unsafe_allow_html=True)
    st.metric("Severity Score", f"{severity_score:.2f} / 1.00")
else:
    st.info("Upload an image and run prediction to see severity.")
st.write("---")

# ---------------- FINAL REPORT ----------------
st.header("Final Report")

report_text = f"""
SURFACE CRACK DETECTION REPORT
===============================
Selected Class: {selected_class}
Predicted Class: {predicted_class}
Confidence: {confidence:.1%}
Severity Level: {severity_label}
Severity Score: {severity_score:.2f}
"""

if class_probs:
    report_text += "\nClass Probabilities:\n"
    for cls, prob in class_probs.items():
        report_text += f"  {cls}: {prob:.1%}\n"

st.text_area("Report Preview", report_text, height=200)

st.download_button(
    label="Download Report",
    data=report_text,
    file_name="final_report.txt",
    mime="text/plain"
)