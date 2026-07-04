import streamlit as st

st.set_page_config(layout="wide")

# ---------------- OPTIONAL: HIDE DEFAULT PAGE NAV ----------------
hide_streamlit_style = """
<style>
[data-testid="stSidebarNav"] {display: none;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ---------------- SIDEBAR (ONLY CLASS SELECTOR) ----------------
selected_class = st.sidebar.radio(
    "Select Class",
    ["POTHOLES", "CRACK", "PATCH", "SURFACE DEFECTS"]
)

# ---------------- MAIN TITLE ----------------
st.markdown(
    "<h1 style='text-align:center; color:black;'>Surface Crack Detection</h1>",
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

# ---------------- SCROLL SECTIONS ----------------

# ---------------- DATA PROCESSED ----------------
st.header("Data Processed")

# Placeholder (connect your processed dataset later)
st.info("Processed and cleaned dataset used for training will be displayed here.")

# Example structure (replace later with real data)
st.write({
    "Total Images": "---",
    "Classes": ["Potholes", "Crack", "Patch", "Surface Defects"],
    "Preprocessing Steps": ["Resizing", "Normalization", "Augmentation"]
})

st.write("---")


# ---------------- PREDICTION ----------------
st.header("Prediction")

# Placeholder for ML model output
st.success("Prediction result will be displayed here after model integration.")

# Example placeholders (replace with model output later)
predicted_class = "---"
confidence = "---"

st.write(f"Class: {predicted_class}")
st.write(f"Confidence: {confidence}%")

st.write("---")


# ---------------- SEVERITY ----------------
st.header("Severity")

# Placeholder (connect logic later)
severity = "---"
st.write(f"Severity Level: {severity}")

st.write("---")


# ---------------- FINAL REPORT ----------------
st.header("Final Report")

# Dynamic report content
report_text = f"""
Surface Crack Detection Report

Selected Class: {selected_class}

Prediction: {predicted_class}
Confidence: {confidence}%
Severity: {severity}

(Data will be filled after ML model integration)
"""

# Preview
st.text_area("Report Preview", report_text, height=200)

# ---------------- DOWNLOAD BUTTON ----------------
st.download_button(
    label="Download Report",
    data=report_text,
    file_name="final_report.txt",
    mime="text/plain"
)