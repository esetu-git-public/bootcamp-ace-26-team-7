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

st.set_page_config(page_title="Register", page_icon="📝")

st.title("📝 Register")

name = st.text_input("Full Name")
email = st.text_input("Email")
phone = st.text_input("Phone Number")
password = st.text_input("Password", type="password")
confirm = st.text_input("Confirm Password", type="password")

if st.button("Create Account", use_container_width=True):

    if password != confirm:
        st.error("Passwords do not match")
    else:
        st.success("Registration Successful ✅")
        st.info("This is a demo. User is not saved.")

st.write("---")

if st.button("⬅ Back to Login"):
    st.switch_page("pages/login.py")