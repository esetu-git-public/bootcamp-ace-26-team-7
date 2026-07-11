import os
import streamlit as st
from backend.auth import login_user, get_github_login_url, complete_github_login

st.set_page_config(
    page_title="Surface Detection System - Login",
    page_icon="🔐",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stSidebar"] {
    display: none;
}

.login-box {
    background-color: #ffffff;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0px 0px 12px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)

st.title("🛣️ Surface Detection System")
st.subheader("Login")

# This must match your Space's live URL + this page's route.
APP_URL = os.getenv("APP_URL", "https://amruthjakku-surface-crack-detection.hf.space/login")

# ----------------------------
# GitHub OAuth Callback
# ----------------------------
query_params = st.query_params

if "code" in query_params:
    try:
        result = complete_github_login(query_params["code"])

        if result.get("success"):
            st.session_state["access_token"] = result["access_token"]
            st.session_state["user"] = result["user"]

            st.query_params.clear()

            st.success("Login Successful ✅")

            st.switch_page("pages/home.py")

        else:
            st.error("GitHub Login Failed")

    except Exception as e:
        st.error(f"GitHub login failed: {e}")

# ----------------------------
# Email / Password Login
# ----------------------------
email = st.text_input("Email")

password = st.text_input(
    "Password",
    type="password"
)

if st.button("Login", use_container_width=True):

    if not email or not password:
        st.error("Please enter both email and password.")

    else:
        try:

            result = login_user(
                email=email,
                password=password
            )

            if result.get("success"):

                st.session_state["access_token"] = result["access_token"]
                st.session_state["user"] = result["user"]

                st.success("Login Successful ✅")

                st.switch_page("pages/home.py")

            else:
                st.error(result.get("message", "Invalid email or password"))

        except Exception as e:
            st.error(str(e))

st.divider()

# ----------------------------
# GitHub Login
# ----------------------------
if st.button("Login with GitHub", use_container_width=True):

    login_url = get_github_login_url(
        redirect_to=APP_URL
    )

    st.link_button(
        "Continue to GitHub →",
        login_url,
        use_container_width=True
    )

st.divider()

# ----------------------------
# Navigation Buttons
# ----------------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("Forgot Password"):
        st.switch_page("pages/forgotpwd.py")

with col2:
    if st.button("Register"):
        st.switch_page("pages/register.py")