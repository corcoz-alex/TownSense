import streamlit as st
import os
import base64

st.markdown(
    """
    <style>
    .fade-in {
        animation: fadeIn 2s ease-in-out;
    }
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns(2, gap="medium", vertical_alignment="center")
with col1:
    image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo_placeholder.png")

    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()

    st.markdown(f"""
        <div class="fade-in">
            <img src="data:image/png;base64,{encoded_image}" width="300">
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.title("Homepage", anchor = False)
    st.write("Text aici")

