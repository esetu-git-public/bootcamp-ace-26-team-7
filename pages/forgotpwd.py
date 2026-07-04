import streamlit as st

st.set_page_config(
    page_title="Surface Detection System - Forgot Password",
    page_icon="🔒",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stSidebar"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)

st.title("🔒 Forgot Password")

st.write("Enter your registered email address.")

email = st.text_input("Email Address")

if st.button("Send Reset Link", use_container_width=True):
    if email:
        st.success("Password reset link has been sent successfully.")
        st.info("Demo version: No email will actually be sent.")
    else:
        st.error("Please enter your email address.")

st.divider()

if st.button("⬅ Back to Login"):
    st.switch_page("pages/login.py")
