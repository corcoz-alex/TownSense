import streamlit as st
from streamlit import Page


# --- App Config ---
st.set_page_config(page_title="TownSense")

# --- Global Styles ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: #726D57;
    }
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle, rgba(255, 246, 237, 1) 60%, rgba(199, 199, 199, 1) 100%);
        color: black;
    }
    [data-testid="stError"] {
        background-color: #FFD2D2;
        color: #800000;
        border: 1px solid #800000;
        border-radius: 5px;
        padding: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

pg = st.navigation(pages=[
    Page(page="pages/account.py", title="Account", icon="👤", default=True),
    Page(page="pages/home.py", title="Homepage", icon="🏙️"),
    Page(page="pages/detection.py", title="TownSense", icon="🔍"),
    Page(page="pages/history.py", title="History", icon="📜"),
    Page(page="pages/contact.py", title="Contact", icon="📞"),
])
pg.run()

if st.session_state.get("token") and st.session_state.get("username"):
    username = st.session_state["username"]
    st.markdown(
        f"""
        <style>
        .sidebar-user {{
            position: fixed;
            bottom: 15px;
            left: 16px;
            color: #ddd;
            font-size: 13px;
            font-style: italic;
            z-index: 999;
        }}
        </style>
        <div class="sidebar-user">
            👤 Logged in as <b>{username}</b>
        </div>
        """,
        unsafe_allow_html=True
    )
