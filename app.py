
import streamlit as st

st.set_page_config(
    page_title="Surface Detection System",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stSidebar"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Surface Detection System")

st.title("🛣️ Surface Detection System")

st.write("Welcome!")

if st.button("Go to Login"):
    st.switch_page("pages/login.py")