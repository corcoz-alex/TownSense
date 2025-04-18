import streamlit as st

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: #726D57;
    }
    [data-testid="stAppViewContainer"] {
        background: #FFF6ED;
        background: radial-gradient(circle,rgba(255, 246, 237, 1) 60%, rgba(199, 199, 199, 1) 100%);
        color : black;
    }
    [data-testid="stError"] {
        background-color: #FFD2D2;
        color: #800000; /* Dark red text */
        border: 1px solid #800000;
        border-radius: 5px;
        padding: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

home_page = st.Page(
    page="pages/home.py",  # Updated to module path
    title="Homepage",
    icon="🏙️",
    default=True,
)

detection_page = st.Page(
    page="pages/detection.py",  # Updated to module path
    title="TownSense",
    icon="🔍",
)

history_page = st.Page(
    page="pages/history.py",  # Updated to module path
    title="History",
    icon="📜",
)

contact_page = st.Page(
    page="pages/contact.py",  # Updated to module path
    title="Contact",
    icon="📞",
)

pg = st.navigation(pages=[home_page, detection_page, history_page, contact_page])
pg.run()
