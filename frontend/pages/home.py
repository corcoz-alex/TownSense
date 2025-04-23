import streamlit as st
import os
import base64

def show_home():
    # if "token" not in st.session_state or not st.session_state["token"]:
    #     st.error("🔒 Please log in to access this page.")
    #     st.stop()

    # Get path to .webm logo
    try:
        webm_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.webm")
        with open(webm_path, "rb") as f:
            base64_webm = base64.b64encode(f.read()).decode()

        st.markdown(f"""
            <div style="text-align: center;">
                <video width="650" autoplay loop muted playsinline>
                    <source src="data:video/webm;base64,{base64_webm}" type="video/webm">
                    Your browser does not support the video tag.
                </video>
            </div>
        """, unsafe_allow_html=True)

    except FileNotFoundError:
        st.error("🚫 Could not load homepage animation (logo.webm not found)")