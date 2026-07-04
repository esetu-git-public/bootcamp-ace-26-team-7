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

st.set_page_config(page_title="Login", page_icon="🔐")

VALID_EMAIL = "admin@surfacedetect.com"
VALID_PASSWORD = "Admin@123"

st.title("🛣️ Surface Detection System")
st.subheader("Login")

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login", use_container_width=True):
    if email == VALID_EMAIL and password == VALID_PASSWORD:
        st.success("Login Successful ✅")
    else:
        st.error("Invalid Email or Password")

st.write("---")

col1, col2 = st.columns(2)

with col1:
    if st.button("Forgot Password"):
        st.switch_page("pages/forgotpwd.py")

with col2:
    if st.button("Register"):
        st.switch_page("pages/register.py")