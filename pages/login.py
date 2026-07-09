import streamlit as st 
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

left, center, right = st.columns([6,6,6])

with center:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    st.title("🛣️ Surface Detection System")
    st.subheader("Login")


    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        # login logic
        pass

    st.markdown("</div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("Forgot Password"):
        st.switch_page("pages/forgotpwd.py")
with col2:
    if st.button("Register"):
        st.switch_page("pages/register.py")