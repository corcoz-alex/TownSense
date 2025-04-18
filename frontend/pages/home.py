import streamlit as st
import os

col1, col2 = st.columns(2, gap = "medium", vertical_alignment="center")
with col1:
    image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo_placeholder.png")
    st.image(image_path, width=300)
with col2:
    st.title("Homepage", anchor = False)
    st.write("Text motivational de pisat aici")