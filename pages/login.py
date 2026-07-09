import streamlit as st
from backend.auth import login_user

st.set_page_config(
    page_title="Surface Detection System - Login",
    page_icon="🛣️",
    initial_sidebar_state="collapsed",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Design tokens
#   Asphalt bg, lane-marking yellow accent, detection-alert red (errors only).
#   Rajdhani for display type, Inter for body/labels, JetBrains Mono for the
#   small system-readout eyebrow text. One accent color, one motion moment
#   (the scanline) — everything else stays quiet.
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap');

    :root{
        --asphalt:#14161A;
        --panel:#1C1F24;
        --panel-border:#2C3036;
        --yellow:#F5C518;
        --yellow-dim:#8a7420;
        --alert:#FF6B4A;
        --text:#ECEAE3;
        --text-dim:#888D96;
    }

    [data-testid="stSidebar"], [data-testid="stHeader"], footer { display:none; }
    [data-testid="stAppViewContainer"], .main { background:var(--asphalt); }
    .block-container { padding-top:0 !important; }

    /* faint lane-marking texture across the page */
    [data-testid="stAppViewContainer"]{
        background-image:
            repeating-linear-gradient(
                115deg,
                transparent 0px, transparent 140px,
                rgba(245,197,24,0.045) 140px, rgba(245,197,24,0.045) 180px
            ),
            linear-gradient(180deg, #14161A 0%, #101216 100%);
    }

    /* ambient scanline sweep -- the one signature motion element */
    .sd-scanline{
        position:fixed; left:0; right:0; top:0; height:2px;
        background:linear-gradient(90deg, transparent, rgba(245,197,24,0.75), transparent);
        box-shadow:0 0 12px 1px rgba(245,197,24,0.35);
        animation:sd-sweep 7s linear infinite;
        z-index:0; pointer-events:none;
    }
    @keyframes sd-sweep{
        0%   { top:-2px; opacity:0; }
        6%   { opacity:1; }
        94%  { opacity:1; }
        100% { top:100vh; opacity:0; }
    }
    @media (prefers-reduced-motion: reduce){ .sd-scanline{ animation:none; display:none; } }

    /* console card -- bracket-cornered, HUD styling */
    [data-testid="stVerticalBlockBorderWrapper"]:has(div.sd-marker){
        background:var(--panel) !important;
        border:1px solid var(--panel-border) !important;
        border-radius:2px !important;
        padding:2.5rem 2.75rem 2rem !important;
        position:relative;
        box-shadow:0 20px 60px rgba(0,0,0,0.45);
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(div.sd-marker)::before,
    [data-testid="stVerticalBlockBorderWrapper"]:has(div.sd-marker)::after{
        content:""; position:absolute; width:22px; height:22px;
        border-color:var(--yellow); border-style:solid; opacity:0.85;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(div.sd-marker)::before{
        top:-1px; left:-1px; border-width:2px 0 0 2px;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(div.sd-marker)::after{
        bottom:-1px; right:-1px; border-width:0 2px 2px 0;
    }

    .sd-eyebrow{
        font-family:'JetBrains Mono',monospace; font-size:0.72rem;
        letter-spacing:0.22em; color:var(--yellow); text-transform:uppercase;
        display:flex; align-items:center; gap:8px; margin-bottom:0.4rem;
    }
    .sd-eyebrow::before{
        content:""; width:6px; height:6px; border-radius:50%;
        background:var(--yellow); box-shadow:0 0 8px 1px var(--yellow);
    }
    .sd-title{
        font-family:'Rajdhani',sans-serif; font-weight:700; font-size:2.1rem;
        letter-spacing:0.01em; color:var(--text); margin:0 0 0.15rem 0; line-height:1.1;
    }
    .sd-sub{
        font-family:'Inter',sans-serif; font-size:0.88rem; color:var(--text-dim);
        margin-bottom:1.9rem;
    }

    /* field labels as mono system-readout text */
    [data-testid="stTextInput"] label p{
        font-family:'JetBrains Mono',monospace !important; font-size:0.7rem !important;
        letter-spacing:0.12em; text-transform:uppercase; color:var(--text-dim) !important;
    }
    [data-testid="stTextInput"] input{
        background:#12141770 !important;
        border:1px solid var(--panel-border) !important;
        border-radius:2px !important;
        color:var(--text) !important;
        font-family:'Inter',sans-serif !important;
        padding:0.65rem 0.8rem !important;
    }
    [data-testid="stTextInput"] input:focus{
        border-color:var(--yellow) !important;
        box-shadow:0 0 0 1px var(--yellow), 0 0 14px rgba(245,197,24,0.25) !important;
    }
    [data-testid="stTextInput"] input::placeholder{ color:#565b63 !important; }

    /* primary login action */
    div[data-testid="stButton"]:has(button:contains("Login")) { display:block; }
    .stButton button{
        font-family:'Rajdhani',sans-serif !important; font-weight:600 !important;
        letter-spacing:0.04em; border-radius:2px !important; height:2.7rem;
        transition:all 0.15s ease;
    }
    /* first button in the form = primary (Login) */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button{
        background:var(--yellow) !important; color:#1a1502 !important;
        border:1px solid var(--yellow) !important; font-size:1.02rem !important;
        text-transform:uppercase;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button:hover{
        background:#ffd23d !important; box-shadow:0 0 18px rgba(245,197,24,0.35);
    }
    /* secondary row buttons (outside the card) = ghost style */
    .sd-secondary-row .stButton button{
        background:transparent !important; color:var(--text-dim) !important;
        border:1px solid var(--panel-border) !important; font-size:0.85rem !important;
        text-transform:none; height:2.3rem;
    }
    .sd-secondary-row .stButton button:hover{
        color:var(--yellow) !important; border-color:var(--yellow-dim) !important;
    }

    .sd-divider{ border-top:1px solid var(--panel-border); margin:1.6rem 0 1.3rem; }

    [data-testid="stAlert"]{ border-radius:2px; font-family:'Inter',sans-serif; }
    </style>

    <div class="sd-scanline"></div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Layout
#   A fixed-max-width console rather than fractional columns -- ratios like
#   [6,6,6] distort at wide viewports, so this caps the card at a readable
#   width and lets the outer columns absorb the remaining space instead.
# ----------------------------------------------------------------------------
left, center, right = st.columns([1, 1.15, 1])

with center:
    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown('<div class="sd-marker"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sd-eyebrow">System access</div>', unsafe_allow_html=True)
        st.markdown('<p class="sd-title">Surface Detection System</p>', unsafe_allow_html=True)
        st.markdown('<p class="sd-sub">Pavement defect analysis console</p>', unsafe_allow_html=True)

        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")

        st.write("")

        if st.button("Login", use_container_width=True):
            if not email or not password:
                st.error("Enter both email and password.")
            else:
                try:
                    result = login_user(email=email, password=password)
                    if result.get("success"):
                        st.session_state["access_token"] = result["access_token"]
                        st.session_state["user"] = result["user"]
                        st.success("Login successful.")
                        st.switch_page("pages/Home.py")
                    else:
                        st.error("Invalid email or password.")
                except Exception as e:
                    st.error(str(e))

        st.markdown('<div class="sd-divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sd-secondary-row">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Forgot password", use_container_width=True):
                st.switch_page("pages/forgotpwd.py")
        with col2:
            if st.button("Register", use_container_width=True):
                st.switch_page("pages/register.py")
        st.markdown('</div>', unsafe_allow_html=True)