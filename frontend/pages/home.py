import streamlit as st
import os
import base64

# if "token" not in st.session_state or not st.session_state["token"]:
#     st.error("🔒 Please log in to access this page.")
#     st.stop()

# Get the path to your .webm file
webm_path = os.path.join(os.path.dirname(__file__), "..", "assets", "output.webm")

with open(webm_path, "rb") as video_file:
    base64_webm = base64.b64encode(video_file.read()).decode()

st.markdown(
    f"""
    <div style="text-align: center;">
        <video width="650" autoplay loop muted playsinline>
            <source src="data:video/webm;base64,{base64_webm}" type="video/webm">
            Your browser does not support the video tag.
        </video>
    </div>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns(2, gap="medium", vertical_alignment="center")
with col2:
    st.title("Homepage", anchor = False)
    st.write("Text aici")
