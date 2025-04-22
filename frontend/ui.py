import streamlit as st
from streamlit_navigation_bar import st_navbar
import pages as pg

st.set_page_config(
    page_title="TownSense",
    layout="wide",
    page_icon="assets/smaller_logo.png",
    initial_sidebar_state="collapsed"
)

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
