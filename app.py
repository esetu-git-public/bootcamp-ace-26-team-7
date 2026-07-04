import streamlit as st
import base64

hide_streamlit_style = """
<style>
[data-testid="stSidebarNav"] {
    display: none;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Surface Crack Detection",
    page_icon="🛣️",
    layout="wide"
)

# -------------------------------------------------
# Load Background Image
# -------------------------------------------------
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

img = get_base64("assets/background.jpeg")

# -------------------------------------------------
# Custom CSS
# -------------------------------------------------
page_bg = f"""
<style>

[data-testid="stHeader"] {{
    display:none;
}}

[data-testid="stToolbar"] {{
    display:none;
}}

[data-testid="stSidebar"] {{
    display:none;
}}

.main {{
    padding:0rem;
}}

.stApp {{
    background-image:
        linear-gradient(rgba(0,0,0,0.45),
        rgba(0,0,0,0.45)),
        url("data:image/jpg;base64,{img}");
    background-size:cover;
    background-position:center;
    background-repeat:no-repeat;
    height:100vh;
}}

.title {{
    text-align:center;
    color:white;
    font-size:60px;
    font-weight:700;
    margin-top:170px;
}}

.description {{
    text-align:center;
    color:white;
    font-size:24px;
    line-height:1.6;
}}

div.stButton > button {{
    display:block;
    margin:auto;
    margin-top:35px;
    width:220px;
    height:60px;
    font-size:24px;
    border-radius:10px;
    border:none;
    background:white;
    color:black;
    font-weight:bold;
}}

div.stButton > button:hover {{
    background:#1565C0;
    color:white;
}}

</style>
"""

st.markdown(page_bg, unsafe_allow_html=True)

# -------------------------------------------------
# Landing Page
# -------------------------------------------------

st.markdown(
    """
    <div class="title">
    Surface Crack Detection System
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="description">
    AI-powered detection and classification of road and bridge surface defects<br>
    using Deep Learning and Computer Vision.
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Login Button
# -------------------------------------------------

left, center, right = st.columns([3, 2, 3])

with center:
    if st.button("Login", use_container_width=True):
        st.switch_page("pages/LOgin.py")