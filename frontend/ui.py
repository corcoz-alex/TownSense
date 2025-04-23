import os
import streamlit as st
from streamlit_navigation_bar import st_navbar
import pages as pg  # your pages/__init__.py must import all functions

# --- App Config ---
st.set_page_config(page_title="TownSense", layout="centered", page_icon="assets/smaller_logo.png")

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
pages = ["Homepage", "TownSense", "History", "Contact", "Account"]
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
        "background-color": "white",
        "color": "black",
        "padding": "14px",
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
    "TownSense": pg.detection,
    "History": pg.history,
    "Contact": pg.contact,
    "Account": pg.account
}

if page == "Homepage":
    pg.show_home()
elif page == "TownSense":
    pg.show_detection()
elif page == "History":
    pg.show_history()
elif page == "Contact":
    pg.show_contact()
elif page == "Account":
    pg.show_account()
else:
    pg.show_account()


