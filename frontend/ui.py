import streamlit as st
from streamlit_navigation_bar import st_navbar
import pages as pg
import requests
import time

st.set_page_config(
    page_title="TownSense",
    layout="wide",
    page_icon="assets/smaller_logo.png",
    initial_sidebar_state="collapsed"
)

# Initialize session state for backend connectivity
if "backend_available" not in st.session_state:
    try:
        # Test connection with short timeout
        requests.get("http://localhost:5000/", timeout=0.5)
        st.session_state.backend_available = True
    except requests.exceptions.RequestException:
        st.session_state.backend_available = False

# Display backend status warning if needed
if not st.session_state.get("backend_available", False):
    st.warning("⚠️ Backend server is not available. Some features may not work properly.")
    # Add a button to retry connection
    if st.button("Retry Connection"):
        try:
            requests.get("http://localhost:5000/", timeout=0.5)
            st.session_state.backend_available = True
            st.rerun()
        except:
            pass

page = st_navbar(
    ["Account", "Homepage", "TownSense", "History", "Contact"],)

if page == "Account":
    pg.show_account()
elif page == "Homepage":
    pg.show_home()
elif page == "TownSense":
    pg.show_detection()
elif page == "History":
    pg.show_history()
elif page == "Contact":
    pg.show_contact()
