import streamlit as st

st.set_page_config(
    page_title="Surface Crack Detection",
    page_icon="🛣️",
    layout="wide"
)

hide_streamlit_style = """
<style>
[data-testid="stSidebarNav"] { display: none; }
[data-testid="stHeader"] { display: none; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stSidebar"] { display: none; }
.main { padding: 0rem; }

.stApp {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.title {
    text-align:center; color:#ffffff; font-size:60px;
    font-weight:700; margin-top:170px;
    text-shadow: 2px 2px 8px rgba(0,0,0,0.5);
}
.description {
    text-align:center; color:#e0e0e0; font-size:24px; line-height:1.6;
    text-shadow: 1px 1px 4px rgba(0,0,0,0.4);
}
div.stButton > button {
    display:block; margin:auto; margin-top:35px; width:220px; height:60px;
    font-size:24px; border-radius:10px; border:none;
    background:white; color:black; font-weight:bold;
}
div.stButton > button:hover { background:#1565C0; color:white; }
</style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.markdown(
    '<div class="title">Surface Crack Detection System</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="description">AI-powered detection and classification of road and bridge surface defects<br>'
    'using Deep Learning and Computer Vision.</div>',
    unsafe_allow_html=True,
)

left, center, right = st.columns([3, 2, 3])
with center:
    if st.button("Login", use_container_width=True):
        st.switch_page("pages/login.py")