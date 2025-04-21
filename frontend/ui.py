import streamlit as st
from streamlit import Page
from streamlit_extras.stylable_container import stylable_container


# --- App Config ---
st.set_page_config(page_title="TownSense", layout="centered", page_icon= "assets/smaller_logo.png")

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

if st.session_state.get("token") and st.session_state.get("username"):
    with st.sidebar:
        with stylable_container(
            key="logout_red_button",
            css_styles="""
                button {
                    background-color: #FF4B4B;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                button:hover {
                    background-color: #d13a3a;
                }
            """,
        ):
            st.button("Logout", key="logout_sidebar_button", on_click=lambda: st.session_state.clear())

if st.session_state.get("token") and st.session_state.get("username"):
    username = st.session_state["username"]
    st.sidebar.text(f"{username}")


pg = st.navigation(pages=[
    Page(page="pages/account.py", title="Account", icon="👤", default=True),
    Page(page="pages/home.py", title="Homepage", icon="🏙️"),
    Page(page="pages/detection.py", title="TownSense", icon="🔍"),
    Page(page="pages/history.py", title="History", icon="📜"),
    Page(page="pages/contact.py", title="Contact", icon="📞"),
])
pg.run()

# Hides streamlit toolbar
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
