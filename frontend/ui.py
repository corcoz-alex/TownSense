import streamlit as st

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
