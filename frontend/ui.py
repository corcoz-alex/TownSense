import streamlit as st

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: #726D57;
    }
    [data-testid="stAppViewContainer"] {
       background: #FFF6ED;
       background: radial-gradient(circle,rgba(255, 246, 237, 1) 67%, rgba(217, 217, 217, 1) 100%);
        color : black;
    }
    [data-testid="stError"] {
        background-color: #FFD2D2; /* Light red background */
        color: #800000; /* Dark red text */
        border: 1px solid #800000; /* Dark red border */
        border-radius: 5px;
        padding: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

home_page = st.Page(
    page="pages/home.py",
    title="Homepage",
    icon="🏙️",
    default=True,
)

detection_page = st.Page(
    page="pages/detection.py",
    title="TownSense",
    icon="🔍",
)

history_page = st.Page(
    page="pages/history.py",
    title="History",
    icon="📜",
)

contact_page = st.Page(
    page="pages/contact.py",
    title="Contact",
    icon="📞",
)

pg = st.navigation(pages=[home_page, detection_page, history_page, contact_page])
pg.run()
