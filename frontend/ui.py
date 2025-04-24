import streamlit as st
st.set_page_config(page_title="TownSense", layout="centered", page_icon="frontend/assets/smaller_logo.png")
import os
from streamlit_navigation_bar import st_navbar
import pages as pg

# --- App Config ---

st.markdown("""
<style>
    .stButton>button:hover {
        border-color: transparent !important;
    }
    form.stButton button:hover {
    border-color: transparent !important;
}
</style>
""", unsafe_allow_html=True)


# --- Navbar Config ---
pages = ["Homepage", "Detection", "History", "Contact", "Account"]
logo_path = os.path.join(os.path.dirname(__file__), "assets", "small_name_logo.svg")
styles = {
    "nav": {
        "background-color": "#ffffff",
        "justify-content": "left",
        "font-family": "Verdana, sans-serif"
    },
    "img": {
        "padding-right": "14px",
    },
    "span": {
        "color": "black",  # 🎨 black text
        "padding": "14px",
        "transition": "all 0.5s ease-in-out",
    },
    "active": {
        "background-color": "#f7f7f7",
        "color": "black",
        "padding": "14px",
        "font-weight": "normal",
    },
    "hover": {
        "color": "#775cff",
        "background-color": "#f7f7f7",
        "padding": "14px",
        "transition": "all 0.5s ease-in-out",
    }
}
options = {
    "show_menu": False,
    "show_sidebar": False,
}

# --- Render Navigation Bar ---
page = st_navbar(
    pages=pages,
    logo_path=logo_path,
    styles=styles,
    options=options,
)

# --- Page Routing ---
functions = {
    "Homepage": pg.home,
    "Detection": pg.detection,
    "History": pg.history,
    "Contact": pg.contact,
    "Account": pg.account
}

if page == "Homepage":
    pg.show_home()
elif page == "Detection":
    pg.show_detection()
elif page == "History":
    pg.show_history()
elif page == "Contact":
    pg.show_contact()
elif page == "Account":
    pg.show_account()
else:
    page = "Account"
    pg.show_account()


